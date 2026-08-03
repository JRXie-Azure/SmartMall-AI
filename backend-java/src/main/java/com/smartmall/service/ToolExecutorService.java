package com.smartmall.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.smartmall.entity.Product;
import com.smartmall.repository.ProductRepository;
import com.smartmall.repository.ProductSpecs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Function Calling 工具执行器 —— 对应 Python 版 llm_service.execute_tool_call。
 *
 * <p>返回值统一是「给 LLM 看的字符串」：命中就是 JSON，未命中就是一句中文提示，
 * 与 Python 版逐字对齐，避免模型行为漂移。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ToolExecutorService {

    private final ProductRepository productRepository;
    private final RagService ragService;
    private final RecommendationService recommendationService;
    private final ObjectMapper mapper;

    @Transactional(readOnly = true)
    public String execute(String toolName, JsonNode args, Long userId) {
        try {
            return switch (toolName) {
                case "search_products" -> searchProducts(args);
                case "get_product_detail" -> getProductDetail(args);
                case "semantic_search" -> semanticSearch(args);
                case "get_recommendations" -> getRecommendations(args, userId);
                default -> "未知工具: " + toolName;
            };
        } catch (Exception e) {
            log.error("工具执行失败 tool={}", toolName, e);
            return "工具执行失败: " + e.getMessage();
        }
    }

    // ====== search_products ======

    private String searchProducts(JsonNode args) throws Exception {
        String keyword = text(args, "keyword");
        String brand = text(args, "brand");
        Double minPrice = number(args, "min_price");
        Double maxPrice = number(args, "max_price");
        String sort = args.hasNonNull("sort") ? args.get("sort").asText("sales") : "sales";
        int limit = args.hasNonNull("limit") ? args.get("limit").asInt(5) : 5;

        Specification<Product> spec = ProductSpecs.search(keyword, null, minPrice, maxPrice, brand);
        List<Product> products = productRepository
                .findAll(spec, PageRequest.of(0, Math.max(limit, 1), toolSort(sort)))
                .getContent();

        // 关键词没命中时退回热销 —— Python 版同样的兜底，保证助手不会空手而归
        if (products.isEmpty()) {
            products = productRepository.findHotProducts(PageRequest.of(0, Math.max(limit, 1)));
        }
        if (products.isEmpty()) {
            return "未找到匹配的商品。";
        }

        ArrayNode arr = mapper.createArrayNode();
        for (Product p : products) {
            ObjectNode n = arr.addObject();
            n.put("id", p.getId());
            n.put("name", p.getName());
            n.put("brand", p.getBrand());
            n.put("price", p.getPrice());
            n.put("original_price", p.getOriginalPrice());
            n.put("rating", p.getRating());
            n.put("sales", p.getSales());
            n.put("stock", p.getStock());
            n.put("description", truncate(p.getDescription(), 100));
            n.put("image", p.getImage());
        }
        return mapper.writeValueAsString(arr);
    }

    private static Sort toolSort(String sort) {
        return switch (sort == null ? "sales" : sort) {
            case "price_asc" -> Sort.by(Sort.Direction.ASC, "price");
            case "price_desc" -> Sort.by(Sort.Direction.DESC, "price");
            case "rating" -> Sort.by(Sort.Direction.DESC, "rating");
            default -> Sort.by(Sort.Direction.DESC, "sales");
        };
    }

    // ====== get_product_detail ======

    private String getProductDetail(JsonNode args) throws Exception {
        if (!args.hasNonNull("product_id")) {
            return "商品不存在。";
        }
        long pid = args.get("product_id").asLong();
        Product p = productRepository.findById(pid).orElse(null);
        if (p == null) {
            return "商品不存在。";
        }
        ObjectNode n = mapper.createObjectNode();
        n.put("id", p.getId());
        n.put("name", p.getName());
        n.put("brand", p.getBrand());
        n.put("price", p.getPrice());
        n.put("original_price", p.getOriginalPrice());
        n.put("description", p.getDescription());
        n.put("rating", p.getRating());
        n.put("sales", p.getSales());
        n.put("stock", p.getStock());
        n.put("image", p.getImage());
        n.set("tags", mapper.valueToTree(p.getTags() == null ? List.of() : p.getTags()));
        return mapper.writeValueAsString(n);
    }

    // ====== semantic_search ======

    private String semanticSearch(JsonNode args) throws Exception {
        String query = text(args, "query");
        int limit = args.hasNonNull("limit") ? args.get("limit").asInt(5) : 5;
        List<RagService.RagHit> hits = ragService.search(query == null ? "" : query, limit);
        if (hits.isEmpty()) {
            return "语义搜索未找到相关商品。";
        }
        return mapper.writeValueAsString(hits);
    }

    // ====== get_recommendations ======

    private String getRecommendations(JsonNode args, Long userId) throws Exception {
        int limit = args.hasNonNull("limit") ? args.get("limit").asInt(5) : 5;
        List<Product> products = recommendationService.getPersonalizedRecommendations(userId, limit);
        if (products.isEmpty()) {
            products = recommendationService.hotProducts(5);
        }
        ArrayNode arr = mapper.createArrayNode();
        for (Product p : products) {
            ObjectNode n = arr.addObject();
            n.put("id", p.getId());
            n.put("name", p.getName());
            n.put("brand", p.getBrand());
            n.put("price", p.getPrice());
            n.put("rating", p.getRating());
            n.put("sales", p.getSales());
            n.put("image", p.getImage());
        }
        return mapper.writeValueAsString(arr);
    }

    // ====== 小工具 ======

    private static String text(JsonNode args, String field) {
        if (args == null || !args.hasNonNull(field)) {
            return null;
        }
        String v = args.get(field).asText("");
        return v.isBlank() ? null : v;
    }

    private static Double number(JsonNode args, String field) {
        if (args == null || !args.hasNonNull(field)) {
            return null;
        }
        double v = args.get(field).asDouble(0);
        // Python 用的是 walrus 真值判断，0 会被当成「没传」，这里保持一致
        return v == 0 ? null : v;
    }

    private static String truncate(String s, int max) {
        if (s == null) {
            return "";
        }
        return s.length() > max ? s.substring(0, max) : s;
    }
}
