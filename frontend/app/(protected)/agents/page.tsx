"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

export default function AgentsPage() {
  const [agents, setAgents] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .agents()
      .then((data) => setAgents(data.agents))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Agentes</h1>
      {error && <p className="error-text">{error}</p>}

      <div style={{ display: "grid", gap: "0.6rem" }}>
        {agents.map((agentId) => (
          <div key={agentId} className="card">
            {agentId}
          </div>
        ))}
        {agents.length === 0 && !error && (
          <p className="muted">Nenhum agente registrado no catálogo.</p>
        )}
      </div>
    </div>
  );
}
