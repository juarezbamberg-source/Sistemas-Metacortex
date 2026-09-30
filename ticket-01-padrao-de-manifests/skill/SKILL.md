---
name: padrao-manifests-metacortex
description: This skill should be used when the user asks to "gerar manifests Kubernetes no padrão da casa", "criar deployment/service para um projeto no padrão Metacortex", "conferir/validar um manifesto contra o padrão da Metacortex", "revisar esse manifesto antes de subir", "por que esse manifesto foi barrado pela Seraph", ou mencionar "padrão de manifests da Metacortex". Dois modos: escrita (gera manifests novos conformes, descobrindo porta/probe/credenciais lendo o projeto) e conferência (aponta cada violação com regra e severidade). Regras mecânicas vão no script embutido; o que exige ler o projeto segue a instrução passo a passo.
version: 1.0.0
---

# Padrão de manifests da Metacortex — skill de escrita e conferência

Empacota o "Padrão de Manifests da Metacortex" (wiki de Plataforma, mantido por Segurança & Compliance — a Seraph revisa todo manifesto). O padrão tem 4 blocos: **1** identidade/nomenclatura, **2** resiliência, **3** segurança, **4** vocabulário. Níveis: *obrigatório* barra sem discussão, *recomendado* exige justificativa no PR, *proibido* não tem exceção.

## Divisão de trabalho (o princípio da skill)

- **Script (`scripts/validar_padrao.py`)** — regras mecânicas: conferidas em qualquer YAML sem saber nada da aplicação. Roda primeiro, resposta determinística.
- **Instrução (este corpo)** — o que exige **ler o projeto**: porta real, endpoint de probe que existe de verdade, variáveis de ambiente, credenciais, particularidades (migração no start, ausência de healthcheck).
- **Trivy** — o catálogo KSV cobre boa parte do Bloco 3 de segurança genérica. **Nunca reimplementar o que o Trivy já pega** (ver `references/mapeamento-trivy.md`).

## Modo conferência (o mais frequente)

Dado um manifesto existente:

1. Rode `python scripts/validar_padrao.py <manifesto-ou-diretorio>`. Saída: `FALHA [regra]` por violação obrigatória/proibida, `aviso [regra]` por recomendado; exit 1 se houver FALHA.
2. Rode `trivy config <manifesto>` (a ferramenta determinística da casa) para a camada de segurança genérica — e **não repita** no laudo o que o Trivy já apontou; cite junto.
3. Para as checagens que **exigem ler o projeto** (abaixo), abra o repositório da aplicação antes de dar veredito sobre probes e variáveis.
4. Entregue o laudo agrupado por regra: o que o script pegou, o que o Trivy pegou, o que só a leitura do projeto revelou — e a correção sugerida para cada item.

## Modo escrita

Dado um projeto para gerar manifests:

1. **Leia o projeto** (não invente): porta em que escuta (Dockerfile/entrypoint/código), endpoints de saúde implementados (`/health`, `/ready` ou similares), variáveis de ambiente de conexão (host/banco/usuário/senha), particularidades de start (migrações, workers).
2. Rode o script sobre os manifests gerados e o Trivy; só entregue com **zero FALHA**.
3. Cabeçalho de comentário em cada YAML dizendo **de onde veio cada valor** (arquivo/linha do projeto).

### Regras que exigem ler o projeto (decisões, não mecânica)

- **2.2 Probes** — o script exige que existam; a instrução define **o que colocar**:
  - Se a app tem endpoints de saúde → `httpGet` neles (readiness ≠ liveness, caminhos diferentes).
  - Se **não tem endpoint nenhum** (ex.: fake-shop) → `tcpSocket` na porta da app como fallback honesto, com **justificativa registrada no YAML** para a Seraph; readiness/liveness em porta TCP provam "processo escutando", não "app sadia" — declare essa limitação.
  - Nunca apontar probe para porta que o container não escuta (o script cruza com `containerPort` via Service; conferir manualmente quando não houver Service).
- **3.3 Credenciais** — o script pega segredo em texto puro no `env`; a instrução manda: senha de banco **sempre** `secretKeyRef`; ConfigMap só para o não sensível (host, nome do banco); Secret versionado com **placeholder em `data` (base64)** e nota para aplicar o valor real fora do Git.
- **Particularidades de start** — migração no start (ex.: `flask db upgrade` no entrypoint do fake-shop): manter no container, documentar no YAML o efeito no rollout (pod novo roda migração antes de servir); considerar `terminationGracePeriodSeconds` maior se o app drena conexões.
- **Imagem** — derivar do registry da casa: `registry.metacortex.io/<cliente>/<app>:<tag>`; tag imutável (nunca `:latest`); se a app pública tem versão conhecida, usar (fake-shop v1.14.2, kube-news 1.0.0).

### Regras mecânicas (o script já cobre — resumo)

1.1 kebab-case · 1.2 namespace `<cliente>-<ambiente>` (dev/stg/prod) · 1.3 os 4 rótulos `app.kubernetes.io/*` em todo objeto · 1.4 selector × matchLabels × template (cruzado Service×Deployment) · 2.1 requests/limits de cpu e memória · 2.2 probes presentes (e endpoints distintos) · 2.3 réplicas ≥ 2 em prod · 2.4 RollingUpdate maxUnavailable 0 em prod · 2.5 PDB em prod (aviso) · 2.6 grace period (aviso) · 3.1 `:latest` proibido · 3.2 securityContext completo · 3.3 segredo em texto puro proibido · 3.4 `automountServiceAccountToken: false` · 3.5 SA dedicada (aviso) · 3.6 hostNetwork/hostPID/privileged proibidos · 3.7 só `registry.metacortex.io` · 4.5 targetPort porta real do container.

## Curadoria (o que ficou de fora e por quê)

- **Bloco 4 inteiro (vocabulário)** — é material de onboarding humano, não regra de revisão; nenhuma conferência automática se aplica. Referência: `references/mapeamento-trivy.md` cita o 4.5, que virou regra cruzada no script.
- **Regras já cobertas pelo Trivy** (KSV-0012 runs-as-root, KSV-0014 rootfs, KSV-0013 tag latest, KSV-0118 security context etc.) — o script as reimplementa **só onde a casa é mais específica** (ex.: `allowPrivilegeEscalation: false` explícito e `drop: ["ALL"]` exigidos pela regra 3.2, mais estritos que o default do Trivy); o resto é do Trivy. Detalhes: `references/mapeamento-trivy.md`.
- **Exceções e histórico do padrão** — a lista de exceções aprovadas e o changelog do wiki não são regras; são contexto organizacional. Fora da skill.
- **2.6 e 3.5 (recomendados)** — ficam como AVISO no script, sem bloquear; a justificativa é humana.
- **`app:` curto** — o padrão permite mantê-lo por compatibilidade; o script não barra o extra, só exige os 4 canônicos.

## Permissões que a skill pede

- **Leitura do repositório da aplicação** (arquivos locais ou clone público) — para descobrir porta/probe/env no modo escrita e validar probes no modo conferência.
- **Execução do script Python** (somente leitura de arquivos YAML; nenhum acesso a rede, nenhum `kubectl`).
- **Execução do Trivy** (`trivy config`, somente leitura dos manifests).
- **Não pede**: acesso a cluster, credenciais, escrita em qualquer lugar. A skill nunca aplica nada — gera e confere YAML.

## Arquivos de apoio

- **`scripts/validar_padrao.py`** — as regras mecânicas (o que usar em qualquer YAML).
- **`references/mapeamento-trivy.md`** — o que o Trivy já cobre (KSV ↔ regras da casa), para não reimplementar.
- **`references/exemplos-execucao.md`** — as saídas reais dos dois modos (kube-news, fake-shop, manifesto barrado).

## Origem

Nasceu do fluxo executado em 2026-09-30 (Desafio 03, Ticket 01): primeiro conferiu-se o manifesto barrado do ticket e geraram-se os manifests de kube-news e fake-shop lendo os projetos; depois o que funcionou foi empacotado. Ferramenta: agente (leao) com script Python próprio + Trivy v0.74.0 + kubeconform v0.8.0. Evidências: `../execucao/`.
