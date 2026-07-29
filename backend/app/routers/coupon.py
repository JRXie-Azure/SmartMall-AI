"""
优惠券路由
- 用户: 领取、查看我的优惠券、应用优惠码
- 管理员: 创建、管理优惠券
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.database import get_db
from app.models import Coupon, UserCoupon, Order, User as UserModel
from app.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/coupons", tags=["优惠券"])


@router.get("/available")
def list_available_coupons(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    """获取当前用户可领取的优惠券"""
    now = datetime.now()
    coupons = db.query(Coupon).filter(
        Coupon.is_active == True,
        (Coupon.valid_from == None) | (Coupon.valid_from <= now),
        (Coupon.valid_until == None) | (Coupon.valid_until >= now),
    ).all()

    # 过滤掉用户已领完次数的
    result = []
    for c in coupons:
        user_count = db.query(func.count(UserCoupon.id)).filter(
            UserCoupon.user_id == user.id,
            UserCoupon.coupon_id == c.id,
        ).scalar() or 0
        if user_count < c.per_user_limit:
            result.append({
                "id": c.id, "code": c.code, "name": c.name,
                "description": c.description, "discount_type": c.discount_type,
                "discount_value": c.discount_value, "min_order_amount": c.min_order_amount,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            })
    return result


@router.post("/claim/{coupon_id}")
def claim_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    """领取优惠券"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon or not coupon.is_active:
        raise HTTPException(status_code=404, detail="优惠券不存在")

    # 检查用户是否已领取
    existing = db.query(UserCoupon).filter(
        UserCoupon.user_id == user.id,
        UserCoupon.coupon_id == coupon_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已领取过该优惠券")

    user_coupon = UserCoupon(user_id=user.id, coupon_id=coupon_id)
    db.add(user_coupon)
    db.commit()
    return {"message": "领取成功"}


@router.get("/my")
def my_coupons(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    """我的优惠券"""
    user_coupons = db.query(UserCoupon).filter(
        UserCoupon.user_id == user.id,
        UserCoupon.is_used == False,
    ).all()
    return [{
        "id": uc.id,
        "coupon_id": uc.coupon_id,
        "code": uc.coupon.code,
        "name": uc.coupon.name,
        "discount_type": uc.coupon.discount_type,
        "discount_value": uc.coupon.discount_value,
        "min_order_amount": uc.coupon.min_order_amount,
        "valid_until": uc.coupon.valid_until.isoformat() if uc.coupon.valid_until else None,
    } for uc in user_coupons]


@router.post("/apply")
def apply_coupon(
    code: str,
    order_amount: float,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    """应用优惠码计算折扣"""
    coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.is_active == True).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠码无效")

    now = datetime.now()
    if coupon.valid_from and coupon.valid_from > now:
        raise HTTPException(status_code=400, detail="优惠券尚未生效")
    if coupon.valid_until and coupon.valid_until < now:
        raise HTTPException(status_code=400, detail="优惠券已过期")
    if coupon.min_order_amount > 0 and order_amount < coupon.min_order_amount:
        raise HTTPException(status_code=400, detail=f"订单金额需满 ¥{coupon.min_order_amount}")

    # 检查用户是否已领取
    user_coupon = db.query(UserCoupon).filter(
        UserCoupon.user_id == user.id,
        UserCoupon.coupon_id == coupon.id,
        UserCoupon.is_used == False,
    ).first()
    if not user_coupon:
        raise HTTPException(status_code=400, detail="您未领取该优惠券")

    # 计算折扣
    if coupon.discount_type == "fixed":
        discount = min(coupon.discount_value, order_amount)
    else:  # percent
        discount = order_amount * (coupon.discount_value / 100)
        if coupon.max_discount:
            discount = min(discount, coupon.max_discount)

    return {
        "coupon_id": coupon.id,
        "code": coupon.code,
        "name": coupon.name,
        "discount": round(discount, 2),
        "final_amount": round(order_amount - discount, 2),
    }


# ====== 管理员接口 ======

@router.post("/admin/create")
def create_coupon(
    data: dict,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """创建优惠券 (管理员)"""
    coupon = Coupon(**data)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return {"id": coupon.id, "code": coupon.code}
