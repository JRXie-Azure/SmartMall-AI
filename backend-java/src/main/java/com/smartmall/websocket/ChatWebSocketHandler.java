package com.smartmall.websocket;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.smartmall.entity.ChatMessage;
import com.smartmall.entity.ChatSession;
import com.smartmall.repository.ChatMessageRepository;
import com.smartmall.repository.ChatSessionRepository;
import com.smartmall.service.LlmService;
import com.smartmall.service.ToolExecutorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * WebSocket 实时客服 —— 对应 Python 版 app/routers/websocket.py 的 /ws/chat。
 *
 * <p>行为约定（与 Python 版逐条对齐）：
 * <ul>
 *   <li>AI 先接，命中转人工关键词后进入 pending 状态，后续消息不再走 LLM</li>
 *   <li>连接建立即落库一条 chat_sessions，断开时置 closed 并记 closed_at</li>
 *   <li>心跳 ping/pong；消息体非法回 {"type":"error"}</li>
 * </ul>
 *
 * <p>消息协议：
 * <pre>
 * 入: {"type":"message","content":"你好","session_id":"xxx"}
 * 出: {"type":"connected"|"reply"|"typing"|"info"|"pong"|"error", ...}
 * </pre>
 *
 * <p>与 Python 的 async 模型不同，这里把 LLM 调用甩到独立线程池：
 * Tomcat 的容器线程不能被一次 10~30s 的模型调用长期占住。
 * 同一条连接的发送用 session 对象加锁串行化 —— WebSocketSession 不是线程安全的。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ChatWebSocketHandler extends TextWebSocketHandler {

    /** 会话 UUID，对外暴露给前端 */
    private static final String ATTR_SID = "smartmall.ws.sid";
    /** chat_sessions 自增主键，chat_messages.session_id 外键指向它 */
    private static final String ATTR_ROW_ID = "smartmall.ws.rowId";

    private static final List<String> HUMAN_KEYWORDS = List.of("转人工", "人工客服", "真人", "找客服");
    private static final String WELCOME = "连接成功！我是 SmartMall AI 客服助手，有什么可以帮你的？";
    private static final String TRANSFER_REPLY = "好的，正在为您转接人工客服，请稍候...";
    private static final int HISTORY_LIMIT = 20;

    /** 在线连接: session_id -> WebSocketSession，对应 Python 的 active_connections */
    private static final Map<String, WebSocketSession> ACTIVE = new ConcurrentHashMap<>();
    /** 等待人工接听的会话，对应 Python 的 pending_human_sessions */
    private static final Set<String> PENDING_HUMAN = ConcurrentHashMap.newKeySet();

    private final ChatSessionRepository chatSessionRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final LlmService llmService;
    private final ToolExecutorService toolExecutor;
    private final ObjectMapper mapper;

    private final ExecutorService worker = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "ws-chat");
        t.setDaemon(true);
        return t;
    });

    // ====== 生命周期 ======

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String sid = UUID.randomUUID().toString();
        ChatSession row = chatSessionRepository.save(
                ChatSession.builder().sessionId(sid).status("active").build());

        session.getAttributes().put(ATTR_SID, sid);
        session.getAttributes().put(ATTR_ROW_ID, row.getId());
        ACTIVE.put(sid, session);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "connected");
        payload.put("session_id", sid);
        payload.put("message", WELCOME);
        send(session, payload);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        JsonNode msg;
        try {
            msg = mapper.readTree(message.getPayload());
        } catch (Exception e) {
            sendError(session, "消息格式错误");
            return;
        }
        if (msg == null || !msg.isObject()) {
            sendError(session, "消息格式错误");
            return;
        }

        String type = msg.path("type").asText("message");

        if ("ping".equals(type)) {
            send(session, Map.of("type", "pong"));
            return;
        }
        if (!"message".equals(type)) {
            return;
        }

        String content = msg.path("content").asText("").trim();
        if (content.isEmpty()) {
            return;
        }
        // LLM 调用是阻塞的，不能占住容器线程
        worker.execute(() -> {
            try {
                handleUserMessage(session, content);
            } catch (Exception e) {
                log.error("WebSocket 消息处理异常", e);
                sendError(session, "服务异常，请稍后重试");
            }
        });
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String sid = (String) session.getAttributes().get(ATTR_SID);
        Long rowId = (Long) session.getAttributes().get(ATTR_ROW_ID);
        log.info("WebSocket 断开: {}", sid);

        if (rowId != null) {
            chatSessionRepository.findById(rowId).ifPresent(s -> {
                s.setStatus("closed");
                s.setClosedAt(LocalDateTime.now());
                chatSessionRepository.save(s);
            });
        }
        if (sid != null) {
            ACTIVE.remove(sid);
            PENDING_HUMAN.remove(sid);
        }
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        log.warn("WebSocket 传输异常: {}", exception.getMessage());
    }

    // ====== 核心：一条用户消息的完整处理 ======

    private void handleUserMessage(WebSocketSession session, String content) {
        String sid = (String) session.getAttributes().get(ATTR_SID);
        Long rowId = (Long) session.getAttributes().get(ATTR_ROW_ID);
        if (sid == null || rowId == null) {
            return;
        }

        // 1. 先落库用户消息，保证转人工后客服能看到完整上下文
        chatMessageRepository.save(ChatMessage.builder()
                .sessionId(rowId).senderType("user").content(content).build());

        // 2. 已转人工：不再打扰 LLM
        if (PENDING_HUMAN.contains(sid)) {
            Map<String, Object> info = new LinkedHashMap<>();
            info.put("type", "info");
            info.put("message", "已为您转接人工客服，请稍候...");
            send(session, info);
            return;
        }

        // 3. 打字指示
        Map<String, Object> typing = new LinkedHashMap<>();
        typing.put("type", "typing");
        typing.put("sender", "ai");
        send(session, typing);

        // 4. 取历史（与 Python 一致：按时间升序取前 20 条）
        List<ObjectNode> messages = new ArrayList<>();
        for (ChatMessage h : chatMessageRepository.findTop20BySessionIdOrderByCreatedAtAsc(rowId)) {
            String role = "user".equals(h.getSenderType()) ? "user" : "assistant";
            messages.add(llmService.message(role, h.getContent()));
        }

        // 5. 第一轮：带工具
        LlmService.ChatResult first = llmService.chatCompletion(messages, true);
        String reply;

        if (!first.toolCalls().isEmpty()) {
            for (LlmService.ToolCall tc : first.toolCalls()) {
                String toolResult = toolExecutor.execute(tc.name(), parseArgs(tc.arguments()), null);
                messages.add(llmService.assistantToolCallMessage(tc));
                messages.add(llmService.toolResultMessage(tc.id(), toolResult));

                // 这个判断刻意保留 Python 的宽松口径（只要提到"人工/客服"就转）
                if ("transfer_to_human".equals(tc.name())
                        || content.contains("人工") || content.contains("客服")) {
                    transferToHuman(sid, rowId);
                }
            }
            // 6. 第二轮：不带工具，让模型把工具结果说成人话
            reply = llmService.chatCompletion(messages, false).content();
        } else {
            reply = first.content();
        }

        // 7. 显式转人工意图覆盖回复
        if (HUMAN_KEYWORDS.stream().anyMatch(content::contains)) {
            transferToHuman(sid, rowId);
            reply = TRANSFER_REPLY;
        }
        if (reply == null || reply.isBlank()) {
            reply = "抱歉，我没太理解您的意思，可以换个说法吗？";
        }

        // 8. 落库并回推
        chatMessageRepository.save(ChatMessage.builder()
                .sessionId(rowId).senderType("ai").content(reply).build());

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("type", "reply");
        out.put("content", reply);
        out.put("sender", "ai");
        out.put("session_id", sid);
        send(session, out);
    }

    private void transferToHuman(String sid, Long rowId) {
        if (!PENDING_HUMAN.add(sid)) {
            return; // 已经在等人工了，不用重复写库
        }
        chatSessionRepository.findById(rowId).ifPresent(s -> {
            s.setStatus("transferred");
            chatSessionRepository.save(s);
        });
    }

    // ====== 发送 ======

    private void send(WebSocketSession session, Map<String, Object> payload) {
        try {
            String json = mapper.writeValueAsString(payload);
            // WebSocketSession 非线程安全，并发 sendMessage 会撕裂帧
            synchronized (session) {
                if (session.isOpen()) {
                    session.sendMessage(new TextMessage(json));
                }
            }
        } catch (Exception e) {
            log.debug("WebSocket 发送失败: {}", e.getMessage());
        }
    }

    private void sendError(WebSocketSession session, String message) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "error");
        payload.put("message", message);
        send(session, payload);
    }

    private JsonNode parseArgs(String raw) {
        try {
            JsonNode node = mapper.readTree(raw == null || raw.isBlank() ? "{}" : raw);
            return node.isObject() ? node : mapper.createObjectNode();
        } catch (Exception e) {
            return mapper.createObjectNode();
        }
    }

    // ====== 供管理端查询实时状态 ======

    public static boolean isOnline(String sessionId) {
        return ACTIVE.containsKey(sessionId);
    }

    public static boolean isWaitingHuman(String sessionId) {
        return PENDING_HUMAN.contains(sessionId);
    }
}
