# Ticket 04 — painel-parque: dashboard de leitura do cluster

Aplicação local **somente leitura** (Node + Express + @kubernetes/client-node) que mostra o retrato de um namespace: pods com estado/reinícios/motivo, deployments com réplicas prontas/desejadas, services com indicador de endpoint (EndpointSlice), eventos recentes, filtro por namespace e busca por nome.

## Onde está cada item do "Entregue"

| Item | Caminho |
|---|---|
| **Documentos de spec** | [`spec/PRD.md`](spec/PRD.md) · [`spec/TRD-ADRs.md`](spec/TRD-ADRs.md) (**5 ADRs** — inclui o recorte da primeira fatia) |
| **Definição de "pronta"** | [`spec/PRD.md` §5.1](spec/PRD.md) — os 4 níveis (container / pod / deployment / service) e as 4 regras de leitura |
| **Ciclo OpenSpec versionado** (proposta, tarefas, specs, arquivamento) | [`openspec/changes/dashboard-leitura/openspec.md`](openspec/changes/dashboard-leitura/openspec.md) |
| **Código** | [`painel-parque/`](painel-parque/) — `src/servidor.js` (API), `src/public/index.html` (UI), `src/verificar-leitura.js` (garantia) |
| **Evidência de execução (capturas reais)** | [`painel-parque/evidencia/`](painel-parque/evidencia/) — ver o README de lá |
| **Script que gerou as capturas** | [`execucao/capturar-cenarios.sh`](execucao/capturar-cenarios.sh) |
| **Registro das skills durante o projeto** | abaixo, seção "Observação das skills" |
| **Curadoria** (spec corrigida, mal-entendidos, justificativas estendidas dos ADRs) | abaixo |

## Como rodar

```bash
cd painel-parque
npm install
KUBECONFIG=~/.kube/config PORTA=3000 node src/servidor.js
# abre http://localhost:3000
```

## Evidência de execução — capturas REAIS (2026-11-18)

Todas as capturas vêm do `src/servidor.js` **rodando de verdade**, cada cenário com o seu
próprio `KUBECONFIG`, contra o `kind-metacortex` (v1.35.0) atrás do túnel. O JSON é a resposta
crua do endpoint `/api/overview`, gravada com `curl` e sem edição.

| Arquivo (em `painel-parque/evidencia/`) | Kubeconfig | Resposta real |
|---|---|---|
| `cenario1-inacessivel.json` | server `https://127.0.0.1:1` (porta fechada) | `cluster-indisponivel` (ECONNREFUSED) nos 5 recursos |
| `cenario2-token-expirado.json` | token inválido | `credencial-expirada` (401) nos 5 recursos |
| `cenario3-acesso-negado.json` | SA `default`, sem RBAC de leitura | `acesso-negado` (403), **um erro por recurso** — a tela continua para o que é permitido |
| `overview-nyx-prod.json` | SA `triagem-ro` | 3 pods, `nyx-api` **371 reinícios / 0 de 2 prontas / OOMKilled exit 137**, 8 eventos |
| `overview-nyx-dev.json` | SA `triagem-ro` | kube-news e kube-news-postgres 1/1 — workload do T01 |
| `overview-orion-dev.json` | SA `triagem-ro` | fake-shop 1/1 — workload do T01 |

O `nyx-prod` fecha o ciclo com o T02: é o **Chamado 1 visto pelo painel** (o mesmo OOMKilled
por limite de 24Mi que a skill de triagem diagnosticou).

## Garantia de leitura (não só intenção)

`npm run verificar-leitura` varre o código por chamadas de escrita e **falha** se encontrar
qualquer `apply`/`delete`/`patch`/`create`/`replace`. O CI roda essa verificação a cada push
(job `painel`). Toda chamada de rede do projeto é `list*` (GET).

## Observação das skills durante o projeto

- **Skill do T01 (manifests)**: disparou sozinha na fase de workload — os YAMLs de nyx-dev/orion-dev vieram direto de `ticket-01/execucao/modo-escrita/` com 2 ajustes (registry interno → imagens do lab; secret placeholder → senha real do lab, que é o fluxo que o padrão da casa prevê: valor real fora do Git). Disparo correto, zero reexplicação.
- **Skill do T02 (triagem)**: apareceu onde **não** devia — ao diagnosticar o CrashLoopBackOff do kube-news no nyx-dev (senha do secret errada), o método de triagem foi útil, mas o contexto era "subir o workload do T04", não um chamado. Anotação honesta: a matriz de roteamento do T02 previa confusão inversa (triagem↔manifests), não "triagem em tarefa de setup"; a distinção real é **sintoma relatado por usuário** vs **falha encontrada no caminho**.
- **Precisei reexplicar**: nada das skills; o que precisei reexplicar ao agente foi ambiente (kubeconfig via arquivo, API 0.x posicional, EADDRINUSE) — temas fora das skills.

## Curadoria

- **Spec corrigida durante a implementação**: o PRD dizia "só leitura garantida em código" — a verificação virou um **script npm** (`verificar-leitura`), mais forte que comentário; e o campo `readyReplicas` ausente virou regra explícita no código (`campo(undefined, 0)`).
- **O agente entendeu diferente**: o TRD inicial assumiu a API orientada a objetos 1.x do cliente k8s; a versão instalada (0.22, CJS) usa assinatura posicional e retorno `{response, body}` — corrigido no código, registrado aqui como lição (a spec não previa versão de biblioteca).
- **Curadoria da vaia 2 (2026-11-18)**: os 3 cenários de falha tinham sido escritos à mão a partir do formato do serializador. Agora são **capturas reais** (tabela acima), e o job `painel` do CI confere o código de erro de cada uma. Também nesta rodada: ADR-01 alinhado ao código (JavaScript puro — TypeScript foi descartado e a decisão ficou registrada) e o fallback Endpoints que o ADR-04 prometia foi **implementado** em `servidor.js`.
- **Endpoints × EndpointSlice**: escolhido EndpointSlice (1.35 no lab), com fallback para Endpoints (v1) quando o slice não está disponível — implementado e coberto pelo ADR-04.

## Limitação honesta de ambiente

O nó do kind (rede do Docker Desktop → Docker Hub dá EOF) não puxa imagens do registro público: por isso as imagens do laboratório foram carregadas com `docker save` + `ctr images import`. No nyx-prod, o `nyx-api` está em CrashLoopBackOff por **OOMKilled (limite de 24Mi)** — não é defeito do painel: o painel retrata o estado real do cluster com precisão, que é exatamente o comportamento esperado nos dados do enunciado.
