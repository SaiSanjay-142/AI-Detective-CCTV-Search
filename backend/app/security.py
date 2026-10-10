from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import User
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto"); bearer = HTTPBearer(auto_error=False)
def hash_password(value: str) -> str: return pwd.hash(value)
def verify_password(value: str, digest: str) -> bool: return pwd.verify(value, digest)
def token_for(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=get_settings().jwt_expire_minutes)
    return jwt.encode({"sub": str(user.id), "exp": expires}, get_settings().jwt_secret, algorithm="HS256")
def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    # Local single-user mode: the investigation UI is usable immediately after startup.
    # Auth endpoints remain available if this is later deployed as a multi-user service.
    if credentials is None:
        user = db.query(User).filter_by(email="local@ai-detective.local").first()
        if user is None:
            user = User(email="local@ai-detective.local", password_hash="local-auth-disabled")
            db.add(user); db.commit(); db.refresh(user)
        return user
    try: user_id = int(jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"])["sub"])
    except Exception: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    user = db.get(User, user_id)
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user
