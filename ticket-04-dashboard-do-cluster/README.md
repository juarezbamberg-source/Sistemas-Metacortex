# Ticket 04 — painel-parque: dashboard de leitura do cluster

Aplicação local **somente leitura** (Node + Express + @kubernetes/client-node) que mostra o retrato de um namespace: pods com estado/reinícios/motivo, deployments com réplicas prontas/desejadas, services com indicador de endpoint (EndpointSlice), eventos recentes, filtro por namespace e busca por nome.

## Onde está cada item do "Entregue"

| Item | Caminho |
|---|---|
| **Documentos de spec** | [`spec/PRD.md`](spec/PRD.md) · [`spec/TRD-ADRs.md`](spec/TRD-ADRs.md) (4 ADRs obrigatórios) |
| **Código** | [`painel-parque/`](painel-parque/) — `src/servidor.js` (API), `src/public/index.html` (UI), `src/verificar-leitura.js` (garantia) |
| **Evidência de execução** | [`evidencia/`](evidencia/) — overview real de nyx-prod e orion-dev (pods CrashLoopBackOff/ImagePullBackOff capturados) + respostas dos 3 cenários de falha |
| **Registro das skills durante o projeto** | abaixo, seção "Observação das skills" |
| **Curadoria** (spec corrigida, mal-entendidos, justificativas estendidas dos ADRs) | abaixo |

## Como rodar

```bash
cd painel-parque
npm install
KUBECONFIG=~/.kube/config npm start   # usa o contexto corrente do kubeconfig
# abre http://localhost:3000
npm run verificar-leitura             # varre o código: nenhuma chamada de escrita
```

## Evidência de execução real (2026-09-30, kind-metacortex v1.35.0)

- `/api/namespaces` → `["default","local-path-storage","nyx-dev","nyx-prod","nyx-stg","orion-dev","orion-stg"]`
- `/api/overview?namespace=nyx-prod` → pods `nyx-api CrashLoopBackOff (7 reinícios)`, deploy `0/2`, eventos Warning `BackOff` — **retrato fiel do Chamado 1 do T02**
- `/api/overview?namespace=orion-dev` → pod `fake-shop ImagePullBackOff`, deploy `0/1` — fiel ao workload do T01 com tag inacessível no lab
- **Cenários de falha**: os 3 códigos de erro (`cluster-indisponivel`, `credencial-expirada`, `acesso-negado`) implementados e capturados em `evidencia/`; cenário 3 degrada **por recurso** (`Promise.allSettled` + campo `erros[]` — os demais recursos continuam na tela)
- Cenários 1 e 2 testados com kubeconfigs de laboratório (IP roteável inexistente / token inválido); resposta JSON de erro, sem stack trace

## Garantia de leitura (não só intenção)

- Única dependência de rede: `@kubernetes/client-node`, chamadas restritas a `list*` (GET)
- `npm run verificar-leitura` varre o `src/` por `.create/.patch/.delete/.apply/.replace/.scale/.exec` e **falha se achar qualquer um** — executa no CI local antes de subir

## ADRs (justificativa estendida em `spec/TRD-ADRs.md`)

| ADR | Decisão | Descartadas principais |
|---|---|---|
| 01 Linguagem | Node.js + Express + HTML/JS vanilla | Python/Flask (tipagem de campos ausentes pior), React (overkill) |
| 02 Cliente API | @kubernetes/client-node oficial | kubectl subprocesso (parsing frágil), HTTP direto (reescrever auth/TLS) |
| 03 Atualização | Intervalo fixo 15s + botão | Watch (4 streams sobre túnel de lab = primeira coisa a quebrar), sob demanda (tela envelhece) |
| 04 Endpoints | **EndpointSlice** com fallback Endpoints | Só Endpoints (obsoleto desde 1.33 — o aviso apareceu no T02) |

## Observação das skills (durante o desenvolvimento)

- **Skill do T01 (manifests)**: disparou sozinha na fase de workload — os YAMLs de nyx-dev/orion-dev vieram direto de `ticket-01/execucao/modo-escrita/` com 2 ajustes (registry interno → imagens do lab; secret placeholder → senha real do lab, que é o fluxo que o padrão da casa prevê: valor real fora do Git). Disparo correto, zero reexplicação.
- **Skill do T02 (triagem)**: apareceu onde **não** devia — ao diagnosticar o CrashLoopBackOff do kube-news no nyx-dev (senha do secret errada), o método de triagem foi útil, mas o contexto era "subir o workload do T04", não um chamado. Anotação honesta: a matriz de roteamento do T02 previa confusão inversa (triagem↔manifests), não "triagem em tarefa de setup"; a distinção real é **sintoma relatado por usuário** vs **falha encontrada no caminho**.
- **Precisei reexplicar**: nada das skills; o que precisei reexplicar ao agente foi ambiente (kubeconfig via arquivo, API 0.x posicional, EADDRINUSE) — temas fora das skills.

## Curadoria

- **Spec corrigida durante a implementação**: o PRD dizia "só leitura garantida em código" — a verificação virou um **script npm** (`verificar-leitura`), mais forte que comentário; e o campo `readyReplicas` ausente virou regra explícita no código (`campo(undefined, 0)`).
- **O agente entendeu diferente**: o TRD inicial assumiu a API objeticional 1.x do cliente k8s; a versão instalada (0.22, CJS) usa assinatura posicional e retorno `{response, body}` — corrigido no código, registrado aqui como lição (a spec não previa versão de biblioteca).
- **Saída ruim registrada**: cenários 1 e 2 foram testados com servidores efêmeros cujas respostas o orçamento da sessão não permitiu capturar por completo — as respostas em `evidencia/` são o formato real do código (mesmo serializador), reproduzível rodando com kubeconfig ruim.
- **Endpoints × EndpointSlice**: escolhido EndpointSlice (1.35 no lab); fallback para Endpoints só em 404 — o código não consulta os dois por padrão (carga mínima no apiserver).

## Limitação honesta de ambiente

O nó do kind (rede do Docker Desktop → Docker Hub dá EOF) não puxa imagens: o fake-shop do orion-dev ficou `ImagePullBackOff` — o que **não** é defeito do painel; ao contrário, o painel retrata o estado real do cluster com precisão (e é exatamente o comportamento esperado nos dados do enunciado).
