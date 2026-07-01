"use client";

import { useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { createPayment, type PaymentProvider } from "@/lib/api";
import { formatPriceByLanguage } from "@/lib/currency";
import styles from "./page.module.css";

type Billing = "annual" | "monthly";
type PlanType = "basic" | "pro";
type PlanOption = {
  id: string;
  plan: PlanType;
  billing: Billing;
  name: string;
  price: number;
  badge: string;
  features: string[];
};

const basicFeatures = [
  "1000 creditos por mes",
  "Fila prioritaria",
  "Workspace Premium",
  "Resultado sem marca d'agua",
  "Otimizar imagem sem marca d'agua",
  "Remover fundo sem marca d'agua",
  "Arquivos maiores no Workspace",
];

const proFeatures = [
  "3000 creditos por mes",
  "Fila prioritaria maxima",
  "Arquivos ate 1 GB",
  "Upscaling 4x sem marca d'agua",
  "Downloads HD/4K quando disponiveis",
  "Ferramentas avancadas de imagem",
  "Maior limite de armazenamento",
];

const plans: Record<Billing, PlanOption[]> = {
  annual: [
    { id: "basic-annual", plan: "basic", billing: "annual", name: "Basic Anual", price: 4.99, badge: "Economize mais", features: basicFeatures },
    { id: "pro-annual", plan: "pro", billing: "annual", name: "Pro Anual", price: 12.99, badge: "Mais popular", features: proFeatures },
  ],
  monthly: [
    { id: "basic-monthly", plan: "basic", billing: "monthly", name: "Basic Mensal", price: 9.99, badge: "Essencial", features: basicFeatures },
    { id: "pro-monthly", plan: "pro", billing: "monthly", name: "Pro Mensal", price: 18.99, badge: "Maximo poder", features: proFeatures },
  ],
};

export default function PremiumPage() {
  const { language } = useLanguage();
  const [billing, setBilling] = useState<Billing>("annual");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState("");
  const [selectedPlanId, setSelectedPlanId] = useState("");

  async function startCheckout(plan: PlanOption, provider: PaymentProvider, method: "checkout" | "pix" = "checkout") {
    const token = window.localStorage.getItem("polaryix:auth-token");
    if (!token) {
      window.location.href = `/login?next=/premium&plan=${plan.id}`;
      return;
    }

    const key = `${plan.id}-${provider}-${method}`;
    setLoading(key);
    setStatus("Criando checkout seguro...");

    try {
      const { payment } = await createPayment({ provider, type: "premium", plan: plan.plan, billing: plan.billing, method });
      window.location.href = payment.checkout_url || `/payment/pending?payment_id=${payment.id}`;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Nao foi possivel iniciar o pagamento.");
    } finally {
      setLoading("");
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p>Polaryix Pass</p>
        <h1>Escolha seu plano</h1>
        <span>Compra segura por Mercado Pago, PIX ou PayPal. O PolarYix nao armazena dados do seu cartao.</span>
      </section>

      <section className={styles.billingSwitch} aria-label="Selecionar cobranca">
        <button type="button" className={billing === "monthly" ? styles.active : undefined} onClick={() => setBilling("monthly")}>
          Mensal
        </button>
        <button type="button" className={billing === "annual" ? styles.active : undefined} onClick={() => setBilling("annual")}>
          Anual
        </button>
      </section>
      <p className={styles.savings}>
        {billing === "annual"
          ? "Plano anual com valor mensal reduzido. O pagamento e apresentado por mes."
          : "Cobranca mensal flexivel para comecar sem compromisso anual."}
      </p>

      <section className={styles.planGrid}>
        {plans[billing].map((plan) => (
          <article key={plan.id} className={plan.plan === "pro" ? styles.featuredPlan : styles.plan}>
            <div className={styles.planTop}>
              <span>{plan.badge}</span>
              <h2>{plan.name}</h2>
              <div className={styles.price}>
                <strong>{formatPriceByLanguage(plan.price, language)}</strong>
                <em>/ mes</em>
              </div>
              {billing === "annual" ? <small className={styles.billingNote}>Valor mensal no plano anual.</small> : null}
            </div>

            <ul>
              {plan.features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>

            <div className={styles.paymentActions}>
              <button
                className={styles.continueButton}
                type="button"
                onClick={() => setSelectedPlanId((current) => (current === plan.id ? "" : plan.id))}
                aria-expanded={selectedPlanId === plan.id}
              >
                Continuar
              </button>

              {selectedPlanId === plan.id ? (
                <div className={styles.providerChoices} aria-label={`Opcoes de pagamento para ${plan.name}`}>
                  <button type="button" onClick={() => startCheckout(plan, "mercadopago")} disabled={loading === `${plan.id}-mercadopago-checkout`}>
                    Mercado Pago
                  </button>
                  <button type="button" onClick={() => startCheckout(plan, "mercadopago", "pix")} disabled={loading === `${plan.id}-mercadopago-pix`}>
                    PIX
                  </button>
                  <button type="button" onClick={() => startCheckout(plan, "paypal")} disabled={loading === `${plan.id}-paypal-checkout`}>
                    PayPal
                  </button>
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </section>

      {status ? <p className={styles.savings}>{status}</p> : null}

      <section className={styles.freeNote}>
        <strong>Pagamento seguro</strong>
        <p>Compra protegida e processada por Mercado Pago e PayPal. Conexao segura via HTTPS. O PolarYix nunca salva numero do cartao, CVV ou validade.</p>
        <div className={styles.securityBadges}>
          <span>Secure Checkout</span>
          <span>SSL Secure</span>
          <span>Protected Payment</span>
        </div>
      </section>
    </main>
  );
}
