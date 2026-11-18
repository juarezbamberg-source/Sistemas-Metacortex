#!/bin/bash
# Captura REAL dos cenários de falha do painel-parque (T04).
#
# Uso: ./capturar-cenarios.sh <dir-com-kubeconfigs>
#   Espera, em <dir>: kc-bom.yaml, kc-inacessivel.yaml, kc-expirado.yaml, kc-negado.yaml
#   (não versionados — contêm tokens). Saída: painel-parque/evidencia/*.json
#
# Cada cenário sobe o painel numa porta diferente com o seu KUBECONFIG, consulta
# /api/overview?namespace=nyx-prod, grava a resposta crua e derruba o processo.
set -u
cd "$(dirname "$0")"
KCDIR="${1:?informe o diretório com os kubeconfigs}"
OUT=../painel-parque/evidencia
APP=../painel-parque
mkdir -p "$OUT"

capturar() {   # $1=nome  $2=kubeconfig  $3=porta
  local nome=$1 kc=$2 porta=$3 pid
  KUBECONFIG="$kc" PORTA="$porta" node "$APP/src/servidor.js" > "/tmp/painel-$nome.log" 2>&1 &
  pid=$!
  for _ in $(seq 1 30); do
    curl -s -m 2 -o /dev/null "http://localhost:$porta/api/namespaces" && break
    sleep 0.5
  done
  curl -s -m 120 "http://localhost:$porta/api/overview?namespace=nyx-prod" \
    -o "$OUT/$nome.raw.txt" -w "  HTTP=%{http_code} bytes=%{size_download}\n"
  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
  python3 - "$OUT/$nome.raw.txt" "$OUT/$nome.json" <<'PY'
import json, sys, os
bruto, destino = sys.argv[1], sys.argv[2]
txt = open(bruto, encoding="utf-8").read().split("\nHTTP=")[0].strip()
d = json.loads(txt)
json.dump(d, open(destino, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
os.remove(bruto)
e = d.get("erro") or (d.get("erros") or [{}])[0]
print(f"  {os.path.basename(destino)}: {e.get('codigo','ok')} · pods={len(d.get('pods',[]))} deploys={len(d.get('deployments',[]))}")
PY
}

capturar cenario1-inacessivel    "$KCDIR/kc-inacessivel.yaml" 3321
capturar cenario2-token-expirado "$KCDIR/kc-expirado.yaml"    3322
capturar cenario3-acesso-negado  "$KCDIR/kc-negado.yaml"      3323
capturar overview-nyx-prod       "$KCDIR/kc-bom.yaml"         3324
