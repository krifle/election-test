"use strict";

let stopped = false;

function createRng(seed) {
  let state = seed >>> 0;
  return function random() {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function buildCdf(n, p) {
  const q = 1 - p;
  const mode = Math.min(n, Math.floor((n + 1) * p));
  const weights = new Float64Array(n + 1);
  weights[mode] = 1;

  for (let k = mode; k < n; k += 1) {
    weights[k + 1] = weights[k] * ((n - k) / (k + 1)) * (p / q);
  }
  for (let k = mode; k > 0; k -= 1) {
    weights[k - 1] = weights[k] * (k / (n - k + 1)) * (q / p);
  }

  let total = 0;
  for (const value of weights) total += value;

  const cdf = new Float64Array(n + 1);
  let cumulative = 0;
  for (let k = 0; k <= n; k += 1) {
    cumulative += weights[k] / total;
    cdf[k] = cumulative;
  }
  cdf[n] = 1;
  return cdf;
}

function sampleFromCdf(cdf, random) {
  const target = random();
  let low = 0;
  let high = cdf.length - 1;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (target <= cdf[middle]) high = middle;
    else low = middle + 1;
  }
  return low;
}

function runSimulation({ n, p, trials, seed, batchSize }) {
  stopped = false;
  const random = createRng(seed);
  const cdf = buildCdf(n, p);
  let completed = 0;
  let matches = 0;
  const started = performance.now();

  function runBatch() {
    if (stopped) {
      postMessage({ type: "stopped", completed, matches });
      return;
    }

    const currentBatch = Math.min(batchSize, trials - completed);
    for (let index = 0; index < currentBatch; index += 1) {
      const first = sampleFromCdf(cdf, random);
      const second = sampleFromCdf(cdf, random);
      if (first === second) matches += 1;
    }
    completed += currentBatch;

    postMessage({
      type: "progress",
      completed,
      matches,
      estimate: matches / completed,
      elapsedSeconds: (performance.now() - started) / 1000,
    });

    if (completed < trials) {
      setTimeout(runBatch, 0);
    } else {
      postMessage({
        type: "done",
        completed,
        matches,
        estimate: matches / completed,
        elapsedSeconds: (performance.now() - started) / 1000,
      });
    }
  }

  runBatch();
}

self.onmessage = (event) => {
  if (event.data.type === "start") runSimulation(event.data);
  if (event.data.type === "stop") stopped = true;
};
