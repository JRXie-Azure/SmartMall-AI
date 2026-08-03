package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.entity.Product;
import com.smartmall.entity.ProductSKU;
import com.smartmall.entity.ProductVariant;
import com.smartmall.entity.User;
import com.smartmall.repository.ProductRepository;
import com.smartmall.repository.ProductSKURepository;
import com.smartmall.repository.ProductVariantRepository;
import com.smartmall.security.CurrentUser;
import com.smartmall.security.Roles;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 商品 SKU 路由 — 规格变体管理。
 *
 * <p>对应 Python routers/sku.py。
 */
@RestController
@RequestMapping("/api/skus")
@RequiredArgsConstructor
public class SkuController {

    private final ProductRepository productRepository;
    private final ProductSKURepository skuRepository;
    private final ProductVariantRepository variantRepository;

    @GetMapping("/product/{productId}")
    @Transactional(readOnly = true)
    public Map<String, Object> getProductSkus(@PathVariable Long productId) {
        productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        List<Map<String, Object>> variants = variantRepository.findByProductId(productId).stream()
                .map(v -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", v.getId());
                    m.put("name", v.getName());
                    m.put("options", v.getOptions() == null ? List.of() : v.getOptions());
                    return m;
                })
                .toList();

        List<Map<String, Object>> skus = skuRepository.findByProductIdAndIsActiveTrue(productId).stream()
                .map(s -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", s.getId());
                    m.put("sku_code", s.getSkuCode());
                    m.put("attributes", s.getAttributes() == null ? Map.of() : s.getAttributes());
                    m.put("price", s.getPrice());
                    m.put("stock", s.getStock());
                    m.put("image", s.getImage() == null ? "" : s.getImage());
                    m.put("is_active", s.getIsActive());
                    return m;
                })
                .toList();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("variants", variants);
        result.put("skus", skus);
        return result;
    }

    @PostMapping("/product/{productId}/variants")
    @Transactional
    public Map<String, Object> createVariant(@PathVariable Long productId,
                                              @RequestBody Map<String, Object> body,
                                              @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        String name = (String) body.getOrDefault("name", "");
        if (name.isBlank()) {
            throw ApiException.badRequest("规格名不能为空");
        }

        @SuppressWarnings("unchecked")
        List<String> options = (List<String>) body.getOrDefault("options", List.of());

        ProductVariant variant = ProductVariant.builder()
                .productId(productId)
                .name(name)
                .options(new ArrayList<>(options))
                .build();
        variant = variantRepository.save(variant);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", variant.getId());
        result.put("name", variant.getName());
        result.put("options", variant.getOptions());
        result.put("created_at", variant.getCreatedAt());
        return result;
    }

    @PostMapping("/product/{productId}")
    @Transactional
    public Map<String, Object> createSku(@PathVariable Long productId,
                                         @RequestBody Map<String, Object> body,
                                         @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        String skuCode = (String) body.getOrDefault("sku_code", "");
        if (skuCode.isBlank()) {
            throw ApiException.badRequest("SKU 编码不能为空");
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> attributes = (Map<String, Object>) body.getOrDefault("attributes", Map.of());

        ProductSKU sku = ProductSKU.builder()
                .productId(productId)
                .skuCode(skuCode)
                .attributes(new LinkedHashMap<>(attributes))
                .price(body.get("price") != null ? ((Number) body.get("price")).doubleValue() : null)
                .stock(body.get("stock") != null ? ((Number) body.get("stock")).intValue() : 0)
                .image((String) body.getOrDefault("image", ""))
                .build();
        sku = skuRepository.save(sku);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", sku.getId());
        result.put("sku_code", sku.getSkuCode());
        result.put("attributes", sku.getAttributes());
        result.put("price", sku.getPrice());
        result.put("stock", sku.getStock());
        result.put("image", sku.getImage());
        result.put("is_active", sku.getIsActive());
        result.put("created_at", sku.getCreatedAt());
        return result;
    }

    @PutMapping("/{skuId}")
    @Transactional
    public Map<String, Object> updateSku(@PathVariable Long skuId,
                                         @RequestBody Map<String, Object> body,
                                         @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        ProductSKU sku = skuRepository.findById(skuId)
                .orElseThrow(() -> ApiException.notFound("SKU不存在"));

        if (body.containsKey("sku_code")) {
            sku.setSkuCode((String) body.get("sku_code"));
        }
        if (body.containsKey("attributes")) {
            @SuppressWarnings("unchecked")
            Map<String, Object> attrs = (Map<String, Object>) body.get("attributes");
            sku.setAttributes(new LinkedHashMap<>(attrs));
        }
        if (body.get("price") != null) {
            sku.setPrice(((Number) body.get("price")).doubleValue());
        }
        if (body.get("stock") != null) {
            sku.setStock(((Number) body.get("stock")).intValue());
        }
        if (body.containsKey("image")) {
            sku.setImage((String) body.get("image"));
        }
        sku = skuRepository.save(sku);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", sku.getId());
        result.put("sku_code", sku.getSkuCode());
        result.put("attributes", sku.getAttributes());
        result.put("price", sku.getPrice());
        result.put("stock", sku.getStock());
        result.put("image", sku.getImage());
        result.put("is_active", sku.getIsActive());
        return result;
    }

    @DeleteMapping("/{skuId}")
    @Transactional
    public Map<String, Object> deleteSku(@PathVariable Long skuId, @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        ProductSKU sku = skuRepository.findById(skuId)
                .orElseThrow(() -> ApiException.notFound("SKU不存在"));
        sku.setIsActive(false);
        skuRepository.save(sku);
        return Map.of("message", "SKU已下架");
    }
}
