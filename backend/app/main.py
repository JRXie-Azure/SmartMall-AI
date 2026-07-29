"""
SmartMall AI — FastAPI 入口
挂载核心路由: auth / products / cart / orders / ai / search
"""
import os
import logging
import logging.handlers
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import engine, Base
from app.config import get_settings
from app.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.routers import auth, products, cart, orders, ai, search, admin

settings = get_settings()

Base.metadata.create_all(bind=engine)

log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "smartmall.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.TimedRotatingFileHandler(
            log_file, when="midnight", backupCount=7, encoding="utf-8"
        ),
    ],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("uvicorn")
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    yield
    logger.info(f"👋 {settings.APP_NAME} 正在关闭...")

app = FastAPI(
    lifespan=lifespan,
    title=f"{settings.APP_NAME} - 智能电商平台",
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(ai.router)
app.include_router(search.router)
app.include_router(admin.router)  # 管理后台路由

static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

@app.get("/")
async def root():
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}



