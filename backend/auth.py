import os
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET is not configured")
        
    try:
        header = jwt.get_unverified_header(token)
        print(f"Token Header: {header}")
        
        payload = jwt.decode(
            token, 
            SUPABASE_JWT_SECRET, 
            algorithms=["HS256", "HS384", "HS512", "RS256"], 
            audience="authenticated"
        )
        user_id = payload.get("sub")
        if user_id is None:
            print("JWT Validation Failed: No 'sub' in payload")
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError as e:
        print(f"JWT Validation Failed: Token expired - {str(e)}")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        print(f"JWT Validation Failed: Invalid token - {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except Exception as e:
        print(f"JWT Validation Failed: Unknown error - {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")
