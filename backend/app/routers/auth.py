"""
认证路由 — 注册/登录/用户信息
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserLogin, Token, UserInfo, UserUpdate
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=Token)
def register(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.email == data.email) | (User.username == data.username)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
    })
    return Token(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    )


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
    })
    return Token(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    )


@router.get("/me", response_model=UserInfo)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserInfo)
def update_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新个人资料"""
    if data.avatar is not None:
        user.avatar = data.avatar
    if data.phone is not None:
        user.phone = data.phone
    if data.email is not None:
        existing = db.query(User).filter(User.email == data.email, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        user.email = data.email
    db.commit()
    db.refresh(user)
    return user
