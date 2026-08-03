package com.smartmall.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/** 客服会话。status: active / closed / transferred（转人工） */
@Entity
@Table(name = "chat_sessions", indexes = {
        @Index(name = "idx_chat_session_sid", columnList = "session_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ChatSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 前端生成的会话 UUID，非自增主键 */
    @Column(name = "session_id", nullable = false, unique = true, length = 64)
    private String sessionId;

    /** 允许为空 —— 匿名访客也能发起会话 */
    @Column(name = "user_id")
    private Long userId;

    @Builder.Default
    @Column(name = "user_name", length = 100)
    private String userName = "访客";

    @Builder.Default
    @Column(length = 20)
    private String status = "active";

    @Column(name = "assigned_agent_id")
    private Long assignedAgentId;

    /** AI 生成的会话摘要 */
    @Builder.Default
    @Column(columnDefinition = "TEXT")
    private String summary = "";

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "closed_at")
    private LocalDateTime closedAt;
}
