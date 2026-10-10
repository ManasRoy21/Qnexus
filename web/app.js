'use strict';

const $ = id => document.getElementById(id);
const percent = value => value == null ? 'No sample' : `${(value * 100).toFixed(2)}%`;
const state = { id: null, material: null, signature: null, sweep: null, verification: null, attack: null, bound: null };
const fields = ['pulse_count', 'distance_km', 'fiber_loss_db_per_km', 'detector_efficiency', 'baseline_qber', 'test_fraction', 'authentication_threshold', 'verification_threshold', 'seed'];
let busy = false;
let activePanel = 'protocol';

function config() {
  return Object.fromEntries(fields.map(name => [name, Number($(name).value)]));
}

function status(message, error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}

async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
  });
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
  return body;
}

function needMaterial() {
  if (!state.id) throw new Error('Generate signature material in step 02 first.');
}

function canOpen(panel) {
  return ['protocol', 'material', 'circuit'].includes(panel) || Boolean(state.id);
}

function updateNavigation() {
  document.querySelectorAll('button').forEach(button => {
    const destination = button.dataset.panel || button.dataset.go;
    button.disabled = busy || Boolean(destination && !canOpen(destination));
    if (destination) button.title = canOpen(destination) ? '' : 'Generate signature material first';
  });
  document.querySelectorAll('.tab').forEach(button => {
    const active = button.dataset.panel === activePanel;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
}

function navigate(panel) {
  if (!canOpen(panel)) {
    status('Generate signature material in step 02 first.', true);
    return;
  }
  activePanel = panel;
  document.querySelectorAll('.panel').forEach(section => { section.hidden = section.id !== panel; });
  updateNavigation();
  if (panel === 'report') renderReport();
}

async function action(button, work) {
  const oldText = button.textContent;
  busy = true;
  updateNavigation();
  button.textContent = 'RUNNING…';
  status('Executing local Qiskit experiment…');
  try {
    await work();
    status('Experiment complete. Results displayed below.');
  } catch (error) {
    status(error.message, true);
  } finally {
    busy = false;
    button.textContent = oldText;
    updateNavigation();
  }
}

function show(id, markup) {
  $(id).innerHTML = markup;
  $(id).hidden = false;
}

function metric(label, value, style = '') {
  return `<div class="metric"><strong class="${style}">${value}</strong><span>${label}</span></div>`;
}

function resultSummary(result) {
  const decision = result.insufficient_data ? 'No data' : result.abort ? 'ABORT' : 'PASS';
  return `<div class="metrics">
    ${metric('Bob test QBER', percent(result.bob.qber))}
    ${metric('Charlie test QBER', percent(result.charlie.qber))}
    ${metric('Channel decision', decision, result.insufficient_data || result.abort ? 'bad' : 'good')}
    ${metric('Bob usable bits', result.bob.untested_bits)}
    ${metric('Charlie usable bits', result.charlie.untested_bits)}
    ${metric('Test samples', result.tested_bits)}
  </div><p>${result.bob.executed_circuits + result.charlie.executed_circuits} circuit variants executed on ${result.backend}. Detection and basis selection reduce attempted pulses to usable samples.</p>`;
}

function updateSliders() {
  $('pulse-label').textContent = Number($('pulse_count').value).toLocaleString();
  $('distance-label').textContent = `${$('distance_km').value} km`;
  $('pipeline-pulses').textContent = `${Number($('pulse_count').value).toLocaleString()} pulses`;
  $('pipeline-distance').textContent = `${$('distance_km').value} km`;
  $('intensity-label').textContent = `${Math.round(Number($('intensity').value) * 100)}%`;
}

function renderReport() {
  if (!state.material) return;
  show('report-summary', resultSummary(state.material) + `<h3>Experiment ID</h3><code>${state.id}</code>
    <div class="metrics report-metrics">
      ${metric('Message signed', state.signature ? 'YES' : 'PENDING')}
      ${metric('Latest integrity check', state.verification == null ? 'PENDING' : state.verification.message_intact ? 'INTACT' : 'CHANGED', state.verification?.message_intact ? 'good' : '')}
      ${metric('Attack simulation', state.attack ? 'DONE' : 'PENDING')}
      ${metric('Sweep points', state.sweep ? state.sweep.points.length : 'PENDING')}
      ${metric('Sampling bound', state.bound ? percent(state.bound.failure_probability_upper_bound) : 'PENDING')}
    </div><p>Actual baseline, signing status, recipient verification, and attack outputs are included in the JSON report. Sweeps have a separate JSON export. This public experiment does not constitute a QDS security certificate.</p>`);
}

function resetWorkflow() {
  Object.keys(state).forEach(key => { state[key] = null; });
  $('material-form').reset();
  $('message').value = 'QNexus hackathon demonstration';
  $('intensity').value = 1;
  $('sweep-min').value = 0;
  $('sweep-max').value = 1;
  $('sweep-step').value = 0.1;
  $('bound-n').value = 162;
  $('bound-epsilon').value = 0.035;
  $('bound-qber').value = 0;
  ['material-result', 'signing-result', 'attack-result', 'sweep-result', 'bounds-result', 'circuit-result'].forEach(id => {
    $(id).hidden = true;
    $(id).innerHTML = '';
  });
  $('material-empty').hidden = false;
  updateSliders();
  navigate('protocol');
  status('Workflow reset. Select the public model to begin a new experiment.');
}

document.querySelectorAll('[data-panel], [data-go]').forEach(button => {
  button.addEventListener('click', () => navigate(button.dataset.panel || button.dataset.go));
});
$('reset-button').addEventListener('click', resetWorkflow);
['pulse_count', 'distance_km', 'intensity'].forEach(id => $(id).addEventListener('input', updateSliders));

$('material-form').addEventListener('submit', event => {
  event.preventDefault();
  action(event.submitter, async () => {
    const result = await api('/api/material', config());
    Object.keys(state).forEach(key => { state[key] = null; });
    state.id = result.simulation_id;
    state.material = result;
    ['signing-result', 'attack-result', 'sweep-result', 'bounds-result'].forEach(id => { $(id).hidden = true; });
    $('material-empty').hidden = true;
    show('material-result', resultSummary(result) + `<h3>Simulation ID</h3><code>${result.simulation_id}</code><h3>Bob register preview</h3><code>${result.bob.register_preview || 'No usable bits'}</code>`);
    $('bound-n').value = Math.max(1, result.tested_bits);
    $('bound-qber').value = result.pooled_test_qber ?? 0;
  });
});

$('sign-button').addEventListener('click', event => action(event.currentTarget, async () => {
  needMaterial();
  const result = await api('/api/sign', { simulation_id: state.id, message: $('message').value });
  state.signature = result.signature;
  state.verification = null;
  show('signing-result', '<span class="pill good">MESSAGE TOKEN CREATED · CLASSICAL DEMO</span><h3>SHA-256 Message Digest</h3><code id="digest-text"></code><h3>HMAC Signature</h3><code id="signature-text"></code>');
  $('digest-text').textContent = result.message_digest;
  $('signature-text').textContent = result.signature;
}));

$('verify-button').addEventListener('click', event => action(event.currentTarget, async () => {
  needMaterial();
  if (!state.signature) throw new Error('Alice must sign the message first.');
  const result = await api('/api/verify', { simulation_id: state.id, message: $('message').value, signature: state.signature });
  state.verification = result;
  show('signing-result', `<div class="metrics">
    ${metric('Message integrity', result.message_intact ? 'INTACT' : 'CHANGED', result.message_intact ? 'good' : 'bad')}
    ${metric('Bob accepts', result.bob_accepts ? 'ACCEPTED' : 'REJECTED', result.bob_accepts ? 'good' : 'bad')}
    ${metric('Charlie accepts', result.charlie_accepts ? 'ACCEPTED' : 'REJECTED', result.charlie_accepts ? 'good' : 'bad')}
  </div><p>Acceptance combines the classical integrity check with simulated mismatch thresholds. These recipient checks do not establish quantum signature security.</p>`);
}));

$('attack-button').addEventListener('click', event => action(event.currentTarget, async () => {
  needMaterial();
  const result = await api('/api/attack', { simulation_id: state.id, intensity: Number($('intensity').value) });
  state.attack = result;
  show('attack-result', resultSummary(result) + `<p>Expected error rate in this model: ${percent(result.expected_sifted_qber)}. Test samples fluctuate around this value. An abort means the configured channel threshold was exceeded; it does not identify the cause uniquely.</p>`);
}));

$('sweep-button').addEventListener('click', event => action(event.currentTarget, async () => {
  const result = await api('/api/sweep', {
    config: state.material?.config ?? config(), minimum: Number($('sweep-min').value),
    maximum: Number($('sweep-max').value), step: Number($('sweep-step').value)
  });
  state.sweep = result;
  show('sweep-result', '<canvas id="sweep-chart" class="chart" width="1000" height="380" role="img" aria-label="Measured and expected QBER across interception intensities"></canvas><div class="chart-key"><span>● Measured Test QBER</span><span>— Model Expectation</span></div><div id="sweep-table" class="table-wrap"></div><button id="export-sweep">EXPORT SWEEP JSON ↓</button>');
  drawChart(result.points);
  $('sweep-table').innerHTML = `<table><thead><tr><th>Intensity</th><th>Measured QBER</th><th>Expected QBER</th><th>Test Samples</th><th>Decision</th></tr></thead><tbody>${result.points.map(point => `<tr><td>${Math.round(point.intensity * 100)}%</td><td>${percent(point.qber)}</td><td>${percent(point.expected_qber)}</td><td>${point.tested_bits}</td><td>${point.insufficient_data ? 'No data' : point.abort ? 'ABORT' : 'PASS'}</td></tr>`).join('')}</tbody></table>`;
  $('export-sweep').addEventListener('click', () => download(result, 'qnexus-sweep.json'));
}));

function drawChart(points) {
  const canvas = $('sweep-chart'), context = canvas.getContext('2d');
  const left = 78, top = 35, width = 880, height = 275;
  const max = Math.max(0.3, ...points.map(point => point.qber ?? 0), ...points.map(point => point.expected_qber));
  const x = value => left + value * width;
  const y = value => top + height - value / max * height;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.font = '16px ui-monospace, monospace';
  context.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const value = max * i / 5;
    context.strokeStyle = '#e0e6e9';
    context.beginPath(); context.moveTo(left, y(value)); context.lineTo(left + width, y(value)); context.stroke();
    context.fillStyle = '#6b7c8f';
    context.fillText(`${(value * 100).toFixed(0)}%`, 16, y(value) + 6);
    context.fillText(`${i * 20}%`, x(i / 5) - 16, top + height + 31);
  }
  context.fillText('Interception Intensity', 385, 370);
  function line(key, color) {
    context.strokeStyle = color; context.lineWidth = 3; context.beginPath();
    let started = false;
    for (const point of points) {
      if (point[key] == null) { started = false; continue; }
      if (!started) { context.moveTo(x(point.intensity), y(point[key])); started = true; }
      else context.lineTo(x(point.intensity), y(point[key]));
    }
    context.stroke();
  }
  line('expected_qber', '#229471'); line('qber', '#071842');
  context.fillStyle = '#071842';
  for (const point of points) if (point.qber != null) {
    context.beginPath(); context.arc(x(point.intensity), y(point.qber), 5, 0, Math.PI * 2); context.fill();
  }
}

$('bound-button').addEventListener('click', event => action(event.currentTarget, async () => {
  const result = await api('/api/bounds', { n: Number($('bound-n').value), epsilon: Number($('bound-epsilon').value), observed_qber: Number($('bound-qber').value) });
  state.bound = result;
  show('bounds-result', `<div class="metrics">
    ${metric('Deviation Probability Upper Bound', percent(result.failure_probability_upper_bound))}
    ${metric('Coverage Lower Bound', percent(result.coverage_lower_bound))}
    ${metric('Sample Size', result.n)}
  </div><p><code>min(1, 2 × exp(−2 × ${result.n} × ${result.epsilon}²))</code></p>
  <p class="${result.informative ? 'good' : 'bad'}">${result.informative ? 'Informative under the stated sampling assumptions.' : 'UNINFORMATIVE: the sample is too small for this tolerance. A 100% bound provides no useful assurance.'}</p>
  <p>Observed rate ± tolerance: ${percent(result.interval[0])} to ${percent(result.interval[1])}. Assumes independent bounded observations; this is not a QDS security certificate.</p>`);
}));

$('circuit-button').addEventListener('click', event => action(event.currentTarget, async () => {
  const result = await api('/api/circuit');
  show('circuit-result', `<div class="metrics">${metric('Actual Aer Shots', result.shots)}${metric('Bob Error Rate', percent(result.qber))}${metric('Qubits', 1)}</div><pre id="circuit-text"></pre><h3>Measurement Counts (Bob, Eve)</h3><pre id="counts-text"></pre><p>Each two-bit count string lists Bob first and Eve second. This circuit isolates the wrong-basis measurement effect.</p>`);
  $('circuit-text').textContent = result.circuit;
  $('counts-text').textContent = JSON.stringify(result.counts, null, 2);
}));

function download(data, filename) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$('report-button').addEventListener('click', event => action(event.currentTarget, async () => {
  needMaterial();
  download(await api(`/api/report/${state.id}`), 'qnexus-experiment-report.json');
}));

updateSliders();
updateNavigation();
