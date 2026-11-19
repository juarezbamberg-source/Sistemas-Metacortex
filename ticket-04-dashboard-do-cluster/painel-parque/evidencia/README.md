# Evidência — capturas REAIS do painel

## Rodada de 2026-11-19 (cluster vivo via túnel)

Origem: `src/servidor.js` rodando no sandbox, com `KUBECONFIG` apontando para o
`kind-metacortex` da máquina do Juarez, acessado pelo túnel
`vienna-pairs-oak-gathered.trycloudflare.com` com token do SA `leao-admin`.
Resposta crua de `/api/overview`, gravada com `curl`, sem edição.

| Arquivo | Kubeconfig | O que a captura mostra |
|---|---|---|
| `cenario1-inacessivel.json` | server `https://127.0.0.1:1` | `cluster-indisponivel` em todos os 5 recursos, HTTP 200 com payload de erro |
| `cenario2-token-expirado.json` | token inválido | `credencial-expirada` (401) nos 5 recursos |
| `cenario3-acesso-negado.json` | SA `sem-permissao` (sem RBAC) | `acesso-negado` (403) **um por recurso** — a tela continua para o que é permitido |
| `overview-nyx-prod.json` | SA `leao-admin` | 4 pods; `nyx-api` **0/2 prontas, 382 reinícios**, estado `CrashLoopBackOff` |
| `overview-nyx-stg.json` | SA `leao-admin` | 3 pods, `nyx-api` **2/2**, todos `Running`, `temEndpoint: true` |
| `overview-chamado3-repro.json` | SA `leao-admin` | 2 pods, deploy **2/2 prontas** — e `temEndpoint: false` |
| `overview-orion-stg.json` | SA `leao-admin` | `orion-web` em `ImagePullBackOff`, 0/1 |
| `overview-nyx-dev.json` | SA `leao-admin` | kube-news 1/1 Running; **`temEndpoint: false`** |
| `overview-orion-dev.json` | SA `leao-admin` | fake-shop 1/1 Running; **`temEndpoint: false`** |

## A captura que prova o valor do cruzamento

Compare `overview-nyx-stg.json` com `overview-chamado3-repro.json`:

| | nyx-stg (corrigido) | chamado3-repro (defeituoso) |
|---|---|---|
| pods Running | 3 | 2 |
| deployment prontas | 2/2 | 2/2 |
| `temEndpoint` do Service | **true** | **false** |

Tudo igual na tela — pods prontos, deployment completo, nenhum evento Warning. A única
diferença é o campo de endpoint. É exatamente por isso que a skill fixa o cruzamento
Service × Pod como obrigatório para sintomas de "sem tráfego".

## Defeito encontrado nos workloads do T01 (não corrigido — registrado)

O painel mostrou `temEndpoint: false` para **kube-news** (nyx-dev) e **fake-shop**
(orion-dev). Fui verificar com o kubectl:

```
Service kube-news : selector = {app: kube-news}
Pods kube-news    : labels   = {app.kubernetes.io/name: kube-news, ...}
EndpointSlice     : kube-news-s55rl   ENDPOINTS=<unset>   (49d)
```

Os manifests gerados pela skill do T01 usam os rótulos recomendados
(`app.kubernetes.io/name`), mas o Service foi escrito com o rótulo antigo (`app`).
Resultado: **os dois workloads do T01 estão no ar mas não recebem tráfego nenhum** — o
mesmo defeito do Chamado 3, nos manifestos que a skill produziu.

**Lições**

1. É um achado legítimo contra a skill do T01: o validador checa que o Service casa com o
   *matchLabels do Deployment*, mas não que o `selector` do Service use o mesmo esquema de
   rótulos do template (`app` × `app.kubernetes.io/name`). Passa no validador e quebra em
   runtime — exatamente a categoria "runtime" que o `ACHADO-RUNTIME.md` já registrava.
2. O painel do T04 encontrou o defeito sozinho. Isso é a demonstração prática do valor que
   o ticket promete: um número que ninguém olha (`temEndpoint`) revelou um problema que
   não aparece em `kubectl get pods`.

Não corrigi os manifests porque isso muda o entregável do T01 — fica registrado para o
Juarez decidir. A correção seria alinhar o `selector` dos Services ao esquema de rótulos
do template.

## Rodada anterior (2026-11-18, capturas substituídas)

Os arquivos `cenario*` de 18/11 foram gerados com kubeconfigs apontando para um túnel que
já não existe e foram substituídos pelos desta rodada, que são do cluster vivo. Nada foi
mantido em duplicata.

## Como reconferir

O script de captura está versionado em [`../../execucao/capturar-cenarios.sh`](../../execucao/capturar-cenarios.sh).
Ele recebe o diretório com os kubeconfigs (não versionados — contêm tokens), sobe o painel
para cada cenário, faz o `curl` e derruba o processo.
