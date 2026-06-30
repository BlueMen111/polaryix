"use client";

import { useState } from "react";
import { createPayment, type PaymentProvider } from "@/lib/api";
import { formatPriceByLanguage } from "@/lib/currency";
import { useLanguage } from "@/i18n/LanguageProvider";
import styles from "../payments.module.css";

type Billing = "annual" | "monthly";
type PlanType = "basic" | "pro";

const plans: Record<Billing, Array<{ plan: PlanType; name: string; price: number; features: string[] }>> = {
  annual: [
    { plan: "basic", name: "Basic Anual", price: 59.88, features: ["1000 creditos por mes", "Fila prioritaria", "Workspace Premium", "Resultado sem marca d'agua"] },
    { plan: "pro", name: "Pro Anual", price: 155.88, features: ["3000 creditos por mes", "Fila prioritaria maxima", "Arquivos ate 1 GB", "Upscaling 4x sem marca d'agua"] },
  ],
  monthly: [
    { plan: "basic", name: "Basic Mensal", price: 9.99, features: ["1000 creditos", "Fila prioritaria", "Workspace Premium", "Resultado sem marca d'agua"] },
    { plan: "pro", name: "Pro Mensal", price: 18.99, features: ["3000 creditos", "Fila prioritaria maxima", "Arquivos ate 1 GB", "Upscaling 4x sem marca d'agua"] },
  ],
};

export default function PremiumPage() {
  const { language } = useLanguage();
  const [billing, setBilling] = useState<Billing>("annual");
  const [loading, setLoading] = useState("");
  const [message, setMessage] = useState("");

  async function startCheckout(plan: PlanType, provider: PaymentProvider, method: "checkout" | "pix" = "checkout") {
    const token = window.localStorage.getItem("polaryix:auth-token");
    if (!token) {
      window.location.href = `/login?next=/premium`;
      return;
    }

    const key = `${plan}-${provider}-${method}`;
    setLoading(key);
    setMessage("Criando checkout seguro...");
    try {
      const { payment } = await createPayment({ provider, type: "premium", plan, billing, method });
      window.localStorage.setItem("polaryix:last-payment-id", payment.id);
      if (payment.checkout_url) {
        window.location.href = payment.checkout_url;
        return;
      }
      window.location.href = `/payment/pending?payment_id=${payment.id}`;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nao foi possivel iniciar o pagamento.");
    } finally {
      setLoading("");
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Polaryix Premium</p>
        <h1>Escolha seu plano</h1>
        <p>Compra segura por Mercado Pago, PIX ou PayPal. O PolarYix nao armazena dados do seu cartao.</p>
      </section>

      <section className={styles.statusActions} aria-label="Selecionar cobranca">
        <button className={billing === "monthly" ? styles.button : styles.ghostButton} type="button" onClick={() => setBilling("monthly")}>Mensal</button>
        <button className={billing === "annual" ? styles.button : styles.ghostButton} type="button" onClick={() => setBilling("annual")}>Anual</button>
      </section>

      {message ? <p className={styles.message}>{message}</p> : null}

      <section className={styles.grid}>
        {plans[billing].map((item) => (
          <article className={styles.panel} key={`${item.plan}-${billing}`}>
            <p className={styles.eyebrow}>{item.plan === "pro" ? "Mais completo" : "Essencial"}</p>
            <h2>{item.name}</h2>
            <div className={styles.price}>
              <strong>{formatPriceByLanguage(item.price, language)}</strong>
              <span>{billing === "annual" ? "/ ano" : "/ mes"}</span>
            </div>
            <ul className={styles.features}>
              {item.features.map((feature) => <li key={feature}>{feature}</li>)}
            </ul>
            <div className={styles.actions}>
              <button className={styles.button} disabled={loading === `${item.plan}-mercadopago-checkout`} type="button" onClick={() => startCheckout(item.plan, "mercadopago")}>Mercado Pago</button>
              <button className={styles.ghostButton} disabled={loading === `${item.plan}-mercadopago-pix`} type="button" onClick={() => startCheckout(item.plan, "mercadopago", "pix")}>PIX</button>
              <button className={styles.ghostButton} disabled={loading === `${item.plan}-paypal-checkout`} type="button" onClick={() => startCheckout(item.plan, "paypal")}>PayPal</button>
            </div>
          </article>
        ))}
      </section>

      <section className={styles.security}>
        <strong>Pagamento seguro</strong>
        <p>Compra protegida, processada por Mercado Pago e PayPal. Conexao segura via HTTPS. O PolarYix nunca salva numero do cartao, CVV ou validade.</p>
        <div className={styles.badges}>
          <span>Secure Checkout</span>
          <span>SSL Secure</span>
          <span>Protected Payment</span>
        </div>
      </section>
    </main>
  );
}
