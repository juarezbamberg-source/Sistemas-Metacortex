# PRD — Ticket 03: Inventário e drift de VMs por SSH

**Projeto**: `metavm` — ferramenta CLI de inventário e detecção de drift em VMs Linux via SSH
**Data**: 2026-09-30 · **Autor**: leao (agente) a pedido de Juarez Bamberg · **Status**: proposto

## 1. Problema

O parque da Metacortex tem VMs Linux sem agente de configuração. Ninguém sabe, de forma verificável, se cada host está conforme a linha de base ("baseline") definida pela plataforma. A pergunta operacional é: **"esta VM está conforme, desviou, ou não consegui verificar?"** — respondida por plantonista, sob pressão, via SSH manual.

## 2. Objetivo

Uma **ferramenta CLI somente leitura** que, dado um arquivo de baseline YAML e uma lista de hosts, conecta por SSH, coleta fatos, compara com a baseline e produz um **veredito por host por item** — em Markdown (para o plantonista) e JSON (para automação).

## 3. Não-objetivos (fora de escopo)

- **Corrigir** qualquer desvio (ferramenta de leitura; remediar é outra ferramenta).
- Instalar **agente** nos hosts (só SSH).
- Gerenciar o ciclo de vida das VMs (provisionamento, escala).
- Usar sudo: todos os comandos rodam como usuário comum.
- Monitoramento contínuo/tempo real (execução pontual, agendável externamente).

## 4. Requisitos funcionais

| ID | Requisito |
|---|---|
| RF-01 | Ler **baseline YAML**: lista de checks declarativos (pacote, serviço, arquivo, kernel/sysctl, comando genérico) |
| RF-02 | Ler **inventário** (hosts, IPs, portas SSH, credenciais por chave) de arquivo ou CLI |
| RF-03 | Conectar via SSH (somente leitura), executar comandos de coleta e capturar saída/exit code |
| RF-04 | Para cada check × host: veredito **`conforme`**, **`desvio`** ou **`nao_verificado`** com severidade (info/warning/critical) |
| RF-05 | `nao_verificado` quando: host inalcançável, auth falha, comando falha — com o motivo registrado |
| RF-06 | Saída **Markdown** (relatório legível, agrupado por host, resumo executivo no topo) e **JSON** (máquina) |
| RF-07 | **Código de saída**: 0 = tudo conforme; 1 = ao menos um desvio; 2 = erro de uso/execução (inalcançável conta como desvio crítico? ver decisões) |
| RF-08 | **Idempotente e sem efeito colateral**: nenhum comando de escrita nos hosts |
| RF-09 | Baseline versionável: herança por perfil (ex.: `base` → `web` → `web-prod`) para não duplicar checks |

## 5. Requisitos não funcionais

- **RNF-01 Segurança**: só leitura; chave SSH de arquivo; nenhum segredo em log; timeout por conexão e por comando.
- **RNF-02 Robustez**: host inalcançável NÃO derruba o run inteiro — isola a falha e continua.
- **RNF-03 Executável no sandbox**: Python 3.12 stdlib + libs leves; SSH client externo ou biblioteca pura (decisão ADR-03).
- **RNF-04 Testabilidade**: coleta separada da comparação; testes com fixtures de saída de comandos (sem SSH real nos unitários).
- **RNF-05 Performance**: hosts em paralelo (thread pool), comando com timeout.

## 6. Histórias de uso (critérios de aceite)

1. **Plantão**: "roda o inventário no parque e me diz o que desviou" → relatório MD com resumo no topo: `3 hosts · 2 conformes · 1 com desvio (1 crítico)`.
2. **Auditoria**: JSON agregado alimenta planilha/dashboard; cada item tem host, check, esperado, observado, veredito, severidade.
3. **Drift pós-change**: rodar antes/depois de uma janela e comparar os dois JSONs (a ferramenta só precisa ser determinística).

## 7. Decisões a tomar (ADRs planejados)

- ADR-01: formato do baseline/inventário (YAML único vs. dois arquivos)
- ADR-02: modelo de veredito e severidades
- ADR-03: cliente SSH — subprocess `dbclient`/OpenSSH vs. biblioteca Python pura
- ADR-04: paralelismo e timeouts

## 8. Métricas de sucesso

- 3 hosts do parque (web-01, web-02, db-01) inventariados ponta a ponta com relatório coerente.
- Teste negativo: baseline com item que desvia → veredito `desvio` + exit 1.
- Host derrubado no meio do run → `nao_verificado` sem afetar os outros.
