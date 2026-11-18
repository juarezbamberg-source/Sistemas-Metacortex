# Evidência — capturas REAIS do painel (2026-11-18)

Origem: servidor `src/servidor.js` rodando de verdade, cada cenário com seu próprio
kubeconfig apontado por `KUBECONFIG`, contra o cluster `kind-metacortex` (v1.35.0)
atrás do túnel. Capturado com `curl` nas rotas do painel; o JSON é a resposta crua
do endpoint, sem edição.

| Arquivo | Kubeconfig usado | Resposta real |
|---|---|---|
| `cenario1-inacessivel.json` | server `https://127.0.0.1:1` (porta fechada) | `erros[]` = `cluster-indisponivel` (ECONNREFUSED) nos 5 recursos, HTTP 200 com payload de erro |
| `cenario2-token-expirado.json` | token inválido (`tokentinvalido...`) | `erros[]` = `credencial-expirada` (401) nos 5 recursos |
| `cenario3-acesso-negado.json` | token do SA `default` (sem RBAC de leitura) | `erros[]` = `acesso-negado` (403), **um por recurso** — a tela continua para o que é permitido |
| `overview-nyx-prod.json` | token do SA `triagem-ro` | 3 pods (`Running (não-ready)`, 349–371 reinícios, OOMKilled exit 137), 2 deployments (`nyx-api` 0/2 prontas), 2 services, 8 eventos, `erros: []` |

## O que isso prova (a pendência da vaia 2)

- Os 3 cenários de falha **não são respostas escritas à mão**: são a saída do código
  executado contra três ambientes degradados diferentes, capturada pelo `curl`.
- O tratamento é **por recurso** (`Promise.allSettled`): com 403 em tudo aparecem 5
  erros distintos e a resposta mantém a forma do contrato — a UI não quebra.
- `nyx-api` com **371 reinícios e 0/2 prontas** é o Chamado 1 do T02 visto pela
  perspectiva do painel: o mesmo OOMKilled, agora visível em um retrato de namespace.

## Reproduzir

O roteiro está versionado em [`../../execucao/capturar-cenarios.sh`](../../execucao/capturar-cenarios.sh)
(os kubeconfigs de cada cenário não são versionados — contêm tokens). Cada cenário sobe
o painel numa porta diferente, faz o `curl`, grava a resposta e derruba o processo.
