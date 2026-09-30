---
name: triagem-cluster-metacortex
description: This skill should be used when the user reports a Kubernetes incident or symptom — "o pod não sobe", "deployment 0/3", "service sem endpoint", "503 no serviço", "pod reiniciando", "CrashLoopBackOff", "ImagePullBackOff", "OOMKilled", "aplicação fora do ar no cluster", "por que o X está quebrado" — e pede diagnóstico/triagem. Executa um método de leitura determinístico sobre o cluster via mcp-server-kubernetes (modo não destrutivo): nunca aplica, edita ou deleta nada. NÃO usar para revisar YAML antes de aplicar (usar a skill do padrão de manifests), para criar manifests do zero, ou para provisionar infraestrutura (VMs, clusters).
version: 1.0.0
---

# Triagem de cluster Metacortex — método único de plantão

Método da Trinity (SRE): toda triagem começa pelo sintoma, desce as camadas numa ordem fixa, cruza fontes quando uma só não decide, e PARA quando a causa está identificada. **A triagem só lê o cluster** — nenhuma correção é aplicada, nem quando o agente tem permissão. A correção é proposta, nunca executada.

## Ferramenta de acesso

`mcp-server-kubernetes` em **modo não destrutivo** (sem flags de delete/apply/scale). Toda leitura vai por ele; se indisponível, `kubectl` somente leitura é o fallback equivalente.

## O método (4 passos, nesta ordem)

### 1. Sintoma → primeiro lugar certo

| Sintoma relatado | Comece por |
|---|---|
| "não sobe", "reinicia", "crash", pod em 0/1 | `get pods -n <ns>` (STATUS + RESTARTS) |
| "0/x réplicas", "não atualiza" | `get deploy -n <ns>` + `rollout status` (com timeout curto) |
| "503", "não acessa", "sem tráfego" | `get endpoints <svc> -n <ns>` |
| "lento" | eventos do namespace + limits/requests |
| "não sei, está fora do ar" | `get pods -A` (varredura) → isolar namespace |

### 2. Descer as camadas nesta ordem (pare no primeiro achado forte)

1. **Pod**: STATUS real + `containerStatuses` (waiting/terminated reason, exitCode, restartCount)
2. **Eventos do namespace** (`--sort-by=.lastTimestamp`, últimos 10 relevantes)
3. **Config do objeto**: resources (limits/requests), probes, env, image (tag!)
4. **Cruzamento** (ver abaixo)
5. **Deploy/ReplicaSet**: rollout status, conditions (Available/Progressing)
6. **Service/EndpointSlice**: selector × labels do pod, subsets

### 3. Cruzar fontes em vez de aprofundar

Regra: **se duas fontes dizem a mesma coisa, a causa está confirmada; se uma fonte contradiz a outra, é aí que a causa mora.** Cruzamentos obrigatórios:
- STATUS do pod × razão do `waiting/terminated` (Running mas `ready:false`? pode ser probe)
- `deploy.status` × pods vivos (réplicas desejadas ≠ pods criados → RS/eventos)
- **Service selector × pod labels** (para 503/sem tráfego — causa nº 1 dessa camada)
- Imagem do spec × registro (tag existe? o erro de pull cita a tag exata)

### 4. Quando PARAR

Triagem termina quando você consegue preencher as 4 linhas do veredito. **Não** continue explorando após a causa; **não** aplique correção; **não** rode comandos "por garantia".

## Formato da saída (sempre estas 4 linhas)

```
CAUSA: <uma frase, na camada X>
PROVA: <o campo/evento exato que prova — cite valores>
CORREÇÃO SUGERIDA: <o que o plantonista deve mudar — eu NÃO aplico>
CONFORTO: <o que continua funcionando ao lado (banco, outros pods)>
```

## Padrões de causa já vistos (atalho honesto)

- `OOMKilled (137)` + limit baixo → limit de memória insuficiente (corte de custos)
- `ImagePullBackOff` + mensagem citando tag → **tag inexistente no registro** (release anunciou o que o pipeline não empurrou) — verificar as tags reais antes de culpar rede
- Pods Running + `Endpoints: <none>` → selector × labels descasados (typo, plural/singular, hífen)
- `CrashLoopBackOff` + exit 1 rápido → erro de app (env var faltando, credencial, banco fora)
- `ErrImagePull` com `EOF`/timeout no `auth.docker.io` → rede/registry, não a app

## Fora de escopo (recusar e apontar)

- Revisar/gerar **YAML de manifest** → skill do padrão de manifests (Ticket 01)
- Provisionar **VM/cluster** (Construct) → time de plataforma, fora do agente
- **Aplicar qualquer correção** → sempre proposta, nunca executada aqui
- Pergunta conceitual ("o que é um DaemonSet?") → responder direto, sem método

## Permissões que a skill pede

- **Leitura** de pods, deployments, services, endpoints/EndpointSlices, eventos, namespaces (via mcp-server-kubernetes non-destructive ou kubectl read-only)
- **NÃO pede**: apply, delete, patch, scale, exec, port-forward, nem credenciais de escrita

## Origem

Nasceu do fluxo executado em 2026-09-30 (Desafio 03, Ticket 02): 3 chamados reais reproduzidos no cluster de laboratório (nyx-prod OOMKilled por limit de 24Mi; orion-stg com tag inexistente v1.14.2; nyx-stg com selector `nyx-api` vs labels `nyxapi` → Endpoints `<none>`), triados com este método antes de serem escritos. Provas e saídas reais em `../execucao/`.
