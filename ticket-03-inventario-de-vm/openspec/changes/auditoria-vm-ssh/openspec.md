# OpenSpec — ciclo T03 (auditoria-vm-ssh)

## Brainstorm (transcrição das decisões reais — 2026-09-30)

Perguntas feitas ao dono do desafio antes da spec (máx. 3 por rodada, skill brainstorm):
1. **Estratégia de host SSH**: sandbox sem sshd/sudo — opções: (a) dropbear estático como usuário comum, (b) host fornecido pelo dono, (c) pular execução real. **Decisão do dono: "Tentar dropbear local no sandbox"** (formulário de confirmação).
2. **Linguagem**: implícita na decisão de stack — Python já usado no validador do T01; confirmada na conversa de spec.
3. **Escopo da coleta**: o enunciado defineia o que coletar; a pergunta real foi "formato do laudo" — respondida pelo contrato do enunciado (host/inventario/conformidade/resumo).

Pontos em aberto ao final do brainstorm: nenhum bloqueante — o arco seguiu direto ao PRD.

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
- [x] 8. Critérios de pronto provados: host real (3 desvios reais), inalcançável (exit 2 com mensagem), idempotência (2ª execução = 1ª) — evidências versionadas em evidencia/ (exec1, exec2, host-inalcancavel, 2026-11-18)

## Specs (specs.md)

### Capability: auditoria de VM por SSH
- **Requirement**: laudo com uma entrada por regra do baseline
  - Scenario: regra coletável e dentro do esperado → conforme
  - Scenario: regra coletável e fora do esperado → desvio com severidade do baseline
  - Scenario: dado exige privilégio que o usuário não tem → nao_verificado com motivo (nunca conforme por falta de evidência; nunca aborta o run)
  - Scenario (correção vaia 2): dado não coletado (ex.: swapon/ss sem saída) → nao_verificado com motivo, nunca falso-conforme
- **Requirement**: host inalcançável
  - Scenario: endereço/porta/chave errados → mensagem que explica, sem stack trace, exit 2, sem confundir com host conforme
- **Requirement**: idempotência
  - Scenario: duas execuções seguidas → mesmo veredito por regra; só o instante muda
- **Requirement**: credencial
  - Scenario: chave privada nunca aparece em saída, log ou erro

## Arquivamento (archive/)

**Status**: IMPLEMENTADO e validado em 2026-10-09 contra host real (web-01 no parque dropbear do laboratório); evidências regeneradas em 2026-11-18 (vaia 2) com exit codes e idempotência versionados.
**Evidência**: `evidencia/exec1/` + `evidencia/exec2/` + `evidencia/host-inalcancavel.txt` (exit 1 com desvios, exit 2 host morto, diff vazio entre execuções).
**Correções da spec durante a implementação** (curadoria pedida pelo enunciado):
1. `ssh.login_de_root` no laboratório não é verificável como config EFETIVA (exigiria `sshd -T` com privilégio) — o veredito correto é `nao_verificado` com motivo, exatamente como o enunciado prevê.
2. `portas_em_escuta` no sandbox lê `ss -tlnp` sem o processo dono (sem privilégio) — o veredito de porta/bind é verificável, o dono nem sempre.
3. O baseline de exemplo anterior (perfis web/db genéricos) foi substituído pelo oficial das 11 regras.
4. (vaia 2) Dado não coletado (swap/portas vazios) era reportado como conforme — corrigido para nao_verificado; por_severidade agora conta só desvios, como o exemplo do enunciado.
