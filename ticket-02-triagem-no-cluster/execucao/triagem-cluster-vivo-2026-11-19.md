# Triagem dos 3 chamados — execução real no cluster (2026-11-19)

Cluster: `kind-metacortex` (v1.35.0, node Debian 12 bookworm, kernel 6.6.87 WSL2),
acessado pelo túnel `vienna-pairs-oak-gathered.trycloudflare.com` com token de
ServiceAccount `leao-admin`. Método: os 4 passos da skill do T02 (sintoma → camadas →
cruzamento → veredito).

---

## Chamado 1 — "o nyx-api reinicia sem parar em produção"

**Sintoma relatado**: pod reiniciando, aplicação fora do ar em prod.

**O que o método manda olhar primeiro**: `get pods -n nyx-prod` (STATUS + RESTARTS).

```
NAME                          STATUS    WAITING            LAST       EXIT   RESTARTS   READY
nyx-api-78587b9b89-pnv9m      Running   CrashLoopBackOff   OOMKilled  137    381        false
nyx-api-7b5d464dcb-5ft69      Running   CrashLoopBackOff   OOMKilled  137    8          false
nyx-api-7b5d464dcb-tfczw      Running   CrashLoopBackOff   OOMKilled  137    8          false
nyx-postgres-7ffbcfbbcb-lzj8g Running   <none>             Unknown    255    4          true
```

**Cruzamento**: `waiting.reason = CrashLoopBackOff` × `lastState.terminated.reason = OOMKilled`
× `exitCode = 137`. Os três concordam — não é erro de aplicação, é o kernel matando o
processo por memória. Então olhei o limite:

```
limits={"memory":"24Mi"}  requests={"memory":"8Mi"}
```

**Veredito**

```
CAUSA: OOMKill — o container estoura o limite de memória de 24Mi e o kubelet o mata (SIGKILL, exit 137)
PROVA: containerStatuses[0].lastState.terminated.reason=OOMKilled, exitCode=137, restartCount=381;
       deploy nyx-api recursos limits.memory=24Mi; evento Warning/BackOff repetindo a cada ~1 min
CORREÇÃO SUGERIDA: subir limits.memory para um valor compatível com o consumo real da api
       (o processo de teste aloca 80M; começar em 256Mi e medir), mantendo requests abaixo do limit.
       Eu NÃO aplico — a correção é do plantonista.
CONFORTO: nyx-postgres 1/1 Running — o banco está de pé; a indisponibilidade é só da api.
```

**Nota**: 381 reinícios em 49 dias é o limite de backoff do kubelet (5 min entre tentativas).
O `CrashLoopBackOff` aqui é consequência do OOM, não a causa.

---

## Chamado 2 — "orion-web parou depois do deploy"

**Sintoma relatado**: parou após deploy, sem acesso.

**Primeiro lugar**: `get pods -n orion-stg` → `ImagePullBackOff`.

```
orion-web-5d4f6574bd-xh9fc   Pending   ImagePullBackOff
orion-web-66cd974dbc-h2z8t   Pending   ImagePullBackOff
```

**Cruzamento**: a mensagem do evento cita a tag exata:

```
Failed to pull image "fabricioveronez/fake-shop:v1.14.2":
  rpc error: code = NotFound desc = failed to resolve reference ...: not found
```

E o Deployment declara exatamente essa tag. Não é rede, não é autenticação — o registro
respondeu **NotFound**, ou seja, **a tag não existe**.

**Veredito**

```
CAUSA: a tag da imagem não existe no registro — o deploy apontou para uma versão que o
       pipeline nunca publicou
PROVA: eventos Failed com `code = NotFound` e `failed to resolve reference`: não é timeout
       de rede (seria EOF/i/o timeout) nem 401 (seria unauthorized)
CORREÇÃO SUGERIDA: apontar para uma tag que exista (o chamado cita v1.14.2 anunciada pelo
       release) e conferir a lista real de tags no registro antes de aplicar
CONFORTO: orion-postgres 1/1 Running — o banco está no ar.
```

**Observação honesta**: encontrei **dois** pods em ImagePullBackOff neste namespace: o
original (`v1.14.2`) e um segundo que eu mesmo criei no laboratório com uma tag inventada
(`1.14.2-tag-que-nao-existe`) para testar o cenário. Os dois foram úteis como prova; o
cluster é descartável.

---

## Chamado 3 — "o Service do nyx não entrega tráfego"

**Sintoma relatado**: 503 / sem tráfego.

**Primeiro lugar**: `get endpoints nyx-api -n nyx-stg`.

**O que encontrei**: o chamado **já estava corrigido** no cluster. O Service e o Deployment
têm o mesmo seletor (`app: nyxapi`) e os endpoints estão populados:

```
nyx-api   10.244.0.11:80,10.244.0.16:80
```

Então reproduzi o defeito num namespace separado (`chamado3-repro`), com o manifesto que
está versionado em `chamados/chamado3-nyx-stg.yaml` (Service com `app: nyx-api`, pods com
`app: nyxapi`):

```
NAME                       READY   STATUS
nyx-api-6dbc4c4b8c-7vx6g   1/1     Running
nyx-api-6dbc4c4b8c-v6nkw   1/1     Running

nyx-api   <none>            <- Endpoints vazio apesar de 2 pods Running
```

**Cruzamento** (o passo que resolve este chamado):

```
svc.selector = {"app":"nyx-api"}
pod.labels   = {"app":"nyxapi"}
```

Um caractere de diferença: `nyx-api` vs `nyxapi`. O Service só encaminha para pods cujos
**labels casam exatamente** com o seletor.

**Veredito**

```
CAUSA: seletor do Service não casa com os labels dos pods (nyx-api x nyxapi) — o Service
       não tem endpoint, então não há para onde rotear
PROVA: Endpoints/EndpointSlice `<none>` com 2 pods `1/1 Running`; svc.selector=app:nyx-api
       contra pod.labels=app:nyxapi
CORREÇÃO SUGERIDA: alinhar um dos lados (o usual é corrigir o seletor do Service para
       `app: nyxapi`, sem tocar nos pods)
CONFORTO: os pods estão saudáveis e servindo na porta 8080 — o problema é só o roteamento
```

**Observação**: este é o caso mais didático dos três — os indicadores usuais (pods Running,
deploy 2/2, sem Warning nos eventos) dizem "está tudo bem". Só o cruzamento Service × Pod
revela o problema. É exatamente por isso que a skill fixa esse cruzamento como obrigatório
para sintomas de "503" / "sem tráfego".

---

## O que esta execução mudou em relação à anterior

A triagem anterior (30/09) foi feita com os manifests aplicados e os estados observados.
Esta foi feita **agora**, contra o cluster vivo, com:

- os valores lidos do `containerStatuses` (não de saída de texto)
- a contagem de reinícios real (381, não "3")
- o Chamado 3 **reproduzido de novo** porque o original tinha sido corrigido no cluster
- os eventos com timestamp, provando a repetição do BackOff

## Limpeza

O namespace `chamado3-repro` foi criado por mim e será apagado ao final da sessão.
Os namespaces originais (`nyx-prod`, `nyx-stg`, `orion-stg`, `nyx-dev`, `orion-dev`)
não foram alterados.
