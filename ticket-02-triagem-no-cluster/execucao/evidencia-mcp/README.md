# Evidência das chamadas ao MCP (2026-11-18, ao vivo)

Servidor: `mcp-server-kubernetes` **v4.2.3** via `npx`, com
`ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS=true` e `KUBECONFIG` apontando para o token
do ServiceAccount `triagem-ro` (RBAC de leitura — `config/rbac-leitura.yaml`).

Prova em 4 partes (arquivo `chamadas-mcp-2026-11-18.txt`, saída integral):

1. **initialize** → serverInfo `kubernetes v4.2.3`.
2. **tools/list** → 17 ferramentas. **Confirmação do alerta da banca**: mesmo em modo
   não destrutivo, `kubectl_apply`, `kubectl_create`, `kubectl_patch`, `kubectl_scale`,
   `install_helm_chart` e `port_forward` continuam expostas — por isso o RBAC.
3. **kubectl_describe** (leitura real) → pod `nyx-api-78587b9b89-8t5hh` do nyx-prod:
   Status Running, Restart Count 364, Last State **OOMKilled** — o Chamado 1 lido via MCP.
4. **kubectl_scale** (escrita) → **negada pelo apiserver**: `Forbidden: User
   "system:serviceaccount:default:triagem-ro" cannot patch deployments/scale` —
   a garantia de só leitura é do RBAC, não do cliente.

Conclusão: o modo não destrutivo do servidor é **necessário mas insuficiente**;
a garantia auditável é a dupla `ALLOW_ONLY_NON_DESTRUCTIVE_TOOLS=true` + ClusterRole
`triagem-somente-leitura` (get/list/watch) com token de SA dedicado.
