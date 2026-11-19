# Evidência — auditoria contra um Linux REAL (2026-11-19)

A rodada anterior (`exec1/`, `exec2/`) auditou um parque dropbear montado sobre o
**próprio sandbox** — por isso 5 `nao_verificado` e o desvio de distribuição para `alpine`.
Esta rodada elimina essa limitação: a auditoria roda contra o **nó do cluster kind**,
que é Debian 12 de verdade.

## Como foi feito

1. Pod privilegiado com `hostPID: true` e `hostNetwork: true` no nó.
2. Coleta com `nsenter -t 1 -m -u -i -n -p`, ou seja, no **PID 1 do host** — não no container.
3. Os 9 comandos de `COLETA` do `metavm.py` foram executados nesse contexto.
4. A saída crua entrou em `metavm.interpretar()` → `metavm.conferir()` → `metavm.resumo()`
   e `metavm.laudo_md()` **do código do repositório**, sem reimplementar nada.

Script: `scripts/auditar-no-real.py` (workspace do agente). O laudo desta pasta é a saída dele.

## Laudo real (Debian 12, kernel WSL2)

| Regra | Veredito | Encontrado |
|---|---|---|
| `so.distribuicao` | **desvio** (alto) | `debian` (esperado `ubuntu`) |
| `so.versao_minima` | **desvio** (alto) | `12` (esperado ≥ 22.04) |
| `kernel.versao_minima` | conforme | `6.6.87.2-microsoft-standard-WSL2` |
| `servicos.ativos` | **desvio** (alto) | só `containerd` ativo (faltam ssh, node_exporter, chrony) |
| `servicos.proibidos` | conforme | nenhum ativo |
| `swap.habilitado` | **desvio** (crítico) | `True` — `/dev/sdc` com 2G |
| `portas_em_escuta.publicas_permitidas` | **desvio** (crítico) | `[6443, 10250, 10256]` expostas (esperado só 22) |
| `portas_em_escuta.somente_rede_interna` | conforme | 2379/2380/2381/10248/10249/10257 em loopback |
| `chaves_ssh.emitidas_por` | não verificado | `authorized_keys` vazio/inacessível |
| `ssh.login_de_root` | não verificado | exigiria `sshd -T` com privilégio de root no host |
| `ntp.sincronizado` | não verificado | `timedatectl` indisponível no nó |

**Resumo: 3 conforme · 5 desvio · 3 não verificado.**

## O que mudou em relação à rodada do sandbox

| | sandbox (exec1/exec2) | Linux real (esta) |
|---|---|---|
| distribuição detectada | `alpine` (o próprio sandbox) | **`debian` 12** |
| swap | `nao_verificado` (sem dados) | **`desvio` — swap de 2G ligado** |
| portas | `nao_verificado` (sem dados) | **`desvio` — 6443/10250/10256 públicas** |
| kernel | `6.12.113` (sandbox) | `6.6.87.2-microsoft-standard-WSL2` (nó) |

Os 3 `nao_verificado` que restam são **legítimos**, não falta de ambiente: `authorized_keys`
do root está vazio, `sshd -T` precisa de root no host, e o nó não tem `timedatectl`.
Isto é o comportamento correto da regra: sem dado, não se inventa veredito.

## Bug encontrado e corrigido graças a este teste

`parse_so()` usava `re.search(r'ID=["\']?([\w-]+)', txt)`, que casa **dentro** de
`VERSION_ID=`. O `/etc/os-release` do Debian lista `VERSION_ID` antes de `ID`, então a
distribuição era lida como `"12"` e a versão como `"12"` — os dois desvios apareciam por
motivo errado.

Corrigido para ancorar no início da linha (`(?m)^ID=` / `(?m)^VERSION_ID=`). Verificado
com os três formatos reais:

```
Debian -> ('debian', '12')
Ubuntu -> ('ubuntu', '22.04')
Alpine -> ('alpine', '3.24.3')
```

Este é o tipo de defeito que só aparece contra um host real: o sandbox é Alpine e lista
`ID` antes de `VERSION_ID`, mascarando o bug.
