"""
订单路由 — 完整状态机 + 事务安全
状态流转: pending → paid → shipped → completed
         pending → cancelled
         paid → refunded
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db, cache_delete_pattern
from app.models import Order, OrderItem, CartItem, Product, Address, User, Coupon, UserCoupon
from app.schemas import OrderOut, OrderCreate, OrderStatusUpdate
from app.auth import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/api/orders", tags=["订单"])
settings = get_settings()

# 订单状态机: 定义合法的状态转换
ORDER_TRANSITIONS = {
    "pending": ["paid", "cancelled"],
    "paid": ["shipped", "refunded", "cancelled"],
    "shipped": ["completed", "refunded"],
    "completed": [],
    "cancelled": [],
    "refunded": [],
}

# 状态中文映射
STATUS_LABELS = {
    "pending": "待付款",
    "paid": "已付款",
    "shipped": "已发货",
    "completed": "已完成",
    "cancelled": "已取消",
    "refunded": "已退款",
}


@router.get("")
def list_orders(
    status: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看我的订单"""
    query = db.query(Order).filter(Order.user_id == user.id)
    if status:
        query = query.filter(Order.status == status)
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"items": orders, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=OrderOut)
def create_order(
    data: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从购物车创建订单"""
    cart_items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="购物车为空")

    # 获取收货地址
    address_snapshot = {"name": user.username, "phone": user.phone or "13800138000"}
    if data.address_id:
        addr = db.query(Address).filter(
            Address.id == data.address_id,
            Address.user_id == user.id
        ).first()
        if addr:
            address_snapshot = {
                "name": addr.name,
                "phone": addr.phone,
                "province": addr.province,
                "city": addr.city,
                "district": addr.district,
                "detail": addr.detail,
            }

    # 计算总价 + 检查库存
    total = 0
    order_items_data = []
    for cart_item in cart_items:
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()
        if not product:
            continue
        if product.stock < cart_item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"商品 {product.name} 库存不足 (剩余 {product.stock})"
            )
        total += product.price * cart_item.quantity
        order_items_data.append({
            "product_id": product.id,
            "product_name": product.name,
            "product_image": product.image,
            "price": product.price,
            "quantity": cart_item.quantity,
        })

    if not order_items_data:
        raise HTTPException(status_code=400, detail="购物车商品无效")

    # 应用优惠券
    discount_amount = 0
    coupon = None
    user_coupon = None
    if data.coupon_code:
        coupon = db.query(Coupon).filter(Coupon.code == data.coupon_code, Coupon.is_active == True).first()
        if not coupon:
            raise HTTPException(status_code=400, detail="无效的优惠码")
        # 检查有效期
        now = datetime.now()
        if coupon.valid_from and now < coupon.valid_from:
            raise HTTPException(status_code=400, detail="优惠券尚未生效")
        if coupon.valid_until and now > coupon.valid_until:
            raise HTTPException(status_code=400, detail="优惠券已过期")
        if total < coupon.min_order_amount:
            raise HTTPException(status_code=400, detail=f"订单金额未满 {coupon.min_order_amount} 元")
        # 校验用户是否拥有该券
        user_coupon = db.query(UserCoupon).filter(
            UserCoupon.user_id == user.id,
            UserCoupon.coupon_id == coupon.id,
            UserCoupon.is_used == False
        ).first()
        if not user_coupon:
            raise HTTPException(status_code=400, detail="您未持有该优惠券或已使用")
        # 计算折扣
        if coupon.discount_type == "fixed":
            discount_amount = coupon.discount_value
        elif coupon.discount_type == "percent":
            discount_amount = min(total * coupon.discount_value / 100, coupon.max_discount or float('inf'))
        discount_amount = min(discount_amount, total)
        total -= discount_amount

    # 创建订单
    order = Order(
        user_id=user.id,
        order_no=f"SM{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}",
        status="pending",
        total_amount=total,
        address_snapshot=address_snapshot,
        note=data.note,
    )
    db.add(order)
    db.flush()

    # 创建订单项 + 扣减库存
    for item_data in order_items_data:
        order_item = OrderItem(order_id=order.id, **item_data)
        db.add(order_item)
        # 扣减库存
        product = db.query(Product).filter(Product.id == item_data["product_id"]).first()
        product.stock -= item_data["quantity"]
        product.sales += item_data["quantity"]

    # 标记优惠券已使用
    if discount_amount > 0 and coupon and user_coupon:
        user_coupon.is_used = True
        user_coupon.used_at = datetime.now()
        user_coupon.order_id = order.id

    # 清空购物车
    for cart_item in cart_items:
        db.delete(cart_item)

    db.commit()
    db.refresh(order)
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")
    return order


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看订单详情"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # 普通用户只能看自己的订单
    if order.user_id != user.id and user.role == "user":
        raise HTTPException(status_code=403, detail="无权查看此订单")
    return order


@router.put("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新订单状态 (用户可: 取消、确认收货; 管理员可: 付款、发货、退款)
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 权限检查
    is_owner = order.user_id == user.id
    is_admin = user.role == "admin"

    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="无权操作此订单")

    # 用户只能执行特定操作
    if not is_admin:
        user_allowed = {
            "pending": ["cancelled"],
            "shipped": ["completed"],
        }
        allowed = user_allowed.get(order.status, [])
        if data.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"您不能将订单从「{STATUS_LABELS.get(order.status, order.status)}」变为「{STATUS_LABELS.get(data.status, data.status)}」"
            )
    else:
        # 管理员: 检查状态机
        allowed = ORDER_TRANSITIONS.get(order.status, [])
        if data.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"订单状态不能从「{STATUS_LABELS.get(order.status, order.status)}」变为「{STATUS_LABELS.get(data.status, data.status)}」"
            )

    # 执行状态转换
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
    elif data.status == "cancelled":
        # 取消订单: 恢复库存
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
                product.sales = max(0, product.sales - item.quantity)
    elif data.status == "refunded":
        # 退款: 恢复库存
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
                product.sales = max(0, product.sales - item.quantity)

    db.commit()
    db.refresh(order)
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")
    return order


@router.get("/stats/summary")
def get_order_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户订单统计"""
    orders = db.query(Order).filter(Order.user_id == user.id).all()
    stats = {
        "total": len(orders),
        "pending": sum(1 for o in orders if o.status == "pending"),
        "paid": sum(1 for o in orders if o.status == "paid"),
        "shipped": sum(1 for o in orders if o.status == "shipped"),
        "completed": sum(1 for o in orders if o.status == "completed"),
        "cancelled": sum(1 for o in orders if o.status == "cancelled"),
        "total_amount": sum(o.total_amount for o in orders if o.status != "cancelled"),
    }
    return stats
