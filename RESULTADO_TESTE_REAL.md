# Resultado da execução real — SOAP x REST (02/11/2026)

**Execução:** 22:41:13 a 22:45:15 (~4 min), `entrada.xlsx` com 1.117 casos, 4 workers, timeout 15 s, endpoints de produção.
**Evidências:** `resultado_novo.xlsx` (execução completa), `resultado_reteste.xlsx` (reteste dos 9 erros, 1 worker, timeout 30 s).

## Veredito

| Critério | Resultado |
|---|---|
| Decisão (Allow/Deny x true/false) | **100% compatível** nos 1.108 casos comparáveis; 0 FALHA |
| Divergências em Code, CodeID, CodeType, AccessMode | **0** |
| ERRO na execução completa | 9 casos (8 SOAP, 1 REST) |
| ERRO após reteste sequencial | **0** (9/9 OK, todos Deny/false) |
| Latência | REST claramente mais rápida (ver abaixo) |
| Veredito do script | REPROVADO só por causa dos 9 erros. O reteste os resolve, mas o script não mescla os dois relatórios |

**Parecer:** a **decisão** da REST é equivalente à do SOAP. O que ainda impede liberar sem ressalvas é o **conteúdo das mensagens** (item 1) e as pendências de segurança (itens 4 e 5), que este teste não cobre.

## Decisões (1.108 comparáveis)

| SOAP | REST | Casos |
|---|---|---|
| Deny | false | 677 |
| Allow | true | 431 |

Não houve nenhum caso Allow/false nem Deny/true.

## Latência

| | Média | p50 | p95 | p99 | Máx |
|---|---|---|---|---|---|
| SOAP | 667 ms | 360 ms | 1.677 ms | 7.777 ms | 22.254 ms |
| REST | 196 ms | 108 ms | 345 ms | 987 ms | 15.046 ms |

A REST é ~3,4x mais rápida na média e ~4,9x no p95. O objetivo de reduzir a latência foi atingido nesta amostra.
Ressalvas: o SOAP sempre roda antes da REST, e há uma nova sessão TLS por caso (viés já descrito no parecer). O máximo da REST (15.046 ms) é o timeout, ou seja, houve **1 timeout na REST** (linha 93), que não se repetiu no reteste.

## Erros da execução completa (9)

| Linhas | Lado | Causa | Reteste |
|---|---|---|---|
| 94, 95, 96, 97, 106 | SOAP | `ReadTimeout` (15 s) | OK |
| 445, 446, 447 | SOAP | `ConnectionResetError 10054` (conexão encerrada pelo servidor) | OK |
| 93 | REST | `ReadTimeout` (15 s) | OK |

As 8 falhas do SOAP e a da REST ocorreram em rajadas (linhas 93 a 97 e 445 a 447), compatíveis com instabilidade do legado e/ou saturação por 4 chamadas simultâneas. O teste não prova qual das duas. **Não é defeito de decisão**, mas o SOAP mostra fragilidade sob concorrência, e a REST teve um timeout que merece investigação nos logs do servidor (horário aproximado 22:41–22:42).

## Pontos que precisam de correção

### 1. [ALTO] Mensagens de bloqueio diferentes (156 dos 677 Deny, 23%)
O script não marca isso como divergência, porque não compara `Message`.

| blockReason REST | Mensagem SOAP | Mensagem REST | Casos |
|---|---|---|---|
| MEMBER_DENIED | Título cancelado | Acesso de membro negado (MEMBER) | 65 |
| MEMBER_DENIED | Título bloqueado | Acesso de membro negado (MEMBER) | 27 |
| MEMBER_DENIED | Sócio desativado | Acesso de membro negado (MEMBER) | 25 |
| MEMBER_DENIED | Título vencido | Acesso de membro negado (MEMBER) | 20 |
| BARCODE_NOT_FOUND | Código desconhecido | Código de acesso desconhecido | 10 |
| TITLETYPE_NOT_AUTHORIZED | BABA / MOTORISTA / ACOMPANHANTE… não permitido | Tipo de carteirinha não autorizado nesta portaria | 8 |
| TITLETYPE_NOT_AUTHORIZED | **Exame de piscina vencido em 06/05/2002** | Tipo de carteirinha não autorizado nesta portaria | 1 |

- Para sócios, a REST **perde a causa real** (cancelado, bloqueado, desativado, vencido) e devolve um texto genérico, com o tipo técnico "(MEMBER)" vazando na mensagem. Se a portaria ou o atendimento usa esse texto, há perda de informação.
- **Provável erro de regra (1 caso):** SOAP diz "Exame de piscina vencido" e a REST classifica como `TITLETYPE_NOT_AUTHORIZED`, sendo que existe o código `EXAM_REQUIRED` (105 casos). Precisa ser investigado: pode ser classificação incorreta do motivo.

### 2. [MÉDIO] Mensagem vazia nos Allow (431 de 431)
O SOAP retorna "Volte sempre" ou "Seja bem vindo". A REST retorna `message` nulo em **todos** os Allow. Se a catraca ou o painel exibe essa mensagem, ela some. Confirmar com o consumidor se é requisito.

### 3. [MÉDIO] Contrato
`CodeID`, `CodeType` e `RegisterType` continuam em PascalCase, enquanto os demais campos estão em camelCase. `RegisterType` só assume `Accessed` (431 Allow) ou nulo (677 Deny).

### 4. [ALTO, pendente] Segurança — não coberta por este teste
O script não envia credencial, e a REST respondeu `200` em 1.116 de 1.117 chamadas. Isso indica que **o endpoint não exige autenticação**. Confirmar e corrigir (401/403).
Para visitantes (225), a REST devolve `personName` (dado pessoal) que o SOAP não devolvia. Para sócios `personName` veio vazio (0 casos), então já existe tratamento diferenciado, mas deve ser decisão explícita (LGPD, minimização).

### 5. [ALTO, pendente] Não testado
Casos negativos e de segurança (código vazio, inválido, injeção, payload malformado, `AccessMode`/`Device` inválidos), fail-closed, rate limit, TLS/headers e carga. A planilha usa só 4 devices de piscina.

## Observações sobre o teste

- **Efeito colateral:** os 431 casos Allow foram chamados duas vezes (SOAP e REST) e todos retornaram Allow nos dois. Não apareceu bloqueio por reentrada nesses devices de piscina, o que sugere que o `Validate` não aplica anti-passback aqui. Isso vale só para este cenário e não elimina o risco em outros devices.
- **Arquivos gerados com dado pessoal:** `resultado_novo.xlsx` e `resultado_reteste.xlsx` contêm `personName` e respostas brutas. Não versionar nem compartilhar. `entrada.xlsx` continua modificado (`M`) no git, e todos os arquivos gerados estão não rastreados.
- **Duplicados:** a planilha tem 97 códigos repetidos e linhas com sobrenomes na coluna `ResultadoEsperado`, então a execução teve só 1 caso com resultado esperado.

## Ações recomendadas

1. Alinhar com o negócio se a mensagem de bloqueio/liberação é requisito; se for, devolver a causa específica na REST (`Título cancelado` etc.) e `message` nos Allow.
2. Investigar o caso "Exame de piscina vencido" classificado como `TITLETYPE_NOT_AUTHORIZED`.
3. Investigar o timeout da REST (linha 93) e as quedas do SOAP sob 4 workers.
4. Executar o teste de segurança (autenticação, casos negativos, fail-closed) antes de liberar.
5. Aplicar as correções do script do parecer anterior (comparar `Message`, sessão por worker, ordem alternada, percentis) e repetir a rodada.
