# Desafio 03 — Parque da Metacortex

Entregas do Desafio 03 da pós em Engenharia Cloud com IA: skills de manifests e triagem, ferramenta de inventário de VM e dashboard do cluster.

## Tickets

| Ticket | Tema | Pasta | Status |
|---|---|---|---|
| 01 | Skill do padrão de manifests (escrita + conferência) | [ticket-01-padrao-de-manifests/](ticket-01-padrao-de-manifests/) | ✅ entregue |
| 02 | Skill de triagem de cluster + roteamento + medição | [ticket-02-triagem-no-cluster/](ticket-02-triagem-no-cluster/) | 🔜 |
| 03 | Inventário e drift de VM por SSH (spec + código) | [ticket-03-inventario-de-vm/](ticket-03-inventario-de-vm/) | 🔜 |
| 04 | Dashboard de leitura do cluster (spec + código) | [ticket-04-dashboard-do-cluster/](ticket-04-dashboard-do-cluster/) | 🔜 |

## Agente e modelos usados

- **Agente**: leao (assistente pessoal do Juarez, sandbox arm64 Linux)
- **Modelo**: GLM (via Z.ai)
- **Ferramentas do fluxo**: Python 3.12 + PyYAML (script das regras), Trivy v0.74.0 (camada de segurança), kubeconform v0.8.0 (schema), gh CLI + git (entrega), pytest (validação)
