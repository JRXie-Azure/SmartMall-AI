package com.smartmall.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.smartmall.common.ApiException;
import com.smartmall.common.CacheService;
import com.smartmall.dto.ProductDtos;
import com.smartmall.entity.*;
import com.smartmall.repository.*;
import com.smartmall.security.CurrentUser;
import com.smartmall.service.RecommendationService;
import jakarta.persistence.criteria.Predicate;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 商品接口，对应 routers/products.py（含分类/评价/收藏） */
@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductRepository productRepository;
    private final CategoryRepository categoryRepository;
    private final ReviewRepository reviewRepository;
    private final FavoriteRepository favoriteRepository;
    private final UserRepository userRepository;
    private final RecommendationService recommendationService;
    private final CacheService cache;

    // ====== 分类 ======

    /** 必须声明在 /{productId} 之前，否则 "categories" 会被当成 id 匹配 */
    @GetMapping("/categories")
    public List<ProductDtos.CategoryRes> listCategories() {
        String key = "products:categories";
        List<ProductDtos.CategoryRes> cached =
                cache.get(key, new TypeReference<List<ProductDtos.CategoryRes>>() {
                });
        if (cached != null) {
            return cached;
        }
        List<ProductDtos.CategoryRes> result = categoryRepository.findAllByOrderBySortOrderAsc()
                .stream().map(ProductDtos.CategoryRes::from).toList();
        cache.set(key, result, 600);
        return result;
    }

    // ====== 列表 ======

    @GetMapping({"", "/"})
    public ProductDtos.ProductListRes listProducts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(name = "page_size", defaultValue = "20") int pageSize,
            @RequestParam(name = "category_id", required = false) Long categoryId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String brand,
            @RequestParam(defaultValue = "default") String sort) {

        if (page < 1) throw ApiException.badRequest("page 必须 >= 1");
        if (pageSize < 1 || pageSize > 100) throw ApiException.badRequest("page_size 需在 1-100 之间");

        Specification<Product> spec = (root, query, cb) -> {
            List<Predicate> ps = new ArrayList<>();
            ps.add(cb.isTrue(root.get("isActive")));
            ps.add(cb.equal(root.get("auditStatus"), "approved"));
            if (categoryId != null) {
                ps.add(cb.equal(root.get("categoryId"), categoryId));
            }
            if (keyword != null && !keyword.isBlank()) {
                ps.add(cb.like(cb.lower(root.get("name")), "%" + keyword.toLowerCase() + "%"));
            }
            if (brand != null && !brand.isBlank()) {
                ps.add(cb.like(cb.lower(root.get("brand")), "%" + brand.toLowerCase() + "%"));
            }
            return cb.and(ps.toArray(Predicate[]::new));
        };

        var pageResult = productRepository.findAll(spec,
                PageRequest.of(page - 1, pageSize, sortOf(sort)));

        return new ProductDtos.ProductListRes(
                pageResult.getContent().stream().map(ProductDtos.ProductRes::from).toList(),
                pageResult.getTotalElements(), page, pageSize);
    }

    static Sort sortOf(String sort) {
        // 追加 id ASC 作为稳定 tie-break：SQLite 在排序键相同时按 rowid(=id) 升序返回，
        // H2/MySQL 无此隐式保证，不显式兜底会导致同价/同销量/同创建时间的商品顺序与 Python 版不一致。
        Sort tieBreak = Sort.by(Sort.Direction.ASC, "id");
        return switch (sort == null ? "default" : sort) {
            case "price_asc" -> Sort.by(Sort.Direction.ASC, "price").and(tieBreak);
            case "price_desc" -> Sort.by(Sort.Direction.DESC, "price").and(tieBreak);
            case "sales" -> Sort.by(Sort.Direction.DESC, "sales").and(tieBreak);
            case "rating" -> Sort.by(Sort.Direction.DESC, "rating").and(tieBreak);
            // newest 与 default 同义，Python 版即如此
            default -> Sort.by(Sort.Direction.DESC, "createdAt").and(tieBreak);
        };
    }

    // ====== 详情 ======

    @GetMapping("/{productId}")
    public ProductDtos.ProductRes getProduct(@PathVariable Long productId,
                                             @CurrentUser(required = false) User user) {
        String key = "products:detail:" + productId;
        ProductDtos.ProductRes cached = cache.get(key, new TypeReference<ProductDtos.ProductRes>() {
        });
        if (cached != null) {
            if (user != null) {
                recommendationService.recordProductView(user.getId(), productId);
            }
            return cached;
        }

        Product product = productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        ProductDtos.ProductRes result = ProductDtos.ProductRes.from(product);
        cache.set(key, result, 300);

        if (user != null) {
            recommendationService.recordProductView(user.getId(), productId);
        }
        return result;
    }

    // ====== 评价 ======

    @GetMapping("/{productId}/reviews")
    public List<ProductDtos.ReviewRes> getProductReviews(@PathVariable Long productId) {
        List<Review> reviews = reviewRepository.findByProductIdOrderByCreatedAtDescIdAsc(productId);
        List<ProductDtos.ReviewRes> out = new ArrayList<>(reviews.size());
        for (Review r : reviews) {
            String username = Boolean.TRUE.equals(r.getIsAnonymous())
                    ? "匿名用户"
                    : userRepository.findById(r.getUserId()).map(User::getUsername).orElse("未知用户");
            out.add(toReviewRes(r, username));
        }
        return out;
    }

    @PostMapping("/{productId}/reviews")
    @Transactional
    public ProductDtos.ReviewRes createReview(@PathVariable Long productId,
                                              @Valid @RequestBody ProductDtos.ReviewCreateReq req,
                                              @CurrentUser User user) {
        if (req.rating() == null || req.rating() < 1 || req.rating() > 5) {
            throw new ApiException(422, "rating: 评分需在 1-5 之间");
        }
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        Review review = Review.builder()
                .userId(user.getId())
                .productId(productId)
                .orderId(req.orderId())
                .rating(req.rating())
                .content(req.content())
                .images(new ArrayList<>(req.images()))
                .isAnonymous(req.isAnonymous())
                .build();
        review = reviewRepository.save(review);

        // 重算商品平均分（含刚写入的这条），保留 1 位小数 —— 与 Python 版口径一致
        List<Review> all = reviewRepository.findByProductId(productId);
        double sum = all.stream().mapToInt(Review::getRating).sum();
        product.setRating(Math.round(sum / all.size() * 10.0) / 10.0);
        productRepository.save(product);
        cache.deletePattern("products:*");

        String username = Boolean.TRUE.equals(review.getIsAnonymous()) ? "匿名用户" : user.getUsername();
        return toReviewRes(review, username);
    }

    private static ProductDtos.ReviewRes toReviewRes(Review r, String username) {
        return new ProductDtos.ReviewRes(
                r.getId(), r.getUserId(), r.getProductId(), r.getRating(),
                r.getContent() == null ? "" : r.getContent(),
                r.getImages() == null ? List.of() : r.getImages(),
                Boolean.TRUE.equals(r.getIsAnonymous()),
                r.getCreatedAt(), username);
    }

    // ====== 收藏 ======

    @GetMapping("/{productId}/favorite")
    public Map<String, Object> checkFavorite(@PathVariable Long productId, @CurrentUser User user) {
        boolean fav = favoriteRepository.findByUserIdAndProductId(user.getId(), productId).isPresent();
        return Map.of("is_favorite", fav);
    }

    @PostMapping("/{productId}/favorite")
    @Transactional
    public Map<String, Object> toggleFavorite(@PathVariable Long productId, @CurrentUser User user) {
        productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        var existing = favoriteRepository.findByUserIdAndProductId(user.getId(), productId);
        Map<String, Object> body = new LinkedHashMap<>();
        if (existing.isPresent()) {
            favoriteRepository.delete(existing.get());
            body.put("is_favorite", false);
            body.put("message", "已取消收藏");
        } else {
            favoriteRepository.save(Favorite.builder()
                    .userId(user.getId()).productId(productId).build());
            body.put("is_favorite", true);
            body.put("message", "已收藏");
        }
        return body;
    }
}
