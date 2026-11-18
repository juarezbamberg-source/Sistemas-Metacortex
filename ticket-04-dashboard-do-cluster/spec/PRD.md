# PRD — Ticket 04: Dashboard de leitura do cluster (parque de K8s)

**Projeto**: `painel-parque` — aplicação local de leitura que mostra o retrato de um namespace
**Data**: 2026-09-30 · **Autor**: leao (agente) a pedido de Juarez Bamberg · **Status**: proposto

## 1. Problema

Toda triagem na Metacortex começa com a mesma sequência de 6–10 comandos para montar o retrato de um namespace (pods com estado/reinícios, deployments com réplicas, services com endpoint, eventos recentes). Isso custa os primeiros minutos de cada chamado e varia de plantonista para plantonista (ver Ticket 02, Parte C).

## 2. Objetivo

Aplicação local, **somente leitura**, que ao abrir mostra:
- namespaces do cluster
- pods: estado, contagem de reinícios, motivo quando em falha (ex.: `CrashLoopBackOff`, `OOMKilled`)
- deployments: réplicas prontas/desejadas
- services: se têm endpoint (se o campo `subsets` não vem, **não há endpoint** — campo ausente ≠ vazio)
- eventos recentes do namespace
- **filtro por namespace** e **busca por nome**

Acesso pelo **contexto corrente do kubeconfig** no momento em que sobe. Multicluster fora de escopo (trocar de contexto é tarefa de fora da aplicação, como hoje).

## 3. Comportamento quando o ambiente falha (requisitos de tela)

- **Cenário 1**: contexto apontando para cluster inacessível → mensagem clara (sem stack trace, sem tela em branco), com dica ("verifique o túnel/VPN e o contexto").
- **Cenário 2**: credencial expirada (401) → mensagem que orienta recriar o token/credencial.
- **Cenário 3**: permissão negada para um tipo de recurso (403) num contexto de leitura restrita → **os outros recursos continuam**: a tela degrada por recurso, não desliga tudo.

## 4. Restrição e garantia de leitura

Nenhuma escrita: nada de apply/delete/patch/scale/exec. A garantia precisa estar **no projeto** (não só na intenção): cliente configurado para métodos GET/watch apenas, e/ou RBAC de leitura documentada no README (a chave do lab é cluster-admin porém a aplicação nunca emite verbo de escrita — garantia em código: a única chamada de rede é `GET`).

## 5. Requisitos funcionais

| ID | Requisito |
|---|---|
| RF-01 | Listar namespaces do cluster |
| RF-02 | Por namespace: pods com estado, restarts, motivo de falha |
| RF-03 | Deployments com réplicas prontas/desejadas (tratando `readyReplicas` ausente = 0) |
| RF-04 | Services com indicador tem/nao-tem endpoint (via EndpointSlice; campo `endpoints` ausente = sem endpoint) |
| RF-05 | Eventos recentes do namespace (warning primeiro, depois normal, mais recentes primeiro) |
| RF-06 | Filtro por namespace + busca por nome (pods/services/deployments) |
| RF-07 | Tratar os 3 cenários de falha do ambiente com mensagens acionáveis |

## 5.1 Vocabulário — o que "pronta" significa (definição que o painel usa)

A palavra "pronta" aparece em quatro níveis diferentes e o painel **não pode misturá-los**.
Esta é a definição que o código implementa, escrita aqui porque um número exibido sem
definição é um número que o plantonista interpreta errado.

| Nível | Campo de origem | "pronta" significa | Como aparece na tela |
|---|---|---|---|
| **Container** | `containerStatuses[i].ready` | o `readinessProbe` do container passou (ou, sem probe declarada, o container está rodando) — o kubelet o inclui nos endpoints do Service | é o que decide se o pod conta como pronto; não é mostrado como número |
| **Pod** | soma dos containers | **todos** os containers estão `ready` — um sidecar não-pronto deixa o pod inteiro não-pronto | estado `Running (não-ready)` + motivo (ex.: "probe não passando"), distinguindo de `Running` |
| **Deployment (contagem)** | `status.readyReplicas` | número de pods cujo conjunto de containers está todo pronto; **campo ausente = 0** (nunca "desconhecido") | `prontas/desejadas`, ex.: `0/2` |
| **Service (endpoint)** | EndpointSlice `endpoints[].conditions.ready` | o endpoint existe **e** está `ready` (o Service só roteia para pronto) | `temEndpoint: true/false` |

Regras de leitura que decorrem disso:

1. **`ready != fase`**: um pod em fase `Running` pode ter `ready: false`. O painel mostra
   `Running (não-ready)` — jamais `Running` puro, que faria o plantonista achar que está tudo bem.
2. **Ausente ≠ zero ≠ vazio**: `readyReplicas` ausente → `0`; `endpoints` ausente no slice → sem
   endpoint; `subsets` ausente no Endpoints (fallback) → sem endpoint. Nunca se infere "ok" de
   um campo que o apiserver não mandou.
3. **Reinício não é falha de readiness**: `restartCount` alto com `ready: true` é pod pronto e
   instável — o painel mostra os dois números separados de propósito.
4. **`desejadas`** é `spec.replicas` e, quando ausente, vale **1** (default do Kubernetes), não 0 —
   o zero é do lado das prontas.

## 6. Requisitos não funcionais

- **RNF-01** Só leitura (garantia em código).
- **RNF-02** Roda local com o kubeconfig da máquina (sem credencial embutida).
- **RNF-03** Atualização por **consulta em intervalo** (padrão 15s) com botão de refresh manual (ADR-03).
- **RNF-04** Sem tela em branco nem stack trace: todo erro vira mensagem.
- **RNF-05** Código executável do sandbox (sem docker; Node 20 disponível).

## 7. Decisões em aberto (ADRs)

1. Linguagem e stack (quem mantém é time de infraestrutura)
2. Cliente de API: cliente oficial vs. kubectl subprocesso vs. HTTP direto
3. Atualização: sob demanda vs. intervalo fixo vs. watch
4. Endpoints vs. EndpointSlice

## 8. Critérios de pronto

- Rodando contra o kind-metacortex com o workload do Ticket 01 (nyx-dev + orion-dev), mostra os 2 namespaces, pods, deploy, services e eventos.
- Os 3 cenários de falha produzem mensagem acionável (testados de verdade: contexto inacessível, token revogado, 403 parcial).
- Nenhuma operação de escrita em todo o código (grep por apply/delete/patch = zero, fora comentários).
