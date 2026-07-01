"use client";

import { useEffect, useState } from "react";
import { exchangeGoogleCode, persistAuthSession } from "@/lib/api";

export default function GoogleCallbackPage() {
  const [status, setStatus] = useState("Conectando sua conta Google...");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const error = params.get("error");

    if (error) {
      setStatus("Google cancelou ou recusou o login. Redirecionando...");
      window.setTimeout(() => {
        window.location.href = "/login?auth_error=google";
      }, 900);
      return;
    }

    if (!code) {
      setStatus("Nao recebemos o codigo do Google. Redirecionando...");
      window.setTimeout(() => {
        window.location.href = "/login?auth_error=missing_code";
      }, 900);
      return;
    }

    const redirectUri = `${window.location.origin}/auth/google/callback`;
    exchangeGoogleCode({ code, redirectUri })
      .then((session) => {
        persistAuthSession(session);
        const nextPath = window.localStorage.getItem("polaryix:auth-next") || "/";
        window.localStorage.removeItem("polaryix:auth-next");
        window.location.href = nextPath.startsWith("/") && !nextPath.startsWith("//") ? nextPath : "/";
      })
      .catch((err) => {
        setStatus(err instanceof Error ? err.message : "Nao foi possivel concluir o login com Google.");
        window.setTimeout(() => {
          window.location.href = "/login?auth_error=google";
        }, 1600);
      });
  }, []);

  return (
    <main style={{ minHeight: "calc(100vh - 78px)", display: "grid", placeItems: "center", padding: "2rem" }}>
      <section
        style={{
          width: "min(460px, 100%)",
          border: "1px solid rgba(8, 116, 255, 0.14)",
          borderRadius: 24,
          background: "rgba(255,255,255,0.86)",
          boxShadow: "0 30px 80px rgba(8, 48, 110, 0.12)",
          color: "#061334",
          padding: "2rem",
          textAlign: "center",
        }}
      >
        <p style={{ margin: 0, color: "#0874ff", fontWeight: 950, textTransform: "uppercase", fontSize: ".78rem" }}>Google</p>
        <h1 style={{ margin: ".5rem 0", fontSize: "1.7rem" }}>Finalizando login</h1>
        <span style={{ color: "#60728e" }}>{status}</span>
      </section>
    </main>
  );
}
