// Heatmap color scales for fuel/ignition/boost maps
// All scales designed to be readable on a #141416 graphite background.

// Viridis-inspired perceptually uniform scale for fuel pulse-width.
const VIRIDIS = [
  [68, 1, 84],     // 0.0 deep purple
  [59, 82, 139],   // 0.25 blue
  [33, 145, 140],  // 0.5 teal
  [94, 201, 98],   // 0.75 green
  [253, 231, 37],  // 1.0 yellow
];

// Diverging blue→neutral→red for ignition timing (cold to hot)
const IGNITION = [
  [8, 81, 156],
  [49, 130, 189],
  [107, 174, 214],
  [180, 200, 220],
  [50, 50, 55],     // neutral mid (charcoal so it disappears into bg)
  [252, 174, 145],
  [251, 106, 74],
  [222, 45, 38],
  [165, 15, 21],
];

// Risk overlay — transparent → amber → red
const RISK = [
  [0, 0, 0, 0],
  [245, 158, 11, 0.45],
  [239, 68, 68, 0.7],
];

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function sampleScale(scale, t) {
  t = Math.max(0, Math.min(1, t));
  if (scale.length === 1) return scale[0];
  const segments = scale.length - 1;
  const idx = t * segments;
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, segments);
  const frac = idx - lo;
  const a = scale[lo];
  const b = scale[hi];
  return a.map((c, i) => Math.round(lerp(c, b[i], frac)));
}

export function colorFuel(value, min, max) {
  const t = (value - min) / Math.max(1e-6, max - min);
  const [r, g, b] = sampleScale(VIRIDIS, t);
  return `rgb(${r},${g},${b})`;
}

export function colorIgnition(value, min, max) {
  // map [min, max] to [0, 1]
  const t = (value - min) / Math.max(1e-6, max - min);
  const [r, g, b] = sampleScale(IGNITION, t);
  return `rgb(${r},${g},${b})`;
}

export function colorDelta(delta, maxAbs) {
  // diverging around 0
  const t = 0.5 + (delta / Math.max(0.0001, 2 * maxAbs));
  const [r, g, b] = sampleScale(IGNITION, t);
  return `rgb(${r},${g},${b})`;
}

export function colorRisk(level /* 0..1 */) {
  const [r, g, b, a] = sampleScale(RISK, level);
  return `rgba(${r},${g},${b},${a})`;
}

export function textOn(rgbString) {
  // accept rgb(a,b,c)
  const m = rgbString.match(/(\d+),(\d+),(\d+)/);
  if (!m) return "#f4f4f5";
  const [r, g, b] = [m[1], m[2], m[3]].map(Number);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.62 ? "#0b0b0d" : "#f4f4f5";
}

export function matMinMax(matrix) {
  let mn = Infinity, mx = -Infinity;
  for (const row of matrix) for (const v of row) {
    if (v < mn) mn = v;
    if (v > mx) mx = v;
  }
  if (!isFinite(mn)) return [0, 1];
  if (mn === mx) mx = mn + 1;
  return [mn, mx];
}

export function matAbsMax(matrix) {
  let mx = 0;
  for (const row of matrix) for (const v of row) {
    if (Math.abs(v) > mx) mx = Math.abs(v);
  }
  return mx || 1;
}
