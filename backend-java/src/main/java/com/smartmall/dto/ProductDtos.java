package com.smartmall.dto;

import com.smartmall.entity.Category;
import com.smartmall.entity.Product;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

import java.time.LocalDateTime;
import java.util.List;

/** 商品/分类相关 DTO */
public final class ProductDtos {

    private ProductDtos() {
    }

    public record CategoryRes(Long id, String name, String icon, Integer sortOrder, LocalDateTime createdAt) {

        public static CategoryRes from(Category c) {
            return new CategoryRes(c.getId(), c.getName(),
                    c.getIcon() == null ? "" : c.getIcon(),
                    c.getSortOrder() == null ? 0 : c.getSortOrder(),
                    c.getCreatedAt());
        }
    }

    public record CategoryCreateReq(@NotBlank(message = "分类名不能为空") String name,
                                    String icon, Integer sortOrder) {
        public CategoryCreateReq {
            if (icon == null) icon = "";
            if (sortOrder == null) sortOrder = 0;
        }
    }

    public record ProductRes(
            Long id, String name, String description, Double price, Double originalPrice,
            String image, List<String> images, Integer stock, Integer sales,
            Long categoryId, List<String> tags, String brand, Double rating,
            Boolean isRecommend, Boolean isNew, Boolean isSale, Boolean isActive,
            String auditStatus, LocalDateTime createdAt
            // 刻意不输出 updated_at：实体虽有该列，但 Python 版 ProductResponse schema
            // 未声明它，所有商品接口的 JSON 里都没有这个 key，加上会破坏字段集一致性
    ) {
        public static ProductRes from(Product p) {
            return new ProductRes(
                    p.getId(), p.getName(),
                    p.getDescription() == null ? "" : p.getDescription(),
                    p.getPrice(), p.getOriginalPrice(),
                    p.getImage() == null ? "" : p.getImage(),
                    p.getImages() == null ? List.of() : p.getImages(),
                    p.getStock() == null ? 0 : p.getStock(),
                    p.getSales() == null ? 0 : p.getSales(),
                    p.getCategoryId(),
                    p.getTags() == null ? List.of() : p.getTags(),
                    p.getBrand() == null ? "" : p.getBrand(),
                    p.getRating() == null ? 5.0 : p.getRating(),
                    Boolean.TRUE.equals(p.getIsRecommend()),
                    Boolean.TRUE.equals(p.getIsNew()),
                    Boolean.TRUE.equals(p.getIsSale()),
                    !Boolean.FALSE.equals(p.getIsActive()),
                    p.getAuditStatus() == null ? "approved" : p.getAuditStatus(),
                    p.getCreatedAt());
        }
    }

    public record ProductListRes(List<ProductRes> items, long total, int page, int pageSize) {
    }

    /**
     * 管理后台商品视图 —— 比 {@link ProductRes} 多一个 updated_at。
     *
     * <p>差异不是疏漏：Python 的 /api/admin/products 直接把 SQLAlchemy 实体丢给 FastAPI 序列化
     * （没有 response_model），于是输出了表里的每一列；而面向 C 端的接口都声明了
     * ProductResponse schema，该 schema 里没有 updated_at。两套视图必须分开，
     * 否则不是 admin 少字段就是 C 端多字段。
     */
    public record AdminProductRes(
            Long id, String name, String description, Double price, Double originalPrice,
            String image, List<String> images, Integer stock, Integer sales,
            Long categoryId, List<String> tags, String brand, Double rating,
            Boolean isRecommend, Boolean isNew, Boolean isSale, Boolean isActive,
            String auditStatus, LocalDateTime createdAt, LocalDateTime updatedAt
    ) {
        public static AdminProductRes from(Product p) {
            ProductRes base = ProductRes.from(p);
            return new AdminProductRes(
                    base.id(), base.name(), base.description(), base.price(), base.originalPrice(),
                    base.image(), base.images(), base.stock(), base.sales(),
                    base.categoryId(), base.tags(), base.brand(), base.rating(),
                    base.isRecommend(), base.isNew(), base.isSale(), base.isActive(),
                    base.auditStatus(), base.createdAt(),
                    p.getUpdatedAt());
        }
    }

    public record ProductCreateReq(
            @NotBlank(message = "商品名不能为空") String name,
            String description,
            @Positive(message = "价格必须大于 0") Double price,
            Double originalPrice, String image, List<String> images, String brand,
            Integer stock, Long categoryId, List<String> tags,
            Boolean isRecommend, Boolean isNew, Boolean isSale
    ) {
        public ProductCreateReq {
            if (description == null) description = "";
            if (image == null) image = "";
            if (images == null) images = List.of();
            if (brand == null) brand = "";
            if (stock == null) stock = 0;
            if (tags == null) tags = List.of();
            if (isRecommend == null) isRecommend = false;
            if (isNew == null) isNew = false;
            if (isSale == null) isSale = false;
        }
    }

    /** 全部可选，null 表示不修改 —— 对应 Pydantic 的 Optional[...] = None */
    public record ProductUpdateReq(
            String name, String description, Double price, Double originalPrice,
            String image, List<String> images, String brand, Integer stock,
            Long categoryId, List<String> tags,
            Boolean isRecommend, Boolean isNew, Boolean isSale, Boolean isActive,
            String auditStatus
    ) {
    }

    public record ProductAuditReq(String auditStatus, String reason) {
    }

    public record ReviewCreateReq(Long productId, Long orderId, Integer rating,
                                  String content, List<String> images, Boolean isAnonymous) {
        public ReviewCreateReq {
            if (content == null) content = "";
            if (images == null) images = List.of();
            if (isAnonymous == null) isAnonymous = false;
        }
    }

    public record ReviewRes(Long id, Long userId, Long productId, Integer rating,
                            String content, List<String> images, Boolean isAnonymous,
                            LocalDateTime createdAt, String username) {
    }

    public record FavoriteRes(Long id, Long productId, ProductRes product, LocalDateTime createdAt) {
    }
}
