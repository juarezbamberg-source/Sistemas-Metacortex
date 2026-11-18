# TRD + ADRs — painel-parque (Ticket 04)

## ADR-01 — Linguagem e stack: Node.js (JavaScript puro) + Express + frontend leve (HTML/JS vanilla servido pelo Express)

**Contexto**: quem mantém é um time de infraestrutura (SRE/plataforma), não um time de produto frontend. O sandbox tem Node 20 e npx; o agente executa e valida local sem Docker.
**Alternativas descartadas**:
- *Python + Flask/FastAPI*: também familiar a infra, mas o cliente Kubernetes Python tipa menos bem os campos ausentes que o JS (`undefined` natural para campo que não vem) e o sandbox de execução do agente já usa Node para mcp-server-kubernetes — consistência de stack entre as skills e o painel reduz o custo de manutenção.
- *React/Next*: deixa o projeto 10× maior para uma tela única de leitura; overkill. Ganho real seria componentização — perdido em build tooling.
- *TypeScript*: avaliado e **descartado na implementação** — o código entregue é JavaScript puro ('use strict' + JSDoc nos pontos críticos), porque o painel é pequeno (2 arquivos JS) e o custo de toolchain (tsconfig, build) não se paga; registrado aqui para alinhar ADR × código (o rascunho original dizia TypeScript).
**Ganho**: uma dependência de runtime (`express`), zero build para o frontend. **Perda**: sem componentes prontos (tabelas/filtros escritos à mão — aceitável em tela única).

## ADR-02 — Cliente de API: cliente oficial (@kubernetes/client-node)

**Contexto**: 3 caminhos possíveis: cliente oficial JS, `kubectl` como subprocesso, HTTP direto ao apiserver.
**Alternativas descartadas**:
- *kubectl subprocesso*: resolve autenticação/contexto de graça, mas cada chamada é um processo novo (spawn), parse de texto sem tipagem, e dificulta watch/inferência de campos ausentes. Ganho: zero código de auth. Perda: performance, parsing frágil, controle de erro pior.
- *HTTP direto*: máximo controle, mas reescrever descoberta de API, TLS/CA, rotatividade de token e serialização — alto custo de manutenção, e é exatamente o que o cliente oficial existe para abstrair.
**Ganho (cliente oficial)**: kubeconfig lido do caminho padrão (`KUBECONFIG`), tipagem fraca porém direta (JSON → objetos JS), suporte a watch e cluster contexts. **Perda**: dependência pesada e camada de abstração quando algo quebra.

## ADR-03 — Atualização: consulta em intervalo fixo (15s) + refresh manual

**Contexto**: sob demanda (só botão) deixa a tela velha sem o operador perceber; watch (streaming) é o mais atual, mas mantém conexão aberta por recurso (4 watches) e reacende o problema de reconexão ao túnel de laboratório.
**Alternativas descartadas**:
- *Sob demanda*: simples, mas o painel envelhece silenciosamente.
- *Watch*: dados sempre atuais; perde em carga persistente no apiserver, complexidade de reconexão (4 streams, backoff, resync), e num cluster de laboratório via túnel a conexão longa é a primeira a quebrar.
**Ganho (intervalo)**: 4 requisições GET a cada 15s (carga trivial), erros de rede aparecem como "última atualização há Xs" com banner, reconexão natural. **Perda**: até 15s de atraso — aceitável para um retrato, não para um monitor.

## ADR-04 — Fonte dos endpoints: EndpointSlice (discovery.k8s.io/v1), com fallback Endpoints IMPLEMENTADO

**Contexto**: Endpoints (v1) está descontinuado desde 1.33 (aviso do próprio kubectl); EndpointSlice é o caminho atual.
**Alternativa descartada**:
- *Só Endpoints*: funciona até ~1.33 e em clusters antigos, mas o código nasce obsoleto — o aviso do kubectl já apareceu no T02 (`Warning: v1 Endpoints is deprecated`).
**Ganho (EndpointSlice)**: código viável no 1.33+ (o lab é 1.35), granularidade por porta, sem aviso de deprecação. **Perda**: clusters pré-1.21 não têm.
**Fallback (verificável no código)**: em `servidor.js`, `lerNamespace()` — quando `discoveryV1.listNamespacedEndpointSlice(ns)` rejeita, o painel chama `coreV1.listNamespacedEndpoints(ns)` e calcula `temEndpoint` por `e.subsets.length > 0`; o erro do EndpointSlice fica registrado em `erros[]`. Sem o fallback, um cluster antigo mostraria TODOS os services como "sem endpoint" — informação errada para quem triagem faz.

## Modelo de dados e endpoints do painel

```
GET /api/namespaces                  → [{name}]
GET /api/overview?namespace=X        → { pods: [...], deployments: [...], services: [...], eventos: [...], erros: [...] }
```

- `pods[].estado` derivado: `Running/Ready`, `Running (não-ready)` com motivo de probe, `waiting.reason` (CrashLoopBackOff, ImagePullBackOff...), `lastState.terminated.reason` (OOMKilled com exit code), restarts.
- `deployments[]`: `{nome, desejadas: spec.replicas ?? 1, prontas: status.readyReplicas ?? 0}` — campo ausente = 0 (regra do enunciado).
- `services[]`: `{nome, temEndpoint, portas}` — campo ausente = sem endpoint.
- `events[]`: `{tipo, motivo, objeto, mensagem, contagem, ultimaOcorrencia}` ordenado Warning>Normal, mais recente primeiro.
- Erros: `{codigo: "cluster-indisponivel"|"credencial-expirada"|"acesso-negado", mensagem}` — a UI traduz para mensagem acionável.

## Garantia de leitura (código)

- Única dependência de rede: `@kubernetes/client-node`; chamadas restritas a `listNamespaced*`/`list*` (GET).
- Roteiro de verificação: `grep -rnE "\.apply|\.delete|\.patch|\.create|\.replace" src/` deve retornar vazio — verificado no teste.

## ADR-05 — Recorte da primeira fatia: retrato de UM namespace, sem watch, sem histórico

**Contexto**: o PRD lista tudo que a tela "precisa no mínimo" — mas tentar entregar tudo de uma vez (multicluster, watch, histórico, detalhe por pod, logs) faria a primeira versão atrasar e o time não validaria o valor real cedo.

**Alternativas consideradas**:
1. **Fatia mínima vertical (escolhida)**: retrato de UM namespace (pods/deployments/services/eventos + filtro + busca + 3 cenários de falha), atualização por intervalo, contexto corrente fixo.
2. **Fatia por camada**: primeiro só pods, depois services, depois eventos — cada fatia é horizontal e nenhuma entrega valor sozinha. Descartada: fatia vertical entrega valor completo por vez.
3. **Fatia completa de leitura + já com watch**: inclui streaming de mudanças desde a v1. Descartada: watch multiplica a complexidade de reconexão (4 streams sobre túnel) antes de o time validar o valor do retrato estático.

**Decisão**: fatia 1 = retrato vertical de um namespace, somente leitura, intervalo fixo, com os 3 cenários de falha TRATADOS desde o início (não são "detalhe": são requisito de plantão). Ficam para fatias seguintes: watch/streaming, detalhe por pod (logs/describe), histórico de reinícios, e qualquer multicluster (fora de escopo por decisão do PRD).

**Consequências**: + a primeira versão foi entregue e validada ponta a ponta em uma sessão; − o operador que quiser comparar dois namespaces alterna no filtro (aceitável para o retrato de plantão).
