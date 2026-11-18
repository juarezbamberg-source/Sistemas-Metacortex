# Evidência — metavm (T03), execuções de 2026-11-18

Todos os arquivos abaixo vêm de execuções reais do `metavm.py` deste repositório, no host
alpine do parque dropbear do laboratório (`127.0.0.11:2221`) e em um endereço inexistente.

| Arquivo | O que prova |
|---|---|
| `exec1/laudo.json` + `exec1/laudo.md` + `exec1-console.txt` | execução com desvios: **3 conforme · 3 desvio · 5 nao_verificado**, exit **1** |
| `exec2/laudo.json` + `exec2/laudo.md` + `exec2-console.txt` | 2ª execução seguida, mesmo host: laudo **idêntico** ao exec1 exceto `coletado_em` (idempotência) |
| `host-inalcancavel.txt` | endereço inexistente: mensagem clara, nada coletado, exit **2** |
| `laudo.json` (raiz, de 2026-10-09) | execução anterior à correção da vaia 2 — mantida só como histórico |

## Como reconferir a idempotência

```bash
python3 -c "
import json
a=json.load(open('exec1/laudo.json')); b=json.load(open('exec2/laudo.json'))
a['host']['coletado_em']=b['host']['coletado_em']='<ts>'
print(json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True))"   # True
```

## O que a vaia 2 cobrava e como está respondido

- **Falsos conformes**: `swap.habilitado` e `portas_em_escuta.publicas_permitidas` aparecem como
  `nao_verificado` com motivo explícito quando a coleta volta vazia — nunca `conforme`.
- **`por_severidade` ambíguo**: conta **apenas desvios** (`critico: 1, alto: 2, medio: 0`), como no
  exemplo do enunciado.
- **Campo `encontrado`**: traz o valor coletado ou `null`; nunca o texto do veredito.
- **Evidência versionada**: exit codes nos consoles, host morto, 2ª execução para idempotência.

## Limitação declarada (honesta)

O parque é de dropbear estático sobre o kernel do próprio sandbox — não são VMs de verdade.
Isso não muda os vereditos de software (distro, kernel, portas, chaves, swap), mas explica os
`nao_verificado` de `systemctl`, `timedatectl` e `ss`: o ambiente mínimo não tem esses serviços.
O ideal, registrado no relatório, é rodar a mesma CLI contra um host Linux real do parque.
