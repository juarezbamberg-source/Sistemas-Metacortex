# Ticket 03 — metavm: inventário e drift de VMs por SSH

CLI **somente leitura** que conecta por SSH, coleta fatos das VMs, compara com a baseline e dá veredito por check: `conforme` / `desvio` / `nao_verificado` (com motivo e severidade). Saída Markdown + JSON; exit 0/1/2.

## Entregue

| Item | Caminho |
|---|---|
| Especificação (arco OpenSpec) | [`spec/PRD.md`](spec/PRD.md) · [`spec/TRD-ADRs.md`](spec/TRD-ADRs.md) (4 ADRs) |
| Ferramenta | [`metavm.py`](metavm.py) (módulo único: modelo, baseline com herança `extends`, coleta, comparação, relatórios, CLI) |
| Baseline e inventário de exemplo | [`exemplos/baseline.yaml`](exemplos/baseline.yaml) · [`exemplos/inventario.yaml`](exemplos/inventario.yaml) |
| Relatórios reais do parque | [`exemplos/saida/laudo.md`](exemplos/saida/laudo.md) · [`exemplos/saida/laudo.json`](exemplos/saida/laudo.json) |

## Parque de execução (sandbox, sem OpenSSH/sudo)

3 "VMs" = servidores **dropbear** (binário estático Alpine aarch64 + musl) em `127.0.0.11/12/13:2221`, hostkeys distintas, auth por chave ed25519 — instalados em `tmp/vm/` do sandbox (fora do repo). Limitação honesta: mesmo kernel/sistema; os checks provam o fluxo ponta a ponta, não heterogeneidade real.

## Prova de execução (2026-09-30)

```
$ python3 metavm.py check --baseline exemplos/baseline.yaml --inventario exemplos/inventario.yaml --saida exemplos/saida
3 hosts · 7 conforme(s) · 0 desvio(s) · 6 não verificado(s)
  web-01: banner-metacortex → nao_verificado (info) cat: can't open '/etc/issue.net': No such file
  db-01: postgres-usuario  → nao_verificado (critical) id: unknown user postgres
  ...
exit=1
```

Os `nao_verificado` são reais (sandbox não tem esses usuários/arquivos) — exatamente o comportamento exigido (RF-05): isolar falha por item, não derrubar o run. **Teste unitário** (comparação regex/igualdade, herança `extends`, host inalcançável isolado): `TESTES OK`.

## Como reproduzir

```bash
# no sandbox do agente (parque dropbear no ar)
python3 metavm.py check --baseline exemplos/baseline.yaml --inventario exemplos/inventario.yaml --saida exemplos/saida

# testes unitários (sem SSH)
python3 -c "import metavm; ..."   # ver README acima / sessão de execução
```

Requisitos: Python 3.10+, PyYAML; cliente SSH (`dbclient` do dropbear ou OpenSSH) configurável em `inventario.yaml → opcoes.ssh_cmd`.
