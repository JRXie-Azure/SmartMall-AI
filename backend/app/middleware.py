"""
SmartMall-AI 中间件
- RateLimitMiddleware: 基于 Redis 的 API 限流 (Redis 不可用时降级为内存限流)
- RequestLoggingMiddleware: 请求日志记录
"""
import time
import logging
import json
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.config import get_settings
from app.database import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API 限流中间件

    策略:
    - 基于客户端 IP + 请求路径 进行限流
    - 优先使用 Redis (分布式限流, 多实例共享)
    - Redis 不可用时降级为内存限流 (单实例)

    配置 (在 config.py / .env 中设置):
    - RATE_LIMIT_ENABLED: 是否启用限流 (默认 True)
    - RATE_LIMIT_REQUESTS: 时间窗口内最大请求数 (默认 100)
    - RATE_LIMIT_WINDOW: 时间窗口秒数 (默认 60)
    - RATE_LIMIT_AI_REQUESTS: AI 接口单独限制 (默认 20, 防止 LLM 滥用)
    """

    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.enabled = getattr(settings, "RATE_LIMIT_ENABLED", True)
        self.max_requests = getattr(settings, "RATE_LIMIT_REQUESTS", 100)
        self.window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
        self.ai_max_requests = getattr(settings, "RATE_LIMIT_AI_REQUESTS", 20)
        # 内存限流 fallback: { key: deque([timestamp, ...]) }
        self._memory_store: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if not self.enabled:
            return await call_next(request)

        # 跳过非 API 路径 (静态文件/前端页面)
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        # 跳过健康检查
        if path in ("/api/health",):
            return await call_next(request)

        # 获取客户端 IP
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"ratelimit:{client_ip}:{path}"

        # AI 接口使用更严格的限流
        is_ai_endpoint = path.startswith("/api/ai/")
        limit = self.ai_max_requests if is_ai_endpoint else self.max_requests

        # 尝试 Redis 限流
        redis = get_redis()
        if redis:
            allowed = self._check_redis(redis, rate_key, limit, self.window)
        else:
            allowed = self._check_memory(rate_key, limit, self.window)

        if not allowed:
            logger.warning(f"Rate limit exceeded: {client_ip} -> {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "请求过于频繁，请稍后再试",
                    "retry_after": self.window,
                    "limit": limit,
                    "window": self.window,
                },
                headers={"Retry-After": str(self.window)},
            )

        return await call_next(request)

    def _check_redis(self, redis, key: str, limit: int, window: int) -> bool:
        """Redis 滑动窗口限流"""
        try:
            import time as _time
            now = _time.time()
            pipe = redis.pipeline()
            # 移除过期记录
            pipe.zremrangebyscore(key, 0, now - window)
            # 添加当前请求
            pipe.zadd(key, {str(now): now})
            # 统计当前窗口内请求数
            pipe.zcard(key)
            # 设置 key 过期时间
            pipe.expire(key, window)
            results = pipe.execute()
            count = results[2]
            return count <= limit
        except Exception as e:
            logger.warning(f"Redis rate limit failed, fallback to memory: {e}")
            return self._check_memory(key, limit, window)

    def _check_memory(self, key: str, limit: int, window: int) -> bool:
        """内存滑动窗口限流 (单实例 fallback)"""
        now = time.time()
        store = self._memory_store[key]

        # 移除过期记录
        while store and store[0] < now - window:
            store.popleft()

        # 检查是否超限
        if len(store) >= limit:
            return False

        store.append(now)
        return True


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录每个 API 请求的方法、路径、状态码、耗时
    """

    async def dispatch(self, request, call_next):
        start_time = time.time()

        # 执行请求
        response = await call_next(request)

        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000

        # 只记录 API 请求
        path = request.url.path
        if path.startswith("/api/"):
            logger.info(
                f"{request.method} {path} -> {response.status_code} ({duration_ms:.0f}ms)"
            )

        # 添加响应头
        response.headers["X-Process-Time"] = f"{duration_ms:.0f}ms"

        return response
