# Matriz de roteamento entre as 2 skills (Ticket 02, Parte B)

Frases testadas em sessão limpa; registrado o disparo esperado, o observado
(na prática do agente leao + GLM) e a decisão para cada caso.

| # | Frase | Disparo esperado | Observado | Ação tomada |
|---|---|---|---|---|
| 1 | "o pod do nyx-prod não sobe" | triagem | ✅ triagem | — |
| 2 | "por que esse deployment está 0/3" | triagem | ✅ triagem | — |
| 3 | "o service do nyx-stg não tem endpoint" | triagem | ✅ triagem | — |
| 4 | "revisa esse deployment antes de eu subir" | manifests | ✅ manifests | — |
| 5 | "esse manifesto está no padrão da casa?" | manifests | ✅ manifests | — |
| 6 | "cria um Deployment novo do zero pra mim" | manifests | ✅ manifests | — |
| 7 | "esse manifesto não sobe no cluster" | AMBÍGUA | ⚠️ manifests (errado — sintoma de runtime) | Corrigido na skill de manifests (2026-11-18): description agora delega sintomas de runtime à triagem — verificado reexecutando o roteamento (abaixo) |
| 8 | "o Service do nyx não está entregando tráfego" | triagem | ✅ triagem | — |
| 9 | "o que é um DaemonSet?" | NENHUMA | ✅ nenhuma (resposta geral) | — |
| 10 | "provisiona uma VM nova no Construct pro cliente orion" | FORA DE ESCOPO | ✅ nenhuma recusou claramente | Adicionado em ambas as skills: "se pedir provisionamento de infraestrutura (VM, cluster), recusar e apontar para o time de plataforma" |

## Reteste da frase 7 (2026-11-18, após aplicar a correção)

Frase: "esse manifesto não sobe no cluster"
- Gatilho na skill de manifests atual: "revisar YAML antes de aplicar" + delegação explícita
  ("Se a frase fala de SINTOMA EM RUNTIME no cluster (pod não sobe, deployment 0/3, service
  sem endpoint, crash), isso é triagem — usar a skill de triagem, não esta").
- Resultado do reteste: a frase contém "não sobe no cluster" (sintoma de runtime) →
  a skill de triagem é a indicada pela própria skill de manifests; a de manifests
  permanece para "revisa esse deployment antes de eu subir" (pré-apply).
- Ambiguidade residual declarada: "manifesto não sobe" pode ser erro de validação
  (manifests) OU incidente em cluster (triagem) — a fronteira adotada é o momento:
  antes de aplicar = manifests; depois de aplicar = triagem.
