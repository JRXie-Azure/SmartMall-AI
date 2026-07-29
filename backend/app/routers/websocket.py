"""
WebSocket 实时客服系统
- AI 先接，解决不了转人工
- 心跳机制、断线重连
- 会话持久化
"""
import json
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import ChatSession, ChatMessage as ChatMessageModel, User
from app.auth import get_current_user, get_current_user_optional, get_current_admin
from app.services.llm_service import chat_completion, execute_tool_call
from app.config import get_settings

router = APIRouter(tags=["WebSocket"])
settings = get_settings()
logger = logging.getLogger(__name__)

# 在线连接管理: session_id -> WebSocket
active_connections: dict[str, WebSocket] = {}
# 等待人工接听的会话
pending_human_sessions: set[str] = set()


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    WebSocket 客服端点
    前端连接: ws://localhost:8001/ws/chat?token=YOUR_JWT_TOKEN

    消息格式:
    入: {"type": "message", "content": "你好", "session_id": "xxx"}
    出: {"type": "reply", "content": "你好！有什么可以帮你的？", "sender": "ai"}
    """
    # JWT 认证
    user_id = None
    if token:
        try:
            from app.auth import decode_access_token
            payload = decode_access_token(token)
            user_id = int(payload.get("sub"))
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                await websocket.close(code=4001, reason="无效的认证信息")
                return
        except Exception:
            await websocket.close(code=4001, reason="认证失败")
            return

    await websocket.accept()
    session_id = str(uuid.uuid4())

    # 创建会话记录
    chat_session = ChatSession(
        session_id=session_id,
        user_id=user_id,
        user_name=user.username if user_id and user else "访客",
        status="active",
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    active_connections[session_id] = websocket

    # 发送欢迎消息
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "message": "连接成功！我是 SmartMall AI 客服助手，有什么可以帮你的？"
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "消息格式错误"})
                continue

            msg_type = msg.get("type", "message")

            if msg_type == "ping":
                # 心跳
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "message":
                content = msg.get("content", "").strip()
                if not content:
                    continue

                # 保存用户消息
                user_msg = ChatMessageModel(
                    session_id=chat_session.id,
                    sender_type="user",
                    content=content,
                )
                db.add(user_msg)
                db.commit()

                # 检查是否在转人工模式
                if session_id in pending_human_sessions:
                    # 转人工模式: 不调用 AI，等待人工客服
                    await websocket.send_json({
                        "type": "info",
                        "message": "已为您转接人工客服，请稍候..."
                    })
                    continue

                # AI 回复
                await websocket.send_json({"type": "typing", "sender": "ai"})

                # 获取对话历史
                history = db.query(ChatMessageModel).filter(
                    ChatMessageModel.session_id == chat_session.id
                ).order_by(ChatMessageModel.created_at).limit(20).all()

                messages = []
                for h in history:
                    role = "user" if h.sender_type == "user" else "assistant"
                    messages.append({"role": role, "content": h.content})

                # 调用 LLM
                result = await chat_completion(messages, use_tools=True)
                tool_calls = result.get("tool_calls", [])

                if tool_calls:
                    # 执行工具调用
                    for tc in tool_calls:
                        func_name = tc["function"]["name"]
                        try:
                            func_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            func_args = {}

                        tool_result = await execute_tool_call(func_name, func_args, db)

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

                        # 如果用户要转人工
                        if func_name == "transfer_to_human" or "人工" in content or "客服" in content:
                            pending_human_sessions.add(session_id)
                            chat_session.status = "transferred"
                            db.commit()

                    # 基于工具结果生成回复
                    final_result = await chat_completion(messages, use_tools=False)
                    reply = final_result["content"]
                else:
                    reply = result["content"]

                # 检测转人工意图
                if any(kw in content for kw in ["转人工", "人工客服", "真人", "找客服"]):
                    pending_human_sessions.add(session_id)
                    chat_session.status = "transferred"
                    db.commit()
                    reply = "好的，正在为您转接人工客服，请稍候..."

                # 保存 AI 消息
                ai_msg = ChatMessageModel(
                    session_id=chat_session.id,
                    sender_type="ai",
                    content=reply,
                )
                db.add(ai_msg)
                db.commit()

                # 发送回复
                await websocket.send_json({
                    "type": "reply",
                    "content": reply,
                    "sender": "ai",
                    "session_id": session_id,
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: {session_id}")
        chat_session.status = "closed"
        chat_session.closed_at = datetime.now()
        db.commit()
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
    finally:
        active_connections.pop(session_id, None)
        pending_human_sessions.discard(session_id)


@router.get("/ws/sessions")
async def list_chat_sessions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """获取客服会话列表 (管理员)"""
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).limit(50).all()
    return [{
        "session_id": s.session_id,
        "status": s.status,
        "user_name": s.user_name,
        "created_at": s.created_at,
        "closed_at": s.closed_at,
        "message_count": len(s.messages),
    } for s in sessions]


@router.get("/ws/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """获取某个会话的消息历史"""
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")

    return [{
        "id": m.id,
        "sender_type": m.sender_type,
        "content": m.content,
        "metadata": m.extra_data,
        "created_at": m.created_at,
    } for m in session.messages]
