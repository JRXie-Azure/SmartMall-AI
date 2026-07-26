"""
管理后台路由 — 增强版
- 时间序列统计 (销售额趋势、用户增长、订单状态分布、品类分布)
- 商品管理 (CRUD + 审核)
- 用户管理
- 订单管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from datetime import datetime, timedelta
from app.database import get_db, cache_get, cache_set, cache_delete_pattern
from app.models import (
    Product, Order, OrderItem, User, Category, Review,
    ProductUpdate, OrderStatusUpdate, ProductAudit,
)
from app.schemas import (
    AdminStatsOut, ProductCreate, ProductOut, ProductUpdate as ProductUpdateSchema,
    ProductAudit as ProductAuditSchema, OrderStatusUpdate as OrderStatusUpdateSchema,
    OrderOut,
)
from app.auth import get_current_admin, get_current_user
from app.models import User as UserModel

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


# ====== 统计看板 ======

@router.get("/stats")
def get_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """
    管理后台统计数据 (含时间序列，用于 ECharts)
    """
    # 缓存
    cache_key = f"admin:stats:{days}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    now = datetime.now()
    start_date = now - timedelta(days=days)

    # 基础统计
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_sales = db.query(func.sum(Order.total_amount)).filter(
        Order.status != "cancelled"
    ).scalar() or 0
    total_users = db.query(func.count(UserModel.id)).scalar() or 0

    # 销售趋势 (按天)
    sales_trend = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_sales = db.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= day_start,
            Order.created_at < day_end,
            Order.status != "cancelled"
        ).scalar() or 0
        day_orders = db.query(func.count(Order.id)).filter(
            Order.created_at >= day_start,
            Order.created_at < day_end
        ).scalar() or 0
        sales_trend.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "sales": round(day_sales, 2),
            "orders": day_orders,
        })

    # 订单状态分布
    order_status_dist = db.query(
        Order.status,
        func.count(Order.id).label("count")
    ).group_by(Order.status).all()
    order_status_dist = [{"status": s.status, "count": s.count} for s in order_status_dist]

    # 品类分布
    category_dist = db.query(
        Category.name,
        func.count(Product.id).label("count")
    ).join(Product, Product.category_id == Category.id).group_by(Category.name).all()
    category_dist = [{"category": c.name, "count": c.count} for c in category_dist]

    # 用户增长 (按天)
    user_growth = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(UserModel.id)).filter(
            UserModel.created_at >= day_start,
            UserModel.created_at < day_end
        ).scalar() or 0
        user_growth.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count,
        })

    # 热销商品 TOP 10
    top_products = db.query(
        Product.name,
        func.sum(OrderItem.quantity).label("total_sold")
    ).join(OrderItem, OrderItem.product_id == Product.id).group_by(
        Product.id, Product.name
    ).order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()
    top_products = [{"name": p.name, "sales": int(p.total_sold)} for p in top_products]

    result = {
        "total_products": total_products,
        "total_orders": total_orders,
        "total_sales": round(total_sales, 2),
        "total_users": total_users,
        "sales_trend": sales_trend,
        "order_status_dist": order_status_dist,
        "category_dist": category_dist,
        "user_growth": user_growth,
        "top_products": top_products,
    }

    cache_set(cache_key, result, expire=60)
    return result


# ====== 商品管理 ======

@router.get("/products")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    audit_status: str = None,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """商品列表 (含审核状态)"""
    query = db.query(Product)
    if audit_status:
        query = query.filter(Product.audit_status == audit_status)
    total = query.count()
    products = query.order_by(Product.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"items": products, "total": total, "page": page, "page_size": page_size}


@router.post("/products", response_model=ProductOut)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """创建商品"""
    product = Product(
        **data.model_dump(),
        audit_status="approved",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdateSchema,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """更新商品"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(product, k, v)

    db.commit()
    db.refresh(product)
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")
    return product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """删除商品 (软删除)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.is_active = False
    db.commit()
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")
    return {"message": "已下架"}


@router.put("/products/{product_id}/audit")
def audit_product(
    product_id: int,
    data: ProductAuditSchema,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """商品审核"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    if data.audit_status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="审核状态无效")

    product.audit_status = data.audit_status
    if data.audit_status == "rejected":
        product.is_active = False
    db.commit()
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")
    return {"message": f"商品已{'通过' if data.audit_status == 'approved' else '拒绝'}审核"}


# ====== 用户管理 ======

@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str = None,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """用户列表"""
    query = db.query(UserModel)
    if role:
        query = query.filter(UserModel.role == role)
    total = query.count()
    users = query.order_by(UserModel.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {
        "items": [{
            "id": u.id, "username": u.username, "email": u.email,
            "role": u.role, "is_active": u.is_active,
            "avatar": u.avatar, "phone": u.phone,
            "created_at": u.created_at,
        } for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.put("/users/{user_id}/status")
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """启用/禁用用户"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"用户已{'启用' if user.is_active else '禁用'}", "is_active": user.is_active}


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """修改用户角色"""
    if role not in ("user", "merchant", "admin"):
        raise HTTPException(status_code=400, detail="角色无效")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.role = role
    db.commit()
    return {"message": f"角色已更新为 {role}"}


# ====== 订单管理 ======

@router.get("/orders")
def list_all_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = None,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """全部订单列表"""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"items": orders, "total": total, "page": page, "page_size": page_size}


@router.put("/orders/{order_id}/status")
def update_order_status_admin(
    order_id: int,
    data: OrderStatusUpdateSchema,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """管理员更新订单状态"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    valid_transitions = {
        "pending": ["paid", "cancelled"],
        "paid": ["shipped", "refunded"],
        "shipped": ["completed", "refunded"],
        "completed": [],
        "cancelled": [],
        "refunded": [],
    }

    allowed = valid_transitions.get(order.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"订单状态不能从 {order.status} 变为 {data.status}"
        )

    order.status = data.status
    now = datetime.now()
    if data.status == "paid":
        order.paid_at = now
    elif data.status == "shipped":
        order.shipped_at = now
        if data.tracking_no:
            order.tracking_no = data.tracking_no
        if data.logistics_company:
            order.logistics_company = data.logistics_company
    elif data.status == "completed":
        order.completed_at = now

    db.commit()
    return {"message": f"订单状态已更新为 {data.status}"}
