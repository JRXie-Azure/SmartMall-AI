"""
SmartMall-AI 数据模型
包含: 用户/地址/分类/商品/购物车/订单/评价 + 浏览记录/收藏/客服会话/搜索历史
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    user = "user"
    merchant = "merchant"
    admin = "admin"


class OrderStatus(str, enum.Enum):
    pending = "pending"      # 待付款
    paid = "paid"            # 已付款
    shipped = "shipped"      # 已发货
    completed = "completed"  # 已完成
    cancelled = "cancelled"  # 已取消
    refunded = "refunded"    # 已退款


class ChatSessionStatus(str, enum.Enum):
    active = "active"
    closed = "closed"
    transferred = "transferred"  # 已转人工


class SenderType(str, enum.Enum):
    user = "user"
    ai = "ai"
    agent = "agent"  # 人工客服


# ==================== 用户系统 ====================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    avatar = Column(String(500), default="")
    phone = Column(String(20), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    orders = relationship("Order", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    product_views = relationship("ProductView", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    province = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    district = Column(String(50), nullable=False)
    detail = Column(String(500), nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="addresses")


# ==================== 商品系统 ====================

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(200), default="")
    sort_order = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False, index=True)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    image = Column(String(500), default="")
    images = Column(JSON, default=list)
    stock = Column(Integer, default=0)
    sales = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    tags = Column(JSON, default=list)
    brand = Column(String(100), default="")
    rating = Column(Float, default=5.0)
    is_recommend = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)
    is_sale = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    # 商品审核状态: pending / approved / rejected
    audit_status = Column(String(20), default="approved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="product")
    views = relationship("ProductView", back_populates="product", cascade="all, delete-orphan")
    skus = relationship("ProductSKU", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")

    __table_args__ = (
        Index("idx_cart_user", "user_id"),
    )


# ==================== 订单系统 ====================

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_no = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    total_amount = Column(Float, nullable=False)
    address_snapshot = Column(JSON, nullable=False)
    note = Column(Text, default="")
    # 支付信息
    payment_method = Column(String(50), default="")
    paid_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # 物流信息
    tracking_no = Column(String(100), default="")
    logistics_company = Column(String(100), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_order_user_status", "user_id", "status"),
        Index("idx_order_created", "created_at"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(300), nullable=False)
    product_image = Column(String(500), default="")
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    __table_args__ = (
        Index("idx_order_item_order", "order_id"),
    )


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    rating = Column(Integer, nullable=False)
    content = Column(Text, default="")
    images = Column(JSON, default=list)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")

    __table_args__ = (
        Index("idx_review_product", "product_id"),
    )


# ==================== 新增: 浏览记录 (用于推荐) ====================

class ProductView(Base):
    """用户浏览商品记录，用于协同过滤推荐"""
    __tablename__ = "product_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    view_count = Column(Integer, default=1)
    duration = Column(Integer, default=0)  # 停留秒数
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="product_views")
    product = relationship("Product", back_populates="views")

    __table_args__ = (
        Index("idx_view_user", "user_id"),
        Index("idx_view_product", "product_id"),
        Index("idx_view_user_product", "user_id", "product_id", unique=True),
    )


# ==================== 新增: 收藏 ====================

class Favorite(Base):
    """用户收藏的商品"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="favorites")
    product = relationship("Product", back_populates="favorites")

    __table_args__ = (
        Index("idx_fav_user_product", "user_id", "product_id", unique=True),
    )


# ==================== 新增: 客服会话系统 ====================

class ChatSession(Base):
    """AI/人工客服会话"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 可能为匿名用户
    user_name = Column(String(100), default="访客")
    status = Column(String(20), default="active")  # active / closed / transferred
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 分配的人工客服
    summary = Column(Text, default="")  # AI 生成的会话摘要
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """客服会话消息"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    sender_type = Column(String(20), nullable=False)  # user / ai / agent
    content = Column(Text, nullable=False)
    extra_data = Column("metadata", JSON, default=dict)  # 附加信息: 推荐商品ID列表、工具调用结果等
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("idx_chatmsg_session", "session_id"),
    )


# ==================== 新增: 搜索历史 ====================

class SearchHistory(Base):
    """用户搜索历史，用于搜索优化和个性化"""
    __tablename__ = "search_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    keyword = Column(String(500), nullable=False)
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_search_user", "user_id"),
        Index("idx_search_keyword", "keyword"),
    )


# ==================== 商品 SKU 系统 ====================

class ProductSKU(Base):
    """商品规格 SKU (颜色/尺寸等变体)"""
    __tablename__ = "product_skus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sku_code = Column(String(100), nullable=False, index=True)  # 如: RED-42
    # 规格属性 JSON: {"颜色": "红色", "尺寸": "42码"}
    attributes = Column(JSON, default=dict)
    price = Column(Float, nullable=True)  # 覆盖商品基础价，None 则使用商品价
    stock = Column(Integer, default=0)
    image = Column(String(500), default="")  # SKU 专属图片
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="skus")

    __table_args__ = (
        Index("idx_sku_product", "product_id"),
    )


class ProductVariant(Base):
    """商品规格模板 (如: 颜色、尺寸)"""
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(50), nullable=False)  # 如: "颜色"
    options = Column(JSON, default=list)  # ["红色", "蓝色", "黑色"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="variants")


# ==================== 优惠券系统 ====================

class Coupon(Base):
    """优惠券/折扣券"""
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 优惠码
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    # 优惠类型: fixed = 固定金额, percent = 百分比
    discount_type = Column(String(20), default="fixed")
    discount_value = Column(Float, nullable=False)  # 减多少元 / 百分比
    min_order_amount = Column(Float, default=0)  # 最低消费
    max_discount = Column(Float, nullable=True)  # 最大减免 (百分比时限制)
    # 有效期
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    # 使用限制
    total_limit = Column(Integer, default=0)  # 0 = 不限量
    used_count = Column(Integer, default=0)
    per_user_limit = Column(Integer, default=1)  # 每个用户限用次数
    # 适用商品
    applicable_products = Column(JSON, default=list)  # [product_id, ...] 空=全店通用
    applicable_categories = Column(JSON, default=list)  # [category_id, ...]
    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserCoupon(Base):
    """用户领取的优惠券"""
    __tablename__ = "user_coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    used_count = Column(Integer, default=0)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    coupon = relationship("Coupon")

    __table_args__ = (
        Index("idx_user_coupon", "user_id", "coupon_id"),
    )

# ==================== 营销活动 ====================

class MarketingCampaign(Base):
    """营销活动 (限时折扣/满减/秒杀)"""
    __tablename__ = "marketing_campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    campaign_type = Column(String(30), default="discount")  # discount / flash_sale / full_reduction
    description = Column(Text, default="")
    banner_image = Column(String(500), default="")
    # 优惠规则
    discount_value = Column(Float, default=0)  # 折扣金额或折扣率
    min_order_amount = Column(Float, default=0)  # 满减门槛
    # 时间范围
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    # 适用范围
    applicable_products = Column(JSON, default=list)
    applicable_categories = Column(JSON, default=list)
    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==================== Banner 轮播图 ====================

class Banner(Base):
    """首页轮播图"""
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), default="")
    image = Column(String(500), nullable=False)
    link = Column(String(500), default="")  # 跳转链接
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==================== 网站配置 ====================

class SiteConfig(Base):
    """系统配置 (键值对)"""
    __tablename__ = "site_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, default="")
    description = Column(String(500), default="")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

