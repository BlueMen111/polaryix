"use client";

import { useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { activatePremiumPlan } from "@/lib/api";
import { formatPriceByLanguage } from "@/lib/currency";
import styles from "./page.module.css";

type Billing = "annual" | "monthly";
type PlanType = "basic" | "pro";
type PlanOption = {
  id: string;
  plan: PlanType;
  billing: Billing;
  nameKey: string;
  price: number;
  badgeKey: string;
  featureKeys: string[];
};

const basicFeatureKeys = [
  "premium.basicFeature1",
  "premium.basicFeature2",
  "premium.basicFeature3",
  "premium.basicFeature4",
  "premium.basicFeature5",
  "premium.basicFeature6",
  "premium.basicFeature7",
];

const proFeatureKeys = [
  "premium.proFeature1",
  "premium.proFeature2",
  "premium.proFeature3",
  "premium.proFeature4",
  "premium.proFeature5",
  "premium.proFeature6",
  "premium.proFeature7",
];

const plans = {
  annual: [
    { id: "basic-annual", plan: "basic", billing: "annual", nameKey: "premium.basicAnnual", price: 4.99, badgeKey: "premium.saveMore", featureKeys: basicFeatureKeys },
    { id: "pro-annual", plan: "pro", billing: "annual", nameKey: "premium.proAnnual", price: 12.99, badgeKey: "premium.popular", featureKeys: proFeatureKeys },
  ],
  monthly: [
    { id: "basic-monthly", plan: "basic", billing: "monthly", nameKey: "premium.basicMonthly", price: 9.99, badgeKey: "premium.flexible", featureKeys: basicFeatureKeys },
    { id: "pro-monthly", plan: "pro", billing: "monthly", nameKey: "premium.proMonthly", price: 18.99, badgeKey: "premium.maxPower", featureKeys: proFeatureKeys },
  ],
} satisfies Record<Billing, PlanOption[]>;

export default function PremiumPage() {
  const { language, t } = useLanguage();
  const [billing, setBilling] = useState<Billing>("annual");
  const [status, setStatus] = useState("");
  const [isActivating, setIsActivating] = useState("");
  const visiblePlans = plans[billing];

  async function selectPlan(plan: PlanOption) {
    const token = window.localStorage.getItem("polaryix:auth-token");
    if (!token) {
      window.location.href = `/login?next=/premium&plan=${plan.id}`;
      return;
    }

    setIsActivating(plan.id);
    setStatus("Ativando plano...");

    try {
      const result = await activatePremiumPlan({ plan: plan.plan, billing: plan.billing });
      setStatus(`${result.user.plan === "pro" ? "Pro Premium" : "Basic"} ativado. Redirecionando...`);
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
        <h1>{t("premium.title")}</h1>
        <span>{t("premium.subtitle")}</span>
      </section>

      <section className={styles.billingSwitch} aria-label="Selecionar cobranca">
        <button type="button" className={billing === "monthly" ? styles.active : undefined} onClick={() => setBilling("monthly")}>
          {t("premium.monthly")}
        </button>
        <button type="button" className={billing === "annual" ? styles.active : undefined} onClick={() => setBilling("annual")}>
          {t("premium.annual")}
        </button>
      </section>
      <p className={styles.savings}>{t("premium.savings")}</p>

      <section className={styles.planGrid}>
        {visiblePlans.map((plan) => (
          <article key={plan.id} className={plan.id.includes("pro") ? styles.featuredPlan : styles.plan}>
            <div className={styles.planTop}>
              <span>{t(plan.badgeKey)}</span>
              <h2>{t(plan.nameKey)}</h2>
              <div className={styles.price}>
                <strong>{formatPriceByLanguage(plan.price, language)}</strong>
                <em>{t("premium.perMonth")}</em>
              </div>
            </div>

            <ul>
              {plan.featureKeys.map((featureKey) => (
                <li key={featureKey}>{t(featureKey)}</li>
              ))}
            </ul>

            <button type="button" onClick={() => selectPlan(plan)} disabled={isActivating === plan.id}>
              {isActivating === plan.id ? t("premium.activating") : t("premium.continue")}
            </button>
          </article>
        ))}
      </section>

      {status ? <p className={styles.savings}>{status}</p> : null}

      <section className={styles.freeNote}>
        <strong>{t("premium.freePlan")}</strong>
        <p>{t("premium.freeNote")}</p>
      </section>
    </main>
  );
}
