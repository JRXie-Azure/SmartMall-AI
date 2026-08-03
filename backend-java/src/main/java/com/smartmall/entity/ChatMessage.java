package com.smartmall.entity;

import com.smartmall.common.JsonConverters;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 客服消息。
 *
 * <p>注意列名: Python 侧写的是 {@code Column("metadata", JSON)}，即物理列叫 metadata，
 * 属性叫 extra_data。这里保持物理列名 metadata 不变（MySQL 保留字需反引号，H2 MODE=MySQL 同样接受），
 * Java 属性名沿用 extraData，序列化后为 extra_data，与 Pydantic 输出一致。
 */
@Entity
@Table(name = "chat_messages", indexes = {
        @Index(name = "idx_chat_msg_session", columnList = "session_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ChatMessage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 指向 chat_sessions.id（自增主键），不是 ChatSession.sessionId */
    @Column(name = "session_id", nullable = false)
    private Long sessionId;

    /** user / ai / agent */
    @Column(name = "sender_type", nullable = false, length = 20)
    private String senderType;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Builder.Default
    @Convert(converter = JsonConverters.JsonMapConverter.class)
    @Column(name = "`metadata`", columnDefinition = "TEXT")
    private Map<String, Object> extraData = new LinkedHashMap<>();

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
