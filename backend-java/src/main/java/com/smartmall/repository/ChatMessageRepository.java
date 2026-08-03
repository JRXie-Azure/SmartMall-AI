package com.smartmall.repository;

import com.smartmall.entity.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Collection;
import java.util.List;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {

    List<ChatMessage> findBySessionIdOrderByCreatedAtAsc(Long sessionId);

    List<ChatMessage> findTop50BySessionIdOrderByCreatedAtDesc(Long sessionId);

    /**
     * 送进 LLM 的对话上下文。
     * 注意是「升序取前 20 条」而不是「最近 20 条」—— Python 版
     * {@code order_by(created_at).limit(20)} 就是这个语义，刻意保持一致。
     */
    List<ChatMessage> findTop20BySessionIdOrderByCreatedAtAsc(Long sessionId);

    /** 会话列表的 message_count，批量算避免 N+1 */
    @Query("select m.sessionId, count(m) from ChatMessage m where m.sessionId in :ids group by m.sessionId")
    List<Object[]> countGroupBySessionIds(@Param("ids") Collection<Long> ids);
}
