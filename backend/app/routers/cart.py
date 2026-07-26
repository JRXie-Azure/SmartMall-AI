"""
购物车路由 — 增删改查 + 数量更新
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CartItem, Product, User
from app.schemas import CartItemCreate, CartItemOut, CartItemUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/api/cart", tags=["购物车"])


@router.get("/items", response_model=list[CartItemOut])
def list_cart_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """购物车列表"""
    items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    return items


@router.post("/items", response_model=CartItemOut)
def add_to_cart(
    data: CartItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """加入购物车"""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if product.stock < data.quantity:
        raise HTTPException(status_code=400, detail=f"库存不足 (剩余 {product.stock})")

    existing = db.query(CartItem).filter(
        CartItem.user_id == user.id,
        CartItem.product_id == data.product_id
    ).first()

    if existing:
        existing.quantity += data.quantity
        if existing.quantity > product.stock:
            raise HTTPException(status_code=400, detail=f"超过库存 (剩余 {product.stock})")
        db.commit()
        db.refresh(existing)
        return existing
    else:
        item = CartItem(user_id=user.id, product_id=data.product_id, quantity=data.quantity)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


@router.put("/items/{item_id}", response_model=CartItemOut)
def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改购物车数量"""
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="购物车项不存在")

    product = db.query(Product).filter(Product.id == item.product_id).first()
    if product and data.quantity > product.stock:
        raise HTTPException(status_code=400, detail=f"超过库存 (剩余 {product.stock})")

    item.quantity = data.quantity
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
def remove_from_cart(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移除购物车项"""
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    db.delete(item)
    db.commit()
    return {"message": "已移除"}


@router.delete("/items")
def clear_cart(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清空购物车"""
    db.query(CartItem).filter(CartItem.user_id == user.id).delete()
    db.commit()
    return {"message": "购物车已清空"}


@router.get("/count")
def get_cart_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """购物车商品数量"""
    count = db.query(CartItem).filter(CartItem.user_id == user.id).count()
    return {"count": count}
