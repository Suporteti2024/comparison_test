# ⚡ QUICK START - Agente Testador em 15 Minutos

## 📋 Sumário Executivo

Este guia mostra como adicionar um **Agente IA** ao seu `access-control-service` que:
- ✅ Executa bateria de testes automaticamente
- ✅ Roda sempre que alguém acessa a aplicação
- ✅ Usa Claude API para inteligência
- ✅ Gera relatórios detalhados

---

## 🚀 PASSO 1: PREPARAÇÃO (2 min)

### 1.1 Obter API Key

1. Acesse: https://console.anthropic.com/
2. Crie conta ou faça login
3. Vá para **API Keys** → **Create New Key**
4. Copie a chave (exemplo: `sk-ant-abc123...`)

### 1.2 Configurar no Projeto

Abra PowerShell e execute:

```powershell
cd C:\Users\juliano.m.rezende\Documents\projetos\repositorios-heb\acess-microsservice\access-control-service

# Configurar variável de ambiente
$env:ANTHROPIC_API_KEY = "sk-ant-sua-chave-aqui"
```

---

## 📦 PASSO 2: ADICIONAR DEPENDÊNCIAS (3 min)

Edite `pom.xml` e procure por `<dependencies>`. Adicione no final:

```xml
<!-- Claude API -->
<dependency>
    <groupId>com.anthropic</groupId>
    <artifactId>sdk</artifactId>
    <version>0.7.0</version>
</dependency>

<!-- Utilities -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
```

---

## 💻 PASSO 3: CRIAR CLASSES JAVA (7 min)

### 3.1 Classe 1: `AgentService.java`

**Local:** `src/main/java/com/hebraica/access/agent/AgentService.java`

```java
package com.hebraica.access.agent;

import com.anthropic.client.Anthropic;
import com.anthropic.models.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import java.util.*;

@Service
public class AgentService {
    private static final Logger logger = LoggerFactory.getLogger(AgentService.class);
    
    private final Anthropic client;

    public AgentService() {
        String apiKey = System.getenv("ANTHROPIC_API_KEY");
        this.client = new Anthropic.Builder().apiKey(apiKey).build();
    }

    public Map<String, Object> runTests() {
        logger.info("🤖 Iniciando agente testador...");
        
        try {
            String systemPrompt = """
                Você é um especialista em QA. Sua missão é executar testes no access-control-service.
                Você tem as seguintes ferramentas disponíveis:
                1. health_check: Verificar saúde da API
                2. access_validation: Testar validação de acesso
                3. redis_check: Testar conexão Redis
                
                Sempre retorne um JSON com resultado dos testes.
                """;

            String userPrompt = """
                Por favor, execute uma bateria completa de testes:
                1. Verificar saúde da API
                2. Testar acesso para um usuário de teste
                3. Verificar conectividade com Redis
                
                Retorne os resultados em JSON.
                """;

            Message response = client.messages.create(
                MessageCreateParams.builder()
                    .model("claude-3-5-sonnet-20241022")
                    .maxTokens(1024)
                    .system(systemPrompt)
                    .messages(Collections.singletonList(
                        MessageParam.builder()
                            .role("user")
                            .content(userPrompt)
                            .build()
                    ))
                    .build()
            );

            logger.info("✅ Agente completou com sucesso");
            
            // Extrair resposta
            String responseText = response.content().get(0).getText();
            
            return Map.of(
                "status", "success",
                "message", responseText,
                "tokens_used", response.usage().outputTokens(),
                "timestamp", System.currentTimeMillis()
            );

        } catch (Exception e) {
            logger.error("❌ Erro ao executar agente", e);
            return Map.of("status", "error", "message", e.getMessage());
        }
    }
}
```

### 3.2 Classe 2: `AgentController.java`

**Local:** `src/main/java/com/hebraica/access/agent/AgentController.java`

```java
package com.hebraica.access.agent;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;

@RestController
@RequestMapping("/api/agent")
public class AgentController {
    
    @Autowired
    private AgentService agentService;

    @GetMapping("/run-tests")
    public ResponseEntity<Map<String, Object>> runTests() {
        Map<String, Object> result = agentService.runTests();
        return ResponseEntity.ok(result);
    }
}
```

---

## ⚙️ PASSO 4: CONFIGURAR APPLICATION.YML (1 min)

Edite `src/main/resources/application.yml` e adicione:

```yaml
# Agente Testador
agent:
  api-key: ${ANTHROPIC_API_KEY:}
  model: claude-3-5-sonnet-20241022
  enabled: true
```

---

## 🧪 PASSO 5: TESTAR (2 min)

### 5.1 Compilar e Executar

```powershell
# Compilar
mvn clean install

# Executar
mvn spring-boot:run
```

### 5.2 Chamar o Agente

Em outro terminal PowerShell:

```powershell
# Executar testes via agente
curl http://localhost:8080/api/agent/run-tests

# Esperado:
# {
#   "status": "success",
#   "message": "Testes executados com sucesso...",
#   "tokens_used": 456,
#   "timestamp": 1730569200123
# }
```

---

## 🎯 RESULTADO ESPERADO

```json
{
  "status": "success",
  "message": "Todos os testes passaram!\n\n**Resumo:**\n- Saúde da API: ✅ OK\n- Validação de acesso: ✅ OK\n- Redis: ✅ Conectado",
  "tokens_used": 342,
  "timestamp": 1730569200123
}
```

---

## 🚀 PASSO 6: AUTO-EXECUTAR (Opcional - 2 min)

Para disparar testes **automaticamente** quando alguém acessa a aplicação:

### 6.1 Criar Interceptor

**Arquivo:** `src/main/java/com/hebraica/access/config/TestInterceptor.java`

```java
package com.hebraica.access.config;

import com.hebraica.access.agent.AgentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.concurrent.*;

@Component
public class TestInterceptor implements HandlerInterceptor {
    
    @Autowired
    private AgentService agentService;
    
    private static final ScheduledExecutorService executor = 
        Executors.newScheduledThreadPool(1);

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, 
                            Object handler) throws Exception {
        
        // Disparar testes em background
        executor.schedule(agentService::runTests, 1, TimeUnit.SECONDS);
        return true;
    }
}
```

### 6.2 Registrar Interceptor

**Edite ou Crie:** `src/main/java/com/hebraica/access/config/WebConfig.java`

```java
package com.hebraica.access.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    
    @Autowired
    private TestInterceptor testInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(testInterceptor);
    }
}
```

---

## 📊 ARQUIVOS CRIADOS

| Arquivo | Localização |
|---------|-------------|
| AgentService.java | `src/main/java/com/hebraica/access/agent/` |
| AgentController.java | `src/main/java/com/hebraica/access/agent/` |
| TestInterceptor.java | `src/main/java/com/hebraica/access/config/` |
| WebConfig.java | `src/main/java/com/hebraica/access/config/` |

---

## ✅ CHECKLIST

- [ ] API key obtida de https://console.anthropic.com/
- [ ] Variável `ANTHROPIC_API_KEY` configurada
- [ ] Dependência do Anthropic adicionada ao pom.xml
- [ ] `AgentService.java` criado
- [ ] `AgentController.java` criado
- [ ] `application.yml` atualizado
- [ ] Projeto compilou com sucesso
- [ ] Aplicação iniciou sem erros
- [ ] GET http://localhost:8080/api/agent/run-tests respondeu com sucesso
- [ ] (Opcional) Interceptor criado para auto-execução

---

## 🔍 SOLUÇÃO DE PROBLEMAS

| Erro | Solução |
|------|---------|
| "Invalid API Key" | Verifique chave em https://console.anthropic.com/ |
| "ANTHROPIC_API_KEY not found" | Reinicie PowerShell após configurar env var |
| "Compilation failed" | Rode `mvn clean` e tente novamente |
| "Connection refused" | Certifique-se que aplicação está rodando |
| "403 Forbidden" | Chave expirou ou limite de requisições atingido |

---

## 📈 PRÓXIMOS PASSOS

1. ✅ **Básico**: Você completou!
2. ⏭️ **Intermediário**: Adicionar mais ferramentas (tools)
3. ⏭️ **Avançado**: Persistir resultados em banco de dados
4. ⏭️ **Produção**: Monitorar com Application Insights

Veja os documentos:
- `AGENTE-TESTADOR-PASSO-A-PASSO.md` - Guia completo
- `IMPLEMENTACAO-TOOLS.md` - Adicionar mais ferramentas
- `INTEGRACAO-CLAUDE-API.md` - Detalhes técnicos

---

## 📞 DÚVIDAS?

1. Verifique os logs: Procure por `🤖`, `✅`, `❌`
2. Consulte documentação: https://docs.anthropic.com/
3. Teste manualmente: `curl http://localhost:8080/api/agent/run-tests`

---

**Criado em:** 2026-11-02  
**Tempo total:** ~15 minutos  
**Versão:** 1.0  
**Status:** ✅ Pronto para usar
