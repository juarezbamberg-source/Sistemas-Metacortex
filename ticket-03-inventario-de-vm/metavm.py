#!/usr/bin/env python3
"""metavm — inventário e drift de VMs Linux via SSH (somente leitura).

Uso: metavm check --baseline baseline.yaml --inventario inventario.yaml [--saida DIR]
Vereditos: conforme | desvio | nao_verificado. Exit: 0 ok, 1 desvio/não-verificado, 2 erro de uso.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from pathlib import Path

import yaml


# ---------- modelo ----------
@dataclass
class Check:
    id: str
    tipo: str  # pacote | servico | arquivo | sysctl | comando
    severidade: str = "warning"
    nome: str = ""
    chave: str = ""
    caminho: str = ""
    comando: str = ""
    esperado: str = ""
    esperado_regex: str = ""

@dataclass
class Host:
    nome: str
    host: str
    porta: int
    usuario: str
    chave: str
    perfil: str

@dataclass
class Resultado:
    host: str
    check: str
    veredito: str
    severidade: str
    esperado: str = ""
    observado: str = ""
    motivo: str = ""

@dataclass
class Laudo:
    resultados: list[Resultado] = field(default_factory=list)
    def resumo(self):
        r = self.resultados
        return {"hosts_total": len({x.host for x in r}),
                "conforme": sum(1 for x in r if x.veredito == "conforme"),
                "desvio": sum(1 for x in r if x.veredito == "desvio"),
                "nao_verificado": sum(1 for x in r if x.veredito == "nao_verificado")}


# ---------- baseline (herança extends) ----------
def carregar_baseline(caminho: Path) -> dict[str, list[Check]]:
    bruto = yaml.safe_load(caminho.read_text())["perfis"]
    resolvido: dict[str, list[Check]] = {}

    def resolver(nome: str, pilha: tuple[str, ...] = ()) -> list[Check]:
        if nome in resolvido:
            return resolvido[nome]
        if nome in pilha:
            raise SystemExit(f"ciclo de extends em {nome}")
        p = bruto[nome]
        checks = list(p.get("checks") or [])
        pai = p.get("extends")
        if pai:
            herdados = {c.id: dict(c.__dict__) if isinstance(c, Check) else c
                        for c in resolver(pai, pilha + (nome,))}
            for c in checks:
                herdados[c["id"]] = c  # filho sobrescreve pelo id
            checks = list(herdados.values())
        objs = [Check(**{k: v for k, v in c.items() if k in Check.__dataclass_fields__}) for c in checks]
        resolvido[nome] = objs
        return objs

    for nome in bruto:
        resolver(nome)
    return resolvido


def carregar_inventario(caminho: Path):
    inv = yaml.safe_load(caminho.read_text())
    hosts = [Host(**{k: h[k] for k in ("nome", "host", "porta", "usuario", "chave", "perfil")})
             for h in inv["hosts"]]
    return hosts, inv.get("opcoes") or {}


# ---------- comandos de coleta (todos somente leitura) ----------
def comando_do_check(c: Check) -> str:
    if c.tipo == "pacote":
        return f"(command -v dpkg >/dev/null && dpkg -s {c.nome} >/dev/null 2>&1 && echo presente) || (rpm -q {c.nome} >/dev/null 2>&1 && echo presente) || echo ausente"
    if c.tipo == "servico":
        return f"systemctl is-active {c.nome} 2>/dev/null || (service {c.nome} status >/dev/null 2>&1 && echo ativo) || echo inativo"
    if c.tipo == "arquivo":
        if c.esperado == "existe":
            return f"test -e {c.caminho} && echo existe || echo ausente"
        return f"stat -c '%a' {c.caminho} 2>/dev/null || echo ausente"
    if c.tipo == "sysctl":
        return f"sysctl -n {c.chave} 2>/dev/null || echo sem-fato"
    return c.comando  # tipo comando


# ---------- coleta ----------
def coletar(check: Check, host: Host, opcoes: dict) -> tuple[str, str]:
    """Retorna (observado, motivo). motivo vazio = ok."""
    remoto = comando_do_check(check)
    base = opcoes.get("ssh_cmd", "dbclient")
    argv = [base]
    if not opcoes.get("strict_hostkeys", False):
        argv += ["-y"]
    argv += ["-T", "-i", host.chave, "-p", str(host.porta),
             f"{host.usuario}@{host.host}", remoto]
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=opcoes.get("timeout_comando", 15), stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return "", f"cliente ssh '{base}' não encontrado"
    except subprocess.TimeoutExpired:
        return "", "timeout do comando"
    if p.returncode != 0 and not p.stdout.strip():
        return "", f"comando falhou (rc={p.returncode}): {p.stderr.strip()[:120]}"
    return p.stdout.strip(), ""


def alcancavel(host: Host, opcoes: dict) -> tuple[bool, str]:
    base = opcoes.get("ssh_cmd", "dbclient")
    argv = [base, "-y", "-T", "-i", host.chave, "-p", str(host.porta),
            f"{host.usuario}@{host.host}", "true"]
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=opcoes.get("timeout_conexao", 10), stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return False, f"cliente ssh '{base}' não encontrado"
    except subprocess.TimeoutExpired:
        return False, "timeout de conexão"
    if p.returncode != 0:
        return False, f"conexão falhou: {(p.stderr or '').strip().splitlines()[-1][:120] if (p.stderr or '').strip() else f'rc={p.returncode}'}"
    return True, ""


# ---------- comparação ----------
import re

def compara(check: Check, observado: str) -> bool:
    if check.esperado_regex:
        return re.search(check.esperado_regex, observado) is not None
    return observado == check.esperado


def verificar_host(host: Host, checks: list[Check], opcoes: dict) -> list[Resultado]:
    ok, motivo = alcancavel(host, opcoes)
    if not ok:
        return [Resultado(host.nome, c.id, "nao_verificado", c.severidade,
                          motivo=motivo) for c in checks]
    out = []
    for c in checks:
        obs, motivo = coletar(c, host, opcoes)
        if motivo and not obs:
            out.append(Resultado(host.nome, c.id, "nao_verificado", c.severidade, motivo=motivo))
        elif compara(c, obs):
            out.append(Resultado(host.nome, c.id, "conforme", c.severidade, observado=obs))
        else:
            out.append(Resultado(host.nome, c.id, "desvio", c.severidade,
                                 esperado=c.esperado_regex or c.esperado, observado=obs))
    return out


# ---------- relatórios ----------
def markdown(laudo: Laudo) -> str:
    r = laudo.resumo()
    linhas = [f"# Inventário de VMs — metavm", "",
              f"**{r['hosts_total']} hosts · {r['conforme']} conforme(is) · {r['desvio']} desvio(s) · {r['nao_verificado']} não verificado(s)**", ""]
    por_host: dict[str, list[Resultado]] = {}
    for x in laudo.resultados:
        por_host.setdefault(x.host, []).append(x)
    icon = {"conforme": "✅", "desvio": "❌", "nao_verificado": "❔"}
    for host, rs in por_host.items():
        linhas += [f"## {host}", "", "| check | veredito | severidade | esperado | observado | motivo |", "|---|---|---|---|---|---|"]
        for x in rs:
            linhas.append(f"| {icon[x.veredito]} {x.check} | {x.veredito} | {x.severidade} | {x.esperado} | {x.observado} | {x.motivo} |")
        linhas.append("")
    return "\n".join(linhas)


# ---------- CLI ----------
def main() -> int:
    ap = argparse.ArgumentParser(prog="metavm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ck = sub.add_parser("check", help="roda baseline contra o inventário")
    ck.add_argument("--baseline", required=True)
    ck.add_argument("--inventario", required=True)
    ck.add_argument("--saida", default=None, help="diretório p/ relatorios (md+json)")
    args = ap.parse_args()

    caminho_b = Path(args.baseline)
    caminho_i = Path(args.inventario)
    if not caminho_b.exists() or not caminho_i.exists():
        print(f"erro de uso: arquivo inexistente ({caminho_b} / {caminho_i})", file=sys.stderr)
        return 2
    perfis = carregar_baseline(caminho_b)
    hosts, opcoes = carregar_inventario(caminho_i)
    # resolver chave relativa ao inventário
    for h in hosts:
        ch = Path(h.chave)
        if not ch.exists():
            alt = caminho_i.parent / h.chave
            h.chave = str(alt if alt.exists() else ch)

    laudo = Laudo()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for rs in ex.map(lambda h: verificar_host(h, perfis.get(h.perfil, perfis.get("base", [])), opcoes), hosts):
            laudo.resultados += rs

    r = laudo.resumo()
    print(f"{r['hosts_total']} hosts · {r['conforme']} conforme(s) · {r['desvio']} desvio(s) · {r['nao_verificado']} não verificado(s)")
    for x in laudo.resultados:
        if x.veredito != "conforme":
            det = x.motivo or f"esperado '{x.esperado}', observado '{x.observado}'"
            print(f"  {x.host}: {x.check} → {x.veredito} ({x.severidade}) {det}")
    if args.saida:
        d = Path(args.saida); d.mkdir(parents=True, exist_ok=True)
        (d / "laudo.md").write_text(markdown(laudo))
        (d / "laudo.json").write_text(json.dumps({"resumo": r, "resultados": [asdict(x) for x in laudo.resultados]}, indent=2, ensure_ascii=False))
        print(f"relatórios em {d}/laudo.md e laudo.json")
    return 1 if (r["desvio"] or r["nao_verificado"]) else 0


if __name__ == "__main__":
    sys.exit(main())
