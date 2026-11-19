#!/usr/bin/env python3
"""Audita o NÓ do kind (Debian 12 real) com as funções do metavm.

Coleta dentro de um pod privilegiado com nsenter no PID 1 do nó, então o que
o metavm vê é o HOST (Debian/kernel/swap/portas reais), não o container.
"""
import base64
import importlib.util
import json
import os
import subprocess
import sys

METAVM = '/home/ethos/.assistant/workspace/Sistemas-Metacortex/ticket-03-inventario-de-vm/metavm.py'
KUBECONFIG = '/home/ethos/.assistant/workspace/work/cluster-remoto/kubeconfig.yaml'
SAIDA = '/tmp/aud/linux-real'

spec = importlib.util.spec_from_file_location('metavm', METAVM)
mv = importlib.util.module_from_spec(spec)
sys.modules['metavm'] = mv
spec.loader.exec_module(mv)

# todos os comandos numa chamada só (paralelo/fragmentado perde saída pelo túnel)
COLETA = r'''
echo "==@ident"
hostname
echo "==@so"
grep -E "^(ID|VERSION_ID)=" /etc/os-release
echo "==@kernel"
uname -r
echo "==@servicos"
for s in ssh containerd node_exporter chrony; do
  e=$(systemctl is-active "$s.service" 2>/dev/null)
  [ -z "$e" ] && e=$(systemctl is-active "$s" 2>/dev/null)
  [ -z "$e" ] && e=inativo
  echo "$s:$e"
done
for p in telnet.socket rpcbind.socket; do
  e=$(systemctl is-active "$p" 2>/dev/null)
  [ -z "$e" ] && e=inativo
  echo "proibido-$p:$e"
done
echo "==@swap"
swapon --show 2>/dev/null | tail -n +2 | head -1
echo "==@portas"
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null
echo "==@chaves"
cat /root/.ssh/authorized_keys 2>/dev/null || echo sem-arquivo
echo "==@sshd"
sshd -T 2>/dev/null | grep -i permitrootlogin || grep -ri permitrootlogin /etc/ssh/sshd_config 2>/dev/null | tail -1
echo "==@ntp"
timedatectl show 2>/dev/null | grep -E "NTPSynchronized|NTPService"
echo "==@fim"
'''

cmd = ['kubectl', 'exec', 'node-shell', '--', 'nsenter', '-t', '1', '-m', '-u', '-i', '-n', '-p',
       '--', 'bash', '-c', COLETA]
env = dict(os.environ, KUBECONFIG=KUBECONFIG)
r = subprocess.run(cmd, capture_output=True, text=True, timeout=240, env=env)
bruto = r.stdout
if not bruto.strip():
    print("FALHA na coleta:", r.stderr[:400])
    sys.exit(1)

def bloco(nome):
    chave = f"==@{nome}"
    i = bruto.find(chave)
    if i < 0:
        return ''
    i = bruto.find('\n', i) + 1
    j = bruto.find('==@', i)
    return bruto[i:j if j > 0 else len(bruto)].strip()

inv_bruto = {
    'ident':    bloco('ident'),
    'so':       bloco('so'),
    'kernel':   bloco('kernel'),
    'servicos': bloco('servicos'),
    'swap':     bloco('swap'),
    'portas':   bloco('portas'),
    'chaves':   bloco('chaves'),
    'sshd':     bloco('sshd'),
    'ntp':      bloco('ntp'),
}

inventario = mv.interpretar(inv_bruto)
conf = mv.conferir(inventario)
res = mv.resumo(conf)

laudo = {
    'host': {
        'endereco': 'metacortex-control-plane (node do kind, via nsenter no PID 1)',
        'hostname': inv_bruto['ident'],
        'coletado_em': '2026-11-19',
    },
    'inventario': inventario,
    'conformidade': conf,
    'resumo': res,
}

os.makedirs(SAIDA, exist_ok=True)
json.dump(laudo, open(f'{SAIDA}/laudo.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
open(f'{SAIDA}/laudo.md', 'w', encoding='utf-8').write(mv.laudo_md(laudo))

print("SO         :", inventario['so'])
print("kernel     :", inventario['kernel'])
print("swap       :", inventario['swap'])
print("portas     :", len(inventario['portas_em_escuta']),
      [p['porta'] for p in inventario['portas_em_escuta']][:10])
print("servicos   :", [(s['nome'], s['estado']) for s in inventario['servicos']])
print()
for c in conf:
    motivo = f"  ({c['motivo']})" if c.get('motivo') else ''
    print(f"  {c['veredito']:16s} {c['regra']:40s} {str(c['encontrado'])[:38]}{motivo}")
print()
print("RESUMO:", res)
