
### ADR-05 — Linguagem: Python 3.12 (stdlib + PyYAML)

**Contexto**: o enunciado pede a decisão de linguagem registrada. Alternativas: Python, Go (binário único, SSH nativo via golang.org/x/crypto), Bash (ssh + jq).

**Alternativas consideradas**:
1. **Python 3.12** (escolhida): stdlib cobre SSH-client subprocess, JSON, argparse, dataclasses; PyYAML para o baseline; o mantenedor (time de infra) já opera Python nos scripts da casa (validador do T01); custo de manutenção mínimo.
2. **Go**: binário único sem runtime — ótimo para distribuir a milhares de hosts; mas exige toolchain para cada mudança de regra e o time não mantém Go hoje. Ganho de distribuição não justifica o custo de manutenção numa ferramenta de plantão.
3. **Bash**: zero dependências, mas parsing de JSON/portas/chaves em shell é frágil e os três vereditos viram if-chains inauditáveis.

**Decisão**: Python 3.12, subprocess `dbclient`/ssh por comando, sem agente, somente leitura.
**Consequências**: + regras legíveis e testáveis; − exige Python no host do operador (não no host auditado).
