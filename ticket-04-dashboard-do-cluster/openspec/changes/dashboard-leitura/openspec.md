# OpenSpec — ciclo T04 (dashboard-leitura)

## Proposta

**Por quê**: toda triagem começa com 6–10 comandos para montar o retrato de um namespace. O painel encurta os primeiros minutos de cada chamado.

**O que muda**: aplicação local somente leitura (contexto corrente do kubeconfig) com pods/deployments/services/eventos, filtro por namespace e busca.

## Tarefas

- [x] 1. PRD (7 RFs, 3 cenários de falha, garantia de leitura em código)
- [x] 2. TRD + 4 ADRs (linguagem, cliente, atualização, endpoints)
- [x] 3. Implementação: /api/namespaces + /api/overview (Promise.allSettled por recurso)
- [x] 4. UI com filtro/busca/refresh 15s
- [x] 5. verificar-leitura (varredura por chamadas de escrita — gate)
- [x] 6. Evidências contra o cluster real + 3 cenários de falha
- [x] 7. **ADR-05 (esta correção): recorte da primeira fatia**

## Specs

### Capability: retrato de namespace (somente leitura)
- **Requirement**: pods com estado, reinícios e motivo
  - Scenario: waiting.reason presente → estado = reason (CrashLoopBackOff, ImagePullBackOff…)
  - Scenario: Running mas ready=false → "Running (não-ready)" com motivo de probe
  - Scenario: lastState OOMKilled → motivo com exit code
- **Requirement**: campo ausente ≠ campo vazio
  - Scenario: readyReplicas ausente → 0 prontas
  - Scenario: EndpointSlice sem endpoints → SEM endpoints
- **Requirement**: falha do ambiente
  - Scenario: cluster inacessível → banner com ação, sem stack trace
  - Scenario: 401 → credencial-expirada com orientação
  - Scenario: 403 em um recurso → os demais continuam (erros por recurso)

## Arquivamento

**Status**: IMPLEMENTADO e validado (2026-10-01 no sandbox via API; 2026-10-01 QA visual na máquina do usuário — "tudo certo").
**Evidência**: `evidencia/` (overview real de nyx-prod com CrashLoopBackOff 7 reinícios; 3 cenários de falha).
**Correções da spec durante a implementação**: cliente k8s 0.x é posicional e retorna {response, body} (ADR-02 assumiu 1.x — registrado); emptyDir não cria subdiretórios (achado de runtime documentado no T01).
