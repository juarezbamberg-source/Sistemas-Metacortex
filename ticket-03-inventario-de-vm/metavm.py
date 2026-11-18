#!/usr/bin/env python3
"""metavm — inventário e drift de VM Linux por SSH (somente leitura).

Baseline: as 11 regras do padrão do parque da Metacortex (enunciado T03).
Laudo: contrato completo — host, inventario, conformidade (regra/esperado/
encontrado/veredito/severidade), resumo (contagens + por_severidade).
Saídas: JSON (para o Roster) e Markdown (para o plantão).
Exit: 0 conforme puro · 1 desvios/não-verificados · 2 erro de uso/host morto.

Correções da vaia 2 (2026-11-18):
- dado não coletado (swap/portas vazios) agora é nao_verificado COM MOTIVO,
  nunca falso-conforme; o campo 'encontrado' fica None (nunca o texto do veredito)
- por_severidade conta apenas DESVIOS (como o exemplo do enunciado)
- ADR-05 de linguagem registrada no TRD
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------- baseline oficial (11 regras) ----------
BASELINE = {
    "so.distribuicao":                       dict(esperado="ubuntu",  severidade="alto",    tipo="cmd"),
    "so.versao_minima":                      dict(esperado="22.04",  severidade="alto",    tipo="versao"),
    "kernel.versao_minima":                  dict(esperado="6.5",    severidade="medio",   tipo="versao"),
    "servicos.ativos":                       dict(esperado=["ssh", "containerd", "node_exporter", "chrony"], severidade="alto", tipo="lista"),
    "servicos.proibidos":                    dict(esperado=["telnet.socket", "rpcbind.socket"], severidade="alto", tipo="lista_proibida"),
    "swap.habilitado":                       dict(esperado=False,    severidade="critico", tipo="bool"),
    "portas_em_escuta.publicas_permitidas":  dict(esperado=[22],     severidade="critico", tipo="portas"),
    "portas_em_escuta.somente_rede_interna": dict(esperado=[9100],    severidade="critico", tipo="portas_internas"),
    "chaves_ssh.emitidas_por":               dict(esperado="metacortex-platform", severidade="critico", tipo="chaves"),
    "ssh.login_de_root":                     dict(esperado=False,    severidade="alto",    tipo="sshd"),
    "ntp.sincronizado":                      dict(esperado=True,     severidade="medio",   tipo="ntp"),
}

COLETA = {
    "ident":   "hostname",
    "so":      "cat /etc/os-release 2>/dev/null | head -2",
    "kernel":  "uname -r",
    "servicos": "for s in ssh containerd node_exporter chrony; do echo \"$s:$(systemctl is-active $s.service 2>/dev/null || systemctl is-active $s 2>/dev/null || echo inativo)\"; done; for p in telnet.socket rpcbind.socket; do echo \"proibido-$p:$(systemctl is-active $p 2>/dev/null || echo inativo)\"; done",
    "swap":    "swapon --show 2>/dev/null | tail -n +2 | head -1",
    "portas":  "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null",
    "chaves":  "cat ~/.ssh/authorized_keys 2>/dev/null || echo sem-arquivo",
    "sshd":    "sshd -T 2>/dev/null | grep -i permitrootlogin || grep -ri permitrootlogin /etc/ssh/sshd_config /etc/ssh/sshd_config.d/ 2>/dev/null | tail -1",
    "ntp":     "timedatectl show 2>/dev/null | grep -E 'NTPSynchronized|NTPService' || timedatectl 2>/dev/null | grep -i sync",
}

FALHA_CONEXAO = "host inalcançável"

@dataclass
class Host:
    nome: str
    endereco: str
    porta: int
    usuario: str
    chave: str

def ssh_exec(host: Host, cmd: str, timeout: int = 15):
    argv = ["dbclient", "-y", "-T", "-i", host.chave, "-p", str(host.porta), f"{host.usuario}@{host.endereco}", cmd]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return "", "cliente ssh não encontrado"
    except subprocess.TimeoutExpired:
        return "", "timeout"
    if p.returncode != 0 and not p.stdout.strip():
        return "", f"rc={p.returncode}"
    return p.stdout.strip(), ""

def coletar_host(host: Host) -> dict:
    inv = {}
    for chave, cmd in COLETA.items():
        out, motivo = ssh_exec(host, cmd)
        if motivo == FALHA_CONEXAO:
            return {"_falha": motivo}
        inv[chave] = out if out else None
    return inv

def parse_so(txt):
    if not txt: return None, None
    dist = re.search(r'ID=["\']?([\w-]+)', txt)
    ver = re.search(r'VERSION_ID=["\']?([\d.]+)', txt)
    return (dist.group(1) if dist else None), (ver.group(1) if ver else None)

def versao_ok(encontrada, minima):
    if not encontrada: return False
    try:
        e = [int(x) for x in encontrada.split(".")[:2]]
        m = [int(x) for x in str(minima).split(".")[:2]]
        return e >= m
    except ValueError:
        return False

def interpretar(inv: dict) -> dict:
    dist, ver = parse_so(inv.get("so"))
    servicos = []
    for linha in (inv.get("servicos") or "").splitlines():
        if ":" in linha:
            nome, estado = linha.rsplit(":", 1)
            servicos.append({"nome": nome, "tipo": "socket" if ".socket" in nome else "service", "estado": estado})
    swap_linha = inv.get("swap")
    swap_coletado = bool(swap_linha and swap_linha.strip())
    swap_hab = bool(swap_coletado and swap_linha != "sem-fato")
    swap_tam = swap_linha.split()[1] if swap_coletado and len(swap_linha.split()) > 1 else None
    portas = []
    for linha in (inv.get("portas") or "").splitlines()[1:]:
        m = re.match(r'\s*(LISTEN|0\.0\.0\.0:|\[::\]:|\d+\.){1}.*', linha)
        if m and ("LISTEN" in linha or "0.0.0.0" in linha):
            partes = linha.split()
            addr_porta = next((p for p in partes if ":" in p and p != "0.0.0.0:*"), "")
            bind, _, porta = addr_porta.rpartition(":")
            if porta.isdigit():
                proc = partes[-1] if "users:" in linha else ""
                portas.append({"porta": int(porta), "bind": bind or "0.0.0.0", "processo": proc.strip('()"')})
    chaves = []
    for linha in (inv.get("chaves") or "").splitlines():
        if linha.startswith(("ssh-", "ecdsa-", "sk-")):
            m = re.search(r'\s(\S+@\S+)\s*$', linha)
            chaves.append({"identificacao": m.group(1) if m else "desconhecida"})
    sshd_txt = inv.get("sshd") or ""
    m = re.search(r'permitrootlogin\s+(\S+)', sshd_txt, re.I)
    root_login = None
    if "sshd -T" in sshd_txt or (m and "sshd -T" not in sshd_txt and "rc=" not in sshd_txt):
        if m:
            root_login = m.group(1).lower() not in ("no", "prohibit-password", "without-password", "forced-commands-only")
    ntp_txt = inv.get("ntp") or ""
    ntp_sync = None
    m = re.search(r'NTPSynchronized=(\S+)', ntp_txt) or re.search(r'synchronized:\s*(\S+)', ntp_txt, re.I)
    if m:
        ntp_sync = m.group(1).lower() in ("yes", "true", "sincronizado", "active")
    return {
        "so": {"distribuicao": dist, "versao": ver},
        "kernel": {"versao": inv.get("kernel")},
        "servicos": servicos,
        "swap": {"habilitado": swap_hab, "tamanho": swap_tam, "coletado": swap_coletado},
        "portas_em_escuta": portas,
        "chaves_ssh": chaves,
        "ssh": {"login_de_root": root_login},
        "ntp": {"sincronizado": ntp_sync, "mecanismo": "systemd-timesyncd" if ntp_sync else None},
    }

def conferir(inv: dict) -> list:
    conf = []
    def add(regra, esperado, encontrado, veredito, sev, motivo=None):
        item = {"regra": regra, "esperado": esperado, "encontrado": encontrado,
                "veredito": veredito, "severidade": BASELINE[regra]["severidade"]}
        if motivo: item["motivo"] = motivo
        conf.append(item)
    nv = "nao_verificado"
    so = inv["so"]
    add("so.distribuicao", "ubuntu", so["distribuicao"],
        "conforme" if so["distribuicao"] == "ubuntu" else ("desvio" if so["distribuicao"] else nv), None)
    if so["versao"]:
        add("so.versao_minima", "22.04", so["versao"], "conforme" if versao_ok(so["versao"], "22.04") else "desvio", None)
    else:
        add("so.versao_minima", "22.04", None, nv, None, "dado não coletado")
    if inv["kernel"]["versao"]:
        add("kernel.versao_minima", "6.5", inv["kernel"]["versao"], "conforme" if versao_ok(inv["kernel"]["versao"], "6.5") else "desvio", None)
    else:
        add("kernel.versao_minima", "6.5", None, nv, None, "dado não coletado")
    ativos = {s["nome"]: s["estado"] for s in inv["servicos"] if not s["nome"].startswith("proibido-")}
    faltando = [s for s in BASELINE["servicos.ativos"]["esperado"] if ativos.get(s) != "active"]
    (add("servicos.ativos", BASELINE["servicos.ativos"]["esperado"], [k for k, v in ativos.items() if v == "active"], "desvio" if faltando else "conforme", None)
     if ativos else add("servicos.ativos", BASELINE["servicos.ativos"]["esperado"], None, nv, None, "sem systemctl acessível"))
    proibidos_ativos = [s["nome"].replace("proibido-", "") for s in inv["servicos"] if s["nome"].startswith("proibido-") and s["estado"] == "active"]
    add("servicos.proibidos", "nenhum ativo", proibidos_ativos or [], "desvio" if proibidos_ativos else "conforme", None)
    if inv["swap"].get("coletado") is False:
        add("swap.habilitado", False, None, nv, None, "swapon não retornou dados neste host")
    else:
        add("swap.habilitado", False, inv["swap"]["habilitado"], "desvio" if inv["swap"]["habilitado"] else "conforme", None)
    portas_coletadas = bool(inv.get("portas_em_escuta"))
    publicas = sorted({p["porta"] for p in inv["portas_em_escuta"] if p["bind"] in ("0.0.0.0", "*", "[::]", "::")}) if portas_coletadas else []
    permitidas = BASELINE["portas_em_escuta.publicas_permitidas"]["esperado"]
    fora = [p for p in publicas if p not in permitidas]
    if portas_coletadas:
        add("portas_em_escuta.publicas_permitidas", permitidas, publicas, "desvio" if fora else "conforme", None)
    else:
        add("portas_em_escuta.publicas_permitidas", permitidas, None, nv, None, "ss/netstat não retornaram dados")
    internas = sorted({p["porta"] for p in inv["portas_em_escuta"] if p["bind"] not in ("0.0.0.0", "*", "[::]", "::")})
    esperadas_int = BASELINE["portas_em_escuta.somente_rede_interna"]["esperado"]
    expostas = [p for p in esperadas_int if p in publicas]
    add("portas_em_escuta.somente_rede_interna", f"{esperadas_int} só na rede interna", internas or (publicas if expostas else []), "desvio" if expostas else "conforme", None)
    ids = [c["identificacao"] for c in inv["chaves_ssh"]]
    nao_plataforma = [i for i in ids if "metacortex-platform" not in i]
    (add("chaves_ssh.emitidas_por", "metacortex-platform", ids or None, "desvio" if nao_plataforma else "conforme", None)
     if ids else add("chaves_ssh.emitidas_por", "metacortex-platform", None, nv, None, "authorized_keys vazio ou inacessível"))
    rl = inv["ssh"]["login_de_root"]
    if rl is None:
        add("ssh.login_de_root", False, None, nv, None, "exige privilégio que o usuário da coleta não tem")
    else:
        add("ssh.login_de_root", False, rl, "desvio" if rl else "conforme", None)
    ntp = inv["ntp"]["sincronizado"]
    (add("ntp.sincronizado", True, ntp, "conforme" if ntp else ("desvio" if ntp is False else nv), None)
     if ntp is not None else add("ntp.sincronizado", True, None, nv, None, "dado não coletado"))
    for c in conf:
        c["severidade"] = BASELINE[c["regra"]]["severidade"]
    return conf

def resumo(conf):
    r = {"conforme": 0, "desvio": 0, "nao_verificado": 0, "por_severidade": {"critico": 0, "alto": 0, "medio": 0}}
    for c in conf:
        r[c["veredito"]] += 1
        if c["veredito"] == "desvio":  # por_severidade conta DESVIOS (exemplo do enunciado)
            r["por_severidade"][c["severidade"]] += 1
    return r

def laudo_json(host: Host, inv: dict, hostname=None) -> dict:
    conf = conferir(inv)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"host": {"endereco": host.endereco, "hostname": hostname or inv.get("ident"), "coletado_em": agora}, "inventario": inv, "conformidade": conf, "resumo": resumo(conf)}

def laudo_md(laudo: dict) -> str:
    h = laudo["host"]
    linhas = [f"# Inventário de {h['hostname'] or '?'} ({h['endereco']})", f"Coletado em {h['coletado_em']} · baseline Metacortex v1 (11 regras)", "", "## Desvios", "", "| Severidade | Regra | Esperado | Encontrado |", "|---|---|---|---|"]
    desvios = [c for c in laudo["conformidade"] if c["veredito"] == "desvio"]
    for c in desvios:
        linhas.append(f"| {c['severidade']} | {c['regra']} | {c['esperado']} | {c['encontrado']} |")
    if not desvios:
        linhas.append("| — | nenhum | — | — |")
    linhas += ["", "## Não verificado", "", "| Regra | Motivo |", "|---|---|"]
    nvs = [c for c in laudo["conformidade"] if c["veredito"] == "nao_verificado"]
    for c in nvs:
        linhas.append(f"| {c['regra']} | {c.get('motivo') or 'dado não coletado neste host'} |")
    if not nvs:
        linhas.append("| — | nenhum |")
    linhas += ["", "## Conforme", "", " · ".join(c["regra"] for c in laudo["conformidade"] if c["veredito"] == "conforme") or "—"]
    r = laudo["resumo"]
    linhas += ["", f"**Resumo: {r['conforme']} conforme · {r['desvio']} desvio · {r['nao_verificado']} não verificado**"]
    return "\n".join(linhas)

def main() -> int:
    ap = argparse.ArgumentParser(prog="metavm")
    ap.add_argument("endereco")
    ap.add_argument("--porta", type=int, default=22)
    ap.add_argument("--usuario", default="ethos")
    ap.add_argument("--chave", required=True)
    ap.add_argument("--nome", default=None)
    ap.add_argument("--saida", default=None, help="diretório para laudo .json e .md")
    args = ap.parse_args()
    chave = Path(args.chave)
    if not chave.exists():
        print(f"erro de uso: chave não encontrada: {chave}", file=sys.stderr)
        return 2
    host = Host(args.nome or args.endereco, args.endereco, args.porta, args.usuario, str(chave))
    _, motivo = ssh_exec(host, "true", timeout=10)
    if motivo:
        print(f"host inalcançável ({args.endereco}:{args.porta}): {motivo}", file=sys.stderr)
        print("verifique endereço, porta, chave e se o SSH está no ar — nada foi coletado", file=sys.stderr)
        return 2
    inv = coletar_host(host)
    inv["ident"] = ssh_exec(host, "hostname")[0] or args.endereco
    inventario = interpretar(inv)
    laudo = laudo_json(host, inventario, inv["ident"])
    if args.saida:
        d = Path(args.saida); d.mkdir(parents=True, exist_ok=True)
        (d / "laudo.json").write_text(json.dumps(laudo, indent=2, ensure_ascii=False), encoding="utf-8")
        (d / "laudo.md").write_text(laudo_md(laudo), encoding="utf-8")
        print(f"laudos em {d}/laudo.json e {d}/laudo.md")
    else:
        print(json.dumps(laudo, indent=2, ensure_ascii=False))
    r = laudo["resumo"]
    print(f"resumo: {r['conforme']} conforme · {r['desvio']} desvio · {r['nao_verificado']} nao_verificado")
    return 1 if (r["desvio"] or r["nao_verificado"]) else 0

if __name__ == "__main__":
    sys.exit(main())
