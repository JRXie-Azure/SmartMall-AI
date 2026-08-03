package com.smartmall.repository;

import com.smartmall.entity.SearchHistory;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface SearchHistoryRepository extends JpaRepository<SearchHistory, Long> {

    List<SearchHistory> findTop20ByUserIdOrderByCreatedAtDescIdAsc(Long userId);

    /**
     * 热搜榜: [keyword, count]。
     *
     * <p>并列时按 keyword 升序 —— 注意这与 ProductRepository.countGroupByBrand 的降序相反，
     * 不是笔误：SQLite 这条走覆盖索引 idx_search_keyword 完成分组，brands 那条走 TEMP B-TREE
     * 分组，两种计划下相同 count 的输出方向恰好是反的。方向以实测为准，无法靠推理。
     */
    @Query("SELECT s.keyword, COUNT(s) AS c FROM SearchHistory s " +
            "GROUP BY s.keyword ORDER BY c DESC, s.keyword ASC")
    List<Object[]> findHotKeywords(Pageable pageable);

    /** 搜索联想: 前缀/包含匹配的历史关键词，MIN(id) 复现 SQLite 的 rowid 扫描序 */
    @Query("SELECT s.keyword FROM SearchHistory s WHERE LOWER(s.keyword) LIKE LOWER(CONCAT('%', :kw, '%')) " +
            "GROUP BY s.keyword ORDER BY MIN(s.id)")
    List<String> findKeywordsContaining(@Param("kw") String kw, Pageable pageable);
}
