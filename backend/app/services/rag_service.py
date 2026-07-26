"""
RAG 服务 — 向量检索增强生成
使用 sentence-transformers 生成商品向量 + ChromaDB 存储/检索
"""
import logging
import json
from typing import List, Dict, Optional
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 懒加载: 只在首次使用时初始化
_embedding_model = None
_chroma_client = None
_chroma_collection = None


def _get_embedding_model():
    """懒加载 sentence-transformers 模型"""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(f"Embedding 模型加载成功: {settings.EMBEDDING_MODEL}")
        except ImportError:
            logger.warning("sentence-transformers 未安装，RAG 功能降级")
            return None
        except Exception as e:
            logger.warning(f"Embedding 模型加载失败: {e}")
            return None
    return _embedding_model


def _get_chroma_collection():
    """懒加载 ChromaDB collection"""
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        try:
            import chromadb
            _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="products",
                metadata={"description": "SmartMall 商品向量索引"}
            )
            logger.info("ChromaDB 初始化成功")
        except ImportError:
            logger.warning("chromadb 未安装，RAG 功能降级")
            return None
        except Exception as e:
            logger.warning(f"ChromaDB 初始化失败: {e}")
            return None
    return _chroma_collection


def index_product(product_id: int, name: str, description: str, brand: str,
                  price: float, category: str = "", tags: list = None):
    """将商品索引进 ChromaDB"""
    collection = _get_chroma_collection()
    model = _get_embedding_model()
    if not collection or not model:
        return

    # 构造文档: 综合商品名称、品牌、描述、分类、标签
    tags_str = " ".join(tags) if tags else ""
    doc_text = f"{name} {brand} {category} {tags_str} {description}"
    doc_text = doc_text.strip()

    try:
        embedding = model.encode(doc_text).tolist()
        collection.upsert(
            ids=[str(product_id)],
            embeddings=[embedding],
            documents=[doc_text],
            metadatas=[{
                "product_id": product_id,
                "name": name,
                "brand": brand,
                "price": price,
                "category": category,
            }]
        )
    except Exception as e:
        logger.error(f"商品索引失败 (id={product_id}): {e}")


def index_all_products(db):
    """批量索引所有商品"""
    from app.models import Product, Category
    products = db.query(Product).filter(Product.is_active == True).all()
    categories = {c.id: c.name for c in db.query(Category).all()}

    for p in products:
        cat_name = categories.get(p.category_id, "")
        index_product(
            product_id=p.id,
            name=p.name,
            description=p.description or "",
            brand=p.brand or "",
            price=p.price,
            category=cat_name,
            tags=p.tags if p.tags else []
        )
    logger.info(f"已索引 {len(products)} 个商品到 ChromaDB")
    return len(products)


def rag_search(query: str, top_k: int = 5) -> List[Dict]:
    """
    RAG 语义搜索: 用户自然语言 → 向量检索 → 返回相关商品
    """
    collection = _get_chroma_collection()
    model = _get_embedding_model()

    if not collection or not model:
        return []

    try:
        query_embedding = model.encode(query).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        items = []
        for i, pid in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            similarity = 1 - distance  # 距离越小相似度越高
            items.append({
                "id": int(pid),
                "name": meta.get("name", ""),
                "brand": meta.get("brand", ""),
                "price": meta.get("price", 0),
                "category": meta.get("category", ""),
                "similarity": round(similarity, 4),
                "document": results["documents"][0][i][:200]
            })
        return items
    except Exception as e:
        logger.error(f"RAG 搜索失败: {e}")
        return []


def is_rag_available() -> bool:
    """检查 RAG 是否可用"""
    return _get_chroma_collection() is not None and _get_embedding_model() is not None
