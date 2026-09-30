# Mapeamento Trivy ↔ padrão da casa

Rodado com **Trivy v0.74.0** (`trivy config`, scanner misconfig) sobre o manifesto barrado do Ticket 01, em 2026-09-30. Conclusão: o Trivy cobre boa parte do **Bloco 3** (segurança genérica de container) e **nada** dos Blocos 1, 2 e 4.

## O que o Trivy já pega (não reimplementar além do estrito)

| KSV | Severidade | Regra da casa relacionada | Observação |
|---|---|---|---|
| KSV-0013 | MEDIUM | 3.1 (`:latest` proibida) | Trivy dá MEDIUM; a casa dá **proibido** → script mantém FALHA |
| KSV-0012 / KSV-0118 | MEDIUM/HIGH | 3.2 (runs as root / securityContext) | a casa é mais específica: exige `runAsNonRoot`, `runAsUser`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem`, `drop: ["ALL"]` — o script checa os 5 explicitamente |
| KSV-0014 | HIGH | 3.2 (rootfs read-only) | idem, coberto pelos dois |
| KSV-0001 / KSV-0003 / KSV-0004 | MEDIUM/LOW | 3.2 (privilege escalation, capabilities) | script exige `drop: ["ALL"]` (mais estrito que o default do Trivy) |
| KSV-0011 / KSV-0015 / KSV-0016 / KSV-0018 | LOW/MEDIUM | 2.1 (requests/limits) | Trivy em severidades baixas; a casa trata como **obrigatório** → script dá FALHA |
| KSV-0104 / KSV-0030 | MEDIUM/LOW | (não é regra da casa) | seccomp — fora do padrão; não duplicar no script |
| KSV-0125 | MEDIUM | 3.7 (registry interno) | Trivy usa allowlist genérica; script fixa `registry.metacortex.io` |
| KSV-0020 / KSV-0021 / KSV-0106 | LOW | 3.2 adjacente | UID/GID e NET_BIND_SERVICE — Trivy cobre, script não repete |

## O que o Trivy NÃO pega (o script é o único que pega)

| Regra | O que é | Por que o Trivy não pega |
|---|---|---|
| 1.1 | kebab-case no nome | convenção da casa, não é segurança |
| 1.2 | namespace `<cliente>-<ambiente>` | convenção organizacional |
| 1.3 | 4 rótulos `app.kubernetes.io/*` | inventário/custeio da casa |
| 1.4 | selector × matchLabels × template **cruzados entre objetos** | Trivy analisa objeto a objeto |
| 2.2 | probes presentes, endpoints distintos | resiliência da casa |
| 2.3 | réplicas ≥ 2 em prod | regra de ambiente |
| 2.4 | RollingUpdate maxUnavailable 0 em prod | regra de ambiente |
| 2.5 | PDB em prod | objeto separado (Trivy não cruza) |
| 3.3 | **segredo em texto puro no env** (`postgres://...`) | **confirmado na prática**: o manifesto barrado tem a senha inline e o Trivy não reportou nenhum achado de segredo — os 18 KSVs citam outros motivos |
| 3.4 | `automountServiceAccountToken: false` | não está no catálogo KSV default |
| 4.5 | targetPort × containerPort | cruzamento entre Service e Deployment |

## Evidência da execução (manifesto barrado)

- `trivy config manifesto-barrado.yaml` → **18 KSVs** (2 HIGH, 6 MEDIUM, 10 LOW) — nenhum cita o segredo; nenhum trata identidade/regras de ambiente.
- `python scripts/validar_padrao.py manifesto-barrado.yaml` → **19 FALHAs + 4 avisos** com regra citada, incluindo 3.3 (segredo) e 1.4 (seletor cruzado).
- Conclusão da curadoria: script + Trivy são **complementares**; a sobreposição (3.1, 3.2, 3.7) é intencional — a casa é mais estrita que o catálogo genérico.
