package com.smartmall.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.smartmall.common.ApiException;
import com.smartmall.common.CacheService;
import com.smartmall.dto.ProductDtos;
import com.smartmall.entity.Product;
import com.smartmall.entity.User;
import com.smartmall.repository.ProductRepository;
import com.smartmall.security.CurrentUser;
import com.smartmall.service.LlmService;
import com.smartmall.service.RagService;
import com.smartmall.service.RecommendationService;
import com.smartmall.service.ToolExecutorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * AI 接口，对应 routers/ai.py。
 *
 * <p>核心是「两轮 LLM 调用」：第一轮带工具让模型决定要查什么，
 * 执行工具后把结果回灌，第二轮让模型用自然语言总结。
 */
@Slf4j
@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class AiController {

    /** 会带出商品卡片的工具，与 Python 版判断集合一致 */
    private static final Set<String> PRODUCT_TOOLS =
            Set.of("search_products", "get_recommendations", "semantic_search");

    /** 保留最近 10 轮上下文 */
    private static final int MAX_CONTEXT = 10;

    private final LlmService llmService;
    private final ToolExecutorService toolExecutor;
    private final RagService ragService;
    private final RecommendationService recommendationService;
    private final ProductRepository productRepository;
    private final CacheService cache;
    private final ObjectMapper mapper;

    /** SSE 推流线程池：Tomcat 的请求线程不能长期占着 */
    private final ExecutorService sseExecutor =
            Executors.newCachedThreadPool(r -> {
                Thread t = new Thread(r, "ai-sse");
                t.setDaemon(true);
                return t;
            });

    public record ChatReq(String message, String sessionId, List<Map<String, Object>> context) {
    }

    public record ChatRes(String reply, List<ProductDtos.ProductRes> products,
                          String sessionId, String toolUsed) {
    }

    // ====== 非流式对话 ======

    @PostMapping("/chat")
    @Transactional
    public ChatRes chat(@RequestBody ChatReq req, @CurrentUser(required = false) User user) {
        if (req == null || req.message() == null || req.message().isBlank()) {
            throw new ApiException(422, "message: 消息不能为空");
        }
        Long userId = user == null ? null : user.getId();

        List<ObjectNode> messages = toMessages(req.context());
        messages.add(llmService.userMessage(req.message()));

        LlmService.ChatResult first = llmService.chatCompletion(messages, true);

        List<Product> recommended = new ArrayList<>();
        String toolUsed = null;
        String reply;

        if (!first.toolCalls().isEmpty()) {
            for (LlmService.ToolCall tc : first.toolCalls()) {
                toolUsed = tc.name();
                JsonNode args = parseArgs(tc.arguments());
                String toolResult = toolExecutor.execute(tc.name(), args, userId);

                if (PRODUCT_TOOLS.contains(tc.name())) {
                    recommended = extractProducts(toolResult);
                }

                messages.add(llmService.assistantToolCallMessage(tc));
                messages.add(llmService.toolResultMessage(tc.id(), toolResult));
            }

            LlmService.ChatResult second = llmService.chatCompletion(messages, false);
            reply = second.content();

            if (reply == null || reply.isBlank()) {
                // 推理模型有时只吐工具指令不吐人话，用工具结果兜底组装一句
                if (!recommended.isEmpty()) {
                    String names = recommended.stream().limit(5)
                            .map(p -> p.getName() + "（¥" + p.getPrice() + "）")
                            .reduce((a, b) -> a + "、" + b).orElse("");
                    reply = "根据您的需求，为您找到以下商品推荐：" + names + "。点击商品卡片可以查看详情哦！";
                } else {
                    reply = "我理解您的需求，但暂时没有找到完全匹配的商品。您可以换个关键词试试，或者浏览我们的推荐栏目～";
                }
            } else if (first.content() != null && !first.content().isBlank()) {
                reply = first.content() + "\n\n" + reply;
            }
        } else {
            reply = first.content();
        }

        return new ChatRes(reply,
                recommended.stream().map(ProductDtos.ProductRes::from).toList(),
                req.sessionId(), toolUsed);
    }

    // ====== 流式对话 ======

    /** SSE 逐字返回。事件体与 Python 版一致：{"content": "..."}，以 [DONE] 收尾 */
    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public ResponseEntity<SseEmitter> chatStream(@RequestBody ChatReq req,
                                                 @CurrentUser(required = false) User user) {
        if (req == null || req.message() == null || req.message().isBlank()) {
            throw new ApiException(422, "message: 消息不能为空");
        }

        List<ObjectNode> messages = toMessages(req.context());
        messages.add(llmService.userMessage(req.message()));

        SseEmitter emitter = new SseEmitter(Duration.ofMinutes(5).toMillis());
        sseExecutor.execute(() -> {
            try {
                llmService.chatCompletionStream(messages, false, chunk -> {
                    try {
                        ObjectNode node = mapper.createObjectNode();
                        node.put("content", chunk);
                        emitter.send(SseEmitter.event().data(mapper.writeValueAsString(node),
                                MediaType.TEXT_PLAIN));
                    } catch (Exception e) {
                        throw new IllegalStateException(e);
                    }
                });
                emitter.send(SseEmitter.event().data("[DONE]", MediaType.TEXT_PLAIN));
                emitter.complete();
            } catch (Exception e) {
                log.warn("SSE 推流中断: {}", e.getMessage());
                emitter.completeWithError(e);
            }
        });

        return ResponseEntity.ok()
                .header("Cache-Control", "no-cache")
                .header("Connection", "keep-alive")
                .header("X-Accel-Buffering", "no")
                .contentType(new MediaType(MediaType.TEXT_EVENT_STREAM, StandardCharsets.UTF_8))
                .body(emitter);
    }

    // ====== 个性化推荐 ======

    @GetMapping("/recommendations")
    @Transactional(readOnly = true)
    public List<ProductDtos.ProductRes> recommendations(@RequestParam(defaultValue = "5") int limit,
                                                        @CurrentUser(required = false) User user) {
        if (limit < 1 || limit > 20) {
            throw new ApiException(422, "limit: 需在 1-20 之间");
        }
        Long userId = user == null ? null : user.getId();

        String cacheKey = "ai:recommendations:" + userId + ":" + limit;
        List<ProductDtos.ProductRes> cached =
                cache.get(cacheKey, new TypeReference<List<ProductDtos.ProductRes>>() {
                });
        if (cached != null) {
            return cached;
        }

        List<ProductDtos.ProductRes> result = recommendationService
                .getPersonalizedRecommendations(userId, limit).stream()
                .map(ProductDtos.ProductRes::from).toList();

        cache.set(cacheKey, result, 60);
        return result;
    }

    // ====== RAG ======

    @PostMapping("/rag/search")
    @Transactional(readOnly = true)
    public Map<String, Object> ragSearch(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> data = body == null ? Map.of() : body;
        String query = Objects.toString(data.get("query"), "");
        int topK = data.get("limit") instanceof Number n ? n.intValue() : 5;

        if (query.isBlank()) {
            throw ApiException.badRequest("查询不能为空");
        }

        List<RagService.RagHit> hits = ragService.search(query, topK);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("query", query);
        out.put("mode", "rag");
        if (hits.isEmpty()) {
            out.put("results", List.of());
            return out;
        }

        Map<Long, Product> byId = new HashMap<>();
        productRepository.findAllById(hits.stream().map(RagService.RagHit::id).toList())
                .forEach(p -> byId.put(p.getId(), p));

        List<Map<String, Object>> results = new ArrayList<>();
        for (RagService.RagHit hit : hits) {
            Product p = byId.get(hit.id());
            if (p == null) {
                continue;
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("product", ProductDtos.ProductRes.from(p));
            row.put("similarity", hit.similarity());
            row.put("matched_text", hit.document());
            results.add(row);
        }
        out.put("results", results);
        return out;
    }

    /** 手动重建向量索引（需登录，与 Python 版一致仅要求 get_current_user） */
    @PostMapping("/rag/index")
    public Map<String, Object> ragIndex(@CurrentUser User user) {
        if (!ragService.available()) {
            throw ApiException.serviceUnavailable("RAG 服务未启用");
        }
        int count = ragService.indexAll();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("message", "成功索引 " + count + " 个商品");
        out.put("count", count);
        return out;
    }

    // ====== 状态 ======

    @GetMapping("/status")
    public Map<String, Object> status() {
        Map<String, Object> out = new LinkedHashMap<>();
        boolean enabled = llmService.enabled();
        out.put("llm_enabled", enabled);
        out.put("llm_model", enabled ? llmService.model() : "未配置");
        out.put("rag_enabled", ragService.available());
        out.put("embedding_model", ragService.available() ? ragService.embeddingModelName() : "未加载");
        return out;
    }

    // ====== 内部工具 ======

    /** 把前端传来的历史消息转成 LLM 消息体，只保留最近 10 条 */
    private List<ObjectNode> toMessages(List<Map<String, Object>> context) {
        List<ObjectNode> messages = new ArrayList<>();
        if (context == null || context.isEmpty()) {
            return messages;
        }
        int from = Math.max(0, context.size() - MAX_CONTEXT);
        for (Map<String, Object> m : context.subList(from, context.size())) {
            String role = Objects.toString(m.get("role"), "user");
            String content = Objects.toString(m.get("content"), "");
            messages.add(llmService.message(role, content));
        }
        return messages;
    }

    private JsonNode parseArgs(String raw) {
        try {
            JsonNode node = mapper.readTree(raw == null || raw.isBlank() ? "{}" : raw);
            return node.isObject() ? node : mapper.createObjectNode();
        } catch (Exception e) {
            return mapper.createObjectNode();
        }
    }

    /** 从工具返回的 JSON 里抠出 id，再回查商品实体用于渲染卡片 */
    private List<Product> extractProducts(String toolResult) {
        try {
            JsonNode node = mapper.readTree(toolResult);
            if (!node.isArray()) {
                return List.of();
            }
            List<Long> ids = new ArrayList<>();
            node.forEach(n -> {
                if (n.hasNonNull("id")) {
                    ids.add(n.get("id").asLong());
                }
            });
            if (ids.isEmpty()) {
                return List.of();
            }
            // 保持工具返回的顺序（相关度/销量序），不要被数据库主键序打乱
            Map<Long, Product> byId = new HashMap<>();
            productRepository.findAllById(ids).forEach(p -> byId.put(p.getId(), p));
            return ids.stream().map(byId::get).filter(Objects::nonNull).toList();
        } catch (Exception e) {
            return List.of();
        }
    }

    /** 仅为可读性引入的小工具类型 */
    private static final class Duration {
        static java.time.Duration ofMinutes(long m) {
            return java.time.Duration.ofMinutes(m);
        }
    }
}
