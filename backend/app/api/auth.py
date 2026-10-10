from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, RegisterIn
from ..security import current_user, hash_password, token_for, verify_password
router=APIRouter(prefix="/api/auth", tags=["auth"])
@router.post("/register")
def register(data: RegisterIn, db: Session=Depends(get_db)):
    if db.query(User).filter_by(email=data.email.lower()).first(): raise HTTPException(409,"Email already registered")
    user=User(email=data.email.lower(),password_hash=hash_password(data.password)); db.add(user); db.commit(); db.refresh(user); return {"access_token":token_for(user),"token_type":"bearer","user":{"id":user.id,"email":user.email}}
@router.post("/login")
def login(data: LoginIn, db: Session=Depends(get_db)):
    user=db.query(User).filter_by(email=data.email.lower()).first()
    if not user or not verify_password(data.password,user.password_hash): raise HTTPException(401,"Incorrect email or password")
    return {"access_token":token_for(user),"token_type":"bearer","user":{"id":user.id,"email":user.email}}
@router.get("/me")
def me(user: User=Depends(current_user)): return {"id":user.id,"email":user.email}

