package com.smartmall.repository;

import com.smartmall.entity.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface ProductRepository extends JpaRepository<Product, Long>, JpaSpecificationExecutor<Product> {

    List<Product> findByIsActiveTrueAndAuditStatus(String auditStatus);

    /** 热销兜底推荐。p.id ASC 是必需的 tie-break —— 种子数据里存在 sales/rating 完全相同的商品 */
    @Query("SELECT p FROM Product p WHERE p.isActive = true AND p.auditStatus = 'approved' " +
            "ORDER BY p.sales DESC, p.rating DESC, p.id ASC")
    List<Product> findHotProducts(Pageable pageable);

    @Query("SELECT p FROM Product p WHERE p.id IN :ids AND p.isActive = true AND p.auditStatus = 'approved'")
    List<Product> findActiveByIdIn(@Param("ids") List<Long> ids);

    long countByAuditStatus(String auditStatus);

    long countByStockLessThan(Integer threshold);

    /** 分类分布: [categoryId, count] */
    @Query("SELECT p.categoryId, COUNT(p) FROM Product p WHERE p.isActive = true GROUP BY p.categoryId")
    List<Object[]> countGroupByCategory();

    /**
     * 管理后台品类分布: [categoryName, count]。
     * 与 Python 版 admin.py 一致 —— 内连接 Category，且不过滤 is_active。
     */
    @Query("SELECT c.name, COUNT(p) FROM Category c JOIN Product p ON p.categoryId = c.id GROUP BY c.name")
    List<Object[]> countGroupByCategoryName();

    /** 销量 TOP N */
    @Query("SELECT p FROM Product p WHERE p.isActive = true ORDER BY p.sales DESC, p.id ASC")
    List<Product> findTopBySales(Pageable pageable);

    // ====== 管理后台列表 ======

    /**
     * 排序一律由调用方通过 Pageable 显式指定（createdAt DESC + id ASC）。
     * 这里刻意不提供 findAllByOrderByCreatedAtDesc 这类方法名派生排序 ——
     * 它们没有 tie-break，在 H2/MySQL 上顺序不稳定。
     */
    Page<Product> findByAuditStatus(String auditStatus, Pageable pageable);

    // ====== 搜索 ======

    /**
     * 品牌聚合: [brand, count]，用于筛选侧栏。
     * ORDER BY 第二键 p.brand DESC 是为对齐 SQLite：count 相同时它按分组键降序吐出，
     * 而 H2/MySQL 顺序未定义，不补兜底会与 Python 版结果不一致。
     */
    @Query("SELECT p.brand, COUNT(p) AS c FROM Product p WHERE p.isActive = true AND p.brand <> '' " +
            "GROUP BY p.brand ORDER BY c DESC, p.brand DESC")
    List<Object[]> countGroupByBrand();

    /**
     * 搜索联想: 命中商品名。
     * 用 GROUP BY 而非 DISTINCT —— DISTINCT 下无法 ORDER BY 非投影列，
     * 而 MIN(p.id) 正好复现 SQLite DISTINCT 扫描时的 rowid 升序。
     */
    @Query("SELECT p.name FROM Product p WHERE p.isActive = true " +
            "AND LOWER(p.name) LIKE LOWER(CONCAT('%', :kw, '%')) " +
            "GROUP BY p.name ORDER BY MIN(p.id)")
    List<String> findNamesContaining(@Param("kw") String kw, Pageable pageable);

    /** 搜索联想: 命中品牌，排序理由同上 */
    @Query("SELECT p.brand FROM Product p WHERE p.isActive = true AND p.brand <> '' " +
            "AND LOWER(p.brand) LIKE LOWER(CONCAT('%', :kw, '%')) " +
            "GROUP BY p.brand ORDER BY MIN(p.id)")
    List<String> findBrandsContaining(@Param("kw") String kw, Pageable pageable);

    /**
     * RAG 索引语料: 所有上架商品。
     * 刻意不过滤 audit_status —— Python 版 rag_service.index_all_products 就只按 is_active 取。
     */
    @Query("SELECT p FROM Product p WHERE p.isActive = true ORDER BY p.id")
    List<Product> findAllIndexable();
}
