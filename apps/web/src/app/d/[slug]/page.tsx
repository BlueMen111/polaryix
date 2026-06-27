"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getPublicDashboard } from "@/lib/api";
import type { Dashboard } from "@/types";
import styles from "./page.module.css";

type ChartItem = {
  label: string;
  value: number;
};

export default function PublicDashboardPage() {
  const params = useParams<{ slug: string }>();

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string>>({});

  useEffect(() => {
    getPublicDashboard(params.slug)
      .then((response) => setDashboard(response.dashboard))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Erro ao carregar dashboard.")
      );
  }, [params.slug]);

  if (error) {
    return (
      <main className={styles.shell}>
        <section className={styles.dashboard}>
          <h1>Dashboard não encontrado</h1>
          <p style={{ color: "var(--danger)" }}>{error}</p>
        </section>
      </main>
    );
  }

  if (!dashboard) {
    return (
      <main className={styles.shell}>
        <section className={styles.dashboard}>
          <p className={styles.muted}>Carregando dashboard...</p>
        </section>
      </main>
    );
  }

  const widgetType = (widget: Dashboard["widgets"][number]) =>
    widget.type ?? widget.widget_type;
  const profile = dashboard.dataset.profile;
  const context = dashboard.analysis_context;
  const filters = (context?.filters ?? []).slice(0, 8);
  const kpis = dashboard.widgets.filter((widget) => widgetType(widget) === "kpi");
  const charts = dashboard.widgets.filter((widget) =>
    ["bar", "line", "drilldown_bar", "chart"].includes(String(widgetType(widget)))
  );
  const files = (context?.files ?? []).slice(0, 6);
  const missingValues = profile.column_profiles.reduce(
    (total, column) => total + column.missing_count,
    0
  );

  const updateFilter = (key: string, value: string) => {
    setSelectedFilters((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const selectedValueForColumn = (column: unknown) => {
    if (!column) {
      return "";
    }

    const suffix = `:${String(column)}`;
    const entry = Object.entries(selectedFilters).find(([key, value]) =>
      key.endsWith(suffix) && Boolean(value)
    );

    return entry?.[1] ?? "";
  };

  const widgetItems = (widget: Dashboard["widgets"][number]): ChartItem[] => {
    const config = widget.config as {
      items?: unknown;
      items_by_parent?: Record<string, unknown>;
      parent_column?: unknown;
    };
    const selectedParent = selectedValueForColumn(config.parent_column);
    const rawItems =
      selectedParent && config.items_by_parent?.[selectedParent]
        ? config.items_by_parent[selectedParent]
        : config.items;

    if (!Array.isArray(rawItems)) {
      return [];
    }

    return rawItems
      .map((item) => {
        if (!item || typeof item !== "object") {
          return null;
        }

        const typedItem = item as { label?: unknown; value?: unknown };
        const value = Number(typedItem.value ?? 0);

        return {
          label: String(typedItem.label ?? "-"),
          value: Number.isFinite(value) ? value : 0,
        };
      })
      .filter((item): item is ChartItem => item !== null);
  };

  const formatValue = (widget: Dashboard["widgets"][number], value: number) => {
    if (widget.config.value_format === "currency") {
      return value.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
        maximumFractionDigits: 0,
      });
    }

    return value.toLocaleString("pt-BR");
  };

  const formatKpiValue = (value: unknown) =>
    typeof value === "number" ? value.toLocaleString("pt-BR") : String(value ?? "-");

  return (
    <main className={styles.shell}>
      <section className={styles.dashboard}>
        <header className={styles.topBar}>
          <div className={styles.titleGroup}>
            <div className={styles.iconBox}>📈</div>
            <div>
              <h1 className={styles.title}>{dashboard.title}</h1>
              <p className={styles.subtitle}>
                Dashboard automático baseado nos arquivos enviados
              </p>
            </div>
          </div>
          <button className={styles.actionButton} type="button">
            Atualizar análise
          </button>
        </header>

        {context && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2>Objetivo detectado</h2>
                <p className={styles.muted}>Filtros e gráficos foram montados a partir do pedido informado.</p>
              </div>
              <div className={styles.badgeRow}>
                {context.intent.labels.map((label) => (
                  <span className={styles.badge} key={label}>{label}</span>
                ))}
              </div>
            </div>

            {filters.length > 0 && (
              <div className={styles.filters}>
                {filters.map((filter) => {
                  const key = `${filter.filename}:${filter.column}`;
                  const options =
                    filter.options.length > 0
                      ? filter.options
                      : filter.role === "date"
                        ? ["Dia", "Mês", "Ano"]
                        : [];

                  return (
                    <div className={styles.filterCard} key={key}>
                      <label htmlFor={key}>{filter.label}</label>
                      <select
                        id={key}
                        className={styles.select}
                        value={selectedFilters[key] ?? ""}
                        onChange={(event) => updateFilter(key, event.target.value)}
                      >
                        <option value="">Todos</option>
                        {options.map((option) => (
                          <option key={option} value={option}>{option}</option>
                        ))}
                      </select>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

        <section className={styles.summary}>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Linhas analisadas</span>
            <span className={styles.metricValue}>{profile.rows.toLocaleString("pt-BR")}</span>
          </div>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Colunas detectadas</span>
            <span className={styles.metricValue}>{profile.columns.toLocaleString("pt-BR")}</span>
          </div>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>Valores ausentes</span>
            <span className={styles.metricValue}>{missingValues.toLocaleString("pt-BR")}</span>
          </div>
        </section>

        <section className={styles.contentGrid}>
          <div className={styles.metricList}>
            {kpis.map((widget, index) => (
              <div className={styles.metricCard} key={widget.id}>
                <span className={styles.metricLabel}>{widget.title}</span>
                <span className={styles.metricValue}>{formatKpiValue(widget.config.value)}</span>
                <div className={styles.progressTrack}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${Math.min(95, 45 + index * 12)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className={styles.charts}>
            {charts.map((widget) => {
              const items = widgetItems(widget);
              const maxValue = Math.max(...items.map((item) => item.value), 1);
              const parentColumn = String(widget.config.parent_column ?? "");
              const selectedParent = selectedValueForColumn(parentColumn);

              return (
                <article className={styles.chartCard} key={widget.id}>
                  <div className={styles.sectionHeader}>
                    <div>
                      <h3>{widget.title}</h3>
                      <p className={styles.muted}>
                        {selectedParent
                          ? `Filtrado por ${parentColumn}: ${selectedParent}`
                          : String(widget.config.description ?? "")}
                      </p>
                    </div>
                    <span className={styles.badge}>Gráfico</span>
                  </div>

                  {items.length > 0 ? (
                    items.map((item) => (
                      <div className={styles.barRow} key={`${widget.id}-${item.label}`}>
                        <div className={styles.barTop}>
                          <span className={styles.barLabel}>{item.label}</span>
                          <span className={styles.barValue}>{formatValue(widget, item.value)}</span>
                        </div>
                        <div className={styles.barTrack}>
                          <div
                            className={styles.barFill}
                            style={{ width: `${Math.max((item.value / maxValue) * 100, 4)}%` }}
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className={styles.muted}>Sem dados para este filtro.</p>
                  )}
                </article>
              );
            })}
          </div>
        </section>

        {files.length > 0 && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h2>Arquivos usados</h2>
                <p className={styles.muted}>Resumo simples do papel provável de cada arquivo.</p>
              </div>
            </div>
            <div className={styles.filesGrid}>
              {files.map((file) => (
                <div className={styles.fileCard} key={file.filename}>
                  <span className={styles.badge}>{file.role_labels[0] ?? "Dados"}</span>
                  <h3>{file.filename}</h3>
                  <p className={styles.muted}>
                    {Number(file.rows ?? 0).toLocaleString("pt-BR")} linhas • {Number(file.columns ?? 0).toLocaleString("pt-BR")} colunas
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}
      </section>
    </main>
  );
}
