# Saídas reais das execuções (2026-09-30)

## Modo conferência — manifesto barrado do ticket

`python scripts/validar_padrao.py manifesto-barrado.yaml` → exit **1**

```
✗ manifesto-barrado.yaml
    FALHA [1.1] nome "NyxAPI" fora de kebab-case
    FALHA [1.3] rótulos obrigatórios ausentes: app.kubernetes.io/name, instance, part-of, managed-by
    FALHA [1.3] template sem rótulos obrigatórios: (mesmos 4)
    FALHA [3.4] automountServiceAccountToken não é false
    FALHA [3.2] pod sem runAsNonRoot: true
    FALHA [3.2] pod sem runAsUser
    FALHA [3.1] tag :latest proibida — use tag imutável ou digest
    FALHA [2.1] container "api" sem requests de cpu / memory; sem limits de cpu / memory
    FALHA [2.2] container "api" sem readinessProbe
    FALHA [2.2] container "api" sem livenessProbe
    FALHA [3.2] sem allowPrivilegeEscalation: false / readOnlyRootFilesystem / drop ["ALL"]
    FALHA [3.3] env "DATABASE_URL" com valor sensível em texto puro — use secretKeyRef
    FALHA [1.3] Service sem rótulos obrigatórios
    FALHA [1.4] selector do Service difere do matchLabels do Deployment
    aviso [1.5] anotação metacortex.io/owner ausente (×2)
    aviso [3.5] sem ServiceAccount dedicada
    aviso [2.6] terminationGracePeriodSeconds não declarado

padrão da casa: 1 arquivo(s) · 19 falha(s) · 4 aviso(s)
REVISAÇÃO BARRADA — regra obrigatória/proibida violada.
```

**Trivy no mesmo arquivo** → 18 KSVs (2 HIGH, 6 MEDIUM, 10 LOW), incluindo KSV-0013 (`:latest`), KSV-0012/0118 (root/securityContext), KSV-0014 (rootfs), KSV-0125 (registry), KSV-0011/15/16/18 (requests/limits). **Nenhum achado sobre o segredo** — ele só é pego pelo script da casa (3.3).

**Laudo conjunto (o que a Seraph veria):** o manifesto viola 10 das 14 regras mecânicas + as probes exigem leitura do projeto (kube-news tem `/health` e `/ready` em :8080 — é o que as probes devem apontar); `DATABASE_URL` inline é proibição 3.3 → `secretKeyRef`; seletor `app: nyxapi` vs `app: nyx-api` é o erro clássico 1.4 (o Service ficaria sem endpoint).

## Modo escrita — manifests gerados (autoconferência da skill)

**kube-news (nyx):** `deployment.yaml`, `service.yaml`, `config-secret.yaml`, `serviceaccount.yaml`

```
✓ 4 arquivo(s) · 0 falha(s) · 0 aviso(s) — APROVADO (script)
kubeconform -strict: 10 resources, Valid: 10, Invalid: 0 (kube-news + fake-shop)
trivy config --severity HIGH,CRITICAL: 0 achados em ambos os projetos
```

Valores descobertos **lendo o projeto**: porta 8080 (`src/server.js:81`), probes `/ready` e `/health` (`src/system-life.js`), env vars `DB_HOST/DB_DATABASE/DB_USERNAME/DB_PASSWORD/DB_PORT` (`src/models/post.js:8-12`).

**fake-shop (orion):** `deployment.yaml`, `service-sa.yaml`, `config-secret.yaml` — `0 falha(s) · 0 aviso(s)`

Decisões de projeto registradas nos comentários do YAML:
- **Migração no start**: `src/entrypoint.sh` roda `flask db upgrade` antes do gunicorn — mantida no container (não vira Job); rollout documentado.
- **Sem endpoint de saúde**: probes `tcpSocket: 5000` com justificativa inline para a Seraph (o app não expõe healthcheck; tcpSocket prova processo escutando, não saúde).
- **Senha do banco**: `secretKeyRef: fake-shop-db` — placeholder base64 versionado, valor real fora do Git (3.3).
- **/metrics**: existe (`prometheus_flask_exporter`), mas não é healthcheck — não usado como probe.
