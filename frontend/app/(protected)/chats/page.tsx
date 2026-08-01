"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Chat } from "../../../lib/api";

const PAGE_SIZE = 20;

export default function ChatsPage() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .chats(PAGE_SIZE, offset)
      .then((data) => {
        setChats(data.chats);
        setTotal(data.total);
      })
      .catch((e) => setError(e.message));
  }, [offset]);

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Conversas</h1>
      {error && <p className="error-text">{error}</p>}

      <div className="card" style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Telefone</th>
              <th>Agente</th>
              <th>Última mensagem</th>
              <th>Quando</th>
              <th>Msgs</th>
            </tr>
          </thead>
          <tbody>
            {chats.map((chat) => (
              <tr key={`${chat.phone_number}:${chat.agent_id}`}>
                <td>
                  <Link href={`/chats/${encodeURIComponent(chat.phone_number)}`}>
                    {chat.phone_number}
                  </Link>
                </td>
                <td>{chat.agent_id}</td>
                <td style={{ maxWidth: 320 }}>{chat.last_message ?? "-"}</td>
                <td className="muted">
                  {chat.last_message_at
                    ? new Date(chat.last_message_at).toLocaleString("pt-BR")
                    : "-"}
                </td>
                <td>{chat.message_count}</td>
              </tr>
            ))}
            {chats.length === 0 && !error && (
              <tr>
                <td colSpan={5} className="muted">
                  Nenhuma conversa ainda.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={{ display: "flex", gap: "0.6rem", marginTop: "1rem" }}>
        <button
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
        >
          Anterior
        </button>
        <button
          disabled={offset + PAGE_SIZE >= total}
          onClick={() => setOffset(offset + PAGE_SIZE)}
        >
          Próxima
        </button>
        <span className="muted" style={{ alignSelf: "center" }}>
          {total} conversa(s)
        </span>
      </div>
    </div>
  );
}
