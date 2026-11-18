# OpenSpec — ciclo T04 (dashboard-leitura)

## Brainstorm (transcrição das decisões reais — 2026-09-30)

Perguntas feitas ao dono antes da spec:
1. **Cluster para o painel**: o mesmo kind-metacortex do T02 (workload do T01 já aplicado em nyx-dev/orion-dev)? **Decisão: sim** — sem cluster novo.
2. **Frontend**: React ou algo leve? **Decisão (minha, aceita pelo dono no plano): HTML/JS vanilla servido pelo Express** — tela única de leitura.
3. **Atualização**: watch vs intervalo? Levado ao ADR-03 (intervalo 15s) — o brainstorm não fechou; virou decisão registrada com alternativas descartadas.

Pontos em aberto: nenhum — o arco seguiu ao PRD com as 5 decisões em aberto listadas para ADRs.

## Proposta

**Por quê**: toda triagem começa com 6–10 comandos para montar o retrato de um namespace. O painel encurta os primeiros minutos de cada chamado.

**O que muda**: aplicação local somente leitura (contexto corrente do kubeconfig) com pods/deployments/services/eventos, filtro por namespace e busca.

## Tarefas

- [x] 1. PRD (7 RFs, 3 cenários de falha, garantia de leitura em código)
- [x] 2. TRD + 5 ADRs (linguagem, cliente, atualização, endpoints, recorte da fatia)
- [x] 3. Implementação: /api/namespaces + /api/overview (Promise.allSettled por recurso)
- [x] 4. UI com filtro/busca/refresh 15s
- [x] 5. verificar-leitura (varredura por chamadas de escrita — gate)
- [x] 6. Evidências contra o cluster real + 3 cenários de falha
- [x] 7. ADR-05 (recorte da primeira fatia)
- [x] 8. (vaia 2) ADR-01 alinhado ao código (JavaScript puro, TypeScript descartado e registrado); ADR-04 com fallback Endpoints IMPLEMENTADO no código

## Specs

### Capability: retrato de namespace (somente leitura)
- **Requirement**: pods com estado, reinícios e motivo
  - Scenario: waiting.reason presente → estado = reason (CrashLoopBackOff, ImagePullBackOff…)
  - Scenario: Running mas ready=false → "Running (não-ready)" com motivo de probe
  - Scenario: lastState OOMKilled → motivo com exit code
- **Requirement**: campo ausente ≠ campo vazio
  - Scenario: readyReplicas ausente → 0 prontas
  - Scenario: EndpointSlice sem endpoints → SEM endpoints (fallback: Endpoints v1 com subsets)
- **Requirement**: falha do ambiente
  - Scenario: cluster inacessível → banner com ação, sem stack trace
  - Scenario: 401 → credencial-expirada com orientação
  - Scenario: 403 em um recurso → os demais continuam (erros por recurso)

## Arquivamento

**Status**: IMPLEMENTADO e validado (2026-10-01 no sandbox via API; QA visual na máquina do usuário — "tudo certo").
**Evidência**: `evidencia/` (overview real de nyx-prod com CrashLoopBackOff; 3 cenários de falha).
**Correções da spec durante a implementação**: cliente k8s 0.x é posicional e retorna {response, body} (ADR-02 assumiu 1.x — registrado); emptyDir não cria subdiretórios (achado de runtime documentado no T01); (vaia 2) ADR-01 dizia TypeScript mas o código é JS puro — ADR corrigido; ADR-04 prometia fallback Endpoints — agora implementado no servidor.js.
