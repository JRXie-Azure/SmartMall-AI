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
    metadata = Column(JSON, default=dict)  # 附加信息: 推荐商品ID列表、工具调用结果等
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


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
