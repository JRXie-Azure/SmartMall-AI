package com.smartmall.service;

import com.smartmall.entity.Category;
import com.smartmall.entity.Product;
import com.smartmall.repository.CategoryRepository;
import com.smartmall.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.concurrent.locks.ReentrantLock;

/**
 * RAG 语义检索服务 —— 对应 Python 版 app/services/rag_service.py。
 *
 * <p>Python 侧用的是 scikit-learn 的
 * {@code TfidfVectorizer(analyzer="char_wb", ngram_range=(1,2), min_df=1, max_features=10000)}
 * + {@code cosine_similarity}。Java 这边不引入任何机器学习依赖，直接手写等价实现：
 *
 * <ul>
 *   <li>分词：char_wb —— 先按空白切词，每个词两侧补空格后取 1~2 字符 n-gram（中文友好）</li>
 *   <li>权重：tf × idf，其中 idf = ln((1 + N) / (1 + df)) + 1（smooth_idf=True）</li>
 *   <li>归一化：每行 L2 归一化，于是余弦相似度退化为点积</li>
 * </ul>
 *
 * <p>矩阵按稀疏行存储（索引数组 + 值数组），几千个商品的规模下内存和耗时都可忽略。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RagService {

    private static final int NGRAM_MIN = 1;
    private static final int NGRAM_MAX = 2;
    private static final int MAX_FEATURES = 10000;
    /** 返回给 LLM 的匹配片段长度，与 Python 的 doc[:200] 一致 */
    private static final int DOC_SNIPPET_LEN = 200;

    private final ProductRepository productRepository;
    private final CategoryRepository categoryRepository;

    private final ReentrantLock lock = new ReentrantLock();

    private volatile Index index = null;

    /** 检索结果一条记录，字段与 Python 版 rag_search 返回的 dict 一一对应 */
    public record RagHit(Long id, String name, String brand, Double price,
                         String category, double similarity, String document) {
    }

    /** 不可变索引快照，重建时整体替换，读侧无需加锁 */
    private record Index(Map<String, Integer> vocabulary,
                         double[] idf,
                         List<Long> productIds,
                         List<String> docs,
                         List<Product> products,
                         List<String> categories,
                         int[][] rowIndices,
                         double[][] rowValues) {
    }

    // ====== 对外接口 ======

    /** Java 版内置 TF-IDF 实现，无外部依赖，始终可用 */
    public boolean available() {
        return true;
    }

    public String embeddingModelName() {
        return "TF-IDF (char_wb 1-2gram, 内置实现)";
    }

    /** 商品发生增删改后调用，下次检索时惰性重建 */
    public void markStale() {
        index = null;
    }

    /** 手动全量重建索引，返回索引到的商品数 */
    @Transactional(readOnly = true)
    public int indexAll() {
        Index built = build();
        index = built;
        return built.productIds().size();
    }

    /**
     * 语义检索。返回按相似度降序的 top_k 命中（相似度 &lt;= 0 的会被丢弃）。
     *
     * <p>注意与 Python 完全一致的一个细节：先取 top_k 再过滤 0 分，
     * 因此结果条数可能少于 top_k，而不是「补齐到 top_k」。
     */
    @Transactional(readOnly = true)
    public List<RagHit> search(String query, int topK) {
        if (query == null || query.isBlank() || topK <= 0) {
            return List.of();
        }
        Index idx = ensureIndexed();
        if (idx == null || idx.productIds().isEmpty()) {
            return List.of();
        }

        double[] queryVec = transform(query, idx);
        if (queryVec == null) {
            return List.of();
        }

        int n = idx.productIds().size();
        double[] sims = new double[n];
        for (int i = 0; i < n; i++) {
            sims[i] = dot(idx.rowIndices()[i], idx.rowValues()[i], queryVec);
        }

        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        Arrays.sort(order, (a, b) -> Double.compare(sims[b], sims[a]));

        List<RagHit> hits = new ArrayList<>();
        for (int rank = 0; rank < Math.min(topK, n); rank++) {
            int i = order[rank];
            if (sims[i] <= 0) {
                continue;
            }
            Product p = idx.products().get(i);
            String doc = idx.docs().get(i);
            hits.add(new RagHit(
                    p.getId(), p.getName(), p.getBrand(), p.getPrice(),
                    idx.categories().get(i),
                    Math.round(sims[i] * 10000.0) / 10000.0,
                    doc.length() > DOC_SNIPPET_LEN ? doc.substring(0, DOC_SNIPPET_LEN) : doc));
        }
        return hits;
    }

    // ====== 索引构建 ======

    private Index ensureIndexed() {
        Index current = index;
        if (current != null) {
            return current;
        }
        lock.lock();
        try {
            if (index == null) {
                index = build();
            }
            return index;
        } finally {
            lock.unlock();
        }
    }

    /**
     * 构建索引。取所有 is_active 商品（与 Python 一致 —— 这里刻意不过滤 audit_status）。
     */
    private Index build() {
        List<Product> products = productRepository.findAllIndexable();
        Map<Long, String> categoryNames = new HashMap<>();
        for (Category c : categoryRepository.findAll()) {
            categoryNames.put(c.getId(), c.getName());
        }

        List<Long> ids = new ArrayList<>(products.size());
        List<String> docs = new ArrayList<>(products.size());
        List<String> cats = new ArrayList<>(products.size());
        for (Product p : products) {
            String cat = p.getCategoryId() == null ? "" : categoryNames.getOrDefault(p.getCategoryId(), "");
            ids.add(p.getId());
            cats.add(cat);
            docs.add(buildDoc(p.getName(), p.getDescription(), p.getBrand(), cat, p.getTags()));
        }

        if (docs.isEmpty()) {
            log.warn("没有商品可索引");
            return new Index(Map.of(), new double[0], List.of(), List.of(), List.of(), List.of(),
                    new int[0][], new double[0][]);
        }

        // ---- 1. 统计词频 ----
        List<Map<String, Integer>> counts = new ArrayList<>(docs.size());
        Map<String, Integer> totalTf = new HashMap<>();
        Map<String, Integer> df = new HashMap<>();
        for (String doc : docs) {
            Map<String, Integer> c = new HashMap<>();
            for (String gram : charWbNgrams(doc)) {
                c.merge(gram, 1, Integer::sum);
            }
            counts.add(c);
            for (Map.Entry<String, Integer> e : c.entrySet()) {
                totalTf.merge(e.getKey(), e.getValue(), Integer::sum);
                df.merge(e.getKey(), 1, Integer::sum);
            }
        }

        // ---- 2. max_features：按全局词频取 Top N（与 sklearn _limit_features 同策略） ----
        List<String> terms;
        if (totalTf.size() > MAX_FEATURES) {
            terms = totalTf.entrySet().stream()
                    .sorted(Comparator.<Map.Entry<String, Integer>>comparingInt(Map.Entry::getValue)
                            .reversed()
                            .thenComparing(Map.Entry::getKey))
                    .limit(MAX_FEATURES)
                    .map(Map.Entry::getKey)
                    .sorted()
                    .toList();
        } else {
            terms = totalTf.keySet().stream().sorted().toList();
        }

        Map<String, Integer> vocabulary = new HashMap<>(terms.size() * 2);
        for (int i = 0; i < terms.size(); i++) {
            vocabulary.put(terms.get(i), i);
        }

        // ---- 3. idf = ln((1+N)/(1+df)) + 1 ----
        int nDocs = docs.size();
        double[] idf = new double[terms.size()];
        for (int i = 0; i < terms.size(); i++) {
            idf[i] = Math.log((1.0 + nDocs) / (1.0 + df.get(terms.get(i)))) + 1.0;
        }

        // ---- 4. tf-idf + L2 归一化，稀疏存储 ----
        int[][] rowIndices = new int[nDocs][];
        double[][] rowValues = new double[nDocs][];
        for (int r = 0; r < nDocs; r++) {
            Map<String, Integer> c = counts.get(r);
            List<int[]> tmpIdx = new ArrayList<>(c.size());
            List<Double> tmpVal = new ArrayList<>(c.size());
            for (Map.Entry<String, Integer> e : c.entrySet()) {
                Integer col = vocabulary.get(e.getKey());
                if (col == null) {
                    continue; // 被 max_features 裁掉
                }
                tmpIdx.add(new int[]{col});
                tmpVal.add(e.getValue() * idf[col]);
            }
            double norm = 0;
            for (double v : tmpVal) {
                norm += v * v;
            }
            norm = Math.sqrt(norm);

            int[] cols = new int[tmpIdx.size()];
            double[] vals = new double[tmpVal.size()];
            for (int k = 0; k < cols.length; k++) {
                cols[k] = tmpIdx.get(k)[0];
                vals[k] = norm == 0 ? 0 : tmpVal.get(k) / norm;
            }
            rowIndices[r] = cols;
            rowValues[r] = vals;
        }

        log.info("已索引 {} 个商品到 TF-IDF 矩阵 (特征维度: {})", nDocs, terms.size());
        return new Index(vocabulary, idf, ids, docs, products, cats, rowIndices, rowValues);
    }

    /** 查询向量化：只保留词表内的 n-gram，tf×idf 后 L2 归一化。全 0 时返回 null */
    private double[] transform(String query, Index idx) {
        Map<Integer, Double> vec = new HashMap<>();
        for (String gram : charWbNgrams(query)) {
            Integer col = idx.vocabulary().get(gram);
            if (col != null) {
                vec.merge(col, 1.0, Double::sum);
            }
        }
        if (vec.isEmpty()) {
            return null;
        }
        double norm = 0;
        double[] dense = new double[idx.idf().length];
        for (Map.Entry<Integer, Double> e : vec.entrySet()) {
            double v = e.getValue() * idx.idf()[e.getKey()];
            dense[e.getKey()] = v;
            norm += v * v;
        }
        norm = Math.sqrt(norm);
        if (norm == 0) {
            return null;
        }
        for (Integer col : vec.keySet()) {
            dense[col] /= norm;
        }
        return dense;
    }

    private static double dot(int[] cols, double[] vals, double[] dense) {
        double s = 0;
        for (int k = 0; k < cols.length; k++) {
            s += vals[k] * dense[cols[k]];
        }
        return s;
    }

    // ====== 文本处理 ======

    /** 商品文档 = 名称 品牌 分类 标签 描述，与 Python _build_doc 完全一致（含拼接顺序与 strip） */
    static String buildDoc(String name, String description, String brand,
                           String category, List<String> tags) {
        String tagsStr = (tags == null || tags.isEmpty()) ? "" : String.join(" ", tags);
        return (nz(name) + " " + nz(brand) + " " + nz(category) + " " + tagsStr + " " + nz(description)).strip();
    }

    private static String nz(String s) {
        return s == null ? "" : s;
    }

    /**
     * scikit-learn 的 char_wb 分词器 Java 实现。
     *
     * <p>对照 sklearn {@code CountVectorizer._char_wb_ngrams}：
     * 小写化 → 折叠连续空白 → 逐词两侧补空格 → 在词边界内取 n-gram；
     * 词长不足 n 时该词只贡献一次（对应源码里的 {@code if offset == 0: break}）。
     */
    static List<String> charWbNgrams(String text) {
        String normalized = text.toLowerCase(Locale.ROOT).replaceAll("\\s\\s+", " ");
        List<String> ngrams = new ArrayList<>();
        for (String word : normalized.split("\\s+")) {
            if (word.isEmpty()) {
                continue;
            }
            String w = " " + word + " ";
            int len = w.length();
            for (int n = NGRAM_MIN; n <= NGRAM_MAX; n++) {
                int offset = 0;
                ngrams.add(w.substring(offset, Math.min(offset + n, len)));
                while (offset + n < len) {
                    offset++;
                    ngrams.add(w.substring(offset, Math.min(offset + n, len)));
                }
                if (offset == 0) {
                    break; // 短词只计一次
                }
            }
        }
        return ngrams;
    }
}
