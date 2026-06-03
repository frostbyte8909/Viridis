import asyncio
import logging
from datetime import datetime
import numpy as np
from sklearn.ensemble import IsolationForest

from sklearn.preprocessing import MinMaxScaler
import json
import pickle
import base64

from app.core.redis import redis_manager
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.db import WafFeatureWindow
from datetime import timezone, timedelta

logger = logging.getLogger(__name__)

FEATURES_STREAM = "viridis:waf:features:stream"
MODEL_KEY = "viridis:waf:model:current"

# Keep the model in memory
current_model: IsolationForest = None
model_metadata = {
    "version": "cold",
    "state": "cold",
    "train_time": None,
    "sample_count": 0,
    "mean_anomaly_score": 0.0
}

async def train_model_task() -> None:
    """Periodically trains the Isolation Forest model."""
    while True:
        try:
            await train_model()
            # Retrain every hour
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error training model: {e}")
            await asyncio.sleep(60)

def _train_and_score(X_train: list) -> tuple:
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_features = scaler.fit_transform(X_train)
    
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(scaled_features)
    
    scores = model.decision_function(scaled_features)
    mean_score = float(np.mean(scores))
    
    return model, scaler, mean_score

async def train_model() -> None:
    global current_model, model_metadata
    r = redis_manager.get_client()
    blocked_ips = set(await r.smembers("viridis:waf:blocklist"))
    blocked_ips_str = {ip.decode('utf-8', errors='ignore') if isinstance(ip, bytes) else ip for ip in blocked_ips}
    
    X_train = []
    
    async with AsyncSessionLocal() as session:
        query = select(WafFeatureWindow).where(
            WafFeatureWindow.window_end >= datetime.now(timezone.utc) - timedelta(hours=24)
        ).order_by(WafFeatureWindow.window_end.desc())
        
        async with session.stream(query) as result:
            while True:
                rows = await result.fetchmany(1000)
                if not rows:
                    break
                
                for row in rows:
                    w = row[0]
                    client_ip = w.client_ip
                    error_density = float(w.error_density)
                    endpoint_spread = float(w.endpoint_spread)
                    method_diversity = float(w.method_diversity)
                    temporal_variance = float(w.temporal_variance)
                    request_count = float(w.request_count)
                    
                    # Security: Exclude blocked IPs
                    if client_ip in blocked_ips_str:
                        continue
                        
                    # Security: Exclude high-error windows
                    if error_density > 0.9:
                        continue
                        
                    X_train.append([
                        error_density,
                        endpoint_spread,
                        method_diversity,
                        temporal_variance,
                        request_count,
                    ])
            
    sample_count = len(X_train)
    if sample_count < 500:
        logger.info(f"Skipping model training: insufficient samples ({sample_count} < 500)")
        return
        
    # Offload CPU-bound ML training to a thread
    model, scaler, mean_score = await asyncio.to_thread(_train_and_score, X_train)
    
    version = f"iforest-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')}"
    
    # Check drift
    if model_metadata.get("mean_anomaly_score") and model_metadata["mean_anomaly_score"] != 0:
        drift = abs(mean_score - model_metadata["mean_anomaly_score"]) / abs(model_metadata["mean_anomaly_score"])
        if drift > 0.2:
            logger.warning(f"Model drift detected: mean score shifted by {drift*100:.1f}%")
    
    current_model = model
    
    # Determine state
    state = "shadow"
    # If it's been 1 hour (from some arbitrary start time) and >1000 requests processed, it goes to active
    # We will let the admin API flip it to 'active' or 'watch'
    if model_metadata["state"] in ["watch", "active"]:
        state = model_metadata["state"]
        
    model_metadata = {
        "version": version,
        "state": state,
        "train_time": datetime.now(timezone.utc).isoformat(),
        "sample_count": sample_count,
        "mean_anomaly_score": mean_score,
        "scaler_min": scaler.data_min_.tolist(),
        "scaler_max": scaler.data_max_.tolist(),
    }
    
    await r.hset(MODEL_KEY, mapping={
        "version": version,
        "state": state,
        "train_time": model_metadata["train_time"],
        "sample_count": sample_count,
        "mean_anomaly_score": mean_score
    })
    
    await r.set("viridis:waf:model:metadata", json.dumps(model_metadata))
    model_artifact = pickle.dumps(model)
    model_base64 = base64.b64encode(model_artifact).decode('utf-8')
    await r.set("viridis:waf:model:artifact", model_base64)
    
    logger.info(f"Model trained successfully. Version: {version}, Samples: {sample_count}")
