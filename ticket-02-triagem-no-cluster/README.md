# Ticket 02 — Skill de triagem de cluster

Método único de plantão (da Trinity/SRE) empacotado em skill: sintoma → camadas numa ordem fixa → cruzamento de fontes → veredito de 4 linhas. **Somente leitura** via mcp-server-kubernetes (modo não destrutivo).

## Onde está cada item do "Entregue"

| Item | Caminho |
|---|---|
| **A skill completa** | [`skill/SKILL.md`](skill/SKILL.md) |
| **A origem** (fluxo que a gerou, ferramenta) | [`skill/SKILL.md` → seção "Origem"](skill/SKILL.md) |
| **Saída real da triagem** (3 chamados, causas provadas) | [`execucao/triagem-3-chamados.md`](execucao/triagem-3-chamados.md) |
| **Os 3 chamados aplicados no cluster** | [`chamados/`](chamados/) |
| **Matriz de roteamento** (10 frases, erros e correções) | [`execucao/matriz-roteamento.md`](execucao/matriz-roteamento.md) |
| **Comparação com/sem skill** (2 casos: tokens/tempo/qualidade) | [`execucao/parte-c/comparacao.md`](execucao/parte-c/comparacao.md) |
| **A curadoria** (o que o método fixa × deixa ao agente; garantia de leitura) | [`skill/SKILL.md` → "O método", "Fora de escopo", "Permissões"](skill/SKILL.md) |

## Causas identificadas (prova real, cluster kind v1.35.0)

| Chamado | Causa | Prova |
|---|---|---|
| nyx-prod reinicia | OOMKill por limit 24Mi | `lastState: OOMKilled exitCode=137 restarts=3` |
| orion-stg parou após deploy | tag `v1.14.2` inexistente no registro | consulta ao Docker Hub: só `latest,v1,1,v26,v20` |
| nyx-stg 503 | selector `nyx-api` ≠ labels `nyxapi` | `Endpoints: <none>` com pods 2/2 Running |

## Garantia de não-escrita

- Servidor mcp-server-kubernetes em **modo não destrutivo** (sem capacidades de apply/delete/scale)
- A skill lista explicitamente o que **não** pede (apply, delete, patch, scale, exec) e o que faz com cada correção: **propõe, nunca aplica**
- Fluxo executado antes da skill existir provou o comportamento: nenhuma escrita em todo o T02

## Reproduzir

```bash
kubectl apply -f chamados/chamado1-nyx-prod.yaml
kubectl apply -f chamados/chamado2-orion-stg.yaml
kubectl apply -f chamados/chamado3-nyx-stg.yaml
# aguardar ~2 min: nyx-prod → OOMKilled; orion-web → ImagePullBackOff; nyx-stg → Running c/ Endpoints none
```

Obs. de ambiente: o cluster de laboratório não alcança o Docker Hub (EOF no auth.docker.io) — imagens carregadas com `docker save` + `ctr images import` no nó; `kube-news:v1` é arm64-only, usada `v1.0.0` (multi-arch) retaguada como `v1`.
