# Ticket 01 — Skill do padrão de manifests

Skill que empacota o **Padrão de Manifests da Metacortex** com dois modos: **escrita** (gera manifests conformes a partir de um projeto, lendo o código) e **conferência** (aponta cada violação de um manifesto existente, com regra e severidade).

## Onde está cada item do "Entregue"

| Item | Caminho |
|---|---|
| **A skill completa** (corpo, script e arquivos de apoio) | [`skill/SKILL.md`](skill/SKILL.md) · [`skill/scripts/validar_padrao.py`](skill/scripts/validar_padrao.py) · [`skill/references/mapeamento-trivy.md`](skill/references/mapeamento-trivy.md) · [`skill/references/exemplos-execucao.md`](skill/references/exemplos-execucao.md) |
| **A origem da skill** (fluxo que a gerou, ferramentas) | [`skill/SKILL.md` → seção "Origem"](skill/SKILL.md) |
| **Saída real — modo escrita** (manifests gerados) | [`execucao/modo-escrita/kube-news/`](execucao/modo-escrita/kube-news/) e [`execucao/modo-escrita/fake-shop/`](execucao/modo-escrita/fake-shop/) |
| **Saída real — modo conferência** (manifesto barrado) | [`execucao/modo-conferencia/manifesto-barrado.yaml`](execucao/modo-conferencia/manifesto-barrado.yaml) + laudo em [`skill/references/exemplos-execucao.md`](skill/references/exemplos-execucao.md) |
| **A curadoria** (script × instrução; Trivy; corpo × arquivos; exclusões; permissões) | [`skill/SKILL.md` → seções "Divisão de trabalho", "Curadoria", "Permissões"](skill/SKILL.md) + [`skill/references/mapeamento-trivy.md`](skill/references/mapeamento-trivy.md) |

## Resultado em números

- **Conferência** do manifesto barrado: **19 FALHAs + 4 avisos** (exit 1) — incluindo o segredo em texto puro (3.3) que o **Trivy não pega** e o seletor cruzado Service×Deployment (1.4).
- **Trivy** no mesmo manifesto: 18 KSVs de segurança genérica — complementar, não duplicada (mapeamento completo no reference).
- **Escrita**: 7 manifests para kube-news (nyx) e fake-shop (orion) — **0 falhas/0 avisos** no script, **10/10 válidos** no kubeconform, **0 HIGH/CRITICAL** no Trivy.
- **fake-shop**: as 3 decisões difíceis do ticket resolvidas e registradas — migração no start mantida no container, probes `tcpSocket` com justificativa (a app não tem healthcheck), senha só por `secretKeyRef`.

## Como reproduzir

```bash
# conferência
python skill/scripts/validar_padrao.py execucao/modo-conferencia/manifesto-barrado.yaml

# autoconferência dos manifests gerados
python skill/scripts/validar_padrao.py execucao/modo-escrita/kube-news
python skill/scripts/validar_padrao.py execucao/modo-escrita/fake-shop

# camadas externas
trivy config --severity HIGH,CRITICAL execucao/modo-escrita/
kubeconform -strict -summary -ignore-missing-schemas execucao/modo-escrita/
```

Requisitos: Python 3.10+ com `pyyaml`; Trivy (opcional, recomendado); kubeconform (opcional).
