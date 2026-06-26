"use client";

import { useState } from "react";
import styles from "./DashboardShowcase.module.css";

const dashboardExamples = [
  {
    id: 1,
    title: "Dashboard Comercial",
    category: "Vendas",
    description: "Acompanhe vendas, ticket médio e desempenho de vendedores",
    icon: "📈",
    color: "#4a90e2",
    metrics: ["Receita Total", "Vendas por Região", "Top Produtos", "Conversão"],
  },
  {
    id: 2,
    title: "Dashboard Financeiro",
    category: "Financeiro",
    description: "Controle financeiro completo com DRE e fluxo de caixa",
    icon: "💰",
    color: "#27ae60",
    metrics: ["Fluxo de Caixa", "Despesas", "Lucratividade", "Margem"],
  },
  {
    id: 3,
    title: "Dashboard de RH",
    category: "Recursos Humanos",
    description: "Análise de colaboradores, turnover e satisfação",
    icon: "👥",
    color: "#9b59b6",
    metrics: ["Turnover", "Satisfação", "Treinamentos", "Performance"],
  },
  {
    id: 4,
    title: "Dashboard de Marketing",
    category: "Marketing",
    description: "Métricas de campanhas, ROI e engajamento",
    icon: "📊",
    color: "#e74c3c",
    metrics: ["ROI", "Conversões", "Engajamento", "Alcance"],
  },
  {
    id: 5,
    title: "Dashboard Operacional",
    category: "Operacional",
    description: "Monitoramento de processos e eficiência",
    icon: "⚙️",
    color: "#f39c12",
    metrics: ["Eficiência", "Tempo de Ciclo", "Qualidade", "Custos"],
  },
  {
    id: 6,
    title: "Dashboard de Logística",
    category: "Logística",
    description: "Rastreamento de entregas e otimização de rotas",
    icon: "🚚",
    color: "#1abc9c",
    metrics: ["Entregas", "Tempo Médio", "Custos", "Rastreamento"],
  },
];

export function DashboardShowcase() {
  const [selectedDashboard, setSelectedDashboard] = useState(dashboardExamples[0]);

  return (
    <div className={styles.showcase}>
      <div className={styles.grid}>
        {dashboardExamples.map((dashboard) => (
          <div
            key={dashboard.id}
            className={`${styles.card} ${
              selectedDashboard.id === dashboard.id ? styles.active : ""
            }`}
            onClick={() => setSelectedDashboard(dashboard)}
            style={{
              "--accent-color": dashboard.color,
            } as React.CSSProperties}
          >
            <div className={styles.cardIcon}>{dashboard.icon}</div>
            <h3 className={styles.cardTitle}>{dashboard.title}</h3>
            <p className={styles.cardCategory}>{dashboard.category}</p>
            <p className={styles.cardDescription}>{dashboard.description}</p>
            <div className={styles.cardArrow}>→</div>
          </div>
        ))}
      </div>

      <div className={styles.preview}>
        <div className={styles.previewHeader}>
          <div className={styles.previewTitle}>
            <span className={styles.previewIcon}>{selectedDashboard.icon}</span>
            <div>
              <h3>{selectedDashboard.title}</h3>
              <p>{selectedDashboard.category}</p>
            </div>
          </div>
          <button className={styles.tryButton}>
            🚀 Testar Este Modelo
          </button>
        </div>

        <div className={styles.previewContent}>
          <div className={styles.metricsGrid}>
            {selectedDashboard.metrics.map((metric, index) => (
              <div key={index} className={styles.metricCard}>
                <div className={styles.metricIcon}>
                  {selectedDashboard.icon}
                </div>
                <div className={styles.metricInfo}>
                  <h4>{metric}</h4>
                  <div className={styles.metricBar}>
                    <div 
                      className={styles.metricProgress}
                      style={{
                        width: `${Math.random() * 40 + 60}%`,
                        backgroundColor: selectedDashboard.color,
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className={styles.chartPreview}>
            <div className={styles.chartHeader}>
              <h4>Visualização Interativa</h4>
              <div className={styles.chartTabs}>
                <span className={styles.chartTab}>Gráfico</span>
                <span className={styles.chartTab}>Tabela</span>
                <span className={styles.chartTab}>Exportar</span>
              </div>
            </div>
            <div className={styles.chartArea}>
              <div className={styles.barChart}>
                {[65, 85, 45, 90, 70, 80, 55].map((height, i) => (
                  <div
                    key={i}
                    className={styles.bar}
                    style={{
                      height: `${height}%`,
                      backgroundColor: selectedDashboard.color,
                      animationDelay: `${i * 0.1}s`,
                    }}
                  />
                ))}
              </div>
              <div className={styles.chartLabels}>
                {["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul"].map(
                  (month) => (
                    <span key={month}>{month}</span>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}