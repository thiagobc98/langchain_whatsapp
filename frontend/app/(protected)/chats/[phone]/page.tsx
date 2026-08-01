"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type ChatMessage } from "../../../../lib/api";

export default function ChatDetailPage() {
  const params = useParams<{ phone: string }>();
  const phone = decodeURIComponent(params.phone);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .chatMessages(phone)
      .then((data) => setMessages(data.messages))
      .catch((e) => setError(e.message));
  }, [phone]);

  return (
    <div>
      <p>
        <Link href="/chats">&larr; Conversas</Link>
      </p>
      <h1 style={{ marginTop: 0 }}>{phone}</h1>
      {error && <p className="error-text">{error}</p>}

      <div style={{ display: "grid", gap: "0.8rem" }}>
        {messages.map((msg) => (
          <div key={msg.id} className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "0.5rem",
              }}
            >
              <span className="muted">
                {msg.created_at
                  ? new Date(msg.created_at).toLocaleString("pt-BR")
                  : "-"}
              </span>
              <StatusBadge status={msg.status} />
            </div>
            <p style={{ margin: "0 0 0.4rem" }}>
              <strong>Usuário:</strong> {msg.incoming_message || msg.normalized_input || "-"}
            </p>
            <p style={{ margin: 0 }}>
              <strong>Agente:</strong> {msg.response || msg.error || "-"}
            </p>
          </div>
        ))}
        {messages.length === 0 && !error && (
          <p className="muted">Nenhuma mensagem para este contato.</p>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "done" ? "var(--success)" : status === "failed" ? "var(--danger)" : "var(--text-muted)";
  return (
    <span className="muted" style={{ color }}>
      {status}
    </span>
  );
}
