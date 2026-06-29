"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { getDashboard, type DashboardSummary, type WorkspaceFile } from "@/lib/api";
import styles from "./page.module.css";

function formatBytes(value: number) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value: string | null | undefined, locale: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function statusLabel(status: WorkspaceFile["status"], t: (key: string) => string) {
  const labels: Record<WorkspaceFile["status"], string> = {
    queued: t("common.queued"),
    processing: t("common.processing"),
    completed: t("common.completed"),
    failed: t("common.failed"),
    expired: t("common.expired"),
    deleted: t("common.deleted"),
  };
  return labels[status] ?? status;
}

export default function DashboardPage() {
  const { language, t } = useLanguage();
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [status, setStatus] = useState(t("dashboard.loading"));

  useEffect(() => {
    if (!window.localStorage.getItem("polaryix:auth-token")) {
      window.location.href = "/login";
      return;
    }

    getDashboard()
      .then((data) => {
        setDashboard(data);
        setStatus("");
      })
      .catch((error) => setStatus(error instanceof Error ? error.message : t("dashboard.loadError")));
  }, [t]);

  if (!dashboard) {
    return (
      <main className={styles.page}>
        <section className={styles.panel}>
          <p className={styles.message}>{status}</p>
        </section>
      </main>
    );
  }

  const storageText = `${formatBytes(dashboard.storage.used)} de ${formatBytes(dashboard.storage.limit)}`;

  return (
    <main className={styles.page}>
      <section className={styles.heroPanel}>
        <div>
          <p className={styles.eyebrow}>{t("dashboard.eyebrow")}</p>
          <h1>{t("dashboard.greeting", { name: dashboard.user.name })}</h1>
          <p>{t("dashboard.subtitle")}</p>
        </div>
        <Link href="/workspace">{t("dashboard.openWorkspace")}</Link>
      </section>

      <section className={styles.statsGrid}>
        <Stat label={t("dashboard.availableCredits")} value={String(dashboard.credits)} detail={t("dashboard.accountTokens")} />
        <Stat
          label={t("dashboard.currentPlan")}
          value={dashboard.plan === "free" ? "Free" : dashboard.plan.toUpperCase()}
          detail={dashboard.user.is_premium ? t("dashboard.priorityActive") : t("dashboard.upgradeLimits")}
        />
        <Stat label={t("dashboard.storage")} value={storageText} detail={t("dashboard.used", { percent: dashboard.storage.percent })} />
        <Stat label={t("dashboard.workspaceFiles")} value={String(dashboard.workspace_count)} detail={t("dashboard.favoritesCount", { count: dashboard.favorite_count })} />
      </section>

      <section className={styles.quickPanel}>
        <div>
          <p className={styles.eyebrow}>{t("dashboard.quickActions")}</p>
          <h2>{t("dashboard.startTask")}</h2>
        </div>
        <div className={styles.quickActions}>
          <Link href="/#converter">{t("dashboard.newConversion")}</Link>
          <Link href="/image/remove-background">{t("common.removeBackground")}</Link>
          <Link href="/image/optimize">{t("image.optimize.title")}</Link>
          <Link href="/image/upscale">{t("common.upscale")}</Link>
        </div>
      </section>

      <section className={styles.contentGrid}>
        <ActivityList title={t("dashboard.recentActivity")} files={dashboard.recent_jobs} language={language} t={t} />
        <ActivityList title={t("dashboard.favorites")} files={dashboard.favorite_files} empty={t("dashboard.noFavorites")} language={language} t={t} />
      </section>
    </main>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className={styles.statCard}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function ActivityList({
  title,
  files,
  empty,
  language,
  t,
}: {
  title: string;
  files: WorkspaceFile[];
  empty?: string;
  language: string;
  t: (key: string) => string;
}) {
  return (
    <section className={styles.listPanel}>
      <div className={styles.listHeader}>
        <h2>{title}</h2>
        <Link href="/workspace">{t("common.viewAll")}</Link>
      </div>
      {files.length ? (
        <div className={styles.activityList}>
          {files.map((file) => (
            <article key={file.id}>
              <div>
                <strong>{file.original_filename}</strong>
                <span>{file.operation_type || file.target_format} - {formatDate(file.created_at, language)}</span>
              </div>
              <small className={styles[file.status]}>{statusLabel(file.status, t)}</small>
            </article>
          ))}
        </div>
      ) : (
        <p className={styles.message}>{empty ?? t("dashboard.noFiles")}</p>
      )}
    </section>
  );
}
