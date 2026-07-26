"""
LLM 服务 — 接入 DeepSeek / OpenAI 兼容接口
支持: 普通对话、流式响应、Function Calling 工具调用
"""
import httpx
import json
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ====== 系统提示词 ======
SYSTEM_PROMPT = """你是 SmartMall AI 智能购物助手，服务于一个电商平台。你的职责：

1. **商品推荐**：理解用户的购物需求（用途、预算、偏好），推荐合适的商品
2. **商品查询**：帮用户搜索、筛选、比较商品
3. **订单咨询**：帮用户查询订单状态、物流信息
4. **售后引导**：处理退换货、投诉等售后问题
5. **使用建议**：提供商品使用、搭配建议

回答要求：
- 用中文回答，语气亲切自然
- 推荐商品时说明推荐理由（基于用户需求和商品特点）
- 如果用户提到的需求不明确，主动追问
- 不要编造不存在的商品信息，只基于搜索结果推荐
- 回答简洁，重点突出，适当使用 emoji 增加亲和力
"""

# ====== Function Calling 工具定义 ======
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "搜索/筛选商品。当用户想找商品、要推荐、比价、查库存时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如'跑鞋'、'手机'"},
                    "category": {"type": "string", "description": "商品分类，如'运动鞋'、'手机数码'"},
                    "max_price": {"type": "number", "description": "最高价格"},
                    "min_price": {"type": "number", "description": "最低价格"},
                    "brand": {"type": "string", "description": "品牌，如'Nike'、'Apple'"},
                    "sort": {"type": "string", "enum": ["sales", "price_asc", "price_desc", "rating"], "description": "排序方式"},
                    "limit": {"type": "integer", "description": "返回数量，默认5"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_detail",
            "description": "获取某个商品的详细信息。当用户询问某个具体商品时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "商品ID"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "语义搜索商品。当用户用自然语言描述需求时调用，如'适合跑步的轻便鞋子'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "自然语言查询，如'经常跑步预算800以内'"},
                    "limit": {"type": "integer", "description": "返回数量，默认5"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": "获取个性化推荐商品。当用户问'有什么推荐的'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "用户ID，用于个性化推荐"},
                    "limit": {"type": "integer", "description": "返回数量，默认5"}
                }
            }
        }
    }
]


async def chat_completion(
    messages: List[dict],
    use_tools: bool = True,
    temperature: float = 0.7,
) -> dict:
    """
    普通对话 (非流式)
    返回: {"content": str, "tool_calls": list}
    """
    if not settings.llm_api_key:
        return {
            "content": "抱歉，AI 服务尚未配置。请联系管理员设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY。",
            "tool_calls": []
        }

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "temperature": temperature,
        "max_tokens": 2000,
    }
    if use_tools:
        payload["tools"] = TOOLS
        payload["tool_choice"] = "auto"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            return {
                "content": choice.get("content", ""),
                "tool_calls": choice.get("tool_calls", []),
            }
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM API 错误: {e.response.status_code} - {e.response.text}")
        return {"content": f"AI 服务暂时不可用 (HTTP {e.response.status_code})", "tool_calls": []}
    except Exception as e:
        logger.error(f"LLM 调用异常: {e}")
        return {"content": "AI 服务暂时不可用，请稍后重试。", "tool_calls": []}


async def chat_completion_stream(
    messages: List[dict],
    use_tools: bool = False,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """
    流式对话 (SSE)
    逐字返回 content
    """
    if not settings.llm_api_key:
        yield "抱歉，AI 服务尚未配置。请联系管理员设置 API Key。"
        return

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "temperature": temperature,
        "max_tokens": 2000,
        "stream": True,
    }
    if use_tools:
        payload["tools"] = TOOLS
        payload["tool_choice"] = "auto"

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
    except Exception as e:
        logger.error(f"流式 LLM 异常: {e}")
        yield f"\n[AI 服务异常: {str(e)}]"


async def execute_tool_call(
    tool_name: str,
    arguments: dict,
    db=None,
    user_id: int = None,
) -> str:
    """
    执行 LLM 返回的工具调用，返回结果字符串
    """
    from app.models import Product
    from sqlalchemy.orm import Session

    if tool_name == "search_products":
        query = db.query(Product).filter(Product.is_active == True, Product.audit_status == "approved")
        if kw := arguments.get("keyword"):
            query = query.filter(Product.name.ilike(f"%{kw}%"))
        if brand := arguments.get("brand"):
            query = query.filter(Product.brand.ilike(f"%{brand}%"))
        if min_p := arguments.get("min_price"):
            query = query.filter(Product.price >= min_p)
        if max_p := arguments.get("max_price"):
            query = query.filter(Product.price <= max_p)
        sort = arguments.get("sort", "sales")
        if sort == "price_asc":
            query = query.order_by(Product.price.asc())
        elif sort == "price_desc":
            query = query.order_by(Product.price.desc())
        elif sort == "rating":
            query = query.order_by(Product.rating.desc())
        else:
            query = query.order_by(Product.sales.desc())
        limit = arguments.get("limit", 5)
        products = query.limit(limit).all()
        if not products:
            return "未找到匹配的商品。"
        return json.dumps([{
            "id": p.id, "name": p.name, "brand": p.brand,
            "price": p.price, "original_price": p.original_price,
            "rating": p.rating, "sales": p.sales, "stock": p.stock,
            "description": p.description[:100] if p.description else "",
            "image": p.image
        } for p in products], ensure_ascii=False)

    elif tool_name == "get_product_detail":
        pid = arguments.get("product_id")
        product = db.query(Product).filter(Product.id == pid).first()
        if not product:
            return "商品不存在。"
        return json.dumps({
            "id": product.id, "name": product.name, "brand": product.brand,
            "price": product.price, "original_price": product.original_price,
            "description": product.description, "rating": product.rating,
            "sales": product.sales, "stock": product.stock, "image": product.image,
            "tags": product.tags
        }, ensure_ascii=False)

    elif tool_name == "semantic_search":
        # RAG 语义搜索
        from app.services.rag_service import rag_search
        results = rag_search(arguments.get("query", ""), top_k=arguments.get("limit", 5))
        if not results:
            return "语义搜索未找到相关商品。"
        return json.dumps(results, ensure_ascii=False)

    elif tool_name == "get_recommendations":
        # 个性化推荐
        from app.services.recommendation_service import get_personalized_recommendations
        products = get_personalized_recommendations(db, user_id, limit=arguments.get("limit", 5))
        if not products:
            # 降级: 返回热销商品
            products = db.query(Product).filter(
                Product.is_active == True
            ).order_by(Product.sales.desc()).limit(5).all()
        return json.dumps([{
            "id": p.id, "name": p.name, "brand": p.brand,
            "price": p.price, "rating": p.rating, "sales": p.sales,
            "image": p.image
        } for p in products], ensure_ascii=False)

    return f"未知工具: {tool_name}"
