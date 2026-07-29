from typing import List
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
from pydantic import BaseModel
from app.database import get_db, cache_get, cache_set, cache_delete_pattern
from app.models import (
    Product, Order, OrderItem, User, Category, Review, Coupon,
    MarketingCampaign, Banner, SiteConfig,
)
from app.schemas import (
    AdminStatsOut, ProductCreate, ProductOut, ProductUpdate as ProductUpdateSchema,
    ProductAudit as ProductAuditSchema, OrderStatusUpdate as OrderStatusUpdateSchema,
    OrderOut, CouponCreate, CouponUpdate,
    MarketingCampaignCreate, MarketingCampaignUpdate, BannerCreate, BannerUpdate, SiteConfigItem,
    CouponOut, MarketingCampaignOut, BannerOut, PaginatedResponse,
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
    start_date = now - timedelta(days=days - 1)  # -1 使趋势包含今天

    # 基础统计
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_sales = db.query(func.sum(Order.total_amount)).filter(
        Order.status != "cancelled"
    ).scalar() or 0
    total_users = db.query(func.count(UserModel.id)).scalar() or 0

    # 销售趋势 (按天) — 单次 GROUP BY 查询替代 N 天循环
    daily_sales = db.query(
        func.date(Order.created_at).label("day"),
        func.sum(Order.total_amount).label("sales"),
        func.count(Order.id).label("orders"),
    ).filter(
        Order.created_at >= start_date,
        Order.created_at < now,
    ).group_by(func.date(Order.created_at)).all()
    sales_map = {}
    for row in daily_sales:
        day_str = row.day if isinstance(row.day, str) else row.day.strftime("%Y-%m-%d")
        sales_map[day_str] = {"sales": round(row.sales or 0, 2), "orders": row.orders}
    sales_trend = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        stat = sales_map.get(day_str, {"sales": 0, "orders": 0})
        sales_trend.append({"date": day_str, "sales": stat["sales"], "orders": stat["orders"]})

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

    # 用户增长 (按天) — 单次 GROUP BY 查询
    daily_users = db.query(
        func.date(UserModel.created_at).label("day"),
        func.count(UserModel.id).label("count"),
    ).filter(
        UserModel.created_at >= start_date,
        UserModel.created_at < now,
    ).group_by(func.date(UserModel.created_at)).all()
    user_map = {}
    for row in daily_users:
        day_str = row.day if isinstance(row.day, str) else row.day.strftime("%Y-%m-%d")
        user_map[day_str] = row.count
    user_growth = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        user_growth.append({"date": day_str, "count": user_map.get(day_str, 0)})

    # 热销商品 TOP 10
    top_products = db.query(
        Product.name,
        func.sum(OrderItem.quantity).label("total_sold")
    ).join(OrderItem, OrderItem.product_id == Product.id).group_by(
        Product.id, Product.name
    ).order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()
    top_products = [{"name": p.name, "sales": int(p.total_sold)} for p in top_products]

    pending_audit = db.query(func.count(Product.id)).filter(
        Product.audit_status == "pending"
    ).scalar() or 0
    low_stock = db.query(func.count(Product.id)).filter(
        Product.stock <= 10, Product.is_active == True
    ).scalar() or 0

    result = {
        "total_products": total_products,
        "total_orders": total_orders,
        "total_sales": round(total_sales, 2),
        "total_revenue": round(total_sales, 2),  # 兼容前端字段
        "total_users": total_users,
        "pending_audit": pending_audit,
        "low_stock": low_stock,
        "ai_conversion": round(
            (db.query(func.count(func.distinct(OrderItem.order_id))).join(
                Product, Product.id == OrderItem.product_id
            ).filter(Product.is_recommend == True).scalar() or 0) / total_orders * 100, 1
        ) if total_orders else 0.0,
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
    keyword: str = None,
    status: str = None,  # active / inactive
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """商品列表 (含审核状态、关键词搜索、上下架筛选)"""
    from sqlalchemy import or_
    query = db.query(Product)
    if audit_status:
        query = query.filter(Product.audit_status == audit_status)
    if keyword:
        query = query.filter(or_(
            Product.name.contains(keyword),
            Product.brand.contains(keyword),
            Product.description.contains(keyword)
        ))
    if status == "active":
        query = query.filter(Product.is_active == True)
    elif status == "inactive":
        query = query.filter(Product.is_active == False)
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


# ====== 库存预警 ======

@router.get("/products/low-stock")
def get_low_stock_products(
    threshold: int = Query(10, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """库存预警商品列表"""
    query = db.query(Product).filter(
        Product.stock <= threshold,
        Product.is_active == True
    )
    total = query.count()
    products = query.order_by(Product.stock.asc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"items": products, "total": total, "page": page, "page_size": page_size}


# ====== 批量操作 ======

class BatchUpdateRequest(BaseModel):
    ids: list[int]
    action: str  # activate / deactivate / delete

@router.post("/products/batch")
def batch_update_products(
    data: BatchUpdateRequest,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """批量操作商品 (上架/下架/删除)"""
    products = db.query(Product).filter(Product.id.in_(data.ids)).all()
    if not products:
        raise HTTPException(status_code=404, detail="未找到商品")

    for p in products:
        if data.action == "activate":
            p.is_active = True
        elif data.action == "deactivate":
            p.is_active = False
        elif data.action == "delete":
            p.is_active = False
            p.audit_status = "rejected"

    db.commit()
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")
    return {"message": f"已处理 {len(products)} 件商品", "action": data.action}


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
    """全部订单列表 (含用户名和商品摘要)"""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    # 批量查询用户和首个订单项, 避免N+1
    order_ids = [o.id for o in orders]
    user_ids = list(set(o.user_id for o in orders))
    users_map = {}
    if user_ids:
        users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
        users_map = {u.id: u.username for u in users}
    first_items_map = {}
    if order_ids:
        all_items = db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).order_by(OrderItem.id).all()
        for item in all_items:
            if item.order_id not in first_items_map:
                first_items_map[item.order_id] = item
    items = []
    for o in orders:
        first_item = first_items_map.get(o.id)
        items.append({
            "id": o.id,
            "order_no": o.order_no,
            "user_id": o.user_id,
            "username": users_map.get(o.user_id, f"用户{o.user_id}"),
            "status": o.status,
            "total_amount": o.total_amount,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": [{"product_name": first_item.product_name, "quantity": first_item.quantity}] if first_item else [],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


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

    old_status = order.status
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

    # 恢复库存: 当订单状态变为 cancelled 或 refunded 时
    if data.status in ("cancelled", "refunded") and old_status not in ("cancelled", "refunded"):
        # 恢复库存
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
                product.sales = max(0, product.sales - item.quantity)

    db.commit()
    return {"message": f"订单状态已更新为 {data.status}"}


# ====== 优惠券管理 ======

@router.get("/coupons", response_model=PaginatedResponse)
def list_coupons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool = None,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """优惠券列表"""
    query = db.query(Coupon)
    if is_active is not None:
        query = query.filter(Coupon.is_active == is_active)
    total = query.count()
    coupons = query.order_by(Coupon.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"items": coupons, "total": total, "page": page, "page_size": page_size}


@router.post("/coupons", response_model=CouponOut)
def create_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """创建优惠券"""
    existing = db.query(Coupon).filter(Coupon.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="优惠码已存在")

    coupon = Coupon(**data.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.put("/coupons/{coupon_id}")
def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """更新优惠券"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(coupon, k, v)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.put("/coupons/{coupon_id}/toggle")
def toggle_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """启用/禁用优惠券"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    coupon.is_active = not coupon.is_active
    db.commit()
    return {"message": f"优惠券已{'启用' if coupon.is_active else '禁用'}", "is_active": coupon.is_active}

# ====== AI 智能分析 ======

@router.get("/ai-analysis")
def get_ai_analysis(
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """AI 智能分析: 销售预测、用户画像、商品洞察、运营建议"""
    now = datetime.now()

    # 最近7天销售数据 — 单次 GROUP BY 查询
    week_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_sales = db.query(
        func.date(Order.created_at).label("day"),
        func.sum(Order.total_amount).label("total"),
    ).filter(
        Order.created_at >= week_start,
        Order.created_at < now,
        Order.status != "cancelled",
    ).group_by(func.date(Order.created_at)).all()
    sales_map = {}
    for row in daily_sales:
        day_str = row.day if isinstance(row.day, str) else row.day.strftime("%Y-%m-%d")
        sales_map[day_str] = row.total or 0
    sales_7d = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        sales_7d.append(sales_map.get(day_str, 0))

    # 简单线性预测未来3天
    n = len(sales_7d)
    x_mean = sum(range(n)) / n
    y_mean = sum(sales_7d) / n
    numerator = sum((i - x_mean) * (sales_7d[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator else 0
    intercept = y_mean - slope * x_mean
    forecast_3d = [round(max(0, intercept + slope * (n + i)), 2) for i in range(1, 4)]

    # 用户画像
    total_users = db.query(func.count(UserModel.id)).scalar() or 0
    new_users_7d = db.query(func.count(UserModel.id)).filter(
        UserModel.created_at >= now - timedelta(days=7)
    ).scalar() or 0
    old_users = total_users - new_users_7d

    # 复购率: 下过2单及以上的用户占比
    users_with_orders = db.query(Order.user_id, func.count(Order.id)).group_by(Order.user_id).having(func.count(Order.id) >= 2).all()
    repurchase_rate = round(len(users_with_orders) / total_users * 100, 1) if total_users else 0

    # 商品洞察
    # 滞销商品: 上架超过30天销量<5
    stagnant_products = db.query(Product).filter(
        Product.is_active == True,
        Product.sales < 5,
        Product.created_at <= now - timedelta(days=30)
    ).order_by(Product.sales.asc()).limit(10).all()

    # 潜力商品: 高评分但销量中等
    potential_products = db.query(Product).filter(
        Product.is_active == True,
        Product.rating >= 4.5,
        Product.sales >= 5,
        Product.sales <= 50
    ).order_by(Product.rating.desc()).limit(10).all()

    # AI 运营建议
    suggestions = []
    avg_sales = sum(sales_7d) / len(sales_7d) if sales_7d else 0
    if avg_sales < 1000:
        suggestions.append("近7日日均销售额偏低，建议增加营销活动或发放优惠券刺激消费")
    if repurchase_rate < 20:
        suggestions.append("用户复购率较低，建议设置会员积分体系或老客专属优惠")
    if stagnant_products:
        suggestions.append(f"检测到 {len(stagnant_products)} 件滞销商品，建议通过限时折扣或捆绑销售清理库存")
    if new_users_7d < total_users * 0.05:
        suggestions.append("新用户增长放缓，建议在社交媒体或搜索引擎增加广告投放")
    if not suggestions:
        suggestions.append("当前经营状况良好，建议保持现有策略并关注用户反馈")

    return {
        "sales_forecast": {
            "historical": sales_7d,
            "forecast": forecast_3d,
            "labels": [(now - timedelta(days=i)).strftime("%m-%d") for i in range(6, -1, -1)] + [
                (now + timedelta(days=i)).strftime("%m-%d") for i in range(1, 4)
            ],
        },
        "user_profile": {
            "total_users": total_users,
            "new_users_7d": new_users_7d,
            "old_users": old_users,
            "repurchase_rate": repurchase_rate,
        },
        "product_insights": {
            "stagnant": [{"id": p.id, "name": p.name, "sales": p.sales, "stock": p.stock} for p in stagnant_products],
            "potential": [{"id": p.id, "name": p.name, "rating": p.rating, "sales": p.sales} for p in potential_products],
        },
        "suggestions": suggestions,
    }


# ====== 营销管理 ======

@router.get("/campaigns", response_model=PaginatedResponse)
def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool = None,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """营销活动列表"""
    query = db.query(MarketingCampaign)
    if is_active is not None:
        query = query.filter(MarketingCampaign.is_active == is_active)
    total = query.count()
    items = query.order_by(MarketingCampaign.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/campaigns", response_model=MarketingCampaignOut)
def create_campaign(
    data: MarketingCampaignCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """创建营销活动"""
    campaign = MarketingCampaign(**data.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.put("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: int,
    data: MarketingCampaignUpdate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """更新营销活动"""
    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="活动不存在")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(campaign, k, v)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.put("/campaigns/{campaign_id}/toggle")
def toggle_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """启用/禁用营销活动"""
    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="活动不存在")
    campaign.is_active = not campaign.is_active
    db.commit()
    return {"message": f"活动已{'启用' if campaign.is_active else '禁用'}", "is_active": campaign.is_active}


# ====== Banner 管理 ======

@router.get("/banners", response_model=List[BannerOut])
def list_banners(
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """Banner 列表"""
    banners = db.query(Banner).order_by(Banner.sort_order.asc()).all()
    return banners


@router.post("/banners", response_model=BannerOut)
def create_banner(
    data: BannerCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """创建 Banner"""
    banner = Banner(**data.model_dump())
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.put("/banners/{banner_id}")
def update_banner(
    banner_id: int,
    data: BannerUpdate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """更新 Banner"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner不存在")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(banner, k, v)
    db.commit()
    db.refresh(banner)
    return banner


@router.delete("/banners/{banner_id}")
def delete_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """删除 Banner"""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner不存在")
    db.delete(banner)
    db.commit()
    return {"message": "已删除"}


# ====== 系统设置 ======

@router.get("/configs")
def list_configs(
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """获取所有系统配置"""
    configs = db.query(SiteConfig).all()
    return {c.config_key: {"value": c.config_value, "description": c.description} for c in configs}


@router.put("/configs")
def update_configs(
    items: list[SiteConfigItem],
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """批量更新系统配置"""
    for item in items:
        config = db.query(SiteConfig).filter(SiteConfig.config_key == item.config_key).first()
        if config:
            config.config_value = item.config_value
            if item.description:
                config.description = item.description
        else:
            config = SiteConfig(
                config_key=item.config_key,
                config_value=item.config_value,
                description=item.description,
            )
            db.add(config)
    db.commit()
    return {"message": "配置已更新"}

