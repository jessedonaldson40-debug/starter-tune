import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getDiagSimSession, listDiagSimScenarios, runDiagSim } from "@/lib/api";
import WarningBanner from "@/components/WarningBanner";
import { fmt } from "@/lib/format";
import { ArrowLeft, Play, Activity, AlertTriangle } from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, ComposedChart, Area, XAxis, YAxis,
  Tooltip as RTooltip, CartesianGrid, ReferenceLine,
} from "recharts";

const tooltipStyle = {
  background: "#0e0e10",
  border: "1px solid #3f3f46",
  borderRadius: 0,
  fontFamily: "JetBrains Mono",
  fontSize: 11,
};

function MetricCard({ label, value, sub, tone = "default", testId }) {
  const borderClass = tone === "danger" ? "border-[var(--st-danger)]"
                    : tone === "warning" ? "border-[var(--st-warning)]"
                    : tone === "safe" ? "border-[var(--st-safe)]"
                    : "border-[var(--st-border)]";
  return (
    <div className={`border ${borderClass} bg-[var(--st-panel-deep)] p-3`} data-testid={testId}>
      <div className="st-data-label">{label}</div>
      <div className="font-mono text-lg mt-1 tabular-nums">{value}</div>
      {sub && <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">{sub}</div>}
    </div>
  );
}

export default function DiagSimSession() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [scenarios, setScenarios] = useState({});
  const [scenarioKey, setScenarioKey] = useState("wot_pull");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    listDiagSimScenarios().then(setScenarios);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    getDiagSimSession(sessionId).then((s) => {
      setSession(s);
      setScenarioKey(s.scenario);
    });
  }, [sessionId]);

  const rerun = async () => {
    if (!session) return;
    setRunning(true);
    try {
      const next = await runDiagSim(session.profile_id, scenarioKey);
      navigate(`/diagsim/${next.session_id}`, { replace: true });
      setSession(next);
    } finally {
      setRunning(false);
    }
  };

  if (!session) {
    return (
      <div className="max-w-[1600px] mx-auto px-6 py-12 text-center font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest">
        LOADING DIAG-SIM SESSION…
      </div>
    );
  }

  const knockSamples = session.samples.filter((s) => s.knock === 1);

  return (
    <div className="max-w-[1600px] mx-auto px-6 py-6" data-testid="diagsim-page">
      <div className="flex items-center justify-between mb-4">
        <Link to={`/profiles/${session.profile_id}`}
              className="font-mono text-[10px] text-[var(--st-text-muted)] hover:text-[var(--st-accent)] uppercase tracking-widest flex items-center gap-2"
              data-testid="back-to-profile-from-diagsim">
          <ArrowLeft className="w-3 h-3" /> Back to profile · {session.profile_name}
        </Link>
        <div className="flex items-center gap-2">
          <Select value={scenarioKey} onValueChange={setScenarioKey}>
            <SelectTrigger className="rounded-none bg-[var(--st-panel-deep)] border-[var(--st-border)] focus:ring-0 focus-visible:ring-0 h-9 font-mono text-xs w-56" data-testid="select-diagsim-scenario">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
              {Object.entries(scenarios).map(([k, s]) => (
                <SelectItem key={k} value={k} className="rounded-none font-mono text-xs">
                  {s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={rerun} disabled={running} data-testid="diagsim-rerun-btn"
                  className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-[11px] uppercase tracking-widest h-9">
            <Play className="w-3.5 h-3.5 mr-2" />
            {running ? "RUNNING…" : "Run Scenario"}
          </Button>
        </div>
      </div>

      <Panel className="mb-4" testId="diagsim-header">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 font-mono text-[10px] text-[var(--st-text-muted)] tracking-widest uppercase mb-2">
              <Activity className="w-3 h-3 text-[var(--st-accent)]" />
              DIAG-SIM SESSION :: {session.session_id.slice(0, 8)}
            </div>
            <h1 className="text-2xl font-medium tracking-tight text-[var(--st-text)]">{session.scenario_name}</h1>
            <p className="text-xs text-[var(--st-text-secondary)] mt-1">{session.scenario_description}</p>
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-2">
              {fmt.date(session.created_at)} · {session.duration_s.toFixed(1)}s @ {session.sample_hz} Hz · {session.summary.n_samples} samples · source generation #{session.source_generation_index + 1}
            </div>
          </div>
        </div>
      </Panel>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-4" data-testid="diagsim-metrics">
        <MetricCard label="PEAK RPM" value={`${session.summary.peak_rpm}`} sub="MAX OBSERVED" />
        <MetricCard label="PEAK BOOST" value={`${session.summary.peak_boost_kpa_over_atm} kPa`} sub="OVER ATMOSPHERIC" />
        <MetricCard label="MAX TIMING" value={`${session.summary.max_timing}°`} sub="COMMANDED" />
        <MetricCard label="MIN AFR" value={session.summary.min_afr.toFixed(2)} sub="MEASURED"
                    tone={session.summary.min_afr < session.envelope_snapshot.afr_min * 0.95 ? "warning" : "safe"} />
        <MetricCard label="MAX AFR" value={session.summary.max_afr.toFixed(2)} sub="MEASURED"
                    tone={session.summary.max_afr > session.envelope_snapshot.afr_max * 1.03 ? "danger" : "safe"} />
        <MetricCard label="KNOCK EVENTS" value={session.summary.knock_events}
                    sub={session.summary.knock_events > 0 ? "DETECTED" : "CLEAN"}
                    tone={session.summary.knock_events > 5 ? "danger" : session.summary.knock_events > 0 ? "warning" : "safe"} />
      </div>

      {/* Fault codes */}
      {session.fault_codes.length > 0 && (
        <div className="space-y-2 mb-4" data-testid="diagsim-faults">
          {session.fault_codes.map((f, i) => (
            <WarningBanner key={i} level={f.severity === "danger" ? "danger" : "warning"}
                           code={f.code} message={f.label} testId={`fault-${f.code}`} />
          ))}
        </div>
      )}

      {/* RPM + MAP */}
      <Panel className="mb-4" testId="diagsim-rpm-map">
        <PanelHeader label="RPM · MAP · TPS" sub={`${session.summary.n_samples} SAMPLES`} />
        <div className="h-72 -mx-2">
          <ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={200}>
            <ComposedChart data={session.samples} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#3f3f46" strokeDasharray="2 4" />
              <XAxis dataKey="t" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <YAxis yAxisId="rpm" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <YAxis yAxisId="map" orientation="right" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <RTooltip contentStyle={tooltipStyle} labelStyle={{ color: "#a1a1aa" }} />
              <Line yAxisId="rpm" type="monotone" dataKey="rpm" stroke="#38BDF8" strokeWidth={1.4} dot={false} name="RPM" isAnimationActive={false} />
              <Line yAxisId="map" type="monotone" dataKey="map_kpa" stroke="#F59E0B" strokeWidth={1.4} dot={false} name="MAP (kPa)" isAnimationActive={false} />
              <Line yAxisId="map" type="monotone" dataKey="tps" stroke="#A1A1AA" strokeWidth={1} dot={false} name="TPS (%)" isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      {/* AFR */}
      <Panel className="mb-4" testId="diagsim-afr">
        <PanelHeader label="AFR // TARGET vs MEASURED" sub={`STOICH BAND`} />
        <div className="h-64 -mx-2">
          <ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={180}>
            <LineChart data={session.samples} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#3f3f46" strokeDasharray="2 4" />
              <XAxis dataKey="t" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <YAxis stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} domain={["dataMin - 0.5", "dataMax + 0.5"]} />
              <ReferenceLine y={session.envelope_snapshot.afr_min} stroke="#EF4444" strokeDasharray="3 3" />
              <ReferenceLine y={session.envelope_snapshot.afr_max} stroke="#EF4444" strokeDasharray="3 3" />
              <RTooltip contentStyle={tooltipStyle} labelStyle={{ color: "#a1a1aa" }} />
              <Line type="monotone" dataKey="afr_target" stroke="#38BDF8" strokeWidth={1.5} dot={false} name="TARGET" isAnimationActive={false} />
              <Line type="monotone" dataKey="afr_measured" stroke="#A1A1AA" strokeWidth={1} dot={false} name="MEASURED" isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      {/* Timing + Knock */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-4">
        <Panel testId="diagsim-timing">
          <PanelHeader label="IGNITION TIMING COMMAND" sub="° BTDC" />
          <div className="h-56 -mx-2">
            <ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={180}>
              <LineChart data={session.samples} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                <CartesianGrid stroke="#3f3f46" strokeDasharray="2 4" />
                <XAxis dataKey="t" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <YAxis stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <ReferenceLine y={session.envelope_snapshot.ignition_ceiling} stroke="#F59E0B" strokeDasharray="3 3" label={{ value: "ENVELOPE CEILING", fill: "#F59E0B", fontSize: 9, fontFamily: "JetBrains Mono", position: "insideTopRight" }} />
                <RTooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="timing_cmd" stroke="#38BDF8" strokeWidth={1.4} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel testId="diagsim-knock">
          <PanelHeader label="KNOCK EVENTS"
                       sub={`${session.summary.knock_events} TOTAL`}
                       right={knockSamples.length > 0 ? <AlertTriangle className="w-4 h-4 text-[var(--st-danger)]" /> : null} />
          {knockSamples.length === 0 ? (
            <div className="font-mono text-xs text-[var(--st-safe)] uppercase tracking-widest py-12 text-center">
              NO KNOCK DETECTED IN THIS RUN
            </div>
          ) : (
            <div className="h-56 -mx-2">
              <ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={180}>
                <ComposedChart data={session.samples} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                  <CartesianGrid stroke="#3f3f46" strokeDasharray="2 4" />
                  <XAxis dataKey="t" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                  <YAxis stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} domain={[0, 1]} />
                  <RTooltip contentStyle={tooltipStyle} />
                  <Area type="step" dataKey="knock" fill="#EF4444" stroke="#EF4444" fillOpacity={0.5} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>
      </div>

      {/* Thermals */}
      <Panel className="mb-4" testId="diagsim-thermals">
        <PanelHeader label="THERMALS // IAT · ECT · BOOST" />
        <div className="h-56 -mx-2">
          <ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={180}>
            <LineChart data={session.samples} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#3f3f46" strokeDasharray="2 4" />
              <XAxis dataKey="t" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <YAxis yAxisId="t" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <YAxis yAxisId="b" orientation="right" stroke="#3f3f46" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} />
              <RTooltip contentStyle={tooltipStyle} />
              <Line yAxisId="t" type="monotone" dataKey="iat" stroke="#F59E0B" strokeWidth={1.2} dot={false} name="IAT (°C)" isAnimationActive={false} />
              <Line yAxisId="t" type="monotone" dataKey="ect" stroke="#38BDF8" strokeWidth={1.2} dot={false} name="ECT (°C)" isAnimationActive={false} />
              <Line yAxisId="b" type="monotone" dataKey="boost_kpa" stroke="#10B981" strokeWidth={1.2} dot={false} name="BOOST (kPa)" isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}
