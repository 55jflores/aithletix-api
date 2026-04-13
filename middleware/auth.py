import os                                                                                                                                                                                                                                                                    
import json                                                                                                                                                                                                                                                                  
from fastapi import HTTPException, Security                                                                                                                                                                                                                                  
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
                                                                                                                                                                                                                                                                            
security = HTTPBearer()
                                                                                                                                                                                                                                                                            
def _load_public_key():
    raw = os.environ.get("SUPABASE_JWT_PUBLIC_KEY")
    if not raw:
        return None
    try:
        return json.loads(raw)   # JWK JSON → dict
    except json.JSONDecodeError:                                                                                                                                                                                                                                             
        return raw               # fallback: treat as plain PEM string
                                                                                                                                                                                                                                                                            
_PUBLIC_KEY = _load_public_key()
                                                                                                                                                                                                                                                                            
                
def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not _PUBLIC_KEY:                                                                                                                                                                                                                                                      
        raise HTTPException(status_code=500, detail="Server misconfiguration: missing public key")
                                                                                                                                                                                                                                                                            
    try:        
        payload = jwt.decode(
            token,
            _PUBLIC_KEY,
            algorithms=["ES256"],
            options={"verify_aud": False}
        )                                                                                                                                                                                                                                                                    
        return payload
    except JWTError:                                                                                                                                                                                                                                                         
        raise HTTPException(status_code=401, detail="Invalid or expired token")


