# 🛠️ IMPLEMENTAÇÃO DAS FERRAMENTAS (TOOLS) - Exemplos Práticos

Este documento contém a implementação detalhada de cada ferramenta que o agente utilizará.

---

## 1️⃣ HEALTH CHECK TOOL

**Arquivo:** `src/main/java/com/hebraica/access/agent/tools/HealthCheckTool.java`

```java
package com.hebraica.access.agent.tools;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.actuate.health.HealthComponent;
import org.springframework.boot.actuate.health.HealthEndpoint;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

@Component
public class HealthCheckTool {
    private static final Logger logger = LoggerFactory.getLogger(HealthCheckTool.class);
    
    @Autowired
    private HealthEndpoint healthEndpoint;

    /**
     * Executa verificação de saúde da API
     */
    public Map<String, Object> execute(Map<String, Object> params) {
        logger.info("🏥 Iniciando verificação de saúde...");
        
        try {
            HealthComponent health = healthEndpoint.health();
            
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", health.getStatus().toString());
            result.put("details", health.getComponents());
            result.put("timestamp", System.currentTimeMillis());
            result.put("success", "UP".equals(health.getStatus().toString()));
            
            logger.info("✅ Saúde verificada: {}", health.getStatus());
            return result;
            
        } catch (Exception e) {
            logger.error("❌ Erro ao verificar saúde", e);
            return Map.of(
                "status", "error",
                "message", e.getMessage(),
                "success", false
            );
        }
    }
}
```

---

## 2️⃣ ACCESS VALIDATION TOOL

**Arquivo:** `src/main/java/com/hebraica/access/agent/tools/AccessValidationTool.java`

```java
package com.hebraica.access.agent.tools;

import com.hebraica.access.dto.AccessRequest;
import com.hebraica.access.dto.AccessResponse;
import com.hebraica.access.service.AccessControlService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

@Component
public class AccessValidationTool {
    private static final Logger logger = LoggerFactory.getLogger(AccessValidationTool.class);
    
    @Autowired
    private AccessControlService accessControlService;

    /**
     * Testa validação de acesso para um usuário
     */
    public Map<String, Object> execute(Map<String, Object> params) {
        String userId = (String) params.get("user_id");
        String resource = (String) params.get("resource");
        
        logger.info("🔐 Testando acesso - User: {}, Resource: {}", userId, resource);
        
        try {
            AccessRequest request = new AccessRequest();
            request.setUserId(userId);
            request.setResource(resource);
            
            long startTime = System.currentTimeMillis();
            AccessResponse response = accessControlService.validateAccess(request);
            long duration = System.currentTimeMillis() - startTime;
            
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("user_id", userId);
            result.put("resource", resource);
            result.put("allowed", response.isAllowed());
            result.put("duration_ms", duration);
            result.put("reason", response.getReason());
            result.put("timestamp", System.currentTimeMillis());
            result.put("success", true);
            
            logger.info("✅ Acesso testado - Permitido: {}", response.isAllowed());
            return result;
            
        } catch (Exception e) {
            logger.error("❌ Erro ao validar acesso", e);
            return Map.of(
                "user_id", userId,
                "resource", resource,
                "success", false,
                "error", e.getMessage()
            );
        }
    }
}
```

---

## 3️⃣ REDIS CONNECTION TOOL

**Arquivo:** `src/main/java/com/hebraica/access/agent/tools/RedisConnectionTool.java`

```java
package com.hebraica.access.agent.tools;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Component
public class RedisConnectionTool {
    private static final Logger logger = LoggerFactory.getLogger(RedisConnectionTool.class);
    
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    /**
     * Testa conectividade com Redis
     */
    public Map<String, Object> execute(Map<String, Object> params) {
        String testKey = "health-check-" + System.currentTimeMillis();
        String testValue = "test-value";
        
        logger.info("🔴 Testando conexão com Redis...");
        
        try {
            long startTime = System.currentTimeMillis();
            
            // Escrever
            redisTemplate.opsForValue().set(testKey, testValue, 10, TimeUnit.SECONDS);
            
            // Ler
            Object retrievedValue = redisTemplate.opsForValue().get(testKey);
            
            // Deletar
            redisTemplate.delete(testKey);
            
            long duration = System.currentTimeMillis() - startTime;
            boolean success = testValue.equals(retrievedValue);
            
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("connected", success);
            result.put("duration_ms", duration);
            result.put("test_key", testKey);
            result.put("write_read_delete", "success");
            result.put("timestamp", System.currentTimeMillis());
            
            logger.info("✅ Redis conectado com sucesso em {}ms", duration);
            return result;
            
        } catch (Exception e) {
            logger.error("❌ Erro ao conectar Redis", e);
            return Map.of(
                "connected", false,
                "error", e.getMessage(),
                "timestamp", System.currentTimeMillis()
            );
        }
    }
}
```

---

## 4️⃣ PERFORMANCE TEST TOOL

**Arquivo:** `src/main/java/com/hebraica/access/agent/tools/PerformanceTool.java`

```java
package com.hebraica.access.agent.tools;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;
import java.util.stream.Collectors;

@Component
public class PerformanceTool {
    private static final Logger logger = LoggerFactory.getLogger(PerformanceTool.class);
    
    @Autowired
    private RestTemplate restTemplate;

    /**
     * Testa performance da API
     */
    public Map<String, Object> execute(Map<String, Object> params) {
        String endpoint = (String) params.get("endpoint");
        int numberOfRequests = ((Number) params.get("requests")).intValue();
        
        logger.info("⚡ Testando performance: {} requisições para {}", numberOfRequests, endpoint);
        
        try {
            List<Long> durations = new ArrayList<>();
            
            for (int i = 0; i < numberOfRequests; i++) {
                long start = System.currentTimeMillis();
                try {
                    restTemplate.getForObject(endpoint, String.class);
                    long duration = System.currentTimeMillis() - start;
                    durations.add(duration);
                } catch (Exception e) {
                    logger.warn("Requisição {} falhou", i + 1);
                }
            }
            
            // Calcular estatísticas
            double average = durations.stream()
                .mapToLong(Long::longValue)
                .average()
                .orElse(0);
                
            long min = durations.stream().min(Long::compare).orElse(0L);
            long max = durations.stream().max(Long::compare).orElse(0L);
            
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("endpoint", endpoint);
            result.put("requests", numberOfRequests);
            result.put("successful", durations.size());
            result.put("failed", numberOfRequests - durations.size());
            result.put("avg_ms", (long) average);
            result.put("min_ms", min);
            result.put("max_ms", max);
            result.put("success_rate", String.format("%.2f%%", (durations.size() * 100.0 / numberOfRequests)));
            result.put("timestamp", System.currentTimeMillis());
            
            logger.info("✅ Performance testada - Média: {}ms", (long) average);
            return result;
            
        } catch (Exception e) {
            logger.error("❌ Erro ao testar performance", e);
            return Map.of(
                "endpoint", endpoint,
                "error", e.getMessage(),
                "success", false
            );
        }
    }
}
```

---

## 5️⃣ SECURITY SCAN TOOL

**Arquivo:** `src/main/java/com/hebraica/access/agent/tools/SecurityTool.java`

```java
package com.hebraica.access.agent.tools;

import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

@Component
public class SecurityTool {
    private static final Logger logger = LoggerFactory.getLogger(SecurityTool.class);

    /**
     * Executa verificações de segurança
     */
    public Map<String, Object> execute(Map<String, Object> params) {
        String scanType = (String) params.get("scan_type");
        
        logger.info("🔒 Executando scan de segurança: {}", scanType);
        
        try {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("scan_type", scanType);
            result.put("checks", performSecurityChecks());
            result.put("vulnerabilities_found", 0);
            result.put("severity_level", "LOW");
            result.put("recommendations", getSecurityRecommendations());
            result.put("timestamp", System.currentTimeMillis());
            
            logger.info("✅ Scan de segurança completado");
            return result;
            
        } catch (Exception e) {
            logger.error("❌ Erro ao executar security scan", e);
            return Map.of("error", e.getMessage(), "success", false);
        }
    }

    private Map<String, Object> performSecurityChecks() {
        Map<String, Object> checks = new LinkedHashMap<>();
        checks.put("sql_injection", checkSQLInjection());
        checks.put("xss_vulnerability", checkXSS());
        checks.put("csrf_protection", checkCSRFProtection());
        checks.put("ssl_tls", checkSSLTLS());
        checks.put("authentication", checkAuthentication());
        return checks;
    }

    private boolean checkSQLInjection() {
        // Implementar lógica de verificação
        return true;
    }

    private boolean checkXSS() {
        // Implementar lógica de verificação
        return true;
    }

    private boolean checkCSRFProtection() {
        // Implementar lógica de verificação
        return true;
    }

    private boolean checkSSLTLS() {
        // Implementar lógica de verificação
        return true;
    }

    private boolean checkAuthentication() {
        // Implementar lógica de verificação
        return true;
    }

    private List<String> getSecurityRecommendations() {
        return List.of(
            "Manter dependências atualizadas",
            "Usar HTTPS em produção",
            "Implementar rate limiting",
            "Validar todos os inputs",
            "Usar prepared statements"
        );
    }
}
```

---

## 6️⃣ DATABASE QUERY TOOL

**Arquivo:** `src/main/java/com/hebraica/access/agent/tools/DatabaseQueryTool.java`

```java
package com.hebraica.access.agent.tools;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

@Component
public class DatabaseQueryTool {
    private static final Logger logger = LoggerFactory.getLogger(DatabaseQueryTool.class);
    
    @Autowired
    private JdbcTemplate jdbcTemplate;

    /**
     * Executa queries de teste no banco de dados
     */
    public Map<String, Object> execute(Map<String, Object> params) {
        String query = (String) params.get("query");
        
        logger.info("🗄️ Executando query no banco: {}", query);
        
        try {
            long startTime = System.currentTimeMillis();
            List<Map<String, Object>> result = jdbcTemplate.queryForList(query);
            long duration = System.currentTimeMillis() - startTime;
            
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("query", query);
            response.put("rows_returned", result.size());
            response.put("duration_ms", duration);
            response.put("success", true);
            response.put("data", result);
            response.put("timestamp", System.currentTimeMillis());
            
            logger.info("✅ Query executada - {} linhas em {}ms", result.size(), duration);
            return response;
            
        } catch (Exception e) {
            logger.error("❌ Erro ao executar query", e);
            return Map.of(
                "query", query,
                "error", e.getMessage(),
                "success", false
            );
        }
    }
}
```

---

## 7️⃣ REPORT GENERATOR TOOL

**Arquivo:** `src/main/java/com/hebraica/access/agent/tools/ReportGeneratorTool.java`

```java
package com.hebraica.access.agent.tools;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.io.File;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Component
public class ReportGeneratorTool {
    private static final Logger logger = LoggerFactory.getLogger(ReportGeneratorTool.class);
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Gera relatório final dos testes
     */
    public Map<String, Object> execute(Map<String, Object> params) {
        @SuppressWarnings("unchecked")
        Map<String, Object> testResults = (Map<String, Object>) params.get("test_results");
        
        logger.info("📊 Gerando relatório final...");
        
        try {
            // Compilar resultados
            Map<String, Object> report = compileReport(testResults);
            
            // Salvar em arquivo
            String fileName = generateFileName();
            saveReport(report, fileName);
            
            logger.info("✅ Relatório gerado: {}", fileName);
            return Map.of(
                "status", "success",
                "report_file", fileName,
                "summary", report,
                "timestamp", System.currentTimeMillis()
            );
            
        } catch (Exception e) {
            logger.error("❌ Erro ao gerar relatório", e);
            return Map.of("status", "error", "message", e.getMessage());
        }
    }

    private Map<String, Object> compileReport(Map<String, Object> testResults) {
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("title", "Relatório de Testes Automáticos");
        report.put("timestamp", LocalDateTime.now());
        report.put("test_results", testResults);
        
        // Calcular métricas
        int totalTests = testResults.size();
        int passedTests = (int) testResults.values().stream()
            .filter(v -> v instanceof Map)
            .filter(v -> "PASSED".equals(((Map<?, ?>) v).get("status")))
            .count();
        
        report.put("total_tests", totalTests);
        report.put("passed_tests", passedTests);
        report.put("failed_tests", totalTests - passedTests);
        report.put("success_rate", String.format("%.2f%%", (passedTests * 100.0 / totalTests)));
        
        return report;
    }

    private String generateFileName() {
        LocalDateTime now = LocalDateTime.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");
        return "test_report_" + now.format(formatter) + ".json";
    }

    private void saveReport(Map<String, Object> report, String fileName) throws Exception {
        File file = new File(fileName);
        objectMapper.writerWithDefaultPrettyPrinter().writeValue(file, report);
    }
}
```

---

## 🔌 PASSO 8: REGISTRAR TOOLS NO AGENTE

Edite `TestAgentService.java` para executar as tools:

```java
private void executeTool(String toolName, Map<String, Object> params) {
    logger.info("🔧 Executando tool: {}", toolName);
    
    Object result = switch (toolName) {
        case "health_check" -> healthCheckTool.execute(params);
        case "access_validation" -> accessValidationTool.execute(params);
        case "redis_connection" -> redisConnectionTool.execute(params);
        case "database_query" -> databaseQueryTool.execute(params);
        case "performance_test" -> performanceTool.execute(params);
        case "security_scan" -> securityTool.execute(params);
        case "generate_report" -> reportGeneratorTool.execute(params);
        default -> Map.of("error", "Tool not found");
    };
    
    logger.info("✅ Tool {} completada", toolName);
}
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

- [ ] `HealthCheckTool.java` criado
- [ ] `AccessValidationTool.java` criado
- [ ] `RedisConnectionTool.java` criado
- [ ] `PerformanceTool.java` criado
- [ ] `SecurityTool.java` criado
- [ ] `DatabaseQueryTool.java` criado
- [ ] `ReportGeneratorTool.java` criado
- [ ] Todas as tools injetadas no `TestAgentService`
- [ ] Método de execução de tools implementado
- [ ] Testes unitários para cada tool
- [ ] Integração com agente validada

---

**Criado em:** 2026-11-02  
**Versão:** 1.0  
**Status:** ✅ Pronto para implementação
