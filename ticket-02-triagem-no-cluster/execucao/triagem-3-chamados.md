# Saída real da triagem dos 3 chamados (2026-09-30, cluster kind-metacortex v1.35.0)

## Chamado 1 — nyx-prod: "a API reinicia sozinha"
```
POD STATUS: 0/1 OOMKilled, restarts=3 (2 em 38s)
lastState.terminated: reason=OOMKilled, exitCode=137, viveu 2s
resources.limits: memory=24Mi, cpu=200m
CAUSA: limit de memória de 24Mi mata o Node.js ao subir (OOMKill 137) —
       corte de custos alterou limits do namespace inteiro.
CORREÇÃO SUGERIDA (não aplicada): limits.memory ≥ 256Mi.
```

## Chamado 2 — orion-stg: "loja parou após publicação do Loom"
```
POD STATUS: 0/1 ImagePullBackOff (3/3 réplicas)
waiting.message: failed to resolve reference docker.io/fabricioveronez/fake-shop:v1.14.2
Tags reais do repositório (consulta ao registro): latest, v1, 1, v26, v20
CAUSA: a tag v1.14.2 anunciada no release nunca existiu no registro —
       o pipeline de publicação (Loom) não empurrou o que o release anunciou.
CORREÇÃO SUGERIDA (não aplicada): publicar a tag correta ou apontar deploy para tag existente.
```

## Chamado 3 — nyx-stg: "503 para quem chama de fora"
```
PODS: 2/2 Running, probes OK (aplicação saudável)
Service nyx-api selector: {app: nyx-api}
Pod labels:              {app: nyxapi}   ← sem hífen
kubectl get endpoints nyx-api → ENDPOINTS <none>
CAUSA: selector do Service não casa com os labels do pod — zero endpoints,
       todo tráfego externo recebe 503. Aplicação perfeita, entrega quebrada.
CORREÇÃO SUGERIDA (não aplicada): alinhar labels do template/selector do Deployment
       para app: nyx-api (padrão da casa), NÃO o seletor do Service.
```

**Lição dos três**: mesmo sintoma ("fora do ar"), três camadas (recursos → imagem/CI → rede/serviço) — e a ordem da triagem muda conforme o sintoma inicial, não conforme o chamado.
