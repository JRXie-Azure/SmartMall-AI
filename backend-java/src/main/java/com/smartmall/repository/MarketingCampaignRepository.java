package com.smartmall.repository;

import com.smartmall.entity.MarketingCampaign;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface MarketingCampaignRepository extends JpaRepository<MarketingCampaign, Long> {

    List<MarketingCampaign> findByIsActiveTrue();
}