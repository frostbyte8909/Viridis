import asyncio
import logging
import json
import time
import base64
import pickle
from typing import Dict
import numpy as np

from app.core.redis import redis_manager
from app.db.session import AsyncSessionLocal
from app.models.db import WafFeatureWindow
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

ANOMALIES_STREAM = "viridis:waf:anomalies:stream"
BLOCKLIST_KEY = "viridis:waf:blocklist"
WATCHLIST_KEY = "viridis:waf:watchlist"
FEATURES_STREAM = "viridis:waf:features:stream"

# Thresholds
watch_threshold = 0.85
block_threshold = 0.95

async def set_thresholds(watch: float, block: float):
    global watch_threshold, block_threshold
    watch_threshold = watch
    block_threshold = block

async def get_thresholds() -> Dict[str, float]:
    return {
        "watch_threshold": watch_threshold,
        "block_threshold": block_threshold
    }

async def _load_model_from_redis(r):
    model = None
    scaler_min = None
    scaler_max = None
    state = "cold"
    model_version = "cold"
    
    model_base64 = await r.get("viridis:waf:model:artifact")
    if model_base64:
        try:
            # if decode_responses=True, model_base64 is a string
            model_artifact = base64.b64decode(model_base64)
            model = pickle.loads(model_artifact)
        except Exception as e:
            logger.error(f"Failed to load model from Redis: {e}")
            
    model_metadata = await r.get("viridis:waf:model:metadata")
    if model_metadata:
        try:
            metadata = json.loads(model_metadata)
            scaler_min = np.array(metadata["scaler_min"])
            scaler_max = np.array(metadata["scaler_max"])
            state = metadata.get("state", "cold")
            model_version = metadata.get("version", "cold")
        except Exception as e:
            logger.error(f"Failed to load metadata from Redis: {e}")
            
    return model, scaler_min, scaler_max, state, model_version

def _score_proba(model, matrix):
    return -model.decision_function(matrix)

async def run_waf_scorer() -> None:
    """Periodically fetches features from Redis, scores them, and enforces rules."""
    logger.info("Started WAF scorer worker")
    
    while True:
        try:
            r = redis_manager.get_client()
            
            # Fetch model from Redis (shared across workers)
            model, scaler_min, scaler_max, state, model_version = await _load_model_from_redis(r)
            
            # 1. Fetch keys
            all_keys = await r.keys("viridis:waf:features:*")
            if not all_keys:
                await asyncio.sleep(10)
                continue
                
            chunk_size = 500
            for i in range(0, len(all_keys), chunk_size):
                chunk_keys = all_keys[i:i + chunk_size]
                
                # Fetch features for this chunk
                pipe = r.pipeline()
                for key in chunk_keys:
                    pipe.get(key)
                results = await pipe.execute()
                
                features = []
                for res in results:
                    if res:
                        features.append(json.loads(res))
                        
                if not features:
                    continue
                
                # 2. Write to Postgres and Stream
                async with AsyncSessionLocal() as session:
                    db_windows = []
                    pipe = r.pipeline()
                    for feat in features:
                        payload = {str(k): str(v) for k, v in feat.items()}
                        pipe.xadd(FEATURES_STREAM, payload, maxlen=100000)
                        
                        db_windows.append({
                            "client_ip": feat.get("client_ip"),
                            "request_count": feat.get("request_count", 0),
                            "error_density": feat.get("error_density", 0.0),
                            "endpoint_spread": feat.get("endpoint_spread", 0.0),
                            "method_diversity": feat.get("method_diversity", 0.0),
                            "temporal_variance": feat.get("temporal_variance", 0.0),
                            "window_end": datetime.fromtimestamp(feat.get("window_end", time.time()), tz=timezone.utc)
                        })
                        
                    if db_windows:
                        try:
                            insert_stmt = insert(WafFeatureWindow).values(db_windows)
                            await session.execute(insert_stmt)
                            await session.commit()
                        except Exception as e:
                            logger.error(f"Failed to write features to Postgres: {e}")
                            await session.rollback()
                    
                    # Execute stream pushes
                    await pipe.execute()
                    
                # 3. Score
                if model is None or state == "cold":
                    continue
                    
                X = []
                for feat in features:
                    X.append([
                        float(feat.get("error_density", 0)),
                        float(feat.get("endpoint_spread", 0)),
                        float(feat.get("method_diversity", 0)),
                        float(feat.get("temporal_variance", 0)),
                        float(feat.get("request_count", 0)),
                    ])
                    
                X_np = np.array(X)
                
                with np.errstate(divide='ignore', invalid='ignore'):
                    scaled = (X_np - scaler_min) / (scaler_max - scaler_min)
                scaled = np.nan_to_num(scaled, nan=0.0, posinf=0.0, neginf=0.0)
                scaled = np.clip(scaled, 0, 1)
                
                raw_scores = await asyncio.to_thread(_score_proba, model, scaled)
                
                normalized_scores = []
                for score in raw_scores:
                    clamped = np.clip(score + 0.5, 0, 1)
                    normalized_scores.append(float(clamped))
                    
                pipe_ops_count = 0
                pipe = r.pipeline()
                
                for feat, normalized_score in zip(features, normalized_scores):
                    decision = "allow"
                    ip = feat.get("client_ip")
                    
                    if normalized_score >= block_threshold:
                        decision = "block"
                    elif normalized_score >= watch_threshold:
                        decision = "watch"
                        
                    if decision != "allow":
                        metadata = {
                            "ip": ip,
                            "decision": decision,
                            "score": normalized_score,
                            "model_version": model_version,
                            "timestamp": time.time()
                        }
                        payload = {str(k): str(v) for k, v in metadata.items()}
                        pipe.xadd(ANOMALIES_STREAM, payload, maxlen=10000)
                        
                        if state == "active":
                            if decision == "block":
                                pipe.sadd(BLOCKLIST_KEY, ip)
                                pipe.setex(f"viridis:waf:blockmeta:{ip}", 7200, json.dumps(metadata))
                                pipe_ops_count += 2
                            elif decision == "watch":
                                pipe.sadd(WATCHLIST_KEY, ip)
                                pipe.setex(f"viridis:waf:watchmeta:{ip}", 7200, json.dumps(metadata))
                                pipe_ops_count += 2
                        elif state == "watch" and decision == "block":
                            pipe.sadd(WATCHLIST_KEY, ip)
                            pipe.setex(f"viridis:waf:watchmeta:{ip}", 7200, json.dumps(metadata))
                            pipe_ops_count += 2
                            
                    if pipe_ops_count >= 500:
                        await pipe.execute()
                        pipe_ops_count = 0
                
                if pipe_ops_count > 0:
                    await pipe.execute()
                    
            await asyncio.sleep(60) # Run scoring every minute
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception(f"WAF scorer error: {e}")
            await asyncio.sleep(5)
