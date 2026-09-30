# Inventário de VMs — metavm

**3 hosts · 7 conforme(is) · 0 desvio(s) · 6 não verificado(s)**

## web-01

| check | veredito | severidade | esperado | observado | motivo |
|---|---|---|---|---|---|
| ✅ sysctl-ip-forward | conforme | warning |  | 1 |  |
| ❔ banner-metacortex | nao_verificado | info |  |  | comando falhou (rc=1): cat: can't open '/etc/issue.net': No such file or directory |
| ✅ home-perms | conforme | critical |  | existe |  |
| ❔ usuario-app | nao_verificado | warning |  |  | comando falhou (rc=1): id: unknown user www-data |

## web-02

| check | veredito | severidade | esperado | observado | motivo |
|---|---|---|---|---|---|
| ✅ sysctl-ip-forward | conforme | warning |  | 1 |  |
| ❔ banner-metacortex | nao_verificado | info |  |  | comando falhou (rc=1): cat: can't open '/etc/issue.net': No such file or directory |
| ✅ home-perms | conforme | critical |  | existe |  |
| ❔ usuario-app | nao_verificado | warning |  |  | comando falhou (rc=1): id: unknown user www-data |

## db-01

| check | veredito | severidade | esperado | observado | motivo |
|---|---|---|---|---|---|
| ✅ sysctl-ip-forward | conforme | warning |  | 1 |  |
| ❔ banner-metacortex | nao_verificado | info |  |  | comando falhou (rc=1): cat: can't open '/etc/issue.net': No such file or directory |
| ✅ home-perms | conforme | critical |  | existe |  |
| ❔ postgres-usuario | nao_verificado | critical |  |  | comando falhou (rc=1): id: unknown user postgres |
| ✅ sysctl-swappiness | conforme | warning |  | 200 |  |
