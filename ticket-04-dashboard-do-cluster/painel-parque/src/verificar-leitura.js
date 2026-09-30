#!/usr/bin/env node
'use strict';
/** Verificação da garantia de leitura: varre o código por chamadas de escrita. */
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '..', 'src');
const padrao = /\.(create|patch|delete|apply|replace|scale|exec)[A-Za-z]*\s*\(/;

let violacoes = 0;
for (const arq of fs.readdirSync(DIR)) {
  if (!arq.endsWith('.js')) continue;
  const linhas = fs.readFileSync(path.join(DIR, arq), 'utf8').split('\n');
  linhas.forEach((l, i) => {
    if (padrao.test(l) && !/verificar-leitura/.test(arq)) {
      console.log(`VIOLAÇÃO ${arq}:${i + 1}: ${l.trim()}`);
      violacoes++;
    }
  });
}
if (violacoes) { console.log(`${violacoes} violação(ões) — o painel deve ser SOMENTE LEITURA`); process.exit(1); }
console.log('OK: nenhuma chamada de escrita no código (garantia de leitura)');
