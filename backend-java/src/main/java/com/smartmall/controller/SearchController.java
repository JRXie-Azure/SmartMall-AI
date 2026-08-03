package com.smartmall.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.smartmall.common.ApiException;
import com.smartmall.common.CacheService;
import com.smartmall.dto.ProductDtos;
import com.smartmall.entity.Product;
import com.smartmall.entity.SearchHistory;
import com.smartmall.entity.User;
import com.smartmall.repository.ProductRepository;
import com.smartmall.repository.ProductSpecs;
import com.smartmall.repository.SearchHistoryRepository;
import com.smartmall.security.CurrentUser;
import com.smartmall.service.RagService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/** 搜索接口，对应 routers/search.py */
@RestController
@RequestMapping("/api/search")
@RequiredArgsConstructor
public class SearchController {

    private final ProductRepository productRepository;
    private final SearchHistoryRepository searchHistoryRepository;
    private final RagService ragService;
    private final CacheService cache;

    // ====== 综合搜索 ======

    /**
     * 关键词 + 筛选 + 排序。
     * sort: relevance(默认) / price_asc / price_desc / sales / rating / newest
     */
    @GetMapping({"", "/"})
    @Transactional
    public ProductDtos.ProductListRes search(
            @RequestParam String keyword,
            @RequestParam(name = "category_id", required = false) Long categoryId,
            @RequestParam(name = "min_price", required = false) Double minPrice,
            @RequestParam(name = "max_price", required = false) Double maxPrice,
            @RequestParam(required = false) String brand,
            @RequestParam(defaultValue = "relevance") String sort,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(name = "page_size", defaultValue = "20") int pageSize,
            @CurrentUser(required = false) User user) {

        if (keyword == null || keyword.isEmpty()) {
            throw new ApiException(422, "keyword: 关键词不能为空");
        }
        if (page < 1) throw new ApiException(422, "page: 必须 >= 1");
        if (pageSize < 1 || pageSize > 100) throw new ApiException(422, "page_size: 需在 1-100 之间");

        // 登录用户才记录搜索历史（匿名搜索不入库，与 Python 版一致）
        if (user != null) {
            searchHistoryRepository.save(SearchHistory.builder()
                    .userId(user.getId()).keyword(keyword).build());
        }

        var spec = ProductSpecs.search(keyword, categoryId, minPrice, maxPrice, brand);
        var result = productRepository.findAll(spec,
                PageRequest.of(page - 1, pageSize, searchSort(sort)));

        return new ProductDtos.ProductListRes(
                result.getContent().stream().map(ProductDtos.ProductRes::from).toList(),
                result.getTotalElements(), page, pageSize);
    }

    /** relevance = 销量优先、评分次之，这是 Python 版对「相关度」的定义 */
    private static Sort searchSort(String sort) {
        // 同 ProductController.sortOf：补 id ASC 兜底以对齐 SQLite 的 rowid 隐式顺序
        Sort tieBreak = Sort.by(Sort.Direction.ASC, "id");
        return switch (sort == null ? "relevance" : sort) {
            case "price_asc" -> Sort.by(Sort.Direction.ASC, "price").and(tieBreak);
            case "price_desc" -> Sort.by(Sort.Direction.DESC, "price").and(tieBreak);
            case "sales" -> Sort.by(Sort.Direction.DESC, "sales").and(tieBreak);
            case "rating" -> Sort.by(Sort.Direction.DESC, "rating").and(tieBreak);
            case "newest" -> Sort.by(Sort.Direction.DESC, "createdAt").and(tieBreak);
            default -> Sort.by(Sort.Direction.DESC, "sales")
                    .and(Sort.by(Sort.Direction.DESC, "rating")).and(tieBreak);
        };
    }

    // ====== 语义搜索 ======

    /** 自然语言 → TF-IDF 向量检索。示例: {"query": "适合户外跑步的轻便鞋子"} */
    @PostMapping("/semantic")
    public Map<String, Object> semanticSearch(@RequestBody(required = false) Map<String, Object> body) {
        Map<String, Object> data = body == null ? Map.of() : body;
        String query = Objects.toString(data.get("query"), "").trim();
        int limit = intOf(data.get("limit"), 10);

        if (query.isEmpty()) {
            throw ApiException.badRequest("查询不能为空");
        }

        List<RagService.RagHit> hits = ragService.search(query, limit);
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

    // ====== 联想 / 热搜 / 品牌 ======

    /** 搜索建议：商品名 + 品牌 + 历史热词 */
    @GetMapping("/suggestions")
    public Map<String, Object> suggestions(@RequestParam String keyword) {
        if (keyword == null || keyword.isEmpty()) {
            throw new ApiException(422, "keyword: 关键词不能为空");
        }
        String cacheKey = "search:suggest:" + keyword;
        Map<String, Object> cached = cache.get(cacheKey, new TypeReference<Map<String, Object>>() {
        });
        if (cached != null) {
            return cached;
        }

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("products", productRepository.findNamesContaining(keyword, PageRequest.of(0, 8)));
        out.put("brands", productRepository.findBrandsContaining(keyword, PageRequest.of(0, 5)));
        out.put("hot_keywords", searchHistoryRepository.findKeywordsContaining(keyword, PageRequest.of(0, 5)));

        cache.set(cacheKey, out, 120);
        return out;
    }

    /** 热门搜索词 TOP 10 */
    @GetMapping("/hot")
    public List<Map<String, Object>> hotSearches() {
        return searchHistoryRepository.findHotKeywords(PageRequest.of(0, 10)).stream()
                .map(row -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("keyword", row[0]);
                    m.put("count", ((Number) row[1]).longValue());
                    return m;
                })
                .toList();
    }

    /** 全部品牌 + 商品数，用于筛选侧栏 */
    @GetMapping("/brands")
    public List<Map<String, Object>> listBrands() {
        return productRepository.countGroupByBrand().stream()
                .map(row -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("name", row[0]);
                    m.put("count", ((Number) row[1]).longValue());
                    return m;
                })
                .toList();
    }

    private static int intOf(Object v, int def) {
        if (v instanceof Number n) {
            return n.intValue();
        }
        if (v instanceof String s && !s.isBlank()) {
            try {
                return Integer.parseInt(s.trim());
            } catch (NumberFormatException ignored) {
                return def;
            }
        }
        return def;
    }
}
