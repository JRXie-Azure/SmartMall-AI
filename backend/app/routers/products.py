"""
商品路由 — 含缓存、分类、浏览记录追踪
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db, cache_get, cache_set, cache_delete_pattern
from app.models import Product, Category, ProductView, Favorite, Review, User
from app.schemas import (
    ProductOut, ProductListOut, CategoryCreate, CategoryOut,
    ReviewCreate, ReviewOut, FavoriteOut,
)
from app.auth import get_current_user, get_current_user_optional
from app.services.recommendation_service import record_product_view
from typing import Optional

router = APIRouter(prefix="/api/products", tags=["商品"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    """商品分类列表"""
    cache_key = "products:categories"
    cached = cache_get(cache_key)
    if cached:
        return cached
    result = db.query(Category).order_by(Category.sort_order).all()
    cache_set(cache_key, [CategoryOut.model_validate(c).model_dump() for c in result], expire=600)
    return result


@router.get("", response_model=ProductListOut)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    keyword: Optional[str] = None,
    brand: Optional[str] = None,
    sort: str = Query("default"),
    db: Session = Depends(get_db),
):
    """商品列表 (分页 + 筛选 + 排序)"""
    query = db.query(Product).filter(
        Product.is_active == True,
        Product.audit_status == "approved"
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)
    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    total = query.count()

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "sales":
        query = query.order_by(Product.sales.desc())
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.offset((page - 1) * page_size).limit(page_size).all()
    return ProductListOut(items=products, total=total, page=page, page_size=page_size)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional),
):
    """商品详情 (自动记录浏览)"""
    cache_key = f"products:detail:{product_id}"
    cached = cache_get(cache_key)
    if cached:
        if user:
            record_product_view(db, user.id, product_id)
        return cached

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    result = ProductOut.model_validate(product).model_dump()
    cache_set(cache_key, result, expire=300)

    if user:
        record_product_view(db, user.id, product_id)

    return product


# ====== 商品评价 ======

@router.get("/{product_id}/reviews", response_model=list[ReviewOut])
def get_product_reviews(
    product_id: int,
    db: Session = Depends(get_db),
):
    """商品评价列表"""
    reviews = db.query(Review).filter(Review.product_id == product_id).order_by(
        Review.created_at.desc()
    ).all()
    result = []
    for r in reviews:
        user = db.query(User).filter(User.id == r.user_id).first()
        result.append(ReviewOut(
            id=r.id, user_id=r.user_id, product_id=r.product_id,
            rating=r.rating, content=r.content, images=r.images or [],
            is_anonymous=r.is_anonymous, created_at=r.created_at,
            username="匿名用户" if r.is_anonymous else (user.username if user else "未知用户"),
        ))
    return result


@router.post("/{product_id}/reviews", response_model=ReviewOut)
def create_review(
    product_id: int,
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发表评价"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    review = Review(
        user_id=user.id,
        product_id=product_id,
        order_id=data.order_id,
        rating=data.rating,
        content=data.content,
        images=data.images,
        is_anonymous=data.is_anonymous,
    )
    db.add(review)

    # 更新商品评分
    all_reviews = db.query(Review).filter(Review.product_id == product_id).all()
    total_rating = sum(r.rating for r in all_reviews) + data.rating
    product.rating = round(total_rating / (len(all_reviews) + 1), 1)

    db.commit()
    db.refresh(review)
    return ReviewOut(
        id=review.id, user_id=review.user_id, product_id=review.product_id,
        rating=review.rating, content=review.content, images=review.images or [],
        is_anonymous=review.is_anonymous, created_at=review.created_at,
        username="匿名用户" if review.is_anonymous else user.username,
    )


# ====== 收藏 ======

@router.get("/{product_id}/favorite")
def check_favorite(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """检查是否已收藏"""
    fav = db.query(Favorite).filter(
        Favorite.user_id == user.id,
        Favorite.product_id == product_id,
    ).first()
    return {"is_favorite": bool(fav)}


@router.post("/{product_id}/favorite")
def toggle_favorite(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏/取消收藏"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    fav = db.query(Favorite).filter(
        Favorite.user_id == user.id,
        Favorite.product_id == product_id,
    ).first()

    if fav:
        db.delete(fav)
        db.commit()
        return {"is_favorite": False, "message": "已取消收藏"}
    else:
        fav = Favorite(user_id=user.id, product_id=product_id)
        db.add(fav)
        db.commit()
        return {"is_favorite": True, "message": "已收藏"}
