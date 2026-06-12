import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging
from app.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

class JWTClaims(BaseModel):
    tenant_id: str
    api_key_id: str
    exp: int
    iat: int

# Initialize PyJWKClient if jwks_url is provided
jwks_client = None
if settings.jwks_url:
    jwks_client = PyJWKClient(settings.jwks_url, cache_keys=True)

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)) -> JWTClaims:
    token = credentials.credentials
    try:
        if jwks_client:
            # Production: Fetch key from JWKS
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
            # Ensure RS256
            algorithms = ["RS256"]
        elif settings.jwt_static_pem:
            # Local Dev fallback
            key = settings.jwt_static_pem
            algorithms = ["RS256"]
        else:
            logger.error("No JWT configuration available (neither jwks_url nor jwt_static_pem).")
            raise HTTPException(status_code=500, detail="Authentication misconfigured")

        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            options={"verify_exp": True, "verify_iat": True}
        )
        
        # Check required claims
        tenant_id = payload.get("tenant_id")
        api_key_id = payload.get("api_key_id")
        
        if not tenant_id or not api_key_id:
            logger.warning("JWT missing required claims: tenant_id or api_key_id")
            raise HTTPException(status_code=401, detail="Invalid token claims")
            
        return JWTClaims(
            tenant_id=tenant_id,
            api_key_id=api_key_id,
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0)
        )
        
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT signature")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        logger.error(f"JWT verification failure: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
