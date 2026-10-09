# Inventário de picoclaw-03ec9e20-64b9d864c5-qqtms (127.0.0.11)
Coletado em 2026-10-09T17:44:53Z · baseline Metacortex v1 (11 regras)

## Desvios

| Severidade | Regra | Esperado | Encontrado |
|---|---|---|---|
| alto | so.distribuicao | ubuntu | alpine |
| alto | servicos.ativos | ['ssh', 'containerd', 'node_exporter', 'chrony'] | [] |
| critico | chaves_ssh.emitidas_por | metacortex-platform | ['ethos@picoclaw-03ec9e20-64b9d864c5-qqtms'] |

## Não verificado

| Regra | Motivo |
|---|---|
| so.versao_minima | dado não coletado neste host |
| ssh.login_de_root | dado não coletado neste host |
| ntp.sincronizado | dado não coletado neste host |

## Conforme

kernel.versao_minima · servicos.proibidos · swap.habilitado · portas_em_escuta.publicas_permitidas · portas_em_escuta.somente_rede_interna

**Resumo: 5 conforme · 3 desvio · 3 não verificado**