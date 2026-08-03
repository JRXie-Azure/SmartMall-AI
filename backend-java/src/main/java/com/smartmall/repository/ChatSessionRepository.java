package com.smartmall.repository;

import com.smartmall.entity.ChatSession;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ChatSessionRepository extends JpaRepository<ChatSession, Long> {

    Optional<ChatSession> findBySessionId(String sessionId);

    List<ChatSession> findByStatusOrderByCreatedAtDesc(String status);

    List<ChatSession> findAllByOrderByCreatedAtDesc();

    List<ChatSession> findAllByOrderByCreatedAtDesc(Pageable pageable);
}
