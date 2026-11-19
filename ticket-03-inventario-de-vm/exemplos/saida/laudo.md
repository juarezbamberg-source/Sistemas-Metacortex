# Inventário de picoclaw-03ec9e20-7cc6b88f9-vwh7h (127.0.0.11)
Coletado em 2026-11-18T18:35:16Z · baseline Metacortex v1 (11 regras)

## Desvios

| Severidade | Regra | Esperado | Encontrado |
|---|---|---|---|
| alto | so.distribuicao | ubuntu | alpine |
| alto | servicos.ativos | ['ssh', 'containerd', 'node_exporter', 'chrony'] | [] |
| critico | chaves_ssh.emitidas_por | metacortex-platform | ['ethos@picoclaw-03ec9e20-7cc6b88f9-vwh7h'] |

## Não verificado

| Regra | Motivo |
|---|---|
| so.versao_minima | dado não coletado |
| swap.habilitado | swapon não retornou dados neste host |
| portas_em_escuta.publicas_permitidas | ss/netstat não retornaram dados |
| ssh.login_de_root | exige privilégio que o usuário da coleta não tem |
| ntp.sincronizado | dado não coletado |

## Conforme

kernel.versao_minima · servicos.proibidos · portas_em_escuta.somente_rede_interna

**Resumo: 3 conforme · 3 desvio · 5 não verificado**

---
Execução real (2026-11-18, vaia 2). Exit code **1** (há desvios e não-verificados).
Host: parque dropbear do laboratório (alpine, kernel 6.12 — daí o desvio de distribuição).
