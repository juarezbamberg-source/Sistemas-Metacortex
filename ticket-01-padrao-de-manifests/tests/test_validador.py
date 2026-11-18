"""Teste negativo do validador do padrão da casa (gate).

O manifesto barrado DEVE reprovar (exit 1) — e, desde a correção de
ambiente-por-namespace, DEVE incluir as regras de produção 2.3/2.4.
"""
import subprocess, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "skill" / "scripts" / "validar_padrao.py"
BARRADO = RAIZ / "execucao" / "modo-conferencia" / "manifesto-barrado.yaml"


def rodar(alvo):
    r = subprocess.run([sys.executable, str(SCRIPT), str(alvo)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def test_manifesto_barrado_falha():
    rc, out = rodar(BARRADO)
    assert rc == 1, f"esperado exit 1, veio {rc}"
    assert "FALHA" in out
    assert "3.3" in out, "segredo em texto puro (regra 3.3)"
    assert "1.4" in out, "seletor cruzado (regra 1.4)"


def test_regras_de_pro_pelo_namespace():
    """Ambiente lido do NAMESPACE (nyx-prod) — não da pasta."""
    rc, out = rodar(BARRADO)
    assert "2.3" in out, "réplicas mínimas em prod (regra 2.3) deve acusar"
    assert "2.4" in out, "RollingUpdate em prod (regra 2.4) deve acusar"


def test_manifestos_gerados_aprovados():
    for proj in ("kube-news", "fake-shop"):
        rc, out = rodar(RAIZ / "execucao" / "modo-escrita" / proj)
        assert rc == 0, f"{proj} deveria estar aprovado: {out[-200:]}"


if __name__ == "__main__":
    test_manifesto_barrado_falha()
    test_regras_de_pro_pelo_namespace()
    test_manifestos_gerados_aprovados()
    print("TESTES OK")
