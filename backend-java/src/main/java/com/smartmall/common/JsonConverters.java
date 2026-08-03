package com.smartmall.common;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * JSON 列转换器。
 *
 * <p>原 SQLAlchemy 模型用 JSON 列存 images / tags / address_snapshot / metadata，
 * 这里用独立的 ObjectMapper 保持与 Python 端一致的存储格式（纯 JSON 文本，
 * 不受全局 snake_case 命名策略影响，避免把已有数据的 key 改写掉）。
 */
public final class JsonConverters {

    /** 独立实例：不启用 snake_case，保证读写的是原始 JSON 结构。 */
    static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonConverters() {
    }

    @Slf4j
    @Converter
    public static class StringListConverter implements AttributeConverter<List<String>, String> {

        @Override
        public String convertToDatabaseColumn(List<String> attribute) {
            if (attribute == null || attribute.isEmpty()) {
                return "[]";
            }
            try {
                return MAPPER.writeValueAsString(attribute);
            } catch (Exception e) {
                log.warn("序列化字符串列表失败", e);
                return "[]";
            }
        }

        @Override
        public List<String> convertToEntityAttribute(String dbData) {
            if (dbData == null || dbData.isBlank()) {
                return new ArrayList<>();
            }
            try {
                List<String> parsed = MAPPER.readValue(dbData, new TypeReference<List<String>>() {
                });
                return parsed == null ? new ArrayList<>() : parsed;
            } catch (Exception e) {
                log.warn("反序列化字符串列表失败: {}", dbData, e);
                return new ArrayList<>();
            }
        }
    }

    @Slf4j
    @Converter
    public static class LongListConverter implements AttributeConverter<List<Long>, String> {

        @Override
        public String convertToDatabaseColumn(List<Long> attribute) {
            if (attribute == null || attribute.isEmpty()) {
                return "[]";
            }
            try {
                return MAPPER.writeValueAsString(attribute);
            } catch (Exception e) {
                log.warn("序列化 Long 列表失败", e);
                return "[]";
            }
        }

        @Override
        public List<Long> convertToEntityAttribute(String dbData) {
            if (dbData == null || dbData.isBlank()) {
                return new ArrayList<>();
            }
            try {
                List<Long> parsed = MAPPER.readValue(dbData, new TypeReference<List<Long>>() {
                });
                return parsed == null ? new ArrayList<>() : parsed;
            } catch (Exception e) {
                log.warn("反序列化 Long 列表失败: {}", dbData, e);
                return new ArrayList<>();
            }
        }
    }

    @Slf4j
    @Converter
    public static class JsonMapConverter implements AttributeConverter<Map<String, Object>, String> {

        @Override
        public String convertToDatabaseColumn(Map<String, Object> attribute) {
            if (attribute == null || attribute.isEmpty()) {
                return "{}";
            }
            try {
                return MAPPER.writeValueAsString(attribute);
            } catch (Exception e) {
                log.warn("序列化 JSON 对象失败", e);
                return "{}";
            }
        }

        @Override
        public Map<String, Object> convertToEntityAttribute(String dbData) {
            if (dbData == null || dbData.isBlank()) {
                return new LinkedHashMap<>();
            }
            try {
                Map<String, Object> parsed = MAPPER.readValue(dbData, new TypeReference<Map<String, Object>>() {
                });
                return parsed == null ? new LinkedHashMap<>() : parsed;
            } catch (Exception e) {
                log.warn("反序列化 JSON 对象失败: {}", dbData, e);
                return new LinkedHashMap<>();
            }
        }
    }
}
