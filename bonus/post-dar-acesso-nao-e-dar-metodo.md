# Dar acesso não é dar método: três lições de automatizar infraestrutura com um agente de IA

*Como um desafio de pós-graduação — quatro tickets, um cluster Kubernetes real e um agente operando de ponta a ponta — mostrou que o que separa uma entrega boa de uma descartável não é o modelo, é o que existe escrito antes do primeiro prompt.*

---

## O momento em que o agente quase errou sozinho

No meio do desafio, um Service Kubernetes não entregava tráfego. Os pods estavam perfeitos: `2/2 Running`, probes passando, aplicação saudável. Só que ninguém chegava neles — 503 para todo mundo.

Pedi o diagnóstico a um agente **sem** método. Ele chegou à causa — o seletor do Service (`app: nyx-api`) não casava com os labels dos pods (`app: nyxapi`, sem hífen) — mas a correção que sugeriu foi **apontar o Service para `nyxapi`**. Tecnicamente funcionaria. Era também a pior das duas opções: consertaria um caso e deixaria o padrão da casa (labels canônicos) furado para sempre.

Depois, o mesmo diagnóstico **com** uma skill de triagem — um método escrito antes, com ordem fixa de camadas e uma regra explícita de cruzar fontes — produziu a correção certa: alinhar os labels do Deployment, não o seletor do Service. E veio 2× mais barato em tokens e 3× mais rápido.

O agente era o mesmo. O modelo era o mesmo. O acesso ao cluster era o mesmo. O que mudou foi o **critério** — e critério é coisa que se escreve antes.

---

## Contexto: o desafio

A pós-graduação em Engenharia Cloud com IA me deu quatro tickets sobre um parque fictício (a "Metacortex"): uma skill que empacota o padrão de manifests Kubernetes da casa, uma skill de triagem de cluster, uma ferramenta CLI de inventário de VMs por SSH e um dashboard de leitura do cluster. Duas regras valiam para tudo:

1. **Toda skill nasce de um fluxo executado** — primeiro resolve, depois empacota. Skill escrita de cabeça não vale.
2. **Nenhum projeto começa pelo código** — brainstorm, PRD, TRD com ADRs, e só então implementação.

Executei os quatro com um agente pessoal (leao, rodando sobre GLM) contra um cluster kind de verdade na minha máquina — incluindo três incidentes reproduzidos de propósito: um pod morrendo de OOM com limite de 24Mi, uma tag de imagem que nunca existiu no registro, e o seletor quebrado da história acima.

O que ficou do desafio não foram os artefatos. Foram três lições sobre onde mora o valor quando automatizamos.

---

## Lição 1 — Dar acesso não é dar método

A tentação com agentes é pensar que basta conectar a ferramenta: dê `kubectl` a ele e pronto, ele tria. Não dá.

Sem método, o agente com acesso total ao cluster fez o que um plantonista novo faz: explorou. Oito comandos, duas voltas desnecessárias (pediu log de pod morto, tentou `top` num cluster sem metrics-server), diagnóstico correto no fim — mas sem severidade, sem prova citada, sem formato que outro plantonista consiga ler às 3h da manhã.

Com a skill de triagem, o caminho virou: sintoma → primeira fonte certa → camadas numa ordem fixa → cruzar duas fontes quando uma não decide → **parar** quando a causa está identificada. A saída saiu num formato de quatro linhas (causa, prova, correção sugerida, o que continua funcionando ao lado) — e com uma trava que se provou essencial: **a triagem só lê o cluster**. A correção é proposta, nunca aplicada.

O detalhe que mais me surpreendeu: a skill também precisava dizer **quando não entrar em ação**. Na matriz de roteamento de dez frases que testei, uma era ambígua ("esse manifesto não sobe no cluster") e disparou a skill errada. A correção não foi mexer no código — foi reescrever a fronteira na descrição: sintoma de runtime é triagem; revisão de YAML antes de aplicar é outra skill. **O método inclui saber o que não é com você.**

---

## Lição 2 — Automatizar é decidir o que fica de fora

A skill de manifests foi a que mais ensinou sobre curadoria, porque o padrão da casa era longo demais para caber inteiro.

Antes de escrever uma linha de validação, rodei a ferramenta determinística disponível (Trivy) contra um manifesto ruim de propósito. Resultado: 18 achados de segurança genérica — e **nenhum** deles pegava o segredo de banco em texto puro no `env`, nem as regras de identidade da casa. Esse mapeamento, feito antes, decidiu a arquitetura da skill: o que o Trivy já cobre não se reimplementa; o que só a casa exige virou script; o que exige **ler o projeto da aplicação** (porta real, endpoint de saúde que existe de verdade, particularidades de start) virou instrução.

E o que ficou de fora ficou de fora **com justificativa**: o bloco de vocabulário do padrão é material de onboarding humano, não regra de revisão; a lista de exceções aprovadas é contexto organizacional, não conferência automática; regras "recomendadas" viram aviso que exige justificativa no PR, não bloqueio.

A recompensa veio depois, em produção do exercício: aplicando os manifests num cluster real, a imagem recusou-se a bootar porque um env apontava para um diretório que o volume não cria. O achado não virou exceção silenciosa — virou documentação na skill, com a lição generalizada ("caminhos de env × volumeMounts precisam existir"). **Uma automação que registra o que aprendeu com o próprio fracasso é a única que melhora com o uso.**

---

## Lição 3 — A especificação vem antes do código (e sobrevive a ele)

Os dois projetos completos (CLI de inventário, dashboard) começaram por PRD e TRD com ADRs — cada decisão em aberto registrada com as alternativas **descartadas** e o que se ganha e perde em cada uma.

O que a spec comprou, na prática:

- **Escopo travado antes da primeira linha.** O dashboard tinha "decisões em aberto" explícitas: linguagem, cliente de API, estratégia de atualização, fonte de endpoints. Quatro ADRs escritos antes do primeiro `npm install` — e a implementação inteira coube neles, sem reabrir discussão no meio.
- **Comportamento de falha como requisito, não como acidente.** Os três cenários (cluster inacessível, credencial expirada, permissão negada por recurso) entraram no PRD com o comportamento esperado — "degrada por recurso, não desliga a tela" — e saíram no código como `Promise.allSettled` + campo de erros por recurso.
- **Garantia de restrição em código, não em intenção.** "O painel é somente leitura" virou um script que varre o código por chamadas de escrita e **falha o build** se achar uma. Intenção não é garantia; verificação é.

E o que a spec **não** pegou — porque não podia: a versão do cliente Kubernetes instalada usava uma assinatura posicional que eu não esperava, e o `emptyDir` do Kubernetes não cria subdiretórios. Mas aqui está o ponto: quando o imprevisto veio, a spec disse exatamente **onde ele morava**. Não foi "o projeto está errado"; foi "o ADR-02 assumiu API 1.x e a realidade é 0.x — corrige-se o ADR, registra-se a lição". A spec não previu tudo. Ela organizou o imprevisto.

---

## O fio que amarra as três

As três lições são a mesma lição em camadas diferentes:

- Na **skill de triagem**, o que escrevi antes foi o **método** (por onde começar, quando cruzar fontes, quando parar).
- Na **skill de manifests**, o que escrevi antes foi a **curadoria** (o que é script, o que é instrução, o que fica fora — e por quê).
- Nos **projetos**, o que escrevi antes foi a **especificação** (requisitos, decisões com alternativas descartadas, critérios de pronto).

Em todas, o agente com acesso era capaz de *fazer*. O que ele não era capaz de fazer sozinho era *decidir o que vale fazer, na ordem certa, com o critério da casa*. Isso não vem do modelo — vem de cima, de quem escreve antes.

Ferramenta resolve alcance. O que você escreve antes resolve critério.

---

*Tudo o que descrevi está público, com as provas de execução: documentos de spec, skills com curadoria justificada, saídas reais dos três chamados de incidente, e o registro honesto do que não funcionou — em [github.com/juarezbamberg-source/Sistemas-Metacortex](https://github.com/juarezbamberg-source/Sistemas-Metacortex).*
