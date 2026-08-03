package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.entity.ChatMessage;
import com.smartmall.entity.ChatSession;
import com.smartmall.entity.User;
import com.smartmall.repository.ChatMessageRepository;
import com.smartmall.repository.ChatSessionRepository;
import com.smartmall.security.CurrentUser;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 客服会话查询接口 —— 对应 websocket.py 里的两个 HTTP 端点。
 *
 * <p>路径前缀是 /ws 而不是 /api/ws，与 Python 版一致（前端管理页直接调这两个地址）。
 * 注意 {@code /ws/chat} 是 WebSocket 端点，由 WebSocketHandlerMapping 处理，
 * 与这里的 {@code /ws/sessions} 不冲突。
 */
@RestController
@RequestMapping("/ws")
@RequiredArgsConstructor
public class WsSessionController {

    private static final int SESSION_LIMIT = 50;

    private final ChatSessionRepository chatSessionRepository;
    private final ChatMessageRepository chatMessageRepository;

    /**
     * 会话列表。
     *
     * <p>Python 版形参名叫 admin 但实际挂的是 get_current_user，只要登录即可，
     * 这里保持同样的宽松口径，避免管理页突然 403。
     */
    @GetMapping("/sessions")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listSessions(@CurrentUser User user) {
        List<ChatSession> sessions = chatSessionRepository
                .findAllByOrderByCreatedAtDesc(PageRequest.of(0, SESSION_LIMIT));
        if (sessions.isEmpty()) {
            return List.of();
        }

        Map<Long, Long> counts = new HashMap<>();
        for (Object[] row : chatMessageRepository.countGroupBySessionIds(
                sessions.stream().map(ChatSession::getId).toList())) {
            counts.put((Long) row[0], ((Number) row[1]).longValue());
        }

        List<Map<String, Object>> out = new ArrayList<>(sessions.size());
        for (ChatSession s : sessions) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("session_id", s.getSessionId());
            row.put("status", s.getStatus());
            row.put("user_name", s.getUserName());
            row.put("created_at", s.getCreatedAt());
            row.put("closed_at", s.getClosedAt());
            row.put("message_count", counts.getOrDefault(s.getId(), 0L));
            out.add(row);
        }
        return out;
    }

    /** 某个会话的完整消息历史（Python 版此接口不校验登录，保持一致） */
    @GetMapping("/sessions/{sessionId}/messages")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> sessionMessages(@PathVariable String sessionId) {
        ChatSession session = chatSessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> ApiException.notFound("会话不存在"));

        List<ChatMessage> messages =
                chatMessageRepository.findBySessionIdOrderByCreatedAtAsc(session.getId());

        List<Map<String, Object>> out = new ArrayList<>(messages.size());
        for (ChatMessage m : messages) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", m.getId());
            row.put("sender_type", m.getSenderType());
            row.put("content", m.getContent());
            // 字段名就叫 metadata（Python 侧 m.extra_data 映射过来的），别改成 extra_data
            row.put("metadata", m.getExtraData());
            row.put("created_at", m.getCreatedAt());
            out.add(row);
        }
        return out;
    }
}
