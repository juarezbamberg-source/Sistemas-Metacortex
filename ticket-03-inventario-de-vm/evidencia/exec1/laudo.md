# Inventário de picoclaw-03ec9e20-7cc6b88f9-vwh7h (127.0.0.11)
Coletado em 2026-11-18T18:10:05Z · baseline Metacortex v1 (11 regras)

## Desvios

| Severidade | Regra | Esperado | Encontrado |
|---|---|---|---|
| alto | so.distribuicao | ubuntu | alpine |
| alto | servicos.ativos | ['ssh', 'containerd', 'node_exporter', 'chrony'] | [] |
| critico | chaves_ssh.emitidas_por | metacortex-platform | ['ethos@picoclaw-03ec9e20-7cc6b88f9-vwh7h'] |

## Não verificado

| Regra | Motivo |
|---|---|
| so.versao_minima | dado não coletado neste host |
| swap.habilitado | dado não coletado neste host |
| portas_em_escuta.publicas_permitidas | dado não coletado neste host |
| ssh.login_de_root | dado não coletado neste host |
| ntp.sincronizado | dado não coletado neste host |

## Conforme

kernel.versao_minima · servicos.proibidos · portas_em_escuta.somente_rede_interna

**Resumo: 3 conforme · 3 desvio · 5 não verificado**

---
Evidência real (2026-11-18, vaia 2): execução contra host Linux do parque dropbear.
Exit code 1 (desvios+não-verificados). Segunda execução idêntica (idempotência) e host
inalcançável (exit 2) versionados ao lado. Laudo JSON completo em exec1/laudo.json.
