# Divergências SOAP x REST — Dispositivo Angelina (2026-11-10)

Fonte: `resultado_angelina.xlsx` (entrada.xlsx, 2234 casos, AngelinaEntrada1/2 e AngelinaSaida1/2).

## Resumo
| Status | Casos |
|---|---|
| OK | 1919 |
| FALHA (decisão diferente) | 3 |
| ERRO (ConnectTimeout no SOAP, sem comparação) | 312 |

## Divergências

### D1 — Linha 521, código 5041501, Entrance / AngelinaEntrada2
- SOAP: **Deny**, mensagem `RESTRIÇÃO`, CodeID 154865, Member
- REST: **allowed=true**, blockReason null, CodeID 154865, Member
- Impacto: liberação indevida (grave).

### D2 — Linha 575, código 1166701, Entrance / AngelinaEntrada2
- SOAP: **Deny**, mensagem `RESTRIÇÃO`, CodeID 15776121, Member
- REST: **allowed=true**, blockReason null, CodeID 15776121, Member
- Impacto: liberação indevida (grave).

D1 e D2 têm o mesmo sintoma: o SOAP nega por `RESTRIÇÃO` (mensagem de PRODUCT ou CHECK) e a REST não detecta a restrição.
O sócio é identificado corretamente (CodeID igual), então o problema é a regra de bloqueio, não a identidade.

### D3 — Linha 1902, código MO00002515, Exit / AngelinaSaida1
- SOAP: **Allow** ("Volte sempre"), CodeID 18234989, Member
- REST: **allowed=false**, `BARCODE_NOT_FOUND`, CodeID null, CodeType Anonymous
- Impacto: sócio barrado na saída (grave: ficaria preso no clube).
- Causa provável: `MO00002515` é um alias `AcessoSocio` (dbo.TitleFieldValues, Field=3002936) que ainda não está em `hebraica:access:code:MO00002515` no Redis. É lacuna de carga/sincronização do ETL, não de regra do serviço.
  O ETL já tem `MissingCodeRefreshService` para isso, e o teste dele usa exatamente este código.

### E — 312 erros
ConnectTimeout em `appmc.hebraica.org.br` (SOAP), 156 por leitor de entrada. Não valida nem reprova o REST. Reexecutar.

## Por que NÃO foi alterado código do serviço
- A causa de `RESTRIÇÃO` está registrada como **desconhecida** em `etl_process/docs/RELATORIO-CAUSA-RAIZ-2026-10-21.md` e `RELATORIO-COMPARACAO-SOAP-VS-API.md` (rodadas 10 e 11).
  Duas regras "razoáveis" de PRODUCT já causaram regressões de 76 para 2.099 casos no mesmo dia. Implementar sem dado do banco repetiria isso.
- Redis (192.168.100.222:6379) e o SQL Server não estão acessíveis desta máquina, então não foi possível ver o que o SOAP consulta para os dois sócios.
- D3 se corrige no ETL (carga do alias), não no `access-control-service`.

## Prompt para validar a regra no ETL

```
Você é um engenheiro de dados validando o ETL (etl_process, Spring Batch) que alimenta o Redis do access-control-service.
Objetivo: descobrir por que o legado MultiClubes (SOAP Validate) nega com a mensagem "RESTRIÇÃO" e o Redis/REST libera, e por que um alias AcessoSocio não está no Redis.

Contexto:
- Divergências no dispositivo Angelina (2026-11-10), todas Member:
  1) AccessCode 5041501 (CodeID 154865), Entrance, AngelinaEntrada2: SOAP Deny "RESTRIÇÃO", REST allowed=true.
  2) AccessCode 1166701 (CodeID 15776121), Entrance, AngelinaEntrada2: SOAP Deny "RESTRIÇÃO", REST allowed=true.
  3) AccessCode MO00002515 (CodeID 18234989), Exit, AngelinaSaida1: SOAP Allow, REST BARCODE_NOT_FOUND.
- Código relevante: MemberBulkLoaderService (loadProductBlocked, loadCheckRestricted, loadReturnedChecksCount, COALESCE(m.Barcode, alias.Value)), MemberCacheRefreshService, MissingCodeRefreshService.
- Histórico: PRODUCT por Parcels.DueDate (14 dias) foi tentado e revertido; CHECK usa Checks.Status = 4. A causa de "RESTRIÇÃO" segue em aberto.

Tarefas (somente leitura no SQL Server e no Redis; não alterar dados):
1. Para os CodeIDs 154865 e 15776121, consulte no SQL Server: Members, Titles (Status), Checks (todos os Status e datas), Parcels (vencidas, pagas, parciais), TitlePendencies, AccessControlPendencies, ProductByMember, AccessControlRules do controle da Angelina (PRODUCT e CHECK com Validate=1).
   Liste TODO dado do sócio que difere de sócios liberados no mesmo controle.
2. No Redis, mostre HGETALL hebraica:access:code:5041501 e :1166701 (campo blockedRules, returnedChecks, memberDenyMessage) e hebraica:access:control:{controlId}:rules.
   Confirme se o ETL gravou PRODUCT/CHECK como bloqueado ou não.
3. Para MO00002515, verifique no SQL Server se Members.Barcode é nulo e se o alias existe em dbo.TitleFieldValues (Field=3002936). Verifique no Redis se code:MO00002515 existe, se está em hebraica:access:missing/pending e se o MissingCodeRefreshService o processou.
4. Para cada caso, conclua uma de: (a) dado ausente no Redis (bug do ETL), (b) regra do legado não replicada (descreva a regra exata, com a query), (c) dado mudou entre as chamadas (timing).
5. Para (a) e (b), proponha o ajuste mínimo no ETL e um teste unitário. Valide a regra proposta contra uma amostra aleatória de pelo menos 200 sócios liberados e 200 negados por "RESTRIÇÃO" no SOAP, e informe a taxa de acerto. Só recomende implementar se for 100% nos casos conhecidos e sem novos falsos negativos.
6. Entregue: causa raiz, queries usadas, evidências (linhas retornadas) e o diff proposto. Não faça deploy.
```

## Próximo passo
Rodar o prompt acima com acesso ao SQL Server e ao Redis de produção/homologação. Com a regra confirmada, aplicar no ETL (e no serviço, se necessário) e reexecutar `entrada.xlsx` para chegar a 100% de paridade.

## Investigação (2026-11-11)

### D3 — CAUSA RAIZ ENCONTRADA E CORRIGIDA (ETL)
- O alias `AcessoSocio` do Member 18234989 está gravado no SQL Server como `'MO00002515 '` (com **espaço no final**, DATALENGTH 22 = 11 caracteres).
  O SQL Server ignora espaço à direita na comparação (por isso o SOAP acha o sócio), mas o ETL gravava a chave Redis `code:MO00002515 ` com o espaço, e o REST busca `code:MO00002515` e não encontra.
- Escopo: 9 de 42.868 aliases têm espaço sobrando; 0 `Members.Barcode`.
- Correção: `RTRIM(alias.Value)` / `RTRIM(tfv.Value)` em todas as queries SQL do ETL (94 ocorrências, 12 arquivos em `etl_process/src/main/java`).
  Efeito: a chave passa a ser `code:MO00002515`. Exige nova carga completa do ETL (e remoção da chave antiga com espaço) para surtir efeito.
- Não compilado: esta máquina não tem Java/JDK (JAVA_HOME ausente). Compilar e rodar os testes no ambiente de build.

### D1/D2 — causa NÃO encontrada
- Reproduzido de forma determinística (SOAP Deny "RESTRIÇÃO" x REST allowed=true, repetido em 2026-11-11).
- Sócios ativos (Members.Status=0, Titles.Status=0), sem suspensão, sem cheque Status 4, `BlockLists`/`BlockedPersons`/`AccessPenalties`/`Protections` vazias, pendência 14161549 já encerrada (EndAction preenchido), `AccessControlPendencies` vazia.
- Os dois títulos têm `Warning` preenchido, mas 4.827 de 11.367 títulos ativos também têm, então não discrimina.
- Mesmo mistério já registrado nas rodadas 10/11. Sem a regra real, não foi alterada nenhuma regra de bloqueio (evita repetir a regressão de 76 para 2.099 casos).
