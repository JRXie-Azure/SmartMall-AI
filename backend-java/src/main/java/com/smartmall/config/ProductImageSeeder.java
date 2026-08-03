package com.smartmall.config;

import com.smartmall.entity.Product;
import com.smartmall.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Slf4j
@Component
@Order(20)
@RequiredArgsConstructor
public class ProductImageSeeder implements CommandLineRunner {

    private final ProductRepository productRepository;

    private static final Map<String, String> PRODUCT_PHOTO_IDS = new LinkedHashMap<>();
    static {
        PRODUCT_PHOTO_IDS.put("Nike Air Max 270", "1542291026-7eec264c27ff");
        PRODUCT_PHOTO_IDS.put("Adidas Ultra Boost 22", "1606107557195-0e29a4b5b4aa");
        PRODUCT_PHOTO_IDS.put("Asics Gel-Kayano 29", "1595950653106-6c9ebd614d3a");
        PRODUCT_PHOTO_IDS.put("Jordan 1 Mid", "1597045566677-8cf032ed6634");
        PRODUCT_PHOTO_IDS.put("New Balance 574", "1551107696-a4b0c5a0d9a2");
        PRODUCT_PHOTO_IDS.put("Converse Chuck 70", "1726279243973-e7323b28cf6a");
        PRODUCT_PHOTO_IDS.put("Vans Old Skool", "1560858001-2a568c6ea1d7");
        PRODUCT_PHOTO_IDS.put("Dr. Martens 1460", "1664246310534-cf20bacd75eb");
        PRODUCT_PHOTO_IDS.put("Timberland 6-Inch Premium", "1729174457163-169712f5ed12");
        PRODUCT_PHOTO_IDS.put("iPhone 15 Pro", "1710023038502-ba80a70a9f53");
        PRODUCT_PHOTO_IDS.put("AirPods Pro 2", "1572569511254-d8f925fe2cbb");
        PRODUCT_PHOTO_IDS.put("Sony WH-1000XM5", "1618366712010-f4ae9c647dcb");
        PRODUCT_PHOTO_IDS.put("iPad Air", "1561154464-82e9adf32764");
        PRODUCT_PHOTO_IDS.put("Samsung Galaxy S24 Ultra", "1707438095940-1eee18e85400");
        PRODUCT_PHOTO_IDS.put("DJI Mini 4 Pro", "1507582020474-9a35b7d455d9");
        PRODUCT_PHOTO_IDS.put("MacBook Air M3", "1611186871348-b1ce696e52c9");
        PRODUCT_PHOTO_IDS.put("Logitech MX Master 3S", "1605773527852-c546a8584ea3");
        PRODUCT_PHOTO_IDS.put("Dell XPS 13 Plus", "1593642702821-c8da6771f0c6");
        PRODUCT_PHOTO_IDS.put("Lenovo ThinkPad X1 Carbon", "1626890871138-a286af648586");
        PRODUCT_PHOTO_IDS.put("Nike Dri-FIT Tee", "1606105961732-6332674f4ee6");
        PRODUCT_PHOTO_IDS.put("Levi's 501 Original Jeans", "1542272604-787c3835535d");
        PRODUCT_PHOTO_IDS.put("Apple Watch Series 9", "1579586337278-3befd40fd17a");
        PRODUCT_PHOTO_IDS.put("Ray-Ban Aviator Classic", "1572635196237-14b3f281503f");
        PRODUCT_PHOTO_IDS.put("Fjallraven Kanken Classic", "1671628031185-8ac6a3b29ed6");
        PRODUCT_PHOTO_IDS.put("Nest Learning Thermostat", "1545259741-2ea3ebf61fa3");
        PRODUCT_PHOTO_IDS.put("Puma RS-X", "1611510338559-2f463335092c");
        PRODUCT_PHOTO_IDS.put("Li-Ning Way of Wade 10", "1605348532760-6753d2c43329");
        PRODUCT_PHOTO_IDS.put("Under Armour HOVR Phantom", "1483721310020-03333e577078");
        PRODUCT_PHOTO_IDS.put("Saucony Endorphin Speed", "1560769629-975ec94e6a86");
        PRODUCT_PHOTO_IDS.put("Clarks Wallabee", "1525966222134-fcfa99b8ae77");
        PRODUCT_PHOTO_IDS.put("Xiaomi 14", "1511707171634-5f897ff02aa9");
        PRODUCT_PHOTO_IDS.put("Huawei Mate 60 Pro", "1592899677977-9c10ca588bbd");
        PRODUCT_PHOTO_IDS.put("ASUS ROG Strix G16", "1588872657578-7efd1f1555ed");
        PRODUCT_PHOTO_IDS.put("Keychron K8 Pro", "1614680376573-df3480f0c6ff");
        PRODUCT_PHOTO_IDS.put("Uniqlo Down Jacket", "1578587018452-892bacefd3f2");
        PRODUCT_PHOTO_IDS.put("Adidas Track Jacket", "1591047139829-d91aecb6caea");
        PRODUCT_PHOTO_IDS.put("Zara Wool Overshirt", "1620799140408-edc6dcb6d633");
        PRODUCT_PHOTO_IDS.put("Garmin Forerunner 265", "1523275335684-37898b6baf30");
        PRODUCT_PHOTO_IDS.put("Herschel Little America", "1553062407-98eeb64c6a62");
        PRODUCT_PHOTO_IDS.put("Dyson V15 Detect", "1581091226825-a6a2a5aee158");
        PRODUCT_PHOTO_IDS.put("Philips Hue Starter Kit", "1585771724684-38269d6639fd");
        PRODUCT_PHOTO_IDS.put("Xiaomi Air Purifier 4 Pro", "1581091226825-a6a2a5aee158");
        // Beauty products - use same photo for all three
        PRODUCT_PHOTO_IDS.put("La Mer Creme de la Mer", "1599305090598-fe179d501227");
        PRODUCT_PHOTO_IDS.put("SK-II Facial Treatment Essence", "1599305090598-fe179d501227");
        PRODUCT_PHOTO_IDS.put("Estee Lauder Advanced Night Repair", "1599305090598-fe179d501227");
        // Mojibake variants (UTF-8 bytes read as Latin-1 in H2 migration)
        PRODUCT_PHOTO_IDS.put("La Mer Cr\u00C3\u00A8me de la Mer", "1599305090598-fe179d501227");
        PRODUCT_PHOTO_IDS.put("Est\u00C3\u00A9e Lauder Advanced Night Repair", "1599305090598-fe179d501227");
    }

    private static final Map<Long, String> CAT_COLORS = new HashMap<>();
    static {
        CAT_COLORS.put(1L, "2563EB");
        CAT_COLORS.put(2L, "0D9488");
        CAT_COLORS.put(3L, "7C3AED");
        CAT_COLORS.put(4L, "4F46E5");
        CAT_COLORS.put(5L, "DB2777");
        CAT_COLORS.put(6L, "D97706");
        CAT_COLORS.put(7L, "16A34A");
        CAT_COLORS.put(8L, "E11D48");
    }

    @Override
    @Transactional
    public void run(String... args) {
        List<Product> products = productRepository.findAll();
        if (products.isEmpty()) {
            log.info("No products found, skipping image seed");
            return;
        }

        int updated = 0;
        for (Product p : products) {
            String expectedImage = productImageUrl(p.getName(), p.getBrand(), p.getCategoryId());
            if (!expectedImage.equals(p.getImage())) {
                p.setImage(expectedImage);
                p.setImages(List.of(expectedImage, expectedImage, expectedImage));
                updated++;
            }
        }

        if (updated > 0) {
            productRepository.saveAll(products);
            log.info("Updated image URLs for {} products (total: {})", updated, products.size());
        } else {
            log.info("All {} product image URLs already correct", products.size());
        }
    }

    private String productImageUrl(String name, String brand, Long catId) {
        if (name == null) name = "";
        if (brand == null) brand = "";

        // 1. Exact match
        String photoId = PRODUCT_PHOTO_IDS.get(name);
        if (photoId != null) {
            return "https://images.unsplash.com/photo-" + photoId + "?w=400&h=400&fit=crop&q=80";
        }

        // 2. Normalized match - strip non-ASCII chars to handle mojibake in DB
        String normalized = normalize(name);
        if (!normalized.isEmpty()) {
            for (Map.Entry<String, String> entry : PRODUCT_PHOTO_IDS.entrySet()) {
                if (normalize(entry.getKey()).equals(normalized)) {
                    return "https://images.unsplash.com/photo-" + entry.getValue() + "?w=400&h=400&fit=crop&q=80";
                }
            }
        }

        // 3. Fallback: local placeholder with brand + name
        String color = CAT_COLORS.getOrDefault(catId, "6366F1");
        String text = brand.isEmpty() ? name : brand + " " + name;
        String encoded = URLEncoder.encode(text, StandardCharsets.UTF_8);
        return "/api/placeholder/" + color + "/" + encoded;
    }

    /** Strip non-ASCII characters and lowercase for fuzzy matching */
    private String normalize(String s) {
        if (s == null) return "";
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            if (c < 128) sb.append(Character.toLowerCase(c));
        }
        return sb.toString();
    }
}
