# Parte C — A skill vale o custo?

## Caso 1 — "o pod do nyx-prod não sobe" (Chamado 1)

**SEM skill (agente com kubectl, sem método):**
- Explorou 8 comandos (get pods, describe, get events com sort, get deploy, get ns, logs, top, get events de novo) antes de achar o OOMKill; 2 voltas desnecessárias (log de pod morto não existe; top sem metrics-server).
- ~5.400 tokens de entrada/saída combinados, ~6 min, diagnóstico correto mas sem severidade nem recomendação estruturada.

**COM skill de triagem:**
- Método: pods → eventos → containerStatuses (lastState) → resources. 5 comandos, ordem fixa.
- ~2.300 tokens, ~2 min, saída estruturada (causa + prova + camada + correção sugerida + "não aplico, triagem só lê").

**Veredito: skill 2,3× mais barata, 3× mais rápida, e saída padronizada.**

## Caso 2 — "o service do nyx-stg não tem endpoint" (Chamado 3)

**SEM skill:**
- Começou pelo Service (get svc), depois pods, depois endpoints — ordem quase certa, mas achou o labels mismatch só no 4º passo e **quase concluiu errado** ("apontar o Service para nyxapi"), pois não cruzou com o padrão da casa (label canônico).
- ~3.100 tokens, ~4 min.

**COM skill de triagem:**
- Método: Service → Endpoints vazio → selector × labels (cruzamento de DUAS fontes — regra 4 do método) → causa e correção com o lado certo de corrigir (labels do Deployment, não o Service).
- ~1.500 tokens, ~1,5 min.

**Veredito: além do custo (2×), a qualidade divergiu: sem skill, a correção sugerida era a pior das duas opções.**

## Custo de manter as skills
- skill manifests: ~4,5k tokens de corpo+script; skill triagem: ~3k tokens.
- Carregam juntas ~7,5k tokens por sessão que as usa — vale em sessões de diagnóstico (economia ≥ 2× no caso medido) e é desperdício em sessões que não tocam em K8s (por isso a matriz de roteamento e a recusa clara).
