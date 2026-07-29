"""
认证路由 — 注册/登录/用户信息
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserLogin, Token, UserInfo, UserUpdate
from app.auth import hash_password, verify_password, create_access_token, get_current_user, create_refresh_token
from jose import jwt
from app.config import get_settings
import time

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["认证"])

# 登录限流: 内存存储 (生产应改用 Redis)
_login_attempts: dict[str, list[float]] = {}  # key -> [timestamps]
_MAX_LOGIN_ATTEMPTS = 10  # 每分钟最多 10 次
_LOGIN_WINDOW = 60


def _check_login_rate_limit(key: str) -> bool:
    """检查登录频率，返回 True 表示允许"""
    now = time.time()
    if key not in _login_attempts:
        _login_attempts[key] = []
    # 清理过期记录
    _login_attempts[key] = [t for t in _login_attempts[key] if now - t < _LOGIN_WINDOW]
    if len(_login_attempts[key]) >= _MAX_LOGIN_ATTEMPTS:
        return False
    _login_attempts[key].append(now)
    return True


@router.post("/register", response_model=Token)
def register(data: UserRegister, db: Session = Depends(get_db)):
    # 密码复杂度校验
    if len(data.password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"密码长度至少 {settings.PASSWORD_MIN_LENGTH} 位"
        )
    if not any(c.isupper() for c in data.password):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个大写字母")
    if not any(c.isdigit() for c in data.password):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个数字")

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
    refresh = create_refresh_token(data={
        "sub": str(user.id),
        "role": user.role,
    })
    return Token(
        access_token=token,
        refresh_token=refresh,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    )


@router.post("/login", response_model=Token)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    # 登录限流
    client_ip = request.client.host if request.client else "unknown"
    if not _check_login_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="登录请求过于频繁，请稍后再试")
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
    refresh = create_refresh_token(data={
        "sub": str(user.id),
        "role": user.role,
    })
    return Token(
        access_token=token,
        refresh_token=refresh,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    )




@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(request: Request, db: Session = Depends(get_db)):
    """使用刷新 Token 获取新的访问 Token"""
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token", "")
    except Exception:
        raise HTTPException(status_code=400, detail="请求格式错误")

    if not refresh_token:
        raise HTTPException(status_code=400, detail="缺少 refresh_token")

    from app.auth import decode_access_token
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="无效的刷新 Token")
    except Exception:
        raise HTTPException(status_code=401, detail="刷新 Token 无效或已过期")

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    new_token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
    })
    new_refresh = create_refresh_token(data={
        "sub": str(user.id),
        "role": user.role,
    })
    return Token(
        access_token=new_token,
        refresh_token=new_refresh,
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
    if data.password is not None:
        if len(data.password) < settings.PASSWORD_MIN_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"密码长度至少 {settings.PASSWORD_MIN_LENGTH} 位"
            )
        user.hashed_password = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return user
