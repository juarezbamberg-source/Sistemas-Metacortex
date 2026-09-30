#!/usr/bin/env python3
"""Regras da casa da Metacortex que nem o Trivy nem o schema cobrem.

Camada determinística da skill: valida apenas o que é mecânico — conferido
em qualquer manifesto sem ler o projeto. O que exige ler o projeto
(probes corretas para a app, credenciais, migração) é instrução, não código.

Níveis:
  FALHA — regra obrigatória ou proibida violada: barra (exit 1).
  AVISO — regra recomendada não atendida: exige justificativa no PR.

Uso: python validar_padrao.py <arquivo-ou-diretorio-com-manifests>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FALHA: pyyaml não instalado (pip install pyyaml)")
    sys.exit(2)

LABELS = (
    "app.kubernetes.io/name",
    "app.kubernetes.io/instance",
    "app.kubernetes.io/part-of",
    "app.kubernetes.io/managed-by",
)
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NS_OK = re.compile(r"^[a-z0-9]+-(dev|stg|prod)$")
REGISTRY = "registry.metacortex.io"
NOMES_RUINS = {"app", "main", "container"}
SECRET_RE = re.compile(
    r"(postgres(ql)?://|mysql://|mongodb(\+srv)?://|redis://|"
    r"password\s*=|passwd|senha\s*=|api[_-]?key\s*=|AKIA[0-9A-Z]{16})",
    re.I,
)
FALHA = "FALHA"
AVISO = "AVISO"


class Achado:
    def __init__(self, nivel: str, regra: str, msg: str):
        self.nivel = nivel
        self.regra = regra
        self.msg = msg


def checar_imagem(imagem: str) -> list[Achado]:
    a: list[Achado] = []
    if not imagem:
        return [Achado(FALHA, "3.1", "container sem imagem")]
    if not imagem.startswith(REGISTRY + "/"):
        a.append(Achado(FALHA, "3.7", f"imagem fora do registry interno: {imagem}"))
    parte = imagem.rsplit("/", 1)[-1]
    if "@" not in imagem:
        if ":" not in parte:
            a.append(Achado(FALHA, "3.1", f"imagem sem tag: {imagem}"))
        elif parte.rsplit(":", 1)[1] == "latest":
            a.append(Achado(FALHA, "3.1", "tag :latest proibida — use tag imutável ou digest"))
    return a


def checar_container(cont: dict) -> list[Achado]:
    a: list[Achado] = []
    nome = cont.get("name") or ""
    if nome in NOMES_RUINS:
        a.append(Achado(AVISO, "1.6", f'container "{nome}" — prefira o nome do componente (api, worker…)'))

    a += checar_imagem(cont.get("image") or "")

    recursos = cont.get("resources") or {}
    for campo in ("requests", "limits"):
        bloco = recursos.get(campo) or {}
        for r in ("cpu", "memory"):
            if r not in bloco:
                a.append(Achado(FALHA, "2.1", f'container "{nome}" sem {campo} de {r}'))

    if not cont.get("readinessProbe"):
        a.append(Achado(FALHA, "2.2", f'container "{nome}" sem readinessProbe'))
    if not cont.get("livenessProbe"):
        a.append(Achado(FALHA, "2.2", f'container "{nome}" sem livenessProbe'))

    ctx = cont.get("securityContext") or {}
    if ctx.get("allowPrivilegeEscalation") is not False:
        a.append(Achado(FALHA, "3.2", f'container "{nome}" sem allowPrivilegeEscalation: false'))
    if ctx.get("readOnlyRootFilesystem") is not True:
        a.append(Achado(FALHA, "3.2", f'container "{nome}" sem readOnlyRootFilesystem: true'))
    drops = (ctx.get("capabilities") or {}).get("drop") or []
    if "ALL" not in drops:
        a.append(Achado(FALHA, "3.2", f'container "{nome}" sem capabilities.drop: ["ALL"]'))

    for ev in cont.get("env") or []:
        if "value" in ev and SECRET_RE.search(str(ev.get("value") or "")):
            a.append(Achado(FALHA, "3.3", f'env "{ev.get("name")}" com valor sensível em texto puro — use secretKeyRef'))

    return a


def checar_deployment(doc: dict, ambiente: str | None) -> list[Achado]:
    a: list[Achado] = []
    spec = doc.get("spec") or {}

    replicas = spec.get("replicas", 1)
    if ambiente == "prod" and replicas < 2:
        a.append(Achado(FALHA, "2.3", f"prod com {replicas} réplica(s) — mínimo 2"))

    if ambiente == "prod":
        estr = spec.get("strategy") or {}
        if estr.get("type") != "RollingUpdate":
            a.append(Achado(FALHA, "2.4", "prod sem strategy RollingUpdate"))
        elif (estr.get("rollingUpdate") or {}).get("maxUnavailable") not in (0, "0", "0%"):
            a.append(Achado(FALHA, "2.4", "prod com maxUnavailable != 0"))

    tmpl_labels = ((spec.get("template") or {}).get("metadata") or {}).get("labels") or {}
    match = (spec.get("selector") or {}).get("matchLabels") or {}
    if not match:
        a.append(Achado(FALHA, "1.4", "Deployment sem selector.matchLabels"))
    for k, v in match.items():
        if tmpl_labels.get(k) != v:
            a.append(Achado(FALHA, "1.4", f'selector "{k}: {v}" não casa com o template'))

    faltam = [r for r in LABELS if r not in tmpl_labels]
    if faltam:
        a.append(Achado(FALHA, "1.3", f"template sem rótulos obrigatórios: {', '.join(faltam)}"))

    podspec = (spec.get("template") or {}).get("spec") or {}
    if podspec.get("automountServiceAccountToken") is not False:
        a.append(Achado(FALHA, "3.4", "automountServiceAccountToken não é false"))
    sa = podspec.get("serviceAccountName")
    if not sa or sa == "default":
        a.append(Achado(AVISO, "3.5", "sem ServiceAccount dedicada"))
    if "terminationGracePeriodSeconds" not in podspec:
        a.append(Achado(AVISO, "2.6", "terminationGracePeriodSeconds não declarado"))
    for k in ("hostNetwork", "hostPID", "hostIPC"):
        if podspec.get(k):
            a.append(Achado(FALHA, "3.6", f"{k}: true é proibido"))

    pctx = podspec.get("securityContext") or {}
    if pctx.get("runAsNonRoot") is not True:
        a.append(Achado(FALHA, "3.2", "pod sem runAsNonRoot: true"))
    if pctx.get("runAsUser") is None:
        a.append(Achado(FALHA, "3.2", "pod sem runAsUser"))

    for cont in podspec.get("containers") or []:
        a += checar_container(cont)
    return a


def validar_objeto(doc: dict, ambiente: str | None) -> list[Achado]:
    a: list[Achado] = []
    kind = doc.get("kind")
    meta = doc.get("metadata") or {}
    nome = meta.get("name") or ""
    rotulos = meta.get("labels") or {}
    namespace = meta.get("namespace")
    anotacoes = meta.get("annotations") or {}

    if not kind:
        return [Achado(FALHA, "estrutura", "objeto sem kind")]
    if kind == "Kustomization":
        return []

    if not KEBAB.match(nome):
        a.append(Achado(FALHA, "1.1", f'nome "{nome}" fora de kebab-case'))

    if kind == "Namespace":
        if not NS_OK.match(nome):
            a.append(Achado(FALHA, "1.2", f'namespace "{nome}" fora do formato <cliente>-<ambiente>'))
    else:
        if namespace is None:
            a.append(Achado(FALHA, "1.2", "objeto namespaced sem namespace"))
        elif not NS_OK.match(namespace):
            a.append(Achado(FALHA, "1.2", f'namespace "{namespace}" fora do formato <cliente>-<ambiente>'))

    faltam = [r for r in LABELS if r not in rotulos]
    if faltam:
        a.append(Achado(FALHA, "1.3", f"rótulos obrigatórios ausentes: {', '.join(faltam)}"))

    if "metacortex.io/owner" not in anotacoes:
        a.append(Achado(AVISO, "1.5", "anotação metacortex.io/owner ausente"))

    if kind == "Deployment":
        a += checar_deployment(doc, ambiente)
    elif kind == "ConfigMap":
        for k, v in (doc.get("data") or {}).items():
            if SECRET_RE.search(str(v)):
                a.append(Achado(FALHA, "3.3", f'ConfigMap "{nome}" chave "{k}" com valor sensível'))
    elif kind == "Secret":
        if doc.get("stringData"):
            a.append(Achado(FALHA, "3.3", "Secret com stringData (texto puro) — use data (base64)"))
    return a


def cruzar(pares: list, ambiente: str | None) -> list[Achado]:
    """Checagens que cruzam objetos: Service × Deployment (1.4) e PDB (2.5)."""
    a: list[Achado] = []
    deps = [d for _, d in pares if d.get("kind") == "Deployment"]
    svcs = [s for _, s in pares if s.get("kind") == "Service"]
    tem_pdb = any(d.get("kind") == "PodDisruptionBudget" for _, d in pares)

    def tmpl_labels(dep: dict) -> dict:
        return (((dep.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("labels") or {}

    for serv in svcs:
        seletor = (serv.get("spec") or {}).get("selector") or {}
        if not seletor:
            a.append(Achado(FALHA, "1.4", "Service sem selector"))
            continue
        ns = (serv.get("metadata") or {}).get("namespace")
        alvo = next((d for d in deps
                     if (d.get("metadata") or {}).get("namespace") == ns
                     and tmpl_labels(d).get("app.kubernetes.io/name") == seletor.get("app.kubernetes.io/name")), None)
        if alvo is None:
            continue
        match = ((alvo.get("spec") or {}).get("selector") or {}).get("matchLabels") or {}
        if seletor != match:
            a.append(Achado(FALHA, "1.4", "selector do Service difere do matchLabels do Deployment"))
        portas: dict[int, str | None] = {}
        for cont in (((alvo.get("spec") or {}).get("template") or {}).get("spec") or {}).get("containers") or []:
            for p in cont.get("ports") or []:
                if isinstance(p, dict) and "containerPort" in p:
                    portas[p["containerPort"]] = p.get("name")
        for ps in (serv.get("spec") or {}).get("ports") or []:
            tp = ps.get("targetPort", ps.get("port"))
            if isinstance(tp, int) and tp not in portas:
                a.append(Achado(FALHA, "4.5", f"targetPort {tp} não é porta que nenhum container escute"))
            elif isinstance(tp, str) and tp not in portas.values():
                a.append(Achado(FALHA, "4.5", f'targetPort "{tp}" sem porta nomeada correspondente'))

    if ambiente == "prod" and deps and not tem_pdb:
        a.append(Achado(AVISO, "2.5", "workload de prod sem PodDisruptionBudget"))
    return a


def main() -> int:
    alvo = Path(sys.argv[1] if len(sys.argv) > 1 else "manifests")
    if not alvo.exists():
        print(f"nada para validar: {alvo} não existe")
        return 2

    arquivos = sorted([*alvo.glob("*.yaml"), *alvo.glob("*.yml")]) if alvo.is_dir() else [alvo]
    if not arquivos:
        print("nenhum manifesto encontrado")
        return 2

    total_f, total_a = 0, 0
    for arq in arquivos:
        ambiente = arq.parent.name if arq.parent.name in ("dev", "stg", "prod") else None
        try:
            docs = [d for d in yaml.safe_load_all(arq.read_text(encoding="utf-8")) if isinstance(d, dict)]
        except yaml.YAMLError as e:
            print(f"✗ {arq}")
            print(f"    FALHA [yaml] erro de parse: {str(e).splitlines()[0]}")
            total_f += 1
            continue
        pares = [(arq, d) for d in docs]
        achados = []
        for d in docs:
            achados += validar_objeto(d, ambiente)
        achados += cruzar(pares, ambiente)

        fs = [x for x in achados if x.nivel == FALHA]
        av = [x for x in achados if x.nivel == AVISO]
        total_f += len(fs)
        total_a += len(av)
        if fs:
            print(f"✗ {arq}")
            for x in fs:
                print(f"    FALHA [{x.regra}] {x.msg}")
            for x in av:
                print(f"    aviso [{x.regra}] {x.msg}")
        elif av:
            print(f"⚠ {arq}")
            for x in av:
                print(f"    aviso [{x.regra}] {x.msg}")
        else:
            print(f"✓ {arq}")

    print()
    print(f"padrão da casa: {len(arquivos)} arquivo(s) · {total_f} falha(s) · {total_a} aviso(s)")
    if total_f:
        print("REVISAÇÃO BARRADA — regra obrigatória/proibida violada.")
        return 1
    if total_a:
        print("APROVADO COM AVISOS — justifique exceções a recomendados no PR.")
        return 0
    print("APROVADO — nenhuma violação.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
