"""
AI 路由 — 真实 LLM 对话 + RAG 语义搜索 + SSE 流式 + 协同过滤推荐
"""
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import get_settings
from app.models import Product, ChatSession, ChatMessage as ChatMessageModel
from app.schemas import ChatMessage, ChatResponse, ProductOut
from app.auth import get_current_user, get_current_user_optional, get_current_admin
from app.models import User
from app.services.llm_service import chat_completion, chat_completion_stream, execute_tool_call
from app.services.rag_service import rag_search, index_all_products, is_rag_available
from app.services.recommendation_service import get_personalized_recommendations
from app.database import cache_get, cache_set

router = APIRouter(prefix="/api/ai", tags=["AI"])
settings = get_settings()


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    data: ChatMessage,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional),
):
    """
    AI 对话 (非流式)
    1. LLM 理解用户意图
    2. Function Calling 调用工具 (搜索/推荐/详情)
    3. LLM 基于工具结果生成自然语言回复
    """
    user_id = user.id if user else None

    # 构建对话历史
    messages = []
    if data.context:
        messages = data.context[-10:]  # 保留最近 10 轮
    messages.append({"role": "user", "content": data.message})

    # 第一次调用 LLM (带工具)
    result = await chat_completion(messages, use_tools=True)
    tool_calls = result.get("tool_calls", [])

    recommended_products = []
    tool_used = None

    if tool_calls:
        # 执行工具调用
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                func_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                func_args = {}

            tool_used = func_name
            tool_result = await execute_tool_call(func_name, func_args, db, user_id)

            # 从工具结果提取推荐商品
            if func_name in ("search_products", "get_recommendations", "semantic_search"):
                try:
                    product_ids = [p["id"] for p in json.loads(tool_result)] if isinstance(tool_result, str) else []
                    if product_ids:
                        recommended_products = db.query(Product).filter(
                            Product.id.in_(product_ids)
                        ).all()
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

            # 把工具结果加入对话，让 LLM 生成最终回复
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tc]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", "call_0"),
                "content": tool_result
            })

        # 第二次调用 LLM (基于工具结果生成回复)
        final_result = await chat_completion(messages, use_tools=False)
        reply = final_result["content"]

        # 如果 LLM 没有生成有效回复 (V4 推理模型有时只返回工具指令)，
        # 用工具结果组装自然语言回复
        if not reply:
            if recommended_products:
                product_names = "、".join(f"{p.name}（¥{p.price}）" for p in recommended_products[:5])
                reply = f"根据您的需求，为您找到以下商品推荐：{product_names}。点击商品卡片可以查看详情哦！"
            else:
                reply = "我理解您的需求，但暂时没有找到完全匹配的商品。您可以换个关键词试试，或者浏览我们的推荐栏目～"
        elif result["content"]:
            # 如果第一次调用就返回了自然语言回复，合并进来
            reply = result["content"] + "\n\n" + reply if reply else result["content"]
    else:
        reply = result["content"]

    return ChatResponse(
        reply=reply,
        products=recommended_products,
        tool_used=tool_used,
    )


@router.post("/chat/stream")
async def ai_chat_stream(
    data: ChatMessage,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional),
):
    """
    AI 对话 (SSE 流式) — 逐字返回
    支持 Function Calling: 先非流式获取工具调用, 执行后再流式输出最终回复
    """
    user_id = user.id if user else None
    messages = []
    if data.context:
        messages = data.context[-10:]
    messages.append({"role": "user", "content": data.message})

    async def event_stream():
        # 1. 先非流式调用, 让 LLM 决定是否需要工具
        result = await chat_completion(messages, use_tools=True)
        tool_calls = result.get("tool_calls", [])

        if tool_calls:
            # 2. 执行工具调用
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                tool_result = await execute_tool_call(func_name, func_args, db, user_id)
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", "call_0"),
                    "content": tool_result
                })

            # 3. 基于工具结果流式输出最终回复
            async for chunk in chat_completion_stream(messages, use_tools=False):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        else:
            # 无工具调用, 直接流式输出第一次回复
            if result.get("content"):
                yield f"data: {json.dumps({'content': result['content']}, ensure_ascii=False)}\n\n"
            else:
                async for chunk in chat_completion_stream(messages, use_tools=False):
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/recommendations", response_model=list[ProductOut])
def get_recommendations(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional),
):
    """个性化推荐 (协同过滤 + 内容推荐 + 热销降级)"""
    user_id = user.id if user else None

    # 尝试缓存
    cache_key = f"ai:recommendations:{user_id}:{limit}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    products = get_personalized_recommendations(db, user_id, limit)

    result = [
        ProductOut(
            id=p.id, name=p.name, description=p.description,
            price=p.price, original_price=p.original_price,
            image=p.image, images=p.images or [], stock=p.stock,
            sales=p.sales, category_id=p.category_id, tags=p.tags or [],
            brand=p.brand, rating=p.rating, is_recommend=p.is_recommend,
            is_new=p.is_new, is_sale=p.is_sale, is_active=p.is_active,
            audit_status=p.audit_status, created_at=p.created_at,
        ) for p in products
    ]

    cache_set(cache_key, [r.model_dump() for r in result], expire=60)
    return result


@router.post("/rag/search")
def rag_product_search(
    data: dict,
    db: Session = Depends(get_db),
):
    """
    RAG 语义搜索: 自然语言 → 向量检索 → 商品列表
    示例: {"query": "适合跑步的轻便鞋子，预算800以内"}
    """
    query = data.get("query", "")
    top_k = data.get("limit", 5)

    if not query:
        raise HTTPException(status_code=400, detail="查询不能为空")

    if not is_rag_available():
        # RAG 不可用时降级为关键词搜索
        products = db.query(Product).filter(
            Product.is_active == True,
            Product.name.ilike(f"%{query}%")
        ).limit(top_k).all()
        return {
            "query": query,
            "results": products,
            "mode": "keyword_fallback",
            "message": "RAG 未启用，使用关键词搜索"
        }

    # RAG 语义搜索
    rag_results = rag_search(query, top_k=top_k)
    if not rag_results:
        return {"query": query, "results": [], "mode": "rag"}

    # 查询完整商品信息
    product_ids = [r["id"] for r in rag_results]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    id_to_product = {p.id: p for p in products}

    # 按相似度排序
    sorted_results = []
    for r in rag_results:
        product = id_to_product.get(r["id"])
        if product:
            sorted_results.append({
                "product": ProductOut(
                    id=product.id, name=product.name, description=product.description,
                    price=product.price, original_price=product.original_price,
                    image=product.image, images=product.images or [],
                    stock=product.stock, sales=product.sales,
                    category_id=product.category_id, tags=product.tags or [],
                    brand=product.brand, rating=product.rating,
                    is_recommend=product.is_recommend, is_new=product.is_new,
                    is_sale=product.is_sale, is_active=product.is_active,
                    audit_status=product.audit_status, created_at=product.created_at,
                ).model_dump(),
                "similarity": r["similarity"],
                "matched_text": r["document"],
            })

    return {"query": query, "results": sorted_results, "mode": "rag"}


@router.post("/rag/index")
def index_products(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """手动触发商品向量索引 (管理员)"""
    if not is_rag_available():
        raise HTTPException(status_code=503, detail="RAG 服务未启用 (需要 scikit-learn)")
    count = index_all_products(db)
    return {"message": f"成功索引 {count} 个商品", "count": count}


@router.get("/status")
def ai_status():
    """AI 服务状态"""
    return {
        "llm_enabled": bool(settings.llm_api_key),
        "llm_model": settings.llm_model if settings.llm_api_key else "未配置",
        "rag_enabled": is_rag_available(),
        "embedding_model": "TF-IDF (scikit-learn)" if is_rag_available() else "未加载",
    }
