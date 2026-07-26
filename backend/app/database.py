"""
SmartMall-AI 数据库配置
支持 MySQL (生产) + SQLite (开发 fallback) + Redis 缓存
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import get_settings
import logging
import json
from typing import Optional, Any
from functools import wraps

settings = get_settings()
logger = logging.getLogger(__name__)

# ====== SQLAlchemy 引擎 ======
if settings.is_mysql:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )
else:
    # SQLite 开发模式
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====== Redis 缓存 (可选，没有 Redis 时自动降级) ======

_redis_client = None
_memory_cache: dict[str, tuple[Any, float]] = {}  # fallback: (value, expire_timestamp)


def get_redis():
    """获取 Redis 客户端，不可用时返回 None"""
    global _redis_client
    if not settings.has_redis:
        return None
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            _redis_client.ping()
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败，降级为内存缓存: {e}")
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """从缓存获取数据"""
    # 优先 Redis
    r = get_redis()
    if r:
        try:
            data = r.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None
    # 降级: 内存缓存
    if key in _memory_cache:
        import time
        value, expire_at = _memory_cache[key]
        if time.time() < expire_at:
            return value
        else:
            del _memory_cache[key]
    return None


def cache_set(key: str, value: Any, expire: int = None):
    """写入缓存"""
    if expire is None:
        expire = settings.CACHE_EXPIRE_SECONDS
    # 优先 Redis
    r = get_redis()
    if r:
        try:
            r.setex(key, expire, json.dumps(value, default=str))
            return
        except Exception:
            pass
    # 降级: 内存缓存
    import time
    _memory_cache[key] = (value, time.time() + expire)


def cache_delete(key: str):
    """删除缓存"""
    r = get_redis()
    if r:
        try:
            r.delete(key)
            return
        except Exception:
            pass
    _memory_cache.pop(key, None)


def cache_delete_pattern(pattern: str):
    """批量删除匹配的缓存"""
    r = get_redis()
    if r:
        try:
            keys = r.keys(pattern)
            if keys:
                r.delete(*keys)
        except Exception:
            pass


def cached(key_prefix: str, expire: int = 300):
    """
    缓存装饰器: 自动缓存函数返回值
    用法: @cached("products:list", expire=60)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            cache_key = f"{key_prefix}:{hash(str(args) + str(sorted(kwargs.items())))}"
            result = cache_get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            if result is not None:
                cache_set(cache_key, result, expire)
            return result
        return wrapper
    return decorator
