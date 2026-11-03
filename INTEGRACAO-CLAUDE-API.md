# 🚀 INTEGRAÇÃO COM CLAUDE API - Guia Prático

Este documento mostra como integrar o agente com Claude API (Anthropic) para executar de forma real.

---

## 1️⃣ INSTALAÇÃO DO SDK ANTHROPIC

Já adicionou no `pom.xml`? Confirme:

```xml
<dependency>
    <groupId>com.anthropic</groupId>
    <artifactId>sdk</artifactId>
    <version>0.7.0</version>
</dependency>
```

Se não, execute:
```bash
mvn dependency:resolve
```

---

## 2️⃣ OBTER API KEY DO ANTHROPIC

1. Acesse: https://console.anthropic.com/
2. Crie uma conta (ou faça login)
3. Vá para **API Keys**
4. Clique em **Create New Key**
5. Copie a chave (formato: `sk-ant-...`)
6. **NUNCA** commit isto no Git!

---

## 3️⃣ CONFIGURAR VARIÁVEL DE AMBIENTE

### No Windows (PowerShell):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-seu-api-key-aqui"

# Verificar
echo $env:ANTHROPIC_API_KEY
```

### No Windows (.env file):

Crie `.env` na raiz do projeto:

```env
ANTHROPIC_API_KEY=sk-ant-seu-api-key-aqui
```

Adicione ao `.gitignore`:
```
.env
.env.local
```

### No application.yml:

```yaml
agent:
  api-key: ${ANTHROPIC_API_KEY:sk-ant-default}
```

---

## 4️⃣ IMPLEMENTAR CLAUDE CLIENT

**Arquivo:** `src/main/java/com/hebraica/access/agent/ClaudeAgentClient.java`

```java
package com.hebraica.access.agent;

import com.anthropic.client.Anthropic;
import com.anthropic.models.Message;
import com.anthropic.models.MessageParam;
import com.anthropic.models.Tool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import java.util.*;

@Component
public class ClaudeAgentClient {
    private static final Logger logger = LoggerFactory.getLogger(ClaudeAgentClient.class);
    
    private final Anthropic client;
    private final String modelName;

    public ClaudeAgentClient(String apiKey, String modelName) {
        this.client = new Anthropic.Builder()
            .apiKey(apiKey)
            .build();
        this.modelName = modelName;
    }

    /**
     * Chamar Claude com tools
     */
    public Map<String, Object> executeWithTools(
            String systemPrompt,
            String userPrompt,
            List<Map<String, Object>> tools) {
        
        logger.info("📞 Chamando Claude API com {} tools", tools.size());
        
        try {
            // 1. Preparar mensagem inicial
            List<MessageParam> messages = new ArrayList<>();
            messages.add(MessageParam.builder()
                .role("user")
                .content(userPrompt)
                .build());
            
            // 2. Converter tools para formato Anthropic
            List<Tool> claudeTools = convertTools(tools);
            
            // 3. Fazer chamada inicial ao Claude
            Message response = client.messages.create(
                com.anthropic.models.MessageCreateParams.builder()
                    .model(modelName)
                    .maxTokens(4096)
                    .system(systemPrompt)
                    .tools(claudeTools)
                    .messages(messages)
                    .build()
            );
            
            logger.info("✅ Resposta do Claude: {} blocks", response.content().size());
            
            // 4. Processar resposta
            return processResponse(response);
            
        } catch (Exception e) {
            logger.error("❌ Erro ao chamar Claude", e);
            return Map.of(
                "status", "error",
                "message", e.getMessage(),
                "error_class", e.getClass().getName()
            );
        }
    }

    /**
     * Converter ferramentas para formato Anthropic
     */
    private List<Tool> convertTools(List<Map<String, Object>> tools) {
        List<Tool> claudeTools = new ArrayList<>();
        
        for (Map<String, Object> tool : tools) {
            @SuppressWarnings("unchecked")
            Map<String, Object> inputSchema = 
                (Map<String, Object>) tool.get("input_schema");
            
            Tool claudeTool = Tool.builder()
                .name((String) tool.get("name"))
                .description((String) tool.get("description"))
                .inputSchema(inputSchema)
                .build();
            
            claudeTools.add(claudeTool);
        }
        
        return claudeTools;
    }

    /**
     * Processar resposta do Claude
     */
    private Map<String, Object> processResponse(Message response) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "success");
        result.put("stop_reason", response.stopReason().toString());
        result.put("content_blocks", response.content().size());
        result.put("usage", Map.of(
            "input_tokens", response.usage().inputTokens(),
            "output_tokens", response.usage().outputTokens()
        ));
        
        // Verificar se tem tool_use
        if ("tool_use".equals(response.stopReason().toString())) {
            result.put("has_tool_calls", true);
            result.put("tool_calls", extractToolCalls(response));
        } else {
            result.put("has_tool_calls", false);
            result.put("response_text", extractText(response));
        }
        
        return result;
    }

    /**
     * Extrair chamadas de tool da resposta
     */
    private List<Map<String, Object>> extractToolCalls(Message response) {
        List<Map<String, Object>> toolCalls = new ArrayList<>();
        
        response.content().forEach(block -> {
            if (block.getClass().getSimpleName().equals("ToolUseBlock")) {
                // Extrair informações do tool
                Map<String, Object> toolCall = new LinkedHashMap<>();
                try {
                    // Usar reflexão para acessar propriedades
                    toolCall.put("tool_name", getFieldValue(block, "name"));
                    toolCall.put("tool_input", getFieldValue(block, "input"));
                    toolCall.put("tool_use_id", getFieldValue(block, "id"));
                    toolCalls.add(toolCall);
                } catch (Exception e) {
                    logger.error("Erro ao extrair tool call", e);
                }
            }
        });
        
        return toolCalls;
    }

    /**
     * Extrair texto da resposta
     */
    private String extractText(Message response) {
        StringBuilder text = new StringBuilder();
        
        response.content().forEach(block -> {
            if (block.getClass().getSimpleName().equals("TextBlock")) {
                try {
                    text.append(getFieldValue(block, "text"));
                } catch (Exception e) {
                    logger.error("Erro ao extrair texto", e);
                }
            }
        });
        
        return text.toString();
    }

    /**
     * Helper para acessar campos via reflexão
     */
    private Object getFieldValue(Object obj, String fieldName) throws Exception {
        java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(obj);
    }
}
```

---

## 5️⃣ ATUALIZAR TEST AGENT ORCHESTRATOR

**Arquivo:** `src/main/java/com/hebraica/access/agent/TestAgentOrchestrator.java`

Substitua a implementação anterior com chamada real:

```java
package com.hebraica.access.agent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import java.util.*;

@Component
public class TestAgentOrchestrator {
    private static final Logger logger = LoggerFactory.getLogger(TestAgentOrchestrator.class);
    
    @Autowired
    private ClaudeAgentClient claudeClient;

    public Map<String, Object> executeAgent(String systemPrompt, String userPrompt, 
                                            List<Map<String, Object>> tools) {
        logger.info("🚀 Executando agente com Claude");
        
        try {
            // Chamar Claude API
            Map<String, Object> claudeResponse = claudeClient.executeWithTools(
                systemPrompt,
                userPrompt,
                tools
            );
            
            // Se tem tool calls, processar
            if (claudeResponse.containsKey("has_tool_calls") && 
                (boolean) claudeResponse.get("has_tool_calls")) {
                
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> toolCalls = 
                    (List<Map<String, Object>>) claudeResponse.get("tool_calls");
                
                processToolCalls(toolCalls);
            }
            
            return claudeResponse;
            
        } catch (Exception e) {
            logger.error("Erro ao executar agente", e);
            return Map.of("status", "error", "message", e.getMessage());
        }
    }

    /**
     * Processar chamadas de tool
     */
    private void processToolCalls(List<Map<String, Object>> toolCalls) {
        logger.info("🔧 Processando {} tool calls", toolCalls.size());
        
        for (Map<String, Object> toolCall : toolCalls) {
            String toolName = (String) toolCall.get("tool_name");
            @SuppressWarnings("unchecked")
            Map<String, Object> toolInput = 
                (Map<String, Object>) toolCall.get("tool_input");
            
            logger.info("  ▸ Executando: {} com input: {}", toolName, toolInput);
            
            // Aqui você chamaria a ferramenta correspondente
            // executeTool(toolName, toolInput);
        }
    }
}
```

---

## 6️⃣ CRIAR BEAN PARA CLAUDE CLIENT

Atualize `AgentConfiguration.java`:

```java
package com.hebraica.access.config;

import com.hebraica.access.agent.ClaudeAgentClient;
import com.hebraica.access.agent.TestAgentService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AgentConfiguration {

    @Value("${agent.api-key:}")
    private String anthropicApiKey;

    @Value("${agent.model:claude-3-5-sonnet-20241022}")
    private String modelName;

    @Value("${agent.enabled:true}")
    private boolean agentEnabled;

    @Bean
    public ClaudeAgentClient claudeAgentClient() {
        return new ClaudeAgentClient(anthropicApiKey, modelName);
    }

    @Bean
    public TestAgentService testAgentService(ClaudeAgentClient claudeClient) {
        return new TestAgentService(claudeClient, agentEnabled);
    }
}
```

---

## 7️⃣ TESTAR INTEGRAÇÃO

### Via PowerShell:

```powershell
# 1. Compilar
cd C:\Users\juliano.m.rezende\Documents\projetos\repositorios-heb\acess-microsservice\access-control-service
mvn clean install

# 2. Executar com API key
$env:ANTHROPIC_API_KEY = "sk-ant-seu-api-key"
mvn spring-boot:run

# 3. Em outro terminal, testar endpoint
curl http://localhost:8080/api/agent/run-tests

# 4. Verificar logs
# Procure por "📞 Chamando Claude API" e "✅ Resposta do Claude"
```

---

## 📊 MONITORAMENTO

### Logs esperados:

```
2026-11-02 22:45:00.123 INFO  TestAgentService       - 🤖 Iniciando agente testador...
2026-11-02 22:45:00.456 INFO  ClaudeAgentClient      - 📞 Chamando Claude API com 7 tools
2026-11-02 22:45:02.789 INFO  ClaudeAgentClient      - ✅ Resposta do Claude: 3 blocks
2026-11-02 22:45:02.890 INFO  TestAgentOrchestrator  - 🚀 Executando agente com Claude
2026-11-02 22:45:02.891 INFO  TestAgentService       - ✅ Agente completou: success
```

---

## 🔍 DEBUGGING

### Erro: "Invalid API Key"

```
Solução:
1. Confirme a chave em https://console.anthropic.com/
2. Verifique se a chave começa com "sk-ant-"
3. Reconecte a variável de ambiente
```

### Erro: "Rate Limited"

```
Solução:
1. Aguarde alguns segundos
2. Implemente backoff exponencial
3. Verifique limite da sua conta
```

### Erro: "Tool Not Found"

```
Solução:
1. Verifique se a tool está no registry
2. Confirme o nome exato da tool
3. Valide o schema de entrada
```

---

## 💰 ESTIMATIVA DE CUSTOS

**Modelo:** Claude 3.5 Sonnet

| Operação | Tokens | Custo (USD) |
|----------|--------|-------------|
| 1 execução agente | ~2,000 | $0.006 |
| 100 execuções/dia | 200,000 | $0.60 |
| 1000 execuções/mês | 2M | $6.00 |

*Consulte https://www.anthropic.com/pricing para valores atualizados*

---

## 🔐 BOAS PRÁTICAS

✅ **Fazer:**
- [ ] Usar variáveis de ambiente para API key
- [ ] Implementar retry logic com backoff
- [ ] Logar todas as chamadas
- [ ] Monitorar uso de tokens
- [ ] Usar rate limiting

❌ **Não fazer:**
- [ ] Commitar API key no Git
- [ ] Exibir chave em logs
- [ ] Usar chave em URLs
- [ ] Deixar chave em códigos comentados
- [ ] Reutilizar mesma chave em múltiplos ambientes

---

## 🔗 RECURSOS

- Documentação Anthropic: https://docs.anthropic.com/
- SDK Java: https://github.com/anthropics/anthropic-sdk-java
- API Reference: https://docs.anthropic.com/reference/
- Console: https://console.anthropic.com/

---

## 📞 SUPORTE

Erro na integração? Checklist:

- [ ] API key válida?
- [ ] Variável de ambiente configurada?
- [ ] pom.xml atualizado?
- [ ] Projeto compilou?
- [ ] Aplicação iniciou sem erros?
- [ ] Endpoint /api/agent/run-tests acessível?
- [ ] Logs mostram chamada ao Claude?

---

**Criado em:** 2026-11-02  
**Versão:** 1.0  
**Status:** ✅ Pronto para integração
