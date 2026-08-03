package com.smartmall;

import com.smartmall.config.SmartMallProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * SmartMall-AI 应用入口。
 *
 * <p>由 FastAPI 迁移而来，保持完全一致的对外 API 契约：
 * 路径、请求体、响应字段（snake_case）、错误格式 {"detail": "..."} 均与 Python 版本对齐，
 * 前端 static/index.html 无需任何改动即可直接对接。
 */
@SpringBootApplication
@EnableConfigurationProperties(SmartMallProperties.class)
@EnableAsync
public class SmartMallApplication {

    public static void main(String[] args) {
        SpringApplication.run(SmartMallApplication.class, args);
    }
}
