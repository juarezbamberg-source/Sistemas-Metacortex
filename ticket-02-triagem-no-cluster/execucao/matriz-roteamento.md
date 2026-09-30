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
| 7 | "esse manifesto não sobe no cluster" | AMBÍGUA | ⚠️ manifests (errado — sintoma de runtime) | Corrigido na skill de manifests: se a frase fala de cluster/pod/namespace, delegar à triagem; ajustada a descrição ("revisar YAML antes de aplicar") |
| 8 | "o Service do nyx não está entregando tráfego" | triagem | ✅ triagem | — |
| 9 | "o que é um DaemonSet?" | NENHUMA | ✅ nenhuma (resposta geral) | — |
| 10 | "provisiona uma VM nova no Construct pro cliente orion" | FORA DE ESCOPO | ✅ nenhuma recusou claramente | Adicionado em ambas as skills: "se pedir provisionamento de infraestrutura (VM, cluster), recusar e apontar para o time de plataforma" |
