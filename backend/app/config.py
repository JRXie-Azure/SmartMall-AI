"""
SmartMall-AI 全局配置
支持 MySQL + Redis + DeepSeek LLM + TF-IDF 语义搜索 + Alembic 数据库迁移 + 微信/支付宝支付
"""
import os
import secrets
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
    # 生产环境务必在 .env 中设置随机 SECRET_KEY (openssl rand -hex 32)
    PASSWORD_MIN_LENGTH: int = 8  # 密码最小长度
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 刷新 Token 有效期
    # 生产环境务必在 .env 中设置随机 SECRET_KEY (openssl rand -hex 32)
    # 优先从环境变量读取，生产环境务必在 .env 中设置固定值
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-not-for-production-32bytes")
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

    # ====== CORS ======
    CORS_ORIGINS: str = "*"

    # ====== API 限流 ======
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100       # 普通 API: 100 次/分钟
    RATE_LIMIT_WINDOW: int = 60          # 时间窗口 (秒)
    RATE_LIMIT_AI_REQUESTS: int = 20     # AI 接口: 20 次/分钟 (防止 LLM 滥用)

    # ====== 文件上传 ======
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # ====== 对象存储 (S3兼容: 阿里云OSS/腾讯云COS/MinIO/AWS S3) ======
    # local = 本地存储 (开发); s3 = 对象存储 (生产)
    STORAGE_TYPE: str = "local"  # local | s3
    S3_ENDPOINT: str = ""        # 如: https://oss-cn-shenzhen.aliyuncs.com
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "cn-shenzhen"
    S3_PUBLIC_URL: str = ""      # CDN 加速域名，空则使用 S3_ENDPOINT

    # ====== 支付 (微信支付V3 / 支付宝) ======
    # 任一渠道配置完整即视为启用支付 (见 payment_enabled 属性)
    # --- 微信支付 V3 ---
    WXPAY_APPID: str = ""                    # 公众号/小程序 AppID
    WXPAY_MCHID: str = ""                    # 商户号
    WXPAY_API_V3_KEY: str = ""               # APIv3 密钥
    WXPAY_CERT_SERIAL_NO: str = ""           # 商户证书序列号
    WXPAY_PRIVATE_KEY_PATH: str = ""         # 商户私钥文件路径 (apiclient_key.pem)
    WXPAY_NOTIFY_URL: str = ""               # 支付回调地址
    # --- 支付宝 ---
    ALIPAY_APP_ID: str = ""                  # 应用 APPID
    ALIPAY_PRIVATE_KEY_PATH: str = ""        # 应用私钥文件路径
    ALIPAY_PUBLIC_KEY_PATH: str = ""         # 支付宝公钥文件路径
    ALIPAY_NOTIFY_URL: str = ""              # 异步回调地址
    ALIPAY_RETURN_URL: str = ""              # 同步跳转地址
    ALIPAY_GATEWAY: str = "https://openapi.alipay.com/gateway.do"
    ALIPAY_SANDBOX: bool = True              # True=沙箱, False=正式环境

    @property
    def storage_is_s3(self) -> bool:
        return self.STORAGE_TYPE == "s3" and bool(self.S3_ENDPOINT and self.S3_ACCESS_KEY and self.S3_BUCKET)

    # ====== 应用 ======
    APP_NAME: str = "SmartMall AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    model_config = {"extra": "ignore", "env_file": ".env", "env_file_encoding": "utf-8"}

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
    def llm_enabled(self) -> bool:
        """LLM 是否已配置可用 (配置了 DeepSeek 或 OpenAI 的 API Key)"""
        return bool(self.llm_api_key)

    @property
    def is_mysql(self) -> bool:
        return "mysql" in self.DATABASE_URL

    @property
    def has_redis(self) -> bool:
        return bool(self.REDIS_URL)

    @property
    def payment_enabled(self) -> bool:
        """支付是否启用 (配置了微信支付商户号或支付宝应用ID)"""
        return bool(self.WXPAY_MCHID or self.ALIPAY_APP_ID)

    @property
    def wxpay_enabled(self) -> bool:
        """微信支付 V3 是否配置完整"""
        return bool(self.WXPAY_APPID and self.WXPAY_MCHID and self.WXPAY_API_V3_KEY and self.WXPAY_CERT_SERIAL_NO)

    @property
    def alipay_enabled(self) -> bool:
        """支付宝是否配置完整"""
        return bool(self.ALIPAY_APP_ID and self.ALIPAY_PRIVATE_KEY_PATH)


@lru_cache()
def get_settings():
    return Settings()
