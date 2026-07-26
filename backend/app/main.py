"""
SmartMall AI — FastAPI 入口
挂载所有路由: auth / products / cart / orders / ai / admin / search / websocket
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import engine, Base
from app.config import get_settings
from app.routers import auth, products, cart, orders, ai, admin, search, websocket

settings = get_settings()

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=f"{settings.APP_NAME} - 智能电商平台",
    description="""
    AI 赋能的全栈电商平台 API

    ## 核心功能
    - **AI 智能对话**: 接入 DeepSeek LLM，支持 Function Calling、SSE 流式响应
    - **RAG 语义搜索**: sentence-transformers + ChromaDB 向量检索
    - **协同过滤推荐**: 基于用户行为的个性化推荐
    - **WebSocket 实时客服**: AI 先接 + 转人工
    - **完整电商闭环**: 商品/购物车/订单/评价/收藏
    - **管理后台**: 数据看板 + 商品/用户/订单管理
    """,
    version=settings.APP_VERSION,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== 路由挂载 ======
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(search.router)
app.include_router(websocket.router)

# ====== 静态文件 ======
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# 上传文件目录
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")


@app.get("/")
async def root():
    """根路径 — 返回前端页面"""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "llm_enabled": bool(settings.llm_api_key),
    }


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    from app.database import get_redis
    import logging
    logger = logging.getLogger("uvicorn")
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    logger.info(f"📊 数据库: {'MySQL' if settings.is_mysql else 'SQLite'}")
    logger.info(f"🔍 LLM: {settings.llm_model if settings.llm_api_key else '未配置'}")
    r = get_redis()
    logger.info(f"💾 Redis: {'已连接' if r else '未启用 (内存缓存降级)'}")
