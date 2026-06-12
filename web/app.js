"use strict";

const elements = {
  nInput: document.querySelector("#nInput"),
  pInput: document.querySelector("#pInput"),
  trialsInput: document.querySelector("#trialsInput"),
  seedInput: document.querySelector("#seedInput"),
  startButton: document.querySelector("#startButton"),
  stopButton: document.querySelector("#stopButton"),
  loadBillionButton: document.querySelector("#loadBillionButton"),
  resultFileInput: document.querySelector("#resultFileInput"),
  exactProbability: document.querySelector("#exactProbability"),
  exactPercent: document.querySelector("#exactPercent"),
  approxProbability: document.querySelector("#approxProbability"),
  approxError: document.querySelector("#approxError"),
  meanValue: document.querySelector("#meanValue"),
  sdValue: document.querySelector("#sdValue"),
  heroProbability: document.querySelector("#heroProbability"),
  heroMeter: document.querySelector("#heroMeter"),
  simulationStatus: document.querySelector("#simulationStatus"),
  progressBar: document.querySelector("#progressBar"),
  liveEstimate: document.querySelector("#liveEstimate"),
  liveDifference: document.querySelector("#liveDifference"),
  districtsInput: document.querySelector("#districtsInput"),
  similarRateInput: document.querySelector("#similarRateInput"),
  allPairs: document.querySelector("#allPairs"),
  eligiblePairs: document.querySelector("#eligiblePairs"),
  expectedMatches: document.querySelector("#expectedMatches"),
  atLeastOne: document.querySelector("#atLeastOne"),
  pmfCanvas: document.querySelector("#pmfCanvas"),
  convergenceCanvas: document.querySelector("#convergenceCanvas"),
  heatmapCanvas: document.querySelector("#heatmapCanvas"),
};

const state = {
  n: 4470,
  p: 3030 / 4470,
  pmf: [],
  exact: 0,
  approximation: 0,
  checkpoints: [],
  worker: null,
  isRunning: false,
};

function formatNumber(value, digits = 3) {
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: digits,
  }).format(value);
}

function formatProbability(value, digits = 9) {
  return value.toFixed(digits);
}

function buildPmf(n, p) {
  if (p <= 0) return [1, ...new Array(n).fill(0)];
  if (p >= 1) return [...new Array(n).fill(0), 1];

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
  return Array.from(weights, (value) => value / total);
}

function exactCollision(pmf) {
  let total = 0;
  for (const probability of pmf) total += probability * probability;
  return total;
}

function localClt(n, p) {
  return 1 / Math.sqrt(4 * Math.PI * n * p * (1 - p));
}

function resizeCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, rect.width);
  const height = Math.max(240, rect.height);
  if (canvas.width !== Math.round(width * ratio)) {
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
  }
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { context, width, height };
}

function drawAxes(context, width, height, color) {
  context.strokeStyle = color;
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(52, 18);
  context.lineTo(52, height - 38);
  context.lineTo(width - 14, height - 38);
  context.stroke();
}

function drawPmf() {
  const { context, width, height } = resizeCanvas(elements.pmfCanvas);
  context.clearRect(0, 0, width, height);
  drawAxes(context, width, height, "rgba(20,34,31,.2)");

  const mean = state.n * state.p;
  const sd = Math.sqrt(state.n * state.p * (1 - state.p));
  const start = Math.max(0, Math.floor(mean - 4.2 * sd));
  const end = Math.min(state.n, Math.ceil(mean + 4.2 * sd));
  const values = state.pmf.slice(start, end + 1);
  const maxPmf = Math.max(...values);
  const maxCollision = maxPmf * maxPmf;
  const chartWidth = width - 72;
  const chartHeight = height - 64;
  const xAt = (index) => 52 + (index / Math.max(1, values.length - 1)) * chartWidth;

  const drawLine = (color, getter, maxValue, lineWidth) => {
    context.strokeStyle = color;
    context.lineWidth = lineWidth;
    context.beginPath();
    values.forEach((probability, index) => {
      const x = xAt(index);
      const normalized = getter(probability) / maxValue;
      const y = height - 38 - normalized * chartHeight;
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
  };

  drawLine("#1e4bff", (value) => value, maxPmf, 2.4);
  drawLine("#ff6b35", (value) => value * value, maxCollision, 2);

  context.fillStyle = "#65706c";
  context.font = "12px system-ui";
  context.textAlign = "center";
  [start, Math.round(mean), end].forEach((value) => {
    const x = 52 + ((value - start) / Math.max(1, end - start)) * chartWidth;
    context.fillText(formatNumber(value, 0), x, height - 15);
  });
  context.save();
  context.translate(16, height / 2);
  context.rotate(-Math.PI / 2);
  context.fillText("각 계열의 최대값 대비", 0, 0);
  context.restore();
}

function drawEmptyConvergence(context, width, height) {
  drawAxes(context, width, height, "rgba(255,255,255,.15)");
  context.fillStyle = "rgba(255,255,255,.45)";
  context.font = "14px system-ui";
  context.textAlign = "center";
  context.fillText("시뮬레이션을 시작하면 수렴 경로가 표시됩니다.", width / 2, height / 2);
}

function drawConvergence() {
  const { context, width, height } = resizeCanvas(elements.convergenceCanvas);
  context.clearRect(0, 0, width, height);

  if (!state.checkpoints.length) {
    drawEmptyConvergence(context, width, height);
    return;
  }

  drawAxes(context, width, height, "rgba(255,255,255,.15)");
  const points = state.checkpoints.filter(
    (point) => Number.isFinite(point.trials) && Number.isFinite(point.estimate),
  );
  const maxTrials = Math.max(...points.map((point) => point.trials));
  const minTrials = Math.max(1, Math.min(...points.map((point) => point.trials)));
  const estimates = points.map((point) => point.estimate);
  const spread = Math.max(
    0.00005,
    ...estimates.map((value) => Math.abs(value - state.exact)),
  );
  const minY = Math.max(0, state.exact - spread * 1.25);
  const maxY = state.exact + spread * 1.25;
  const chartWidth = width - 72;
  const chartHeight = height - 64;
  const minLog = Math.log10(minTrials);
  const maxLog = Math.log10(Math.max(minTrials * 10, maxTrials));
  const xAt = (trials) =>
    52 + ((Math.log10(trials) - minLog) / (maxLog - minLog)) * chartWidth;
  const yAt = (value) =>
    height - 38 - ((value - minY) / Math.max(1e-12, maxY - minY)) * chartHeight;

  context.strokeStyle = "#ff6b35";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(52, yAt(state.exact));
  context.lineTo(width - 14, yAt(state.exact));
  context.stroke();

  context.strokeStyle = "#61e5bd";
  context.lineWidth = 2.2;
  context.beginPath();
  points.forEach((point, index) => {
    const x = xAt(point.trials);
    const y = yAt(point.estimate);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.stroke();

  const last = points[points.length - 1];
  context.fillStyle = "#61e5bd";
  context.beginPath();
  context.arc(xAt(last.trials), yAt(last.estimate), 4, 0, Math.PI * 2);
  context.fill();

  context.fillStyle = "rgba(255,255,255,.5)";
  context.font = "12px system-ui";
  context.textAlign = "left";
  context.fillText(formatNumber(minTrials, 0), 52, height - 15);
  context.textAlign = "right";
  context.fillText(formatNumber(maxTrials, 0), width - 14, height - 15);
  context.textAlign = "right";
  context.fillText((maxY * 100).toFixed(3) + "%", 47, 23);
  context.fillText((minY * 100).toFixed(3) + "%", 47, height - 39);
}

function heatColor(probability, minLog, maxLog) {
  const value = Math.log10(probability);
  const ratio = Math.max(0, Math.min(1, (value - minLog) / (maxLog - minLog)));
  const start = [30, 75, 255];
  const end = [255, 107, 53];
  const rgb = start.map((channel, index) =>
    Math.round(channel + (end[index] - channel) * ratio),
  );
  return `rgb(${rgb.join(",")})`;
}

function drawHeatmap() {
  const { context, width, height } = resizeCanvas(elements.heatmapCanvas);
  context.clearRect(0, 0, width, height);
  const nValues = [250, 500, 1000, 2000, 4470, 8000];
  const pValues = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95];
  const values = pValues.map((p) =>
    nValues.map((n) => exactCollision(buildPmf(n, p))),
  );
  const flat = values.flat();
  const minLog = Math.log10(Math.min(...flat));
  const maxLog = Math.log10(Math.max(...flat));
  const left = 62;
  const top = 26;
  const cellWidth = (width - left - 18) / nValues.length;
  const cellHeight = (height - top - 42) / pValues.length;

  values.forEach((row, rowIndex) => {
    row.forEach((probability, columnIndex) => {
      const x = left + columnIndex * cellWidth;
      const y = top + rowIndex * cellHeight;
      context.fillStyle = heatColor(probability, minLog, maxLog);
      context.fillRect(x + 2, y + 2, cellWidth - 4, cellHeight - 4);
      context.fillStyle = "white";
      context.font = `${cellWidth < 90 ? 10 : 12}px system-ui`;
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillText(
        (probability * 100).toFixed(probability < 0.01 ? 2 : 1) + "%",
        x + cellWidth / 2,
        y + cellHeight / 2,
      );
    });
  });

  context.fillStyle = "#65706c";
  context.font = "12px system-ui";
  context.textBaseline = "alphabetic";
  context.textAlign = "center";
  nValues.forEach((n, index) => {
    context.fillText(
      formatNumber(n, 0),
      left + index * cellWidth + cellWidth / 2,
      height - 12,
    );
  });
  context.textAlign = "right";
  context.textBaseline = "middle";
  pValues.forEach((p, index) => {
    context.fillText(
      `p=${p}`,
      left - 8,
      top + index * cellHeight + cellHeight / 2,
    );
  });
}

function updateMultipleComparison() {
  const districts = Math.max(2, Number(elements.districtsInput.value));
  const similarRate = Math.max(
    0,
    Math.min(1, Number(elements.similarRateInput.value) / 100),
  );
  const allPairs = (districts * (districts - 1)) / 2;
  const eligiblePairs = allPairs * similarRate;
  const expected = eligiblePairs * state.exact;
  const poissonAtLeastOne = 1 - Math.exp(-expected);

  elements.allPairs.textContent = formatNumber(allPairs, 0);
  elements.eligiblePairs.textContent = formatNumber(eligiblePairs, 2);
  elements.expectedMatches.textContent = formatNumber(expected, 3);
  elements.atLeastOne.textContent = (poissonAtLeastOne * 100).toFixed(1) + "%";
}

function updateModel() {
  const n = Math.round(Number(elements.nInput.value));
  const p = Number(elements.pInput.value);
  if (!Number.isFinite(n) || n < 1 || n > 20000) return;
  if (!Number.isFinite(p) || p <= 0 || p >= 1) return;

  state.n = n;
  state.p = p;
  state.pmf = buildPmf(n, p);
  state.exact = exactCollision(state.pmf);
  state.approximation = localClt(n, p);
  state.checkpoints = [];

  const percent = state.exact * 100;
  const relativeError =
    ((state.approximation - state.exact) / state.exact) * 100;
  const mean = n * p;
  const sd = Math.sqrt(n * p * (1 - p));

  elements.exactProbability.textContent = formatProbability(state.exact);
  elements.exactPercent.textContent = percent.toFixed(6) + "%";
  elements.approxProbability.textContent = formatProbability(state.approximation);
  elements.approxError.textContent =
    `정확값과 ${relativeError >= 0 ? "+" : ""}${relativeError.toFixed(4)}%`;
  elements.meanValue.textContent = formatNumber(mean, 2);
  elements.sdValue.textContent = `표준편차 ${formatNumber(sd, 2)}표`;
  elements.heroProbability.textContent = percent.toFixed(6) + "%";
  elements.heroMeter.style.width = `${Math.min(100, percent * 10)}%`;
  elements.liveEstimate.textContent = "-";
  elements.liveDifference.textContent = "정확값과 비교 대기 중";
  elements.simulationStatus.textContent = "모형 변경됨 · 실행 전";
  elements.progressBar.style.width = "0%";

  drawPmf();
  drawConvergence();
  updateMultipleComparison();
}

function setSimulationRunning(running) {
  state.isRunning = running;
  elements.startButton.disabled = running;
  elements.stopButton.disabled = !running;
  elements.loadBillionButton.disabled = running;
  elements.resultFileInput.disabled = running;
  elements.nInput.disabled = running;
  elements.pInput.disabled = running;
  document.querySelectorAll(".preset").forEach((button) => {
    button.disabled = running;
  });
}

function addCheckpoint(message) {
  state.checkpoints.push({
    trials: message.completed,
    estimate: message.estimate,
  });
  const trials = Number(elements.trialsInput.value);
  const progress = (message.completed / trials) * 100;
  const difference = message.estimate - state.exact;

  elements.progressBar.style.width = `${Math.min(100, progress)}%`;
  elements.liveEstimate.textContent = (message.estimate * 100).toFixed(6) + "%";
  elements.liveDifference.textContent =
    `정확값 대비 ${difference >= 0 ? "+" : ""}${(difference * 100).toFixed(6)}%p`;
  elements.simulationStatus.textContent =
    `${formatNumber(message.completed, 0)}회 · 일치 ${formatNumber(message.matches, 0)}회 · ` +
    `${message.elapsedSeconds.toFixed(1)}초`;
  drawConvergence();
}

function startSimulation() {
  if (state.worker) state.worker.terminate();
  state.checkpoints = [];
  drawConvergence();
  setSimulationRunning(true);
  elements.progressBar.style.width = "0%";
  elements.simulationStatus.textContent = "분포 준비 중";

  const trials = Math.max(1000, Number(elements.trialsInput.value));
  const batchSize = Math.min(100000, Math.max(5000, Math.floor(trials / 100)));
  state.worker = new Worker("./simulation-worker.js");
  state.worker.onmessage = (event) => {
    const message = event.data;
    if (message.type === "progress" || message.type === "done") {
      addCheckpoint(message);
    }
    if (message.type === "done") {
      setSimulationRunning(false);
      elements.simulationStatus.textContent += " · 완료";
      state.worker.terminate();
      state.worker = null;
    }
    if (message.type === "stopped") {
      setSimulationRunning(false);
      elements.simulationStatus.textContent += " · 중지됨";
      state.worker.terminate();
      state.worker = null;
    }
  };
  state.worker.onerror = () => {
    setSimulationRunning(false);
    elements.simulationStatus.textContent = "시뮬레이션 오류";
    state.worker.terminate();
    state.worker = null;
  };
  state.worker.postMessage({
    type: "start",
    n: state.n,
    p: state.p,
    trials,
    seed: Number(elements.seedInput.value) || 20260603,
    batchSize,
  });
}

function stopSimulation() {
  if (state.worker) state.worker.postMessage({ type: "stop" });
}

function applyResultData(data, sourceLabel) {
  if (!data.model || !Array.isArray(data.checkpoints)) {
    throw new Error("지원하지 않는 JSON 형식입니다.");
  }

  elements.nInput.value = data.model.n;
  elements.pInput.value = data.model.p;
  updateModel();
  state.checkpoints = data.checkpoints.map((checkpoint) => ({
    trials: checkpoint.trials,
    estimate: checkpoint.estimate,
  }));
  elements.trialsInput.value = data.model.trials;
  elements.progressBar.style.width = "100%";
  elements.liveEstimate.textContent = (data.estimate * 100).toFixed(6) + "%";
  elements.liveDifference.textContent =
    `정확값 대비 ${data.estimate - state.exact >= 0 ? "+" : ""}` +
    `${((data.estimate - state.exact) * 100).toFixed(6)}%p`;
  elements.simulationStatus.textContent =
    `${sourceLabel} · ${formatNumber(data.model.trials, 0)}회 · ` +
    `${Number(data.elapsed_seconds).toFixed(1)}초`;
  drawConvergence();
}

async function loadResultFile(file) {
  const data = JSON.parse(await file.text());
  applyResultData(data, "Python 결과");
}

async function loadBundledBillionResult() {
  if (state.isRunning) return;
  elements.loadBillionButton.disabled = true;
  try {
    const response = await fetch("./data/one-billion.json");
    if (!response.ok) throw new Error("저장된 결과를 읽지 못했습니다.");
    applyResultData(await response.json(), "저장된 10억 회 결과");
  } catch (error) {
    elements.simulationStatus.textContent = error.message;
  } finally {
    elements.loadBillionButton.disabled = state.isRunning;
  }
}

document.querySelectorAll(".preset").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".preset").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
    elements.nInput.value = button.dataset.n;
    elements.pInput.value = button.dataset.p;
    updateModel();
  });
});

elements.nInput.addEventListener("change", updateModel);
elements.pInput.addEventListener("change", updateModel);
elements.districtsInput.addEventListener("input", updateMultipleComparison);
elements.similarRateInput.addEventListener("input", updateMultipleComparison);
elements.startButton.addEventListener("click", startSimulation);
elements.stopButton.addEventListener("click", stopSimulation);
elements.loadBillionButton.addEventListener("click", loadBundledBillionResult);
elements.resultFileInput.addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  try {
    await loadResultFile(file);
  } catch (error) {
    elements.simulationStatus.textContent = error.message;
  }
});

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    drawPmf();
    drawConvergence();
    drawHeatmap();
  }, 100);
});

updateModel();
drawHeatmap();
loadBundledBillionResult();
