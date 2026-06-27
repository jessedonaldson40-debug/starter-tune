import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listProfiles, deleteProfile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import { fmt } from "@/lib/format";
import { Plus, Trash2, ArrowUpRight, Cpu, Gauge, Wrench } from "lucide-react";
import { toast } from "sonner";

export default function Dashboard() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const refresh = () => {
    setLoading(true);
    listProfiles().then((p) => setProfiles(p || [])).finally(() => setLoading(false));
  };
  useEffect(refresh, []);

  const onDelete = async (id, name) => {
    if (!window.confirm(`Delete profile "${name}"? This cannot be undone.`)) return;
    await deleteProfile(id);
    toast.success("Profile deleted");
    refresh();
  };

  return (
    <div className="max-w-[1600px] mx-auto px-6 py-8" data-testid="dashboard-page">
      {/* Hero */}
      <Panel className="p-8 mb-8 relative overflow-hidden" testId="dashboard-hero">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-[0.04] pointer-events-none"
             style={{ background: "url('https://images.unsplash.com/photo-1552656967-7a0991a13906?w=800') center/cover" }} />
        <div className="relative flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 mb-3">
              <span className="font-mono text-[10px] tracking-[0.25em] text-[var(--st-accent)]">SE/v1.0</span>
              <span className="font-mono text-[10px] tracking-[0.25em] text-[var(--st-text-muted)]">// CALIBRATION MODULE</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-medium tracking-tight text-[var(--st-text)] leading-tight">
              From engine metadata<br/>to a credible starter tune<br/>
              <span className="text-[var(--st-text-muted)]">in under thirty seconds.</span>
            </h1>
            <p className="text-sm text-[var(--st-text-secondary)] mt-5 max-w-xl leading-relaxed">
              The Starter Tune Engine builds a complete conservative calibration package — fuel,
              ignition, idle, cold start, boost targets, and a full safety envelope — from minimal
              engine specs. Generated tunes hand off cleanly to DIAG-SIM, Tune Inspector Pro and
              Forensic Inspector.
            </p>
          </div>
          <div className="flex flex-col gap-3 shrink-0">
            <Button
              data-testid="generate-starter-tune-btn"
              onClick={() => navigate("/wizard")}
              className="bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs tracking-[0.18em] uppercase h-12 px-6 rounded-none"
            >
              <Plus className="w-4 h-4 mr-2" />
              Generate Starter Tune
            </Button>
            <span className="font-mono text-[10px] text-[var(--st-text-muted)] uppercase tracking-widest text-right">
              CONSERVATIVE · CREDIBLE · TRACEABLE
            </span>
          </div>
        </div>
      </Panel>

      {/* Stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { Icon: Gauge,  k: "PROFILES", v: profiles.length },
          { Icon: Cpu,    k: "ENGINE COVERAGE", v: "NA · TURBO · S/C" },
          { Icon: Wrench, k: "ADJUSTMENT AXES", v: "AFR · TIM · BOOST · DRIVE" },
          { Icon: ArrowUpRight, k: "HANDOFF TARGETS", v: "DIAG-SIM · TIP · FI · ECU" },
        ].map(({ Icon, k, v }) => (
          <div key={k} className="st-panel p-4">
            <div className="flex items-center justify-between mb-3">
              <Icon className="w-4 h-4 text-[var(--st-text-muted)]" />
              <span className="font-mono text-[9px] tracking-widest text-[var(--st-text-muted)]">{k}</span>
            </div>
            <div className="font-mono text-base text-[var(--st-text)] tracking-tight">{v}</div>
          </div>
        ))}
      </div>

      {/* Profiles list */}
      <Panel testId="profiles-section">
        <PanelHeader index={1} label="STARTER TUNE PROFILES" sub={`${profiles.length} STORED`} />
        {loading ? (
          <div className="text-center py-12 font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest">
            LOADING…
          </div>
        ) : profiles.length === 0 ? (
          <div className="border border-dashed border-[var(--st-border)] p-12 text-center" data-testid="empty-profiles">
            <div className="font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest mb-3">
              NO PROFILES YET
            </div>
            <p className="text-sm text-[var(--st-text-secondary)] mb-5 max-w-md mx-auto">
              Generate your first starter tune to seed a profile. The system will produce a complete
              fuel + ignition + safety package from the engine specs you provide.
            </p>
            <Button
              onClick={() => navigate("/wizard")}
              data-testid="empty-generate-btn"
              className="bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs tracking-widest uppercase rounded-none"
            >
              <Plus className="w-4 h-4 mr-2" /> Generate first starter tune
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {profiles.map((p) => (
              <div key={p.id} className="st-panel-raised p-4 hover:border-[var(--st-border-strong)] transition-colors" data-testid={`profile-card-${p.id}`}>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="min-w-0">
                    <Link to={`/profiles/${p.id}`} className="text-sm text-[var(--st-text)] hover:text-[var(--st-accent)] truncate block" data-testid={`profile-link-${p.id}`}>
                      {p.name}
                    </Link>
                    <div className="font-mono text-[10px] text-[var(--st-text-muted)] uppercase tracking-wider mt-1">
                      {p.engine_metadata.displacement_l}L · {p.engine_metadata.cylinders}cyl ·{" "}
                      {p.engine_metadata.induction} · {p.engine_metadata.fuel_type}
                    </div>
                  </div>
                  <button
                    onClick={() => onDelete(p.id, p.name)}
                    data-testid={`profile-delete-${p.id}`}
                    className="text-[var(--st-text-muted)] hover:text-[var(--st-danger)] p-1"
                    title="Delete profile"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <div className="st-data-label">TARGET</div>
                    <div className="font-mono text-sm">{fmt.hp(p.engine_metadata.target_hp)}</div>
                  </div>
                  <div>
                    <div className="st-data-label">REV LIMIT</div>
                    <div className="font-mono text-sm">{p.engine_metadata.rev_limit} RPM</div>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-[var(--st-border)]">
                  <span className="font-mono text-[10px] text-[var(--st-text-muted)]">
                    {fmt.date(p.created_at)}
                  </span>
                  <Link to={`/profiles/${p.id}`} className="font-mono text-[10px] text-[var(--st-accent)] hover:text-[#7dd3fc] uppercase tracking-widest flex items-center gap-1">
                    OPEN <ArrowUpRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
