"""
SmartMall-AI 全局配置
支持 MySQL + Redis + DeepSeek LLM + ChromaDB 向量数据库 + Meilisearch 搜索引擎
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ====== 数据库 ======
    # 默认 SQLite 方便本地开发；生产环境用 MySQL:
    # mysql+pymysql://user:password@localhost:3306/smartmall
    DATABASE_URL: str = "sqlite:///./smartmall.db"

    # ====== Redis ======
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_EXPIRE_SECONDS: int = 300  # 5 分钟缓存

    # ====== JWT 认证 ======
    SECRET_KEY: str = "smartmall-ai-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 小时

    # ====== DeepSeek LLM (OpenAI 兼容接口) ======
    # DeepSeek API: https://platform.deepseek.com/
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 向后兼容: 也支持 OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ====== ChromaDB 向量数据库 (RAG) ======
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # sentence-transformers 模型

    # ====== Meilisearch 搜索引擎 (可选) ======
    MEILISEARCH_URL: str = ""  # 留空则使用数据库内置搜索
    MEILISEARCH_KEY: str = ""

    # ====== CORS ======
    CORS_ORIGINS: str = "*"

    # ====== 文件上传 ======
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # ====== 应用 ======
    APP_NAME: str = "SmartMall AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def llm_api_key(self) -> str:
        """优先使用 DeepSeek，其次 OpenAI"""
        return self.DEEPSEEK_API_KEY or self.OPENAI_API_KEY

    @property
    def llm_base_url(self) -> str:
        return self.DEEPSEEK_BASE_URL if self.DEEPSEEK_API_KEY else self.OPENAI_BASE_URL

    @property
    def llm_model(self) -> str:
        return self.DEEPSEEK_MODEL if self.DEEPSEEK_API_KEY else self.OPENAI_MODEL

    @property
    def is_mysql(self) -> bool:
        return "mysql" in self.DATABASE_URL

    @property
    def has_redis(self) -> bool:
        return bool(self.REDIS_URL)

    @property
    def has_meilisearch(self) -> bool:
        return bool(self.MEILISEARCH_URL)


@lru_cache()
def get_settings():
    return Settings()
