"""
搜索路由 — 全文搜索 + 语义搜索 + 筛选 + 排序
支持: 关键词搜索、价格区间、品牌筛选、分类筛选、搜索建议、搜索历史
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database import get_db
from app.models import Product, Category, SearchHistory, User
from app.schemas import ProductOut, ProductListOut
from app.auth import get_current_user_optional
from app.services.rag_service import rag_search, is_rag_available
from app.database import cache_get, cache_set
from typing import Optional

router = APIRouter(prefix="/api/search", tags=["搜索"])


@router.get("")
def search(
    keyword: str = Query(..., min_length=1),
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    brand: Optional[str] = None,
    sort: str = Query("relevance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional),
):
    """
    综合搜索: 关键词 + 筛选 + 排序
    sort: relevance(相关度) / price_asc / price_desc / sales / rating / newest
    """
    # 记录搜索历史
    if user:
        history = SearchHistory(user_id=user.id, keyword=keyword)
        db.add(history)
        db.commit()

    # 构建查询
    query = db.query(Product).filter(
        Product.is_active == True,
        Product.audit_status == "approved"
    )

    # 关键词搜索 (名称 + 描述 + 品牌)
    conditions = []
    conditions.append(Product.name.ilike(f"%{keyword}%"))
    conditions.append(Product.description.ilike(f"%{keyword}%"))
    conditions.append(Product.brand.ilike(f"%{keyword}%"))
    # 标签搜索
    conditions.append(Product.tags.cast(__import__('sqlalchemy').Text).ilike(f"%{keyword}%"))
    query = query.filter(or_(*conditions))

    # 筛选
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    total = query.count()

    # 排序
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
        # relevance: 按销量+评分综合排序
        query = query.order_by(
            Product.sales.desc(),
            Product.rating.desc()
        )

    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProductListOut(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/semantic")
def semantic_search(
    data: dict,
    db: Session = Depends(get_db),
):
    """
    语义搜索: 自然语言 → RAG 向量检索
    示例: {"query": "适合户外跑步的轻便鞋子"}
    """
    query = data.get("query", "").strip()
    limit = data.get("limit", 10)

    if not query:
        raise HTTPException(status_code=400, detail="查询不能为空")

    if not is_rag_available():
        # 降级为关键词搜索
        products = db.query(Product).filter(
            Product.is_active == True,
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%"),
                Product.brand.ilike(f"%{query}%"),
            )
        ).order_by(Product.sales.desc()).limit(limit).all()
        return {
            "query": query,
            "results": products,
            "mode": "keyword",
            "message": "RAG 未启用，使用关键词搜索"
        }

    # RAG 语义搜索
    rag_results = rag_search(query, top_k=limit)
    if not rag_results:
        return {"query": query, "results": [], "mode": "rag"}

    # 查询完整商品
    product_ids = [r["id"] for r in rag_results]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    id_to_product = {p.id: p for p in products}

    sorted_results = []
    for r in rag_results:
        p = id_to_product.get(r["id"])
        if p:
            sorted_results.append({
                "product": p,
                "similarity": r["similarity"],
                "matched_text": r["document"],
            })

    return {"query": query, "results": sorted_results, "mode": "rag"}


@router.get("/suggestions")
def search_suggestions(
    keyword: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """搜索建议/自动补全"""
    # 缓存
    cache_key = f"search:suggest:{keyword}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 商品名称建议
    products = db.query(Product.name, Product.brand).filter(
        Product.is_active == True,
        Product.name.ilike(f"%{keyword}%")
    ).distinct().limit(8).all()

    # 品牌建议
    brands = db.query(Product.brand).filter(
        Product.is_active == True,
        Product.brand.ilike(f"%{keyword}%"),
        Product.brand != ""
    ).distinct().limit(5).all()

    # 热门搜索词
    hot_searches = db.query(SearchHistory.keyword).filter(
        SearchHistory.keyword.ilike(f"%{keyword}%")
    ).limit(5).all()

    suggestions = {
        "products": [p.name for p in products],
        "brands": [b.brand for b in brands if b.brand],
        "hot_keywords": [h.keyword for h in hot_searches],
    }

    cache_set(cache_key, suggestions, expire=120)
    return suggestions


@router.get("/hot")
def hot_searches(db: Session = Depends(get_db)):
    """热门搜索词"""
    from sqlalchemy import func
    results = db.query(
        SearchHistory.keyword,
        func.count(SearchHistory.id).label("count")
    ).group_by(SearchHistory.keyword).order_by(
        func.count(SearchHistory.id).desc()
    ).limit(10).all()

    return [{"keyword": r.keyword, "count": r.count} for r in results]


@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    """所有品牌列表 (用于筛选)"""
    from sqlalchemy import func
    brands = db.query(
        Product.brand,
        func.count(Product.id).label("count")
    ).filter(
        Product.is_active == True,
        Product.brand != ""
    ).group_by(Product.brand).order_by(
        func.count(Product.id).desc()
    ).all()

    return [{"name": b.brand, "count": b.count} for b in brands]
