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
- **Ferramentas do fluxo**: Python 3.12 + PyYAML (script das regras), Trivy v0.74.0 (camada de segurança), kubeconform v0.8.0 (schema), gh CLI + git (entrega), pytest (validação)
