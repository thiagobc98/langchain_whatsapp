"use client";

import { useEffect, useState } from "react";
import { api, type Metrics } from "../../../lib/api";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.metrics().then(setMetrics).catch((e) => setError(e.message));
    const interval = setInterval(() => {
      api.metrics().then(setMetrics).catch(() => {});
    }, 10_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      {error && <p className="error-text">{error}</p>}
      {!metrics && !error && <p className="muted">Carregando métricas...</p>}
      {metrics && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "1rem",
          }}
        >
          <StatCard label="Mensagens hoje" value={metrics.total_today} />
          <StatCard label="Falhas hoje" value={metrics.failures_today} />
          <StatCard
            label="Tempo médio (s)"
            value={metrics.avg_processing_time_seconds ?? "-"}
          />
          <StatCard label="Fila atual" value={metrics.queue_size} />
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="card">
      <p className="muted" style={{ margin: 0 }}>
        {label}
      </p>
      <p style={{ fontSize: "1.8rem", margin: "0.3rem 0 0", fontWeight: 600 }}>
        {value}
      </p>
    </div>
  );
}
