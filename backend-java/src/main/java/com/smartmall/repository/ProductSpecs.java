package com.smartmall.repository;

import com.smartmall.entity.Product;
import jakarta.persistence.criteria.Predicate;
import org.springframework.data.jpa.domain.Specification;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * 商品动态查询条件集中处 —— 搜索 / 内容推荐 / LLM 工具调用共用，
 * 避免同一套 ilike 条件在多个 Controller 里重复实现导致口径漂移。
 */
public final class ProductSpecs {

    private ProductSpecs() {
    }

    /** 上架 + 审核通过 */
    public static Specification<Product> onSale() {
        return (root, q, cb) -> cb.and(
                cb.isTrue(root.get("isActive")),
                cb.equal(root.get("auditStatus"), "approved"));
    }

    /**
     * 关键词模糊匹配：名称 / 描述 / 品牌 / 标签。
     * tags 在库里是 JSON 文本列，Python 版用 cast(tags, Text).ilike，这里直接对文本列 like，等价。
     */
    public static Specification<Product> keywordLike(String keyword) {
        return (root, q, cb) -> {
            String kw = "%" + keyword.toLowerCase() + "%";
            return cb.or(
                    cb.like(cb.lower(root.get("name")), kw),
                    cb.like(cb.lower(root.get("description")), kw),
                    cb.like(cb.lower(root.get("brand")), kw),
                    cb.like(cb.lower(root.get("tags").as(String.class)), kw));
        };
    }

    /** 综合搜索条件：关键词 + 分类 + 价格区间 + 品牌 */
    public static Specification<Product> search(String keyword, Long categoryId,
                                                Double minPrice, Double maxPrice, String brand) {
        return (root, query, cb) -> {
            List<Predicate> ps = new ArrayList<>();
            ps.add(cb.isTrue(root.get("isActive")));
            ps.add(cb.equal(root.get("auditStatus"), "approved"));
            if (keyword != null && !keyword.isBlank()) {
                ps.add(keywordLike(keyword).toPredicate(root, query, cb));
            }
            if (categoryId != null) {
                ps.add(cb.equal(root.get("categoryId"), categoryId));
            }
            if (minPrice != null) {
                ps.add(cb.greaterThanOrEqualTo(root.get("price"), minPrice));
            }
            if (maxPrice != null) {
                ps.add(cb.lessThanOrEqualTo(root.get("price"), maxPrice));
            }
            if (brand != null && !brand.isBlank()) {
                ps.add(cb.like(cb.lower(root.get("brand")), "%" + brand.toLowerCase() + "%"));
            }
            return cb.and(ps.toArray(Predicate[]::new));
        };
    }

    /** 内容推荐候选：在售 + 有货 + 排除已浏览 +（可选）限定品牌 */
    public static Specification<Product> contentCandidates(Collection<String> brands,
                                                           Collection<Long> excludeIds) {
        return (root, query, cb) -> {
            List<Predicate> ps = new ArrayList<>();
            ps.add(cb.isTrue(root.get("isActive")));
            ps.add(cb.equal(root.get("auditStatus"), "approved"));
            ps.add(cb.greaterThan(root.get("stock"), 0));
            if (excludeIds != null && !excludeIds.isEmpty()) {
                ps.add(cb.not(root.get("id").in(excludeIds)));
            }
            if (brands != null && !brands.isEmpty()) {
                ps.add(root.get("brand").in(brands));
            }
            return cb.and(ps.toArray(Predicate[]::new));
        };
    }
}
