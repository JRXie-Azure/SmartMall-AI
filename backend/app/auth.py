"""
SmartMall-AI 认证与授权
- 标准 JWT (python-jose) 替代内存 token
- RBAC 三角色: user / merchant / admin
- 权限装饰器: require_role
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db
from app.models import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成标准 JWT Token
    payload 包含: sub (user_id), role, username, exp
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt_encode(to_encode)


def jwt_encode(payload: dict) -> str:
    """使用 python-jose 编码 JWT"""
    from jose import jwt
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def jwt_decode(token: str) -> dict:
    """解码并验证 JWT"""
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT Token 解析当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = jwt_decode(token)
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选认证: 有 token 返回用户，没有返回 None"""
    if not token:
        return None
    try:
        return get_current_user(token=token, db=db)
    except HTTPException:
        return None


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """要求管理员权限"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def get_current_merchant(user: User = Depends(get_current_user)) -> User:
    """要求商家或管理员权限"""
    if user.role not in ("merchant", "admin"):
        raise HTTPException(status_code=403, detail="需要商家或管理员权限")
    return user


def require_role(*roles: str):
    """
    角色权限装饰器
    用法: @router.get("/xxx", dependencies=[Depends(require_role("admin", "merchant"))])
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"需要以下角色之一: {', '.join(roles)}"
            )
        return user
    return role_checker
