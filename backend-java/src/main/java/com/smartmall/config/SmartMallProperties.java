package com.smartmall.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.Arrays;
import java.util.List;

/**
 * 业务配置绑定，对应原 Python 版 app/config.py 的 Settings。
 */
@Data
@ConfigurationProperties(prefix = "smartmall")
public class SmartMallProperties {

    private String appName = "SmartMall AI";
    private String appVersion = "2.0.0";

    private Jwt jwt = new Jwt();
    private Cache cache = new Cache();
    private RateLimit rateLimit = new RateLimit();
    private Llm llm = new Llm();
    private Cors cors = new Cors();
    private Upload upload = new Upload();
    private Web web = new Web();

    @Data
    public static class Jwt {
        private String secretKey = "";
        private long accessTokenExpireMinutes = 1440;
    }

    @Data
    public static class Cache {
        private long expireSeconds = 300;
        private boolean redisEnabled = true;
    }

    @Data
    public static class RateLimit {
        private boolean enabled = true;
        private int requests = 100;
        private int windowSeconds = 60;
        private int aiRequests = 20;
    }

    @Data
    public static class Llm {
        private String deepseekApiKey = "";
        private String deepseekBaseUrl = "https://api.deepseek.com/v1";
        private String deepseekModel = "deepseek-chat";
        private String openaiApiKey = "";
        private String openaiBaseUrl = "https://api.openai.com/v1";
        private String openaiModel = "gpt-4o-mini";
        private int timeoutSeconds = 60;
        private int streamTimeoutSeconds = 120;

        /** 优先使用 DeepSeek，其次 OpenAI —— 与 Python 版 llm_api_key 属性一致。 */
        public String apiKey() {
            return !deepseekApiKey.isBlank() ? deepseekApiKey : openaiApiKey;
        }

        public String baseUrl() {
            return !deepseekApiKey.isBlank() ? deepseekBaseUrl : openaiBaseUrl;
        }

        public String model() {
            return !deepseekApiKey.isBlank() ? deepseekModel : openaiModel;
        }

        public boolean enabled() {
            return !apiKey().isBlank();
        }
    }

    @Data
    public static class Cors {
        private String origins = "*";

        public List<String> originList() {
            if ("*".equals(origins.trim())) {
                return List.of("*");
            }
            return Arrays.stream(origins.split(",")).map(String::trim).filter(s -> !s.isEmpty()).toList();
        }
    }

    @Data
    public static class Upload {
        private String dir = "./uploads";
    }

    @Data
    public static class Web {
        /**
         * 前端静态目录候选，按顺序取第一个存在的。
         * 默认复用 Python 版的 backend/static，保证两套后端跑同一份 index.html。
         * 都不存在时回落到 jar 内的 classpath:/static/。
         */
        private List<String> staticDirs = List.of("./static", "../backend/static", "./backend/static");
    }
}
