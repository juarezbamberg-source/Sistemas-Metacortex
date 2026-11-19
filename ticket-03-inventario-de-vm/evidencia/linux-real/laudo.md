# Inventário de metacortex-control-plane (metacortex-control-plane (node do kind, via nsenter no PID 1))
Coletado em 2026-11-19 · baseline Metacortex v1 (11 regras)

## Desvios

| Severidade | Regra | Esperado | Encontrado |
|---|---|---|---|
| alto | so.distribuicao | ubuntu | debian |
| alto | so.versao_minima | 22.04 | 12 |
| alto | servicos.ativos | ['ssh', 'containerd', 'node_exporter', 'chrony'] | ['containerd'] |
| critico | swap.habilitado | False | True |
| critico | portas_em_escuta.publicas_permitidas | [22] | [6443, 10250, 10256] |

## Não verificado

| Regra | Motivo |
|---|---|
| chaves_ssh.emitidas_por | authorized_keys vazio ou inacessível |
| ssh.login_de_root | exige privilégio que o usuário da coleta não tem |
| ntp.sincronizado | dado não coletado |

## Conforme

kernel.versao_minima · servicos.proibidos · portas_em_escuta.somente_rede_interna

**Resumo: 3 conforme · 5 desvio · 3 não verificado**