import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sparkles, Loader2, RotateCcw, X } from "lucide-react";

/**
 * Inline AI explainer for an Inspector finding.
 * Streams plain-English explanation from Claude Sonnet 4.6 via SSE.
 */
export default function ExplainFinding({
  finding,
  profileName,
  engineMetadata,
  safetyEnvelope,
  apiBase,
  testId,
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const stop = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStreaming(false);
  };

  const run = async () => {
    setOpen(true);
    setText("");
    setError(null);
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch(`${apiBase}/inspector/findings/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          finding,
          profile_name: profileName,
          engine_metadata: engineMetadata,
          safety_envelope: safetyEnvelope,
        }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // SSE frames are separated by blank lines
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          let event = "message";
          let data = "";
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (event === "token") {
            const piece = data.replace(/\\n/g, "\n");
            setText((t) => t + piece);
          } else if (event === "error") {
            setError(data);
          } else if (event === "done") {
            // stream complete
          }
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") {
        setError(String(e.message || e));
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={run}
        data-testid={testId || "explain-finding-btn"}
        className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-accent)] hover:text-[#7dd3fc] border border-[var(--st-accent)] px-2 py-1 flex items-center gap-1.5 transition-colors"
      >
        <Sparkles className="w-3 h-3" /> Explain this finding
      </button>
    );
  }

  return (
    <div
      className="mt-3 border border-[var(--st-accent)] bg-[var(--st-panel-deep)] p-3"
      data-testid={testId ? `${testId}-output` : "explain-output"}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-[var(--st-accent)]" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-accent)]">
            AI EXPLANATION · CLAUDE SONNET 4.6
          </span>
          {streaming && <Loader2 className="w-3 h-3 animate-spin text-[var(--st-accent)]" />}
        </div>
        <div className="flex items-center gap-2">
          {!streaming && (
            <button
              type="button"
              onClick={run}
              className="font-mono text-[10px] text-[var(--st-text-muted)] hover:text-[var(--st-accent)] flex items-center gap-1"
              title="Regenerate"
            >
              <RotateCcw className="w-3 h-3" /> RETRY
            </button>
          )}
          {streaming && (
            <button
              type="button"
              onClick={stop}
              className="font-mono text-[10px] text-[var(--st-text-muted)] hover:text-[var(--st-danger)] flex items-center gap-1"
            >
              STOP
            </button>
          )}
          <button
            type="button"
            onClick={() => { stop(); setOpen(false); }}
            className="text-[var(--st-text-muted)] hover:text-[var(--st-text)]"
            title="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {error ? (
        <div className="font-mono text-xs text-[var(--st-danger)]">ERROR :: {error}</div>
      ) : (
        <div className="text-sm text-[var(--st-text-secondary)] leading-relaxed whitespace-pre-wrap">
          {text}
          {streaming && <span className="inline-block w-2 h-3 bg-[var(--st-accent)] ml-1 animate-pulse" />}
          {!streaming && !text && (
            <span className="text-[var(--st-text-muted)] italic">No response generated.</span>
          )}
        </div>
      )}
    </div>
  );
}
