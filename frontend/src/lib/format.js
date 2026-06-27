// Small formatting helpers used across panels.
export const fmt = {
  hp: (v) => (v == null ? "—" : `${Math.round(v)} hp`),
  kpa: (v) => (v == null ? "—" : `${Number(v).toFixed(0)} kPa`),
  deg: (v) => (v == null ? "—" : `${Number(v).toFixed(1)}°`),
  ms: (v) => (v == null ? "—" : `${Number(v).toFixed(2)} ms`),
  pct: (v) => (v == null ? "—" : `${Number(v).toFixed(0)}%`),
  conf: (v) => (v == null ? "—" : `${(v * 100).toFixed(0)}%`),
  num: (v, d = 2) => (v == null ? "—" : Number(v).toFixed(d)),
  date: (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: "numeric", month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit"
    });
  },
};

export const confidenceLabel = (v) => {
  if (v >= 0.85) return "HIGH";
  if (v >= 0.65) return "MODERATE";
  if (v >= 0.45) return "LOW";
  return "VERY LOW";
};

export const confidenceTone = (v) => {
  if (v >= 0.75) return "safe";
  if (v >= 0.5) return "warning";
  return "danger";
};
