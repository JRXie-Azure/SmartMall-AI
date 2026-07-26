"""
SmartMall-AI Pydantic 模型
请求/响应 Schema 定义
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime


# ====== 用户 ======

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None


class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    role: str
    avatar: str = ""
    phone: str = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    avatar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


# ====== 地址 ======

class AddressCreate(BaseModel):
    name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    is_default: bool = False


class AddressOut(AddressCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ====== 分类 ======

class CategoryCreate(BaseModel):
    name: str
    icon: str = ""
    sort_order: int = 0


class CategoryOut(CategoryCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ====== 商品 ======

class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float = Field(..., gt=0)
    original_price: Optional[float] = None
    image: str = ""
    images: List[str] = []
    brand: str = ""
    stock: int = 0
    category_id: Optional[int] = None
    tags: List[str] = []
    is_recommend: bool = False
    is_new: bool = False
    is_sale: bool = False


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    image: Optional[str] = None
    images: Optional[List[str]] = None
    brand: Optional[str] = None
    stock: Optional[int] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_recommend: Optional[bool] = None
    is_new: Optional[bool] = None
    is_sale: Optional[bool] = None
    is_active: Optional[bool] = None
    audit_status: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    name: str
    description: str = ""
    price: float
    original_price: Optional[float] = None
    image: str = ""
    images: List[str] = []
    stock: int = 0
    sales: int = 0
    category_id: Optional[int] = None
    tags: List[str] = []
    brand: str = ""
    rating: float = 5.0
    is_recommend: bool = False
    is_new: bool = False
    is_sale: bool = False
    is_active: bool = True
    audit_status: str = "approved"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int


# ====== 购物车 ======

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: Optional[ProductOut] = None

    class Config:
        from_attributes = True


# ====== 订单 ======

class OrderCreate(BaseModel):
    address_id: Optional[int] = None
    note: str = ""


class OrderStatusUpdate(BaseModel):
    status: str  # paid / shipped / completed / cancelled
    tracking_no: Optional[str] = None
    logistics_company: Optional[str] = None


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_image: str = ""
    price: float
    quantity: int

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    order_no: str
    status: str
    total_amount: float
    address_snapshot: dict = {}
    note: str = ""
    tracking_no: str = ""
    logistics_company: str = ""
    items: List[OrderItemOut] = []
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ====== 评价 ======

class ReviewCreate(BaseModel):
    product_id: int
    order_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5)
    content: str = ""
    images: List[str] = []
    is_anonymous: bool = False


class ReviewOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    content: str = ""
    images: List[str] = []
    is_anonymous: bool = False
    created_at: Optional[datetime] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


# ====== AI 对话 ======

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[List[dict]] = None  # 多轮对话历史


class ChatResponse(BaseModel):
    reply: str
    products: List[ProductOut] = []
    session_id: Optional[str] = None
    tool_used: Optional[str] = None


# ====== 搜索 ======

class SearchParams(BaseModel):
    keyword: str
    category_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    brand: Optional[str] = None
    sort: str = "relevance"  # relevance / price_asc / price_desc / sales / rating
    page: int = 1
    page_size: int = 20


# ====== 收藏 ======

class FavoriteOut(BaseModel):
    id: int
    product_id: int
    product: Optional[ProductOut] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ====== 管理后台 ======

class ProductAudit(BaseModel):
    audit_status: str  # approved / rejected
    reason: Optional[str] = None


class AdminStatsOut(BaseModel):
    total_products: int
    total_orders: int
    total_sales: float
    total_users: int
    # 时间序列数据
    sales_trend: List[dict] = []  # [{"date": "2026-07-01", "sales": 1234}, ...]
    order_status_dist: List[dict] = []  # [{"status": "pending", "count": 10}, ...]
    category_dist: List[dict] = []  # [{"category": "运动鞋", "count": 5}, ...]
    user_growth: List[dict] = []  # [{"date": "2026-07-01", "count": 100}, ...]
    top_products: List[dict] = []  # [{"name": "xxx", "sales": 100}, ...]
