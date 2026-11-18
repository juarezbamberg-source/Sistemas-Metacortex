# Desafio 03 — Parque da Metacortex

[![Validar YAMLs](https://github.com/juarezbamberg-source/Sistemas-Metacortex/actions/workflows/validar-yamls.yml/badge.svg)](https://github.com/juarezbamberg-source/Sistemas-Metacortex/actions/workflows/validar-yamls.yml) ![Status](https://img.shields.io/badge/status-conclu%C3%ADdo-4c1) ![Tickets](https://img.shields.io/badge/tickets-4%2F4-4c1) ![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) ![Node](https://img.shields.io/badge/Node.js-20-339933?logo=node.js&logoColor=white) ![Kubernetes](https://img.shields.io/badge/Kubernetes-1.35-326CE5?logo=kubernetes&logoColor=white) ![License](https://img.shields.io/badge/license-MIT-blue)

Entregas do Desafio 03 da pós em Engenharia Cloud com IA: skills de manifests e triagem, ferramenta de inventário de VM e dashboard do cluster.

## Tickets

| Ticket | Tema | Pasta | Status |
|---|---|---|---|
| 01 | Skill do padrão de manifests (escrita + conferência) | [ticket-01-padrao-de-manifests/](ticket-01-padrao-de-manifests/) | ✅ entregue |
| 02 | Skill de triagem de cluster + roteamento + medição | [ticket-02-triagem-no-cluster/](ticket-02-triagem-no-cluster/) | ✅ entregue |
| 03 | Inventário e drift de VM por SSH (spec + código) | [ticket-03-inventario-de-vm/](ticket-03-inventario-de-vm/) | ✅ entregue |
| 04 | Dashboard de leitura do cluster (spec + código) | [ticket-04-dashboard-do-cluster/](ticket-04-dashboard-do-cluster/) | ✅ entregue |

## Bônus — marketing pessoal

- [**Dar acesso não é dar método** — post com as três lições do desafio](bonus/post-dar-acesso-nao-e-dar-metodo.md)

## Agente e modelos usados

- **Agente**: leao (assistente pessoal do Juarez, sandbox arm64 Linux)
- **Modelo**: GLM (via Z.ai)
- **Ferramentas do fluxo**: Python 3.12 + PyYAML (script das regras e o metavm), Trivy v0.76.2 (camada de segurança), kubeconform v0.7.0 (schema, a mesma versão que o CI baixa), Node 20 (painel), git (entrega), pytest-compatível (`python3 tests/test_validador.py`)

## O que o CI verifica

O workflow `validar-yamls.yml` roda em todo push que toque `.yaml/.yml/.py/.js` e tem 3 jobs:

| Job | Verifica |
|---|---|
| `manifests` | kubeconform `-strict` nos 10 arquivos (25 recursos), regras da casa em kube-news e fake-shop, e o **teste negativo** (o manifesto barrado tem de reprovar) |
| `ferramentas` | metavm carrega, o baseline tem as **11 regras** do enunciado, os dois laudos versionados respeitam o contrato (`veredito` válido, `encontrado` nunca com texto de veredito, todo `nao_verificado` com motivo) e **exec1 ≡ exec2** (idempotência) |
| `painel` | sintaxe do `servidor.js`, `npm run verificar-leitura` (nenhuma chamada de escrita) e o contrato das capturas (cada cenário com o código de erro certo; os 3 overviews com pods) |

## O que está provado com execução real

- **T01**: manifesto barrado → **21 falhas / 5 avisos** (antes 19, sem as regras de produção); kube-news e fake-shop → aprovados; Trivy no barrado → **18 misconfigurations** (3 HIGH).
- **T02**: `kubectl_scale` via MCP → **Forbidden** pelo RBAC `triagem-ro`; leitura via `kubectl_describe` funcionando.
- **T03**: laudo real com exit **1**, host morto com exit **2**, duas execuções idênticas.
- **T04**: 3 cenários de falha capturados do servidor rodando (inacessível / 401 / 403 por recurso) e overview real do `nyx-prod` (`nyx-api` 371 reinícios, 0/2 prontas, OOMKilled exit 137).

