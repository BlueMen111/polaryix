"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getPublicDashboard } from "@/lib/api";
import type { Dashboard } from "@/types";

export default function PublicDashboardPage() {
  const params = useParams<{ slug: string }>();

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getPublicDashboard(params.slug)
      .then((response) => setDashboard(response.dashboard))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Erro ao carregar dashboard.")
      );
  }, [params.slug]);

  if (error) {
    return (
      <main className="container">
        <section className="card">
          <h1>Dashboard não encontrado</h1>
          <p style={{ color: "var(--danger)" }}>{error}</p>
        </section>
      </main>
    );
  }

  if (!dashboard) {
    return (
      <main className="container">
        <p>Carregando dashboard...</p>
      </main>
    );
  }

  const kpiWidgets = dashboard.widgets.filter((widget) => widget.widget_type === "kpi");
  const chartWidgets = dashboard.widgets.filter((widget) => widget.widget_type === "chart");

  return (
    <main className="container">
      <div className="header">
        <div>
          <h1>{dashboard.title}</h1>
          <p className="muted">
            Dataset: {dashboard.dataset.original_filename} • Link público: /d/{dashboard.slug}
          </p>
        </div>
      </div>

      <section className="grid grid-3">
        {kpiWidgets.map((widget) => (
          <div className="kpi" key={widget.id}>
            <span className="muted">{widget.title}</span>
            <strong>
              {String(widget.config.value ?? "-")}
              {String(widget.config.suffix ?? "")}
            </strong>
            {widget.config.description && (
              <p className="muted">{String(widget.config.description)}</p>
            )}
          </div>
        ))}
      </section>

      <section className="grid grid-2" style={{ marginTop: 24 }}>
        {chartWidgets.map((widget) => (
          <div className="card" key={widget.id}>
            <h3>{widget.title}</h3>
            <p className="muted">{String(widget.config.description ?? "")}</p>
            <p>
              <span className="badge">{String(widget.config.type ?? "chart")}</span>
            </p>
            <p className="muted">
              Eixo X: {String(widget.config.x ?? "-")} <br />
              Eixo Y: {String(widget.config.y ?? "-")}
            </p>
          </div>
        ))}
      </section>
    </main>
  );
}