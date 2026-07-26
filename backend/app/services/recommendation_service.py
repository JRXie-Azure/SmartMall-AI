"""
推荐服务 — 协同过滤 + 内容推荐 + 热销降级
使用 scikit-learn 计算用户相似度
"""
import logging
import numpy as np
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models import Product, ProductView, Order, OrderItem, Favorite

logger = logging.getLogger(__name__)


def get_personalized_recommendations(
    db: Session,
    user_id: Optional[int],
    limit: int = 5,
) -> List[Product]:
    """
    个性化推荐: 协同过滤 → 内容推荐 → 热销降级
    """
    if user_id:
        # 尝试协同过滤
        products = collaborative_filtering(db, user_id, limit)
        if products:
            return products

        # 降级: 基于用户浏览历史的内容推荐
        products = content_based_recommendation(db, user_id, limit)
        if products:
            return products

    # 最终降级: 热销商品
    return db.query(Product).filter(
        Product.is_active == True,
        Product.audit_status == "approved"
    ).order_by(Product.sales.desc()).limit(limit).all()


def collaborative_filtering(
    db: Session,
    user_id: int,
    limit: int = 5,
) -> List[Product]:
    """
    基于用户的协同过滤 (User-Based CF)
    1. 构建 用户-商品 交互矩阵 (浏览 + 购买 + 收藏)
    2. 计算用户相似度 (余弦相似度)
    3. 找到相似用户喜欢的商品
    """
    try:
        from sklearn.metrics.pairwise import cosine_similarity

        # 获取所有有交互记录的用户和商品
        views = db.query(ProductView).all()
        orders = db.query(OrderItem).join(Order).filter(Order.status != "cancelled").all()
        favorites = db.query(Favorite).all()

        if len(views) + len(orders) + len(favorites) < 5:
            return []  # 数据太少，无法推荐

        # 收集所有商品 ID
        all_product_ids = set()
        for v in views:
            all_product_ids.add(v.product_id)
        for o in orders:
            all_product_ids.add(o.product_id)
        for f in favorites:
            all_product_ids.add(f.product_id)

        if not all_product_ids:
            return []

        product_id_list = sorted(all_product_ids)
        product_id_to_idx = {pid: idx for idx, pid in enumerate(product_id_list)}

        # 收集所有用户 ID
        all_user_ids = set()
        for v in views:
            if v.user_id:
                all_user_ids.add(v.user_id)
        for o in orders:
            all_user_ids.add(o.order.user_id)
        for f in favorites:
            all_user_ids.add(f.user_id)

        if user_id not in all_user_ids:
            return []

        user_id_list = sorted(all_user_ids)
        user_id_to_idx = {uid: idx for idx, uid in enumerate(user_id_list)}

        # 构建交互矩阵: 行=用户, 列=商品, 值=交互权重
        # 浏览=1, 收藏=3, 购买=5
        n_users = len(user_id_list)
        n_products = len(product_id_list)
        matrix = np.zeros((n_users, n_products))

        for v in views:
            if v.user_id and v.product_id in product_id_to_idx:
                matrix[user_id_to_idx[v.user_id]][product_id_to_idx[v.product_id]] += 1

        for f in favorites:
            if f.user_id and f.product_id in product_id_to_idx:
                matrix[user_id_to_idx[f.user_id]][product_id_to_idx[f.product_id]] += 3

        for o in orders:
            uid = o.order.user_id
            if uid in user_id_to_idx and o.product_id in product_id_to_idx:
                matrix[user_id_to_idx[uid]][product_id_to_idx[o.product_id]] += 5

        # 计算用户相似度
        target_idx = user_id_to_idx[user_id]
        target_vector = matrix[target_idx].reshape(1, -1)
        similarities = cosine_similarity(target_vector, matrix)[0]

        # 找到最相似的 N 个用户 (排除自己)
        similar_indices = np.argsort(similarities)[::-1][1:6]  # top 5 similar users

        # 收集相似用户喜欢但当前用户没看过的商品
        target_products = set(np.where(matrix[target_idx] > 0)[0])
        recommended_indices = []
        recommended_scores = []

        for idx in similar_indices:
            if similarities[idx] <= 0:
                continue
            user_products = set(np.where(matrix[idx] > 0)[0])
            new_products = user_products - target_products
            for pid in new_products:
                if pid not in recommended_indices:
                    recommended_indices.append(pid)
                    # 加权得分: 相似度 * 交互权重
                    recommended_scores.append(similarities[idx] * matrix[idx][pid])

        if not recommended_indices:
            return []

        # 按得分排序，取 top N
        sorted_pairs = sorted(
            zip(recommended_indices, recommended_scores),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        recommended_product_ids = [product_id_list[idx] for idx, _ in sorted_pairs]

        # 查询商品
        products = db.query(Product).filter(
            Product.id.in_(recommended_product_ids),
            Product.is_active == True,
            Product.stock > 0,
        ).all()

        # 按推荐得分排序
        id_to_product = {p.id: p for p in products}
        return [id_to_product[pid] for pid in recommended_product_ids if pid in id_to_product]

    except ImportError:
        logger.warning("scikit-learn 未安装，协同过滤降级")
        return []
    except Exception as e:
        logger.error(f"协同过滤异常: {e}")
        return []


def content_based_recommendation(
    db: Session,
    user_id: int,
    limit: int = 5,
) -> List[Product]:
    """
    基于内容的推荐: 找用户浏览过的商品的同类/同品牌商品
    """
    # 获取用户最近浏览的商品
    recent_views = db.query(ProductView).filter(
        ProductView.user_id == user_id
    ).order_by(ProductView.updated_at.desc()).limit(10).all()

    if not recent_views:
        return []

    viewed_product_ids = [v.product_id for v in recent_views]
    viewed_products = db.query(Product).filter(Product.id.in_(viewed_product_ids)).all()

    if not viewed_products:
        return []

    # 提取用户偏好: 品牌 + 分类
    brands = set(p.brand for p in viewed_products if p.brand)
    categories = set(p.category_id for p in viewed_products if p.category_id)
    tags = set()
    for p in viewed_products:
        if p.tags:
            tags.update(p.tags)

    # 查询同类/同品牌商品 (排除已浏览的)
    query = db.query(Product).filter(
        Product.is_active == True,
        Product.audit_status == "approved",
        ~Product.id.in_(viewed_product_ids),
        Product.stock > 0,
    )

    from sqlalchemy import or_
    conditions = []
    if brands:
        query = query.filter(Product.brand.in_(brands))

    products = query.order_by(Product.sales.desc()).limit(limit).all()
    return products


def record_product_view(db: Session, user_id: int, product_id: int, duration: int = 0):
    """记录用户浏览商品 (用于推荐)"""
    existing = db.query(ProductView).filter(
        ProductView.user_id == user_id,
        ProductView.product_id == product_id,
    ).first()

    if existing:
        existing.view_count += 1
        existing.duration += duration
    else:
        view = ProductView(
            user_id=user_id,
            product_id=product_id,
            view_count=1,
            duration=duration,
        )
        db.add(view)
    db.commit()
