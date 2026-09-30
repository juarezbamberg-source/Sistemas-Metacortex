'use strict';
/**
 * painel-parque — Ticket 04 (somente leitura).
 *
 * Garantia de leitura em código: toda chamada à API do Kubernetes passa por
 * funções list* (GET). Não existe caminho de escrita neste arquivo nem nos
 * demais; `npm run verificar-leitura` confere por varredura.
 */
const express = require('express');
const path = require('path');
const k8s = require('@kubernetes/client-node');

const kc = new k8s.KubeConfig();
try {
  if (process.env.KUBECONFIG) {
    kc.loadFromFile(process.env.KUBECONFIG.split(':')[0]); // primeiro arquivo
  } else {
    kc.loadFromDefault(); // contexto corrente do kubeconfig da máquina
  }
} catch (e) {
  console.error('kubeconfig não encontrado:', e.message);
  process.exit(2);
}

const coreV1 = kc.makeApiClient(k8s.CoreV1Api);
const appsV1 = kc.makeApiClient(k8s.AppsV1Api);
const discoveryV1 = kc.makeApiClient(k8s.DiscoveryV1Api);

const app = express();
app.use(express.static(path.join(__dirname, 'public')));

const PORTA = process.env.PORTA || 3000;
const INTERVALO_MS = 15000; // ADR-03: intervalo fixo no lado do cliente

function classificarPod(pod) {
  const cs = pod.status?.containerStatuses?.[0];
  const reinicios = cs?.restartCount ?? 0;
  let estado = pod.status?.phase ?? 'Desconhecido';
  let motivo = null;
  const waiting = cs?.state?.waiting;
  const terminated = cs?.lastState?.terminated;
  if (waiting?.reason && waiting.reason !== 'ContainerCreating') {
    estado = waiting.reason;
    motivo = waiting.message ?? null;
  } else if (waiting?.reason === 'ContainerCreating') {
    estado = 'ContainerCreating';
    motivo = waiting.message ?? null;
  }
  if (terminated?.reason === 'OOMKilled') {
    motivo = `última saída: OOMKilled (exit ${terminated.exitCode})`;
  }
  if (estado === 'Running' && cs && !cs.ready) {
    estado = 'Running (não-ready)';
    motivo = motivo ?? 'probe não passando';
  }
  return { nome: pod.metadata.name, estado, reinicios, motivo };
}

function campo(ausenteOuNao, padrao) {
  return ausenteOuNao === undefined || ausenteOuNao === null ? padrao : ausenteOuNao;
}

async function lerNamespace(ns) {
  const [pods, deploys, svcs, slices, eventos] = await Promise.allSettled([
    coreV1.listNamespacedPod(ns),
    appsV1.listNamespacedDeployment(ns),
    coreV1.listNamespacedService(ns),
    discoveryV1.listNamespacedEndpointSlice(ns),
    coreV1.listNamespacedEvent(ns),
  ]);

  const erroDe = (r) => (r.status === 'rejected' ? codificarErro(r.reason) : null);

  const out = { namespace: ns, pods: [], deployments: [], services: [], eventos: [], erros: [] };

  if (pods.status === 'fulfilled') out.pods = pods.value.body.items.map(classificarPod);
  else out.erros.push(erroDe(pods));

  if (deploys.status === 'fulfilled') {
    out.deployments = deploys.value.body.items.map((d) => ({
      nome: d.metadata.name,
      desejadas: campo(d.spec?.replicas, 1),
      prontas: campo(d.status?.readyReplicas, 0), // campo ausente = 0 (regra do enunciado)
    }));
  } else out.erros.push(erroDe(deploys));

  if (svcs.status === 'fulfilled') {
    const slicesOk = slices.status === 'fulfilled' ? slices.value.body.items : [];
    out.services = svcs.value.body.items.map((s) => {
      const doSvc = slicesOk.filter((sl) => sl.metadata.labels?.['kubernetes.io/service-name'] === s.metadata.name);
      const comEndpoint = doSvc.some((sl) => (sl.endpoints ?? []).length > 0); // campo ausente = sem endpoint
      return { nome: s.metadata.name, temEndpoint: comEndpoint, portas: (s.spec?.ports ?? []).map((p) => p.port) };
    });
  } else out.erros.push(erroDe(svcs));

  if (slices.status === 'rejected') out.erros.push(erroDe(slices));

  if (eventos.status === 'fulfilled') {
    out.eventos = eventos.value.body.items
      .map((e) => ({
        tipo: e.type ?? 'Normal',
        motivo: e.reason ?? '',
        objeto: `${e.involvedObject?.kind ?? '?'}/${e.involvedObject?.name ?? '?'}`,
        mensagem: e.message ?? '',
        contagem: e.count ?? 1,
        ultimaOcorrencia: e.lastTimestamp ?? e.firstTimestamp ?? null,
      }))
      .sort((a, b) => {
        if (a.tipo !== b.tipo) return a.tipo === 'Warning' ? -1 : 1;
        return String(b.ultimaOcorrencia ?? '').localeCompare(String(a.ultimaOcorrencia ?? ''));
      })
      .slice(0, 50);
  } else out.erros.push(erroDe(eventos));

  return out;
}

function codificarErro(e) {
  const codigo = e?.statusCode ?? e?.code ?? 0;
  if (codigo === 401) return { codigo: 'credencial-expirada', mensagem: 'Credencial expirada ou inválida (401). Recrie o token/credencial do kubeconfig e reinicie o painel.' };
  if (codigo === 403) return { codigo: 'acesso-negado', mensagem: `Permissão negada (403)${e?.body?.details?.kind ? ' para ' + e.body.details.kind : ''} — este contexto é de leitura restrita; o restante da tela continua.` };
  return { codigo: 'cluster-indisponivel', mensagem: `Cluster não respondeu (${codigo || 'sem resposta'}). Verifique o túnel/VPN e o contexto corrente do kubeconfig.` };
}

app.get('/api/namespaces', async (_req, res) => {
  try {
    const r = await coreV1.listNamespace();
    res.json({ namespaces: r.body.items.map((n) => n.metadata.name).filter((n) => !n.startsWith('kube-')) });
  } catch (e) {
    res.status(502).json({ erro: codificarErro(e) });
  }
});

app.get('/api/overview', async (req, res) => {
  const ns = String(req.query.namespace ?? 'default');
  try {
    res.json(await lerNamespace(ns));
  } catch (e) {
    res.status(502).json({ erro: codificarErro(e) });
  }
});

app.listen(PORTA, () => console.log(`painel-parque em http://localhost:${PORTA} (somente leitura)`));
