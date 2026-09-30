# Achado de runtime (2026-09-30, teste real no kind-metacortex)

Ao aplicar os manifests no cluster com a imagem `fabricioveronez/fake-shop:v26`:

- **Sintoma**: pod em `CrashLoopBackOff`; log do gunicorn: `ValueError: one of env
  PROMETHEUS_MULTIPROC_DIR or env prometheus_multiproc_dir must be set and be a directory`.
- **Causa**: o manifest aponta `PROMETHEUS_MULTIPROC_DIR=/tmp/metrics`, mas o `emptyDir`
  montado em `/tmp` não cria o subdiretório — e a imagem v26 exige que o diretório exista.
- **Correção aplicada no lab**: `PROMETHEUS_MULTIPROC_DIR=/tmp` (o ponto de montagem em si).
- **Lição para a skill (modo escrita)**: quando um env aponta para um caminho dentro de um
  volume, o valor deve ser o ponto de montagem existente (ou o app precisa criar o dir no
  start). Isso é regra candidata à instrução da skill: "caminhos de env × volumeMounts
  precisam existir — emptyDir não cria subdiretórios".
