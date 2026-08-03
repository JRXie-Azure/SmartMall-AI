package com.smartmall.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.smartmall.config.SmartMallProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * LLM 服务 —— 对应 Python 版 app/services/llm_service.py。
 *
 * <p>走 OpenAI 兼容协议（DeepSeek 优先，回落 OpenAI），支持：
 * 普通对话、SSE 流式、Function Calling。
 * 用 JDK 内置 {@link HttpClient} 实现，不额外引入 WebClient/OkHttp。
 *
 * <p>与 Python 版一致的容错策略：任何异常都不往外抛，而是返回一句人话，
 * 保证前端聊天框永远有回复。
 */
@Slf4j
@Service
public class LlmService {

    /** 系统提示词，与 Python 版逐字一致 */
    public static final String SYSTEM_PROMPT = """
            你是 SmartMall AI 智能购物助手，服务于一个电商平台。你的职责：

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
            """;

    private static final String NOT_CONFIGURED =
            "抱歉，AI 服务尚未配置。请联系管理员设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY。";

    private final SmartMallProperties props;
    private final ObjectMapper mapper;
    private final HttpClient http;
    private final ArrayNode tools;

    public LlmService(SmartMallProperties props, ObjectMapper mapper) {
        this.props = props;
        this.mapper = mapper;
        this.http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        this.tools = buildTools(mapper);
    }

    /** 一次对话的结果：自然语言回复 + 模型请求的工具调用 */
    public record ChatResult(String content, List<ToolCall> toolCalls) {
    }

    public record ToolCall(String id, String name, String arguments) {
    }

    public boolean enabled() {
        return props.getLlm().enabled();
    }

    public String model() {
        return props.getLlm().model();
    }

    // ====== 非流式对话 ======

    public ChatResult chatCompletion(List<ObjectNode> messages, boolean useTools) {
        return chatCompletion(messages, useTools, 0.7);
    }

    public ChatResult chatCompletion(List<ObjectNode> messages, boolean useTools, double temperature) {
        if (!enabled()) {
            return new ChatResult(NOT_CONFIGURED, List.of());
        }
        try {
            ObjectNode payload = basePayload(messages, useTools, temperature, false);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(props.getLlm().baseUrl() + "/chat/completions"))
                    .timeout(Duration.ofSeconds(props.getLlm().getTimeoutSeconds()))
                    .header("Authorization", "Bearer " + props.getLlm().apiKey())
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(
                            mapper.writeValueAsString(payload), StandardCharsets.UTF_8))
                    .build();

            HttpResponse<String> resp = http.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (resp.statusCode() >= 400) {
                log.error("LLM API 错误: {} - {}", resp.statusCode(), resp.body());
                return new ChatResult("AI 服务暂时不可用 (HTTP " + resp.statusCode() + ")", List.of());
            }

            JsonNode message = mapper.readTree(resp.body()).path("choices").path(0).path("message");
            String content = message.path("content").asText("");
            // V4 推理模型偶尔把工具指令以 DSML 格式塞进 content，这类内容不能给用户看
            if (content.contains("<｜｜DSML｜｜")) {
                content = "";
            }

            List<ToolCall> calls = new ArrayList<>();
            JsonNode tc = message.path("tool_calls");
            if (tc.isArray()) {
                for (int i = 0; i < tc.size(); i++) {
                    JsonNode node = tc.get(i);
                    calls.add(new ToolCall(
                            node.path("id").asText("call_" + i),
                            node.path("function").path("name").asText(""),
                            node.path("function").path("arguments").asText("{}")));
                }
            }
            return new ChatResult(content, calls);

        } catch (Exception e) {
            log.error("LLM 调用异常", e);
            return new ChatResult("AI 服务暂时不可用，请稍后重试。", List.of());
        }
    }

    // ====== 流式对话 ======

    /**
     * SSE 流式对话，逐段把 delta.content 回调出去。
     * 调用方负责把每段包成 {@code data: {"content": "..."}} 写给前端。
     */
    public void chatCompletionStream(List<ObjectNode> messages, boolean useTools, Consumer<String> onChunk) {
        if (!enabled()) {
            onChunk.accept("抱歉，AI 服务尚未配置。请联系管理员设置 API Key。");
            return;
        }
        try {
            ObjectNode payload = basePayload(messages, useTools, 0.7, true);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(props.getLlm().baseUrl() + "/chat/completions"))
                    .timeout(Duration.ofSeconds(props.getLlm().getStreamTimeoutSeconds()))
                    .header("Authorization", "Bearer " + props.getLlm().apiKey())
                    .header("Content-Type", "application/json")
                    .header("Accept", "text/event-stream")
                    .POST(HttpRequest.BodyPublishers.ofString(
                            mapper.writeValueAsString(payload), StandardCharsets.UTF_8))
                    .build();

            HttpResponse<java.io.InputStream> resp =
                    http.send(request, HttpResponse.BodyHandlers.ofInputStream());
            if (resp.statusCode() >= 400) {
                onChunk.accept("\n[AI 服务异常: HTTP " + resp.statusCode() + "]");
                return;
            }

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(resp.body(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (!line.startsWith("data: ")) {
                        continue;
                    }
                    String data = line.substring(6);
                    if ("[DONE]".equals(data.trim())) {
                        break;
                    }
                    try {
                        String content = mapper.readTree(data)
                                .path("choices").path(0).path("delta").path("content").asText("");
                        if (!content.isEmpty()) {
                            onChunk.accept(content);
                        }
                    } catch (Exception ignored) {
                        // 单个 chunk 解析失败直接跳过，与 Python 版 continue 行为一致
                    }
                }
            }
        } catch (Exception e) {
            log.error("流式 LLM 异常", e);
            onChunk.accept("\n[AI 服务异常: " + e.getMessage() + "]");
        }
    }

    // ====== 消息构造工具 ======

    public ObjectNode userMessage(String content) {
        return message("user", content);
    }

    public ObjectNode message(String role, String content) {
        ObjectNode node = mapper.createObjectNode();
        node.put("role", role);
        node.put("content", content);
        return node;
    }

    /** assistant 消息 + 它请求的工具调用（回灌给模型时必须原样带上） */
    public ObjectNode assistantToolCallMessage(ToolCall call) {
        ObjectNode node = mapper.createObjectNode();
        node.put("role", "assistant");
        node.putNull("content");
        ArrayNode arr = node.putArray("tool_calls");
        ObjectNode tc = arr.addObject();
        tc.put("id", call.id());
        tc.put("type", "function");
        ObjectNode fn = tc.putObject("function");
        fn.put("name", call.name());
        fn.put("arguments", call.arguments());
        return node;
    }

    public ObjectNode toolResultMessage(String toolCallId, String content) {
        ObjectNode node = mapper.createObjectNode();
        node.put("role", "tool");
        node.put("tool_call_id", toolCallId);
        node.put("content", content);
        return node;
    }

    // ====== 内部 ======

    private ObjectNode basePayload(List<ObjectNode> messages, boolean useTools,
                                   double temperature, boolean stream) {
        ObjectNode payload = mapper.createObjectNode();
        payload.put("model", props.getLlm().model());
        ArrayNode arr = payload.putArray("messages");
        arr.add(message("system", SYSTEM_PROMPT));
        messages.forEach(arr::add);
        payload.put("temperature", temperature);
        payload.put("max_tokens", 4096);
        if (stream) {
            payload.put("stream", true);
        }
        if (useTools) {
            payload.set("tools", tools);
            payload.put("tool_choice", "auto");
        }
        return payload;
    }

    /** Function Calling 工具定义，与 Python 版 TOOLS 结构完全一致 */
    private static ArrayNode buildTools(ObjectMapper mapper) {
        ArrayNode tools = mapper.createArrayNode();

        ObjectNode searchParams = mapper.createObjectNode();
        searchParams.put("type", "object");
        ObjectNode sp = searchParams.putObject("properties");
        prop(sp, "keyword", "string", "搜索关键词，如'跑鞋'、'手机'");
        prop(sp, "category", "string", "商品分类，如'运动鞋'、'手机数码'");
        prop(sp, "max_price", "number", "最高价格");
        prop(sp, "min_price", "number", "最低价格");
        prop(sp, "brand", "string", "品牌，如'Nike'、'Apple'");
        ObjectNode sortProp = prop(sp, "sort", "string", "排序方式");
        ArrayNode sortEnum = sortProp.putArray("enum");
        sortEnum.add("sales").add("price_asc").add("price_desc").add("rating");
        prop(sp, "limit", "integer", "返回数量，默认5");
        tools.add(function(mapper, "search_products",
                "搜索/筛选商品。当用户想找商品、要推荐、比价、查库存时调用。", searchParams));

        ObjectNode detailParams = mapper.createObjectNode();
        detailParams.put("type", "object");
        prop(detailParams.putObject("properties"), "product_id", "integer", "商品ID");
        detailParams.putArray("required").add("product_id");
        tools.add(function(mapper, "get_product_detail",
                "获取某个商品的详细信息。当用户询问某个具体商品时调用。", detailParams));

        ObjectNode semanticParams = mapper.createObjectNode();
        semanticParams.put("type", "object");
        ObjectNode qp = semanticParams.putObject("properties");
        prop(qp, "query", "string", "自然语言查询，如'经常跑步预算800以内'");
        prop(qp, "limit", "integer", "返回数量，默认5");
        semanticParams.putArray("required").add("query");
        tools.add(function(mapper, "semantic_search",
                "语义搜索商品。当用户用自然语言描述需求时调用，如'适合跑步的轻便鞋子'。", semanticParams));

        ObjectNode recParams = mapper.createObjectNode();
        recParams.put("type", "object");
        ObjectNode rp = recParams.putObject("properties");
        prop(rp, "user_id", "integer", "用户ID，用于个性化推荐");
        prop(rp, "limit", "integer", "返回数量，默认5");
        tools.add(function(mapper, "get_recommendations",
                "获取个性化推荐商品。当用户问'有什么推荐的'时调用。", recParams));

        return tools;
    }

    private static ObjectNode function(ObjectMapper mapper, String name, String description, ObjectNode params) {
        ObjectNode tool = mapper.createObjectNode();
        tool.put("type", "function");
        ObjectNode fn = tool.putObject("function");
        fn.put("name", name);
        fn.put("description", description);
        fn.set("parameters", params);
        return tool;
    }

    private static ObjectNode prop(ObjectNode holder, String name, String type, String description) {
        ObjectNode node = holder.putObject(name);
        node.put("type", type);
        node.put("description", description);
        return node;
    }
}
