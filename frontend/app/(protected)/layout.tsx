"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, type AdminUser } from "../../lib/api";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setChecked(true));
  }, [router]);

  async function handleLogout() {
    await api.logout().catch(() => {});
    router.push("/login");
  }

  if (!checked) {
    return (
      <main style={{ padding: "2rem" }}>
        <p className="muted">Carregando...</p>
      </main>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <nav
        className="card"
        style={{
          width: 200,
          borderRadius: 0,
          borderTop: "none",
          borderBottom: "none",
          borderLeft: "none",
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          padding: "1.2rem 1rem",
        }}
      >
        <strong style={{ marginBottom: "0.8rem" }}>WhatsApp Admin</strong>
        <Link href="/dashboard">Dashboard</Link>
        <Link href="/chats">Conversas</Link>
        <Link href="/agents">Agentes</Link>
        <div style={{ marginTop: "auto" }}>
          <p className="muted" style={{ marginBottom: "0.4rem" }}>
            {user.username}
          </p>
          <button onClick={handleLogout} style={{ width: "100%" }}>
            Sair
          </button>
        </div>
      </nav>
      <main style={{ flex: 1, padding: "1.5rem 2rem" }}>{children}</main>
    </div>
  );
}
