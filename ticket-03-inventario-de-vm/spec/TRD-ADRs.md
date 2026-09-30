# TRD + ADRs — metavm (Ticket 03)

## ADRs (decisões)

### ADR-01 — Baseline e inventário: dois arquivos YAML
**Contexto**: baseline muda pouco e é versionada por perfil; inventário muda por ambiente/parque.
**Decisão**: `baseline.yaml` (perfis com herança `extends`) e `inventario.yaml` (hosts: nome, host, porta, usuário, chave, perfil).
**Consequência**: reuso de baseline entre parques; 2 arquivos para manter.

### ADR-02 — Veredito e severidades
**Contexto**: plantonista precisa priorizar; auditoria precisa de registro completo.
**Decisão**: veredito ∈ {`conforme`, `desvio`, `nao_verificado`}; severidade ∈ {`info`, `warning`, `critical`} (por check no baseline). `nao_verificado` herda a severidade do check e carrega `motivo`. Exit code: 0 tudo conforme; 1 ≥1 desvio **ou** nao_verificado crítico; 2 erro de uso.
**Consequência**: CI/agendamento consegue falhar o pipeline; plantonista vê motivo claro.

### ADR-03 — Cliente SSH: subprocess `dbclient` (dropbear)
**Contexto**: sandbox sem OpenSSH; dropbear `dbclient` já funciona no parque (chave ed25519). Paramiko exigiria pip + risco crypto.
**Decisão**: CLI abstrai o cliente (`ssh_cmd` configurável, default `dbclient`); subprocess com timeout; `-y` controlado por `strict_hostkeys: false` no inventário.
**Consequência**: portável (troca para `ssh` em qualquer máquina); uma camada de processo por comando (aceitável no volume do parque).

### ADR-04 — Paralelismo: ThreadPoolExecutor, 8 workers
**Contexto**: hosts independentes; SSH é I/O-bound.
**Decisão**: threads por host (não por check); coleta de todos os checks numa única conexão por host é impossível com dbclient (1 comando por conexão) → um subprocess por check, timeouts: conexão 10s, comando 15s.
**Consequência**: simples e isolado; mais conexões (ok em ≤ dezenas de hosts).

## Design técnico

```
metavm/
├── pyproject.toml            # console_script metavm
├── src/metavm/
│   ├── cli.py                # argparse: metavm check --baseline --inventario [--saida out/] [--hosts a,b]
│   ├── modelo.py             # dataclasses: Check, Host, Resultado, Laudo
│   ├── baseline.py           # parse + herança de perfis (extends, override por merge)
│   ├── inventario.py         # parse hosts
│   ├── coleta.py             # ExecutaColeta: subprocess dbclient/ssh; batch de comandos
│   ├── comparacao.py         # fatos × checks → vereditos
│   └── relatorio.py          # markdown + json
└── tests/                    # fixtures de saída; sem SSH nos unitários
```

### Tipos de check (baseline)

```yaml
perfis:
  base:
    checks:
      - id: ntp-ativo
        tipo: servico        # systemctl is-active <nome> (com fallback service)
        nome: chronyd
        esperado: ativo
        severidade: warning
      - id: sshd-config
        tipo: arquivo         # stat -c '%a %U' path (ou test -f/-e + cat)
        caminho: /etc/ssh/sshd_config
        esperado: existe
        severidade: critical
      - id: sysctl-ip-forward
        tipo: sysctl
        chave: net.ipv4.ip_forward
        esperado: "0"
        severidade: warning
      - id: patch-minimo
        tipo: pacote
        nome: openssl
        esperado: presente    # ou ausente
        severidade: critical
      - id: banner
        tipo: comando
        comandos: ["cat /etc/issue.net"]
        esperado_regex: "Metacortex"
        severidade: info
```

### Coleta (comandos reais, todos somente leitura)

- pacote: `command -v dpkg >/dev/null && dpkg -s <n> || rpm -q <n>` → exit 0 = presente
- serviço: `systemctl is-active <n> 2>/dev/null || service <n> status`
- arquivo: `test -e <p> && stat -c '%a' <p>`
- sysctl: `sysctl -n <chave>`
- comando: o(s) comando(s) do próprio check

### Comparação → veredito

- fato coletado e casa com esperado → `conforme`
- fato coletado e não casa → `desvio` (registra esperado vs observado)
- conexão/comando falho ou timeout → `nao_verificado` + motivo
- `servico` inexistente ≠ desvio de configuração → desvio (o check exige o serviço)
