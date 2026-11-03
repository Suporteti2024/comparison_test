# 🤖 AGENTE TESTADOR AUTOMÁTICO - DOCUMENTAÇÃO COMPLETA

## 📚 Índice de Documentação

Este projeto contém uma documentação completa para criar um **Agente IA** que executa testes automaticamente em seu `access-control-service`.

---

## 🎯 COMEÇAR AQUI

### Para implementação rápida (15 min):
👉 **[QUICK-START.md](QUICK-START.md)**
- Guia express com passos essenciais
- Pronto para produção
- Sem configurações complexas

### Para implementação completa:
👉 **[AGENTE-TESTADOR-PASSO-A-PASSO.md](AGENTE-TESTADOR-PASSO-A-PASSO.md)**
- Documentação detalhada (12 passos)
- Explica cada componente
- Inclui diagramas de arquitetura
- Checklist final

---

## 📖 DOCUMENTAÇÃO POR TÓPICO

### 1️⃣ IMPLEMENTAÇÃO DE FERRAMENTAS
**[IMPLEMENTACAO-TOOLS.md](IMPLEMENTACAO-TOOLS.md)** (19 KB)

Implementação prática de 7 ferramentas que o agente usará:
- ✅ `HealthCheckTool.java` - Verificar saúde da API
- ✅ `AccessValidationTool.java` - Testar validação de acesso
- ✅ `RedisConnectionTool.java` - Testar conexão Redis
- ✅ `PerformanceTool.java` - Medir performance
- ✅ `SecurityTool.java` - Verificar segurança
- ✅ `DatabaseQueryTool.java` - Executar queries
- ✅ `ReportGeneratorTool.java` - Gerar relatórios

**Quando usar:** Depois de implementar a estrutura básica

---

### 2️⃣ INTEGRAÇÃO COM CLAUDE API
**[INTEGRACAO-CLAUDE-API.md](INTEGRACAO-CLAUDE-API.md)** (14 KB)

Guia técnico para integrar com Anthropic Claude API:
- 🔑 Obter e configurar API key
- 🚀 Implementar `ClaudeAgentClient.java`
- 📞 Fazer chamadas reais ao Claude
- 🔍 Debugging e troubleshooting
- 💰 Estimativa de custos

**Quando usar:** Quando quiser usar Claude de verdade (não simulado)

---

## 🏗️ ARQUITETURA DO PROJETO

```
access-control-service/
├── src/main/java/com/hebraica/access/
│   ├── agent/
│   │   ├── AgentService.java              ← Serviço principal
│   │   ├── AgentController.java           ← REST API
│   │   ├── AgentOrchestrator.java         ← Orquestrador
│   │   ├── ClaudeAgentClient.java         ← Cliente Claude
│   │   ├── AgentPromptBuilder.java        ← Builder de prompts
│   │   ├── AgentToolRegistry.java         ← Registry de tools
│   │   ├── tools/
│   │   │   ├── HealthCheckTool.java
│   │   │   ├── AccessValidationTool.java
│   │   │   ├── RedisConnectionTool.java
│   │   │   ├── PerformanceTool.java
│   │   │   ├── SecurityTool.java
│   │   │   ├── DatabaseQueryTool.java
│   │   │   └── ReportGeneratorTool.java
│   │   └── model/
│   │       ├── TestResult.java
│   │       ├── AgentRequest.java
│   │       └── AgentResponse.java
│   └── config/
│       ├── AgentConfiguration.java        ← Spring config
│       ├── WebConfig.java                 ← Web MVC config
│       └── TestInterceptor.java           ← Auto-trigger
└── src/main/resources/
    └── application.yml                    ← Config properties
```

---

## 🚀 COMO COMEÇAR

### Opção 1: Quick Start (Recomendado para começar)
```
1. Leia: QUICK-START.md
2. Tempo: ~15 minutos
3. Resultado: Agente básico funcionando
```

### Opção 2: Completo (Recomendado para produção)
```
1. Leia: AGENTE-TESTADOR-PASSO-A-PASSO.md
2. Tempo: ~2-3 horas
3. Resultado: Agente profissional com todas as features
```

### Opção 3: Ferramentas Customizadas (Depois da Opção 2)
```
1. Leia: IMPLEMENTACAO-TOOLS.md
2. Tempo: ~1-2 horas
3. Resultado: 7 ferramentas prontas para usar
```

### Opção 4: Integração Claude Real (Depois da Opção 1)
```
1. Leia: INTEGRACAO-CLAUDE-API.md
2. Tempo: ~30-45 minutos
3. Resultado: Chamadas reais ao Claude API
```

---

## 🔑 CONCEITOS PRINCIPAIS

### Agente
Um sistema inteligente que:
- Recebe uma tarefa
- Usa ferramentas disponíveis para executá-la
- Toma decisões autonomamente
- Retorna resultado estruturado

### Prompt (System)
Instruções que definem:
- Identidade do agente
- Responsabilidades
- Comportamento esperado
- Restrições

### Tools (Ferramentas)
Ações que o agente pode executar:
- Testar saúde da API
- Validar acesso
- Conectar ao Redis
- Medir performance
- Fazer scans de segurança

### Orchestrator
Controlador que:
- Coordena chamadas ao LLM
- Executa ferramentas solicitadas
- Processa respostas
- Retorna resultado final

---

## 📊 ENDPOINTS DA API

### GET /api/agent/run-tests
Executa bateria completa de testes

**Request:**
```bash
curl http://localhost:8080/api/agent/run-tests
```

**Response:**
```json
{
  "status": "success",
  "tests_executed": 6,
  "tests_passed": 6,
  "tests_failed": 0,
  "summary": "Todos os testes passaram com sucesso",
  "recommendations": [],
  "timestamp": 1730569200123
}
```

### GET /api/agent/run-test/{testName}
Executa teste específico

**Request:**
```bash
curl http://localhost:8080/api/agent/run-test/health_check
```

---

## ⚙️ CONFIGURAÇÃO

### application.yml

```yaml
agent:
  enabled: true                    # Ativar/desativar
  api-key: ${ANTHROPIC_API_KEY}    # API key
  model: claude-3-5-sonnet-20241022
  
  scheduling:
    enabled: true
    cron: "0 */6 * * * ?"         # A cada 6 horas
  
  tests:
    timeout-seconds: 300
    max-retries: 3
```

### Variáveis de Ambiente

```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-seu-api-key"

# Ou .env file
ANTHROPIC_API_KEY=sk-ant-seu-api-key
```

---

## 📈 FLUXO DE EXECUÇÃO

```
┌─────────────────────────────────────────┐
│ 1. Requisição chega (GET /api/agent)    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 2. Interceptor dispara em background    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 3. AgentService.runTests() é chamado    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 4. Construir Prompt System              │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 5. Registrar Tools disponíveis          │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 6. Chamar Claude API                    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 7. Claude retorna (com tool calls)      │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 8. Executar tools solicitadas           │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 9. Compilar resultados                  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 10. Retornar resposta JSON              │
└─────────────────────────────────────────┘
```

---

## 📝 PROMPTS PADRÃO

### System Prompt
Define identidade e responsabilidades do agente

### User Prompt
Define tarefa específica a executar

### Few-Shot Examples
Exemplos de como o agente deve se comportar

---

## 🔧 TROUBLESHOOTING

### Problema: "API key inválida"
**Solução:**
1. Confirme chave em https://console.anthropic.com/
2. Reinicie PowerShell
3. Recompile projeto

### Problema: "Agente não dispara"
**Solução:**
1. Verifique se `agent.enabled = true`
2. Confirme que interceptor está registrado
3. Verifique logs procurando por `🤖`

### Problema: "Tool não encontrada"
**Solução:**
1. Verifique nome exato da tool
2. Confirme no `AgentToolRegistry`
3. Valide input schema

---

## 💡 BOAS PRÁTICAS

✅ Fazer:
- Usar variáveis de ambiente para API key
- Logar todas as ações do agente
- Implementar retry logic
- Monitorar uso de tokens
- Testar em staging primeiro

❌ Não fazer:
- Commitar API key no Git
- Usar chave hardcoded no código
- Ignorar erros de integração
- Deixar testes em produção sem cuidado
- Confiar cegamente em respostas do agente

---

## 📊 MONITORAMENTO

### Logs a procurar:

```
🤖 Iniciando agente testador...
📞 Chamando Claude API com 7 tools
✅ Resposta do Claude: 3 blocks
🔧 Executando tool: health_check
✅ Agente completou: success
```

### Métricas importantes:

- Tempo total de execução
- Número de tools executadas
- Taxa de sucesso/falha
- Tokens utilizados
- Erros encontrados

---

## 🎓 RECURSOS DE APRENDIZADO

### Documentação Claude
- https://docs.anthropic.com/
- https://docs.anthropic.com/models/

### Tutoriais
- https://github.com/anthropics/anthropic-sdk-java
- https://console.anthropic.com/docs

### Comunidade
- Claude Discussions: https://github.com/anthropics/anthropic-sdk-java/discussions

---

## 📞 SUPORTE E DÚVIDAS

1. **Verifique os logs** - Procure por mensagens de erro
2. **Releia a documentação** - A resposta pode estar lá
3. **Teste manualmente** - Use curl para chamar endpoints
4. **Busque no Google** - Erro genérico pode ter solução conhecida
5. **Pergunte em comunidades** - Reddit, Stack Overflow, GitHub Issues

---

## 🎉 PRÓXIMOS PASSOS

Depois de implementar o básico:

1. ✅ **Agente funcionando** 
2. ⏭️ Adicionar mais ferramentas
3. ⏭️ Persistir resultados em banco
4. ⏭️ Criar dashboard de métricas
5. ⏭️ Integrar com Slack/Email
6. ⏭️ Escalar para produção

---

## 📄 FICHÁRIO DE ARQUIVOS

| Arquivo | Tamanho | Tempo Leitura | Dificuldade |
|---------|---------|---------------|-------------|
| QUICK-START.md | 10 KB | 5 min | ⭐ Fácil |
| AGENTE-TESTADOR-PASSO-A-PASSO.md | 21 KB | 30 min | ⭐⭐ Médio |
| IMPLEMENTACAO-TOOLS.md | 19 KB | 45 min | ⭐⭐ Médio |
| INTEGRACAO-CLAUDE-API.md | 14 KB | 20 min | ⭐⭐⭐ Difícil |

---

## 📌 VERSÃO E STATUS

- **Versão:** 1.0
- **Data:** 2026-11-02
- **Status:** ✅ Pronto para Produção
- **Última Atualização:** 2026-11-02 22:45 UTC-3

---

## 📧 CONTATO

Para dúvidas ou sugestões sobre esta documentação:
1. Consulte os comentários no código
2. Revise os logs de execução
3. Verifique a documentação do Anthropic

---

**Bem-vindo ao futuro dos testes automáticos com IA! 🚀**
