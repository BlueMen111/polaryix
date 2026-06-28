"use client";

import { useState } from "react";
import { activatePremiumPlan } from "@/lib/api";
import styles from "./page.module.css";

type Billing = "annual" | "monthly";

const plans = {
  annual: [
    {
      id: "basic-annual",
      name: "Basic Anual",
      price: 4.99,
      badge: "Economize mais",
      features: ["300 MB tamanho máximo de ficheiro", "1000 créditos de conversão por mês", "30 conversões simultâneas", "Alta prioridade"],
    },
    {
      id: "pro-annual",
      name: "Pro Premium Anual",
      price: 12.99,
      badge: "Mais popular",
      features: ["1 GB tamanho máximo de ficheiro", "3000 créditos de conversão por mês", "600 conversões simultâneas", "Prioridade premium"],
    },
  ],
  monthly: [
    {
      id: "basic-monthly",
      name: "Basic Mensal",
      price: 9.99,
      badge: "Flexível",
      features: ["300 MB tamanho máximo de ficheiro", "1000 créditos de conversão por mês", "30 conversões simultâneas", "Alta prioridade"],
    },
    {
      id: "pro-monthly",
      name: "Pro Premium Mensal",
      price: 18.99,
      badge: "Máximo poder",
      features: ["1 GB tamanho máximo de ficheiro", "3000 créditos de conversão por mês", "600 conversões simultâneas", "Prioridade premium"],
    },
  ],
} satisfies Record<Billing, Array<{ id: string; name: string; price: number; badge: string; features: string[] }>>;

export default function PremiumPage() {
  const [billing, setBilling] = useState<Billing>("annual");
  const [status, setStatus] = useState("");
  const [isActivating, setIsActivating] = useState("");
  const visiblePlans = plans[billing];

  async function selectPlan(planId: string) {
    const token = window.localStorage.getItem("polaryix:auth-token");
    if (!token) {
      window.location.href = `/login?next=/premium&plan=${planId}`;
      return;
    }

    const planType = planId.includes("pro") ? "pro" : "basic";
    setIsActivating(planId);
    setStatus("Ativando plano...");

    try {
      await activatePremiumPlan({ plan: planType, billing });
      setStatus("Plano ativado. Redirecionando...");
      window.location.href = "/";
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel ativar o plano.");
    } finally {
      setIsActivating("");
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p>Polaryix Pass</p>
        <h1>Escolha o plano certo</h1>
        <span>Créditos mensais, prioridade alta e conversões simultâneas para acelerar seu fluxo.</span>
      </section>

      <section className={styles.billingSwitch} aria-label="Selecionar cobrança">
        <button type="button" className={billing === "monthly" ? styles.active : undefined} onClick={() => setBilling("monthly")}>
          Mensal
        </button>
        <button type="button" className={billing === "annual" ? styles.active : undefined} onClick={() => setBilling("annual")}>
          Anual
        </button>
      </section>
      <p className={styles.savings}>Economize até 50% com planos anuais.</p>

      <section className={styles.planGrid}>
        {visiblePlans.map((plan) => (
          <article key={plan.id} className={plan.id.includes("pro") ? styles.featuredPlan : styles.plan}>
            <div className={styles.planTop}>
              <span>{plan.badge}</span>
              <h2>{plan.name}</h2>
              <div className={styles.price}>
                <small>R$</small>
                <strong>{plan.price}</strong>
                <em>/ mês</em>
              </div>
            </div>

            <ul>
              {plan.features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>

            <button type="button" onClick={() => selectPlan(plan.id)} disabled={isActivating === plan.id}>
              {isActivating === plan.id ? "Ativando..." : "Continuar"}
            </button>
          </article>
        ))}
      </section>

      {status ? <p className={styles.savings}>{status}</p> : null}

      <section className={styles.freeNote}>
        <strong>Plano gratuito</strong>
        <p>Visitantes e usuários free têm 30 créditos por dia. Cada conversão de imagem, documento, áudio ou download por link consome 1 crédito do mesmo saldo.</p>
      </section>
    </main>
  );
}
