package com.smartmall.service;

import com.smartmall.entity.Product;
import com.smartmall.entity.ProductView;
import com.smartmall.repository.FavoriteRepository;
import com.smartmall.repository.OrderRepository;
import com.smartmall.repository.ProductRepository;
import com.smartmall.repository.ProductViewRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

/**
 * 推荐服务 —— 对应 Python 版 app/services/recommendation_service.py。
 *
 * <p>三级策略：User-Based 协同过滤 → 内容推荐（同品牌） → 热销兜底。
 * scikit-learn 的 cosine_similarity 在这里用纯 Java 手写，行为等价：
 * 余弦相似度 = 点积 / (L2 范数乘积)，零向量相似度记 0。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RecommendationService {

    /** 交互权重，与 Python 版一致：浏览 1 / 收藏 3 / 购买 5 */
    private static final double W_VIEW = 1.0;
    private static final double W_FAVORITE = 3.0;
    private static final double W_ORDER = 5.0;

    /** 参与推荐的最相似用户数 */
    private static final int TOP_SIMILAR_USERS = 5;

    /** 行为记录数少于该阈值时不做协同过滤（数据太稀疏） */
    private static final int MIN_INTERACTIONS = 5;

    private final ProductRepository productRepository;
    private final ProductViewRepository productViewRepository;
    private final FavoriteRepository favoriteRepository;
    private final OrderRepository orderRepository;

    // ====== 对外入口 ======

    /** 个性化推荐: 协同过滤 → 内容推荐 → 热销降级 */
    public List<Product> getPersonalizedRecommendations(Long userId, int limit) {
        if (userId != null) {
            List<Product> cf = collaborativeFiltering(userId, limit);
            if (!cf.isEmpty()) {
                return cf;
            }
            List<Product> content = contentBasedRecommendation(userId, limit);
            if (!content.isEmpty()) {
                return content;
            }
        }
        return hotProducts(limit);
    }

    public List<Product> hotProducts(int limit) {
        return productRepository.findHotProducts(PageRequest.of(0, Math.max(limit, 1)));
    }

    // ====== 协同过滤 ======

    /**
     * User-Based CF：
     * 1. 构建 用户×商品 交互矩阵（浏览/收藏/购买加权累加）
     * 2. 对目标用户算余弦相似度，取 top5 相似用户（排除自己）
     * 3. 推荐相似用户有过交互、而目标用户没有的商品，按 相似度 × 交互权重 排序
     */
    public List<Product> collaborativeFiltering(Long userId, int limit) {
        try {
            List<Object[]> views = productViewRepository.findAllViewTriples();
            List<Object[]> favorites = favoriteRepository.findAllFavoritePairs();
            List<Object[]> purchases = orderRepository.findAllOrderItemPairsExcludingCancelled();

            if (views.size() + favorites.size() + purchases.size() < MIN_INTERACTIONS) {
                return List.of();
            }

            // ---- 建立 用户/商品 → 矩阵下标 的映射（按 id 升序，与 Python 的 sorted() 一致） ----
            TreeSet<Long> productIdSet = new TreeSet<>();
            TreeSet<Long> userIdSet = new TreeSet<>();
            collect(views, userIdSet, productIdSet);
            collect(favorites, userIdSet, productIdSet);
            collect(purchases, userIdSet, productIdSet);

            if (productIdSet.isEmpty() || !userIdSet.contains(userId)) {
                return List.of();
            }

            List<Long> productIds = new ArrayList<>(productIdSet);
            List<Long> userIds = new ArrayList<>(userIdSet);
            Map<Long, Integer> productIdx = indexOf(productIds);
            Map<Long, Integer> userIdx = indexOf(userIds);

            double[][] matrix = new double[userIds.size()][productIds.size()];
            accumulate(matrix, views, userIdx, productIdx, W_VIEW);
            accumulate(matrix, favorites, userIdx, productIdx, W_FAVORITE);
            accumulate(matrix, purchases, userIdx, productIdx, W_ORDER);

            // ---- 相似度 ----
            int targetIdx = userIdx.get(userId);
            double[] target = matrix[targetIdx];
            double targetNorm = norm(target);

            double[] similarities = new double[matrix.length];
            for (int i = 0; i < matrix.length; i++) {
                similarities[i] = cosine(target, matrix[i], targetNorm);
            }

            // 相似度降序，跳过自己后取 top5
            Integer[] order = new Integer[similarities.length];
            for (int i = 0; i < order.length; i++) {
                order[i] = i;
            }
            Arrays.sort(order, (a, b) -> Double.compare(similarities[b], similarities[a]));

            // ---- 收集候选 ----
            Set<Integer> targetOwned = new HashSet<>();
            for (int j = 0; j < target.length; j++) {
                if (target[j] > 0) {
                    targetOwned.add(j);
                }
            }

            LinkedHashMap<Integer, Double> candidates = new LinkedHashMap<>();
            int picked = 0;
            for (int rank = 0; rank < order.length && picked < TOP_SIMILAR_USERS; rank++) {
                int idx = order[rank];
                if (idx == targetIdx) {
                    continue; // 排除自己
                }
                picked++;
                if (similarities[idx] <= 0) {
                    continue;
                }
                double[] row = matrix[idx];
                for (int j = 0; j < row.length; j++) {
                    if (row[j] > 0 && !targetOwned.contains(j) && !candidates.containsKey(j)) {
                        candidates.put(j, similarities[idx] * row[j]);
                    }
                }
            }

            if (candidates.isEmpty()) {
                return List.of();
            }

            List<Long> recommendedIds = candidates.entrySet().stream()
                    .sorted(Map.Entry.<Integer, Double>comparingByValue().reversed())
                    .limit(limit)
                    .map(e -> productIds.get(e.getKey()))
                    .toList();

            // ---- 回查商品，过滤下架/无货，并保持推荐顺序 ----
            Map<Long, Product> byId = new HashMap<>();
            for (Product p : productRepository.findAllById(recommendedIds)) {
                if (Boolean.TRUE.equals(p.getIsActive()) && p.getStock() != null && p.getStock() > 0) {
                    byId.put(p.getId(), p);
                }
            }
            return recommendedIds.stream().map(byId::get).filter(Objects::nonNull).toList();

        } catch (Exception e) {
            log.error("协同过滤异常", e);
            return List.of();
        }
    }

    // ====== 内容推荐 ======

    /** 用最近浏览过的商品品牌，找同品牌的其它在售商品 */
    public List<Product> contentBasedRecommendation(Long userId, int limit) {
        List<ProductView> recent = productViewRepository.findTop10ByUserIdOrderByUpdatedAtDesc(userId);
        if (recent.isEmpty()) {
            return List.of();
        }
        List<Long> viewedIds = recent.stream().map(ProductView::getProductId).distinct().toList();
        List<Product> viewed = productRepository.findAllById(viewedIds);
        if (viewed.isEmpty()) {
            return List.of();
        }

        Set<String> brands = new LinkedHashSet<>();
        for (Product p : viewed) {
            if (p.getBrand() != null && !p.getBrand().isBlank()) {
                brands.add(p.getBrand());
            }
        }

        var spec = com.smartmall.repository.ProductSpecs.contentCandidates(brands, viewedIds);
        return productRepository.findAll(spec,
                        PageRequest.of(0, Math.max(limit, 1),
                                org.springframework.data.domain.Sort.by(
                                        org.springframework.data.domain.Sort.Direction.DESC, "sales")))
                .getContent();
    }

    // ====== 浏览记录 ======

    /** 记录商品浏览，用于后续推荐。对应 Python 的 record_product_view */
    @Transactional
    public void recordProductView(Long userId, Long productId) {
        recordProductView(userId, productId, 0);
    }

    @Transactional
    public void recordProductView(Long userId, Long productId, int duration) {
        if (userId == null || productId == null) {
            return;
        }
        try {
            productViewRepository.findByUserIdAndProductId(userId, productId).ifPresentOrElse(
                    v -> {
                        v.setViewCount((v.getViewCount() == null ? 0 : v.getViewCount()) + 1);
                        v.setDuration((v.getDuration() == null ? 0 : v.getDuration()) + duration);
                        productViewRepository.save(v);
                    },
                    () -> productViewRepository.save(ProductView.builder()
                            .userId(userId).productId(productId)
                            .viewCount(1).duration(duration).build()));
        } catch (Exception e) {
            // 浏览记录属于旁路埋点，失败不能影响商品详情主流程
            log.warn("记录浏览失败 userId={} productId={}: {}", userId, productId, e.getMessage());
        }
    }

    // ====== 工具方法 ======

    private static void collect(List<Object[]> rows, Set<Long> users, Set<Long> products) {
        for (Object[] row : rows) {
            Long uid = toLong(row[0]);
            Long pid = toLong(row[1]);
            if (uid != null) {
                users.add(uid);
            }
            if (pid != null) {
                products.add(pid);
            }
        }
    }

    private static void accumulate(double[][] matrix, List<Object[]> rows,
                                   Map<Long, Integer> userIdx, Map<Long, Integer> productIdx,
                                   double weight) {
        for (Object[] row : rows) {
            Long uid = toLong(row[0]);
            Long pid = toLong(row[1]);
            if (uid == null || pid == null) {
                continue;
            }
            Integer i = userIdx.get(uid);
            Integer j = productIdx.get(pid);
            if (i != null && j != null) {
                matrix[i][j] += weight;
            }
        }
    }

    private static Map<Long, Integer> indexOf(List<Long> ids) {
        Map<Long, Integer> map = new HashMap<>(ids.size() * 2);
        for (int i = 0; i < ids.size(); i++) {
            map.put(ids.get(i), i);
        }
        return map;
    }

    private static double norm(double[] v) {
        double s = 0;
        for (double x : v) {
            s += x * x;
        }
        return Math.sqrt(s);
    }

    private static double cosine(double[] a, double[] b, double normA) {
        double normB = norm(b);
        if (normA == 0 || normB == 0) {
            return 0;
        }
        double dot = 0;
        for (int i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
        }
        return dot / (normA * normB);
    }

    private static Long toLong(Object o) {
        return o == null ? null : ((Number) o).longValue();
    }
}
