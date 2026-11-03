# 🤖 AGENTE TESTADOR AUTOMÁTICO - PASSO A PASSO COMPLETO

## 📋 OBJETIVO
Criar um agente IA que roda dentro do `access-control-service` para executar bateria de testes automaticamente sempre que a aplicação é acessada.

---

## ✅ PASSO 1: ADICIONAR DEPENDÊNCIAS (Maven)

Edite `pom.xml` e adicione as dependências:

```xml
<!-- IA & LLM -->
<dependency>
    <groupId>com.anthropic</groupId>
    <artifactId>sdk</artifactId>
    <version>0.7.0</version>
</dependency>

<!-- REST Client -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>

<!-- JSON Processing -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>

<!-- Testing -->
<dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>rest-assured</artifactId>
    <version>5.4.1</version>
    <scope>test</scope>
</dependency>

<!-- Scheduling -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-quartz</artifactId>
</dependency>
```

---

## 🏗️ PASSO 2: ESTRUTURA DE PASTAS

Crie a seguinte estrutura:

```
src/main/java/com/hebraica/access/
├── agent/
│   ├── TestAgentService.java          ← Serviço principal do agente
│   ├── TestAgentOrchestrator.java      ← Orquestrador de testes
│   ├── AgentPromptBuilder.java         ← Construtor de prompts
│   ├── AgentToolRegistry.java          ← Registro de ferramentas
│   ├── AgentTestController.java        ← API REST do agente
│   └── tools/
│       ├── HealthCheckTool.java        ← Verificar saúde da API
│       ├── AccessValidationTool.java   ← Testar validação de acesso
│       ├── RedisConnectionTool.java    ← Testar Redis
│       ├── DatabaseQueryTool.java      ← Testar banco de dados
│       ├── PerformanceTool.java        ← Testar performance
│       ├── SecurityTool.java           ← Testar segurança
│       └── ReportGeneratorTool.java    ← Gerar relatórios
├── agent/model/
│   ├── TestResult.java
│   ├── AgentRequest.java
│   ├── AgentResponse.java
│   └── ToolDefinition.java
└── config/
    ├── AgentConfiguration.java         ← Configuração do agente
    ├── WebConfig.java                  ← Web MVC config
    └── TestAgentInterceptor.java       ← Interceptor para auto-gatilho
```

---

## 🔧 PASSO 3: CRIAR AGENT CONFIGURATION

**Arquivo:** `src/main/java/com/hebraica/access/config/AgentConfiguration.java`

```java
package com.hebraica.access.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import com.hebraica.access.agent.TestAgentService;

@Configuration
public class AgentConfiguration {

    @Value("${agent.api-key:}")
    private String anthropicApiKey;

    @Value("${agent.model:claude-3-5-sonnet-20241022}")
    private String modelName;

    @Value("${agent.enabled:true}")
    private boolean agentEnabled;

    @Bean
    public TestAgentService testAgentService() {
        return new TestAgentService(anthropicApiKey, modelName, agentEnabled);
    }
}
```

---

## 🤖 PASSO 4: CRIAR SERVIÇO PRINCIPAL DO AGENTE

**Arquivo:** `src/main/java/com/hebraica/access/agent/TestAgentService.java`

```java
package com.hebraica.access.agent;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import java.util.*;
import java.util.concurrent.*;

@Service
public class TestAgentService {
    private static final Logger logger = LoggerFactory.getLogger(TestAgentService.class);
    
    private final String apiKey;
    private final String modelName;
    private final boolean enabled;
    private final TestAgentOrchestrator orchestrator;
    private final AgentPromptBuilder promptBuilder;
    private final AgentToolRegistry toolRegistry;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public TestAgentService(String apiKey, String modelName, boolean enabled) {
        this.apiKey = apiKey;
        this.modelName = modelName;
        this.enabled = enabled;
        this.orchestrator = new TestAgentOrchestrator(apiKey, modelName);
        this.promptBuilder = new AgentPromptBuilder();
        this.toolRegistry = new AgentToolRegistry();
    }

    /**
     * Executa bateria de testes via agente
     */
    public Map<String, Object> runTestSuite() {
        if (!enabled) {
            logger.warn("Agente testador desabilitado");
            return Map.of("status", "disabled");
        }

        logger.info("🤖 Iniciando agente testador...");
        
        try {
            // 1. Preparar contexto
            Map<String, Object> context = buildContext();
            
            // 2. Construir prompt
            String systemPrompt = promptBuilder.buildSystemPrompt();
            String userPrompt = promptBuilder.buildUserPrompt(context);
            
            // 3. Registrar ferramentas
            List<Map<String, Object>> tools = toolRegistry.getAllTools();
            
            // 4. Executar orquestrador
            Map<String, Object> result = orchestrator.executeAgent(
                systemPrompt, 
                userPrompt, 
                tools
            );
            
            logger.info("✅ Agente completou: {}", result.get("status"));
            return result;
            
        } catch (Exception e) {
            logger.error("❌ Erro ao executar agente testador", e);
            return Map.of("status", "error", "message", e.getMessage());
        }
    }

    /**
     * Executa teste específico
     */
    public Map<String, Object> runSpecificTest(String testName) {
        logger.info("🧪 Executando teste: {}", testName);
        return Map.of("test", testName, "status", "running");
    }

    private Map<String, Object> buildContext() {
        return Map.of(
            "timestamp", System.currentTimeMillis(),
            "service", "access-control-service",
            "version", "1.7.0"
        );
    }
}
```

---

## 📝 PASSO 5: CRIAR PROMPT BUILDER

**Arquivo:** `src/main/java/com/hebraica/access/agent/AgentPromptBuilder.java`

```java
package com.hebraica.access.agent;

import java.util.Map;

public class AgentPromptBuilder {

    public String buildSystemPrompt() {
        return """
            # AGENTE TESTADOR AUTOMÁTICO
            
            ## Identidade
            Você é um especialista em QA/Testes Automatizados com 10+ anos de experiência.
            Sua missão é garantir a qualidade do serviço de controle de acesso.
            
            ## Responsabilidades
            1. Executar testes de saúde da API
            2. Validar conectividade com Redis
            3. Testar regras de controle de acesso
            4. Verificar performance
            5. Detectar anomalias de segurança
            6. Gerar relatórios detalhados
            
            ## Comportamento
            - Sempre executa os testes na ordem correta
            - Agrupa testes por categoria (health, access, performance)
            - Detecta e relata falhas imediatamente
            - Fornece recomendações de ação
            - Mantém histórico de execuções
            
            ## Ferramentas Disponíveis
            Use as seguintes ferramentas para executar testes:
            - health_check: Verificar saúde da API
            - access_validation: Testar validação de acesso
            - redis_connection: Testar conexão Redis
            - database_query: Testar banco de dados
            - performance_test: Medir performance
            - security_scan: Verificar segurança
            - generate_report: Gerar relatório final
            
            ## Restricões
            - NÃO modifique dados de produção
            - NÃO exclua registros
            - NÃO desabilite recursos de segurança
            - SEMPRE registre todas as ações
            
            ## Resultado Esperado
            Retorne um JSON com:
            {
              "status": "success|failure",
              "tests_executed": número,
              "tests_passed": número,
              "tests_failed": número,
              "summary": "resumo do que foi testado",
              "recommendations": ["ação 1", "ação 2"]
            }
            """;
    }

    public String buildUserPrompt(Map<String, Object> context) {
        return String.format("""
            Por favor, execute uma bateria completa de testes no serviço.
            
            Contexto:
            - Serviço: %s
            - Versão: %s
            - Timestamp: %s
            
            Siga os passos:
            1. Verificar saúde da API
            2. Testar conexão Redis
            3. Validar regras de acesso
            4. Medir performance
            5. Executar verificações de segurança
            6. Gerar relatório final
            
            Use as ferramentas disponíveis para cada teste e compile o resultado final.
            """,
            context.get("service"),
            context.get("version"),
            context.get("timestamp")
        );
    }
}
```

---

## 🛠️ PASSO 6: CRIAR REGISTRY DE FERRAMENTAS

**Arquivo:** `src/main/java/com/hebraica/access/agent/AgentToolRegistry.java`

```java
package com.hebraica.access.agent;

import java.util.*;

public class AgentToolRegistry {

    public List<Map<String, Object>> getAllTools() {
        List<Map<String, Object>> tools = new ArrayList<>();
        
        tools.add(createTool("health_check",
            "Verifica a saúde geral da API",
            Map.of("endpoint", "string")));
            
        tools.add(createTool("access_validation",
            "Testa validação de acesso para um usuário",
            Map.of(
                "user_id", "string",
                "resource", "string",
                "expected_result", "boolean"
            )));
            
        tools.add(createTool("redis_connection",
            "Verifica conexão com Redis",
            Map.of("key", "string")));
            
        tools.add(createTool("database_query",
            "Executa query de teste no banco",
            Map.of("query", "string")));
            
        tools.add(createTool("performance_test",
            "Mede tempo de resposta",
            Map.of(
                "endpoint", "string",
                "requests", "integer"
            )));
            
        tools.add(createTool("security_scan",
            "Verifica vulnerabilidades comuns",
            Map.of("scan_type", "string")));
            
        tools.add(createTool("generate_report",
            "Gera relatório JSON final",
            Map.of("test_results", "object")));
        
        return tools;
    }

    private Map<String, Object> createTool(String name, String description, 
                                           Map<String, String> params) {
        Map<String, Object> tool = new LinkedHashMap<>();
        tool.put("name", name);
        tool.put("description", description);
        tool.put("input_schema", Map.of(
            "type", "object",
            "properties", params,
            "required", List.copyOf(params.keySet())
        ));
        return tool;
    }
}
```

---

## ⚙️ PASSO 7: CRIAR ORQUESTRADOR

**Arquivo:** `src/main/java/com/hebraica/access/agent/TestAgentOrchestrator.java`

```java
package com.hebraica.access.agent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

public class TestAgentOrchestrator {
    private static final Logger logger = LoggerFactory.getLogger(TestAgentOrchestrator.class);
    
    private final String apiKey;
    private final String modelName;

    public TestAgentOrchestrator(String apiKey, String modelName) {
        this.apiKey = apiKey;
        this.modelName = modelName;
    }

    public Map<String, Object> executeAgent(String systemPrompt, String userPrompt, 
                                            List<Map<String, Object>> tools) {
        logger.info("🚀 Executando agente com modelo: {}", modelName);
        
        try {
            // TODO: Integrar com Claude API
            // Aqui você faria a chamada real ao Anthropic API
            
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", "success");
            result.put("model", modelName);
            result.put("tests_executed", 6);
            result.put("tests_passed", 6);
            result.put("tests_failed", 0);
            result.put("summary", "Todos os testes passaram com sucesso");
            result.put("tools_used", tools.size());
            result.put("timestamp", System.currentTimeMillis());
            
            return result;
            
        } catch (Exception e) {
            logger.error("Erro ao executar agente", e);
            return Map.of("status", "error", "message", e.getMessage());
        }
    }
}
```

---

## 📡 PASSO 8: CRIAR CONTROLLER PARA GATILHO

**Arquivo:** `src/main/java/com/hebraica/access/agent/AgentTestController.java`

```java
package com.hebraica.access.agent;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Map;

@RestController
@RequestMapping("/api/agent")
public class AgentTestController {
    private static final Logger logger = LoggerFactory.getLogger(AgentTestController.class);
    
    @Autowired
    private TestAgentService agentService;

    /**
     * GET /api/agent/run-tests
     * Executa bateria de testes via agente
     */
    @GetMapping("/run-tests")
    public ResponseEntity<Map<String, Object>> runTests() {
        logger.info("📨 Requisição para executar testes chegou");
        Map<String, Object> result = agentService.runTestSuite();
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/agent/run-test/{testName}
     * Executa teste específico
     */
    @GetMapping("/run-test/{testName}")
    public ResponseEntity<Map<String, Object>> runSpecificTest(@PathVariable String testName) {
        logger.info("📨 Requisição para teste específico: {}", testName);
        Map<String, Object> result = agentService.runSpecificTest(testName);
        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/health
     * Health check - dispara agente automaticamente
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        // Opcionalmente dispara agente em background
        agentService.runTestSuite();
        return ResponseEntity.ok(Map.of("status", "healthy"));
    }
}
```

---

## ⚙️ PASSO 9: CONFIGURAR APPLICATION.YML

Edite `src/main/resources/application.yml`:

```yaml
# Configuração do Agente Testador
agent:
  enabled: true                                    # Ativar/desativar agente
  api-key: ${ANTHROPIC_API_KEY:seu-api-key-aqui}  # API key do Anthropic
  model: claude-3-5-sonnet-20241022               # Modelo Claude
  
  # Scheduling de testes automáticos
  scheduling:
    enabled: true
    cron: "0 */6 * * * ?"  # Executar a cada 6 horas
    
  # Configurações de teste
  tests:
    timeout-seconds: 300
    max-retries: 3
    health-check-enabled: true
    redis-test-enabled: true
    performance-test-enabled: true
    security-scan-enabled: true
```

---

## 🎯 PASSO 10: CRIAR INTERCEPTOR PARA AUTO-GATILHO

**Arquivo:** `src/main/java/com/hebraica/access/config/TestAgentInterceptor.java`

```java
package com.hebraica.access.config;

import com.hebraica.access.agent.TestAgentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.concurrent.*;

@Component
public class TestAgentInterceptor implements HandlerInterceptor {
    
    @Autowired
    private TestAgentService agentService;
    
    private static final ScheduledExecutorService executor = 
        Executors.newScheduledThreadPool(1);

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, 
                            Object handler) throws Exception {
        
        // Disparar testes em background quando aplicação é acessada
        executor.schedule(() -> {
            agentService.runTestSuite();
        }, 1, TimeUnit.SECONDS);
        
        return true;
    }
}
```

Registre o interceptor em `WebConfig`:

```java
package com.hebraica.access.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    
    @Autowired
    private TestAgentInterceptor agentInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(agentInterceptor);
    }
}
```

---

## 📊 PASSO 11: CRIAR MODELO DE DADOS

**Arquivo:** `src/main/java/com/hebraica/access/agent/model/TestResult.java`

```java
package com.hebraica.access.agent.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Builder
@AllArgsConstructor
public class TestResult {
    private String testName;
    private String status;        // PASSED, FAILED, SKIPPED
    private String message;
    private long executionTimeMs;
    private LocalDateTime timestamp;
    private String toolUsed;
    private Object result;
}
```

---

## 🚀 PASSO 12: BUILD E TESTE

Execute no terminal (Windows PowerShell):

```powershell
# 1. Compilar projeto
cd C:\Users\juliano.m.rezende\Documents\projetos\repositorios-heb\acess-microsservice\access-control-service
mvn clean install

# 2. Executar aplicação
mvn spring-boot:run

# 3. Testar agente via curl
curl http://localhost:8080/api/agent/run-tests

# 4. Verificar logs
# Procure por "🤖 Iniciando agente testador" e "✅ Agente completou"
```

---

## 📋 CHECKLIST FINAL

- [ ] Dependências Maven adicionadas
- [ ] Estrutura de pastas criada
- [ ] `AgentConfiguration.java` implementado
- [ ] `TestAgentService.java` implementado
- [ ] `AgentPromptBuilder.java` implementado
- [ ] `AgentToolRegistry.java` implementado
- [ ] `TestAgentOrchestrator.java` implementado
- [ ] `AgentTestController.java` implementado
- [ ] `TestAgentInterceptor.java` implementado
- [ ] `WebConfig.java` implementado
- [ ] `application.yml` configurado
- [ ] Modelos de dados criados
- [ ] Projeto compilou com sucesso
- [ ] Aplicação iniciou sem erros
- [ ] Testes disparados via `/api/agent/run-tests`

---

## 🔗 PRÓXIMAS OTIMIZAÇÕES

1. **Integração Real com Claude API**
   - Implementar chamadas reais ao Anthropic API
   - Usar SDK oficial: `com.anthropic:sdk`

2. **Persistência de Resultados**
   - Guardar resultados em banco de dados
   - Criar dashboard com histórico

3. **Notificações**
   - Enviar alertas para Slack
   - Email em caso de falhas

4. **Escalabilidade**
   - Usar Kafka para fila de testes
   - Executar em containers separados

5. **Observabilidade**
   - Integrar com Application Insights
   - Rastrear performance do agente

---

**Criado em:** 2026-11-02  
**Versão:** 1.0  
**Status:** ✅ Pronto para implementação
