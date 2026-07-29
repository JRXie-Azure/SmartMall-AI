"""
RAG 服务 — 语义检索增强生成
使用 scikit-learn TF-IDF + 余弦相似度实现轻量级语义搜索
无需 sentence-transformers / chromadb 等重型依赖，适配所有 Python 版本

原理:
1. 将商品文本 (名称+品牌+描述+分类+标签) 用 TF-IDF 向量化
2. 用户查询同样向量化
3. 计算余弦相似度，返回最相关的 top_k 商品
"""
import logging
import json
import numpy as np
from typing import List, Dict, Optional
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 全局索引状态
_vectorizer = None
_tfidf_matrix = None          # 稀疏矩阵: 所有商品的 TF-IDF 向量
_product_ids = []             # 商品 ID 列表 (与矩阵行对应)
_product_docs = []            # 商品文档文本列表 (用于返回匹配片段)
_product_meta = {}            # product_id -> {name, brand, price, category}
_indexed = False              # 是否已索引


def _build_doc(name: str, description: str, brand: str,
               category: str = "", tags: list = None) -> str:
    """构造商品文档文本: 综合名称、品牌、描述、分类、标签"""
    tags_str = " ".join(tags) if tags else ""
    return f"{name} {brand} {category} {tags_str} {description or ''}".strip()


def _init_vectorizer():
    """初始化 TfidfVectorizer (按字符分词，适配中文)"""
    global _vectorizer
    if _vectorizer is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        _vectorizer = TfidfVectorizer(
            analyzer="char_wb",       # 按字符 n-gram 分词 (适配中文)
            ngram_range=(1, 2),       # unigram + bigram
            min_df=1,                 # 最低文档频率
            max_features=10000,       # 最大特征数
        )
        logger.info("TF-IDF 向量化器初始化成功 (analyzer=char_wb, ngram=(1,2))")
    return _vectorizer


def index_product(product_id: int, name: str, description: str, brand: str,
                  price: float, category: str = "", tags: list = None):
    """
    将商品加入索引 (单个)
    注意: 实际索引在 index_all_products 或 _rebuild_index 中批量执行
    """
    doc = _build_doc(name, description, brand, category, tags)
    _product_meta[product_id] = {
        "product_id": product_id,
        "name": name,
        "brand": brand,
        "price": price,
        "category": category,
    }
    # 标记需要重建索引
    global _indexed
    _indexed = False


def index_all_products(db) -> int:
    """批量索引所有商品到 TF-IDF 矩阵"""
    global _product_ids, _product_docs, _product_meta, _tfidf_matrix, _indexed

    from app.models import Product, Category
    products = db.query(Product).filter(Product.is_active == True).all()
    categories = {c.id: c.name for c in db.query(Category).all()}

    _product_ids = []
    _product_docs = []
    _product_meta = {}

    for p in products:
        cat_name = categories.get(p.category_id, "")
        doc = _build_doc(
            name=p.name,
            description=p.description or "",
            brand=p.brand or "",
            category=cat_name,
            tags=p.tags if p.tags else []
        )
        _product_ids.append(p.id)
        _product_docs.append(doc)
        _product_meta[p.id] = {
            "product_id": p.id,
            "name": p.name,
            "brand": p.brand,
            "price": p.price,
            "category": cat_name,
        }

    # 构建 TF-IDF 矩阵
    if _product_docs:
        vectorizer = _init_vectorizer()
        _tfidf_matrix = vectorizer.fit_transform(_product_docs)
        _indexed = True
        logger.info(f"已索引 {len(products)} 个商品到 TF-IDF 矩阵 (特征维度: {_tfidf_matrix.shape[1]})")
    else:
        _tfidf_matrix = None
        _indexed = True
        logger.warning("没有商品可索引")

    return len(products)


def _ensure_indexed(db=None):
    """确保索引已构建 (懒加载)"""
    global _indexed
    if not _indexed:
        if db is None:
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                index_all_products(db)
            finally:
                db.close()
        else:
            index_all_products(db)


def rag_search(query: str, top_k: int = 5, db=None) -> List[Dict]:
    """
    RAG 语义搜索: 用户自然语言 → TF-IDF 向量检索 → 返回相关商品

    示例: rag_search("适合跑步的轻便鞋子，预算800以内") → 返回跑鞋相关商品
    """
    _ensure_indexed(db)

    if _tfidf_matrix is None or not _product_ids:
        return []

    try:
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = _init_vectorizer()
        # 将查询向量化 (使用已 fit 的 vectorizer)
        query_vec = vectorizer.transform([query])

        # 计算查询与所有商品的余弦相似度
        similarities = cosine_similarity(query_vec, _tfidf_matrix).flatten()

        # 取相似度最高的 top_k (过滤掉相似度为 0 的)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            sim = similarities[idx]
            if sim <= 0:
                continue
            pid = _product_ids[idx]
            meta = _product_meta.get(pid, {})
            doc = _product_docs[idx][:200] if idx < len(_product_docs) else ""
            results.append({
                "id": pid,
                "name": meta.get("name", ""),
                "brand": meta.get("brand", ""),
                "price": meta.get("price", 0),
                "category": meta.get("category", ""),
                "similarity": round(float(sim), 4),
                "document": doc,
            })

        return results
    except Exception as e:
        logger.error(f"RAG 搜索失败: {e}")
        return []


def is_rag_available() -> bool:
    """检查 RAG 是否可用 (scikit-learn 已安装即可)"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        return True
    except ImportError:
        logger.warning("scikit-learn 未安装，RAG 功能不可用")
        return False
