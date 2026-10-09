# OpenSpec — ciclo T03 (auditoria-vm-ssh)

## Proposta (proposal.md)

**Por quê**: o Roster (inventário do parque) é mantido à mão e está desatualizado — hosts mudaram de papel, agentes sem registro, chaves SSH órfãs. Ninguém sabe quantas VMs estão fora do padrão.

**O que muda**: primeira peça do substituto — CLI que audita VMs por SSH (sem agente, usuário comum) e compara com o baseline oficial do parque (11 regras), emitindo laudo JSON (para o Roster) e Markdown (para o plantão).

**Escopo**: coleta + conformidade + 2 formatos + exit codes. Fora: corrigir desvios, instalar agente, gerenciar ciclo de vida de VM.

## Tarefas (tasks.md)

- [x] 1. Baseline oficial das 11 regras (so, kernel, servicos, swap, portas, chaves_ssh, ssh.login_de_root, ntp) com severidades
- [x] 2. Coleta SSH somente leitura (9 comandos, usuário comum, timeout)
- [x] 3. Interpretação: coleta bruta → inventário do contrato (config efetiva ≠ escrita no arquivo)
- [x] 4. Conformidade: 1 entrada por regra (regra/esperado/encontrado/veredito/severidade), vereditos conforme|desvio|nao_verificado com motivo
- [x] 5. Saída JSON no contrato do enunciado (host/inventario/conformidade/resumo com por_severidade)
- [x] 6. Saída Markdown de plantão (Desvios por severidade / Não verificado com motivo / Conforme)
- [x] 7. Exit codes: 0 conforme · 1 desvio ou nao_verificado · 2 uso/host inalcançável
- [x] 8. Critérios de pronto provados: host real (3 desvios reais), inalcançável (exit 2 com mensagem), idempotência (2ª execução = 1ª)

## Specs (specs.md)

### Capability: auditoria de VM por SSH
- **Requirement**: laudo com uma entrada por regra do baseline
  - Scenario: regra coletável e dentro do esperado → conforme
  - Scenario: regra coletável e fora do esperado → desvio com severidade do baseline
  - Scenario: dado exige privilégio que o usuário não tem → nao_verificado com motivo (nunca conforme por falta de evidência; nunca aborta o run)
- **Requirement**: host inalcançável
  - Scenario: endereço/porta/chave errados → mensagem que explica, sem stack trace, exit 2, sem confundir com host conforme
- **Requirement**: idempotência
  - Scenario: duas execuções seguidas → mesmo veredito por regra; só o instante muda
- **Requirement**: credencial
  - Scenario: chave privada nunca aparece em saída, log ou erro

## Arquivamento (archive/)

**Status**: IMPLEMENTADO e validado em 2026-10-09 contra host real (web-01 no parque dropbear do laboratório).
**Evidência**: `evidencia/laudo.json` + `evidencia/laudo.md` (5 conforme · 3 desvio · 3 nao_verificado — desvios reais: distribuição alpine≠ubuntu, serviços do parque ausentes, chave não emitida pela plataforma).
**Correções da spec durante a implementação** (curadoria pedida pelo enunciado):
1. `ssh.login_de_root` no laboratório não é verificável como config EFETIVA (exigiria `sshd -T` com privilégio) — o veredito correto é `nao_verificado` com motivo, exatamente como o enunciado prevê; a regra existe e está coberta.
2. `portas_em_escuta` no sandbox lê `ss -tlnp` sem o processo dono (sem privilégio) — o veredito de porta/bind é verificável, o dono nem sempre; documentado no laudo.
3. O baseline de exemplo anterior (perfis web/db genéricos) foi substituído pelo oficial das 11 regras — a vaia estava certa.
