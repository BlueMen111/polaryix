"use client";

import { useState } from "react";
import { createPayment, type PaymentProvider } from "@/lib/api";
import styles from "../payments.module.css";

const packages = [
  { id: "starter", name: "Starter", credits: 250, price: "R$ 6,90" },
  { id: "creator", name: "Creator", credits: 750, price: "R$ 14,90" },
  { id: "studio", name: "Studio", credits: 1800, price: "R$ 29,90" },
] as const;

export default function CreditsPage() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState("");

  async function checkout(packageId: (typeof packages)[number]["id"], provider: PaymentProvider, method: "checkout" | "pix" = "checkout") {
    if (!window.localStorage.getItem("polaryix:auth-token")) {
      window.location.href = "/login?next=/credits";
      return;
    }
    setLoading(`${packageId}-${provider}-${method}`);
    setMessage("Preparando pagamento seguro...");
    try {
      const { payment } = await createPayment({ provider, type: "credits", creditsPackage: packageId, method });
      window.localStorage.setItem("polaryix:last-payment-id", payment.id);
      window.location.href = payment.checkout_url || `/payment/pending?payment_id=${payment.id}`;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nao foi possivel iniciar o pagamento.");
    } finally {
      setLoading("");
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Creditos PolarYix</p>
        <h1>Compre pacotes de tokens</h1>
        <p>Use seus creditos em conversoes, ferramentas de imagem e downloads Premium.</p>
      </section>
      {message ? <p className={styles.message}>{message}</p> : null}
      <section className={styles.threeGrid}>
        {packages.map((item) => (
          <article className={styles.panel} key={item.id}>
            <p className={styles.eyebrow}>{item.credits} tokens</p>
            <h2>{item.name}</h2>
            <div className={styles.price}><strong>{item.price}</strong></div>
            <ul className={styles.features}>
              <li>Entrega apos confirmacao do pagamento</li>
              <li>Compra protegida pelo provedor</li>
              <li>Sem dados de cartao no PolarYix</li>
            </ul>
            <div className={styles.actions}>
              <button className={styles.button} disabled={loading === `${item.id}-mercadopago-checkout`} type="button" onClick={() => checkout(item.id, "mercadopago")}>Mercado Pago</button>
              <button className={styles.ghostButton} disabled={loading === `${item.id}-mercadopago-pix`} type="button" onClick={() => checkout(item.id, "mercadopago", "pix")}>PIX</button>
              <button className={styles.ghostButton} disabled={loading === `${item.id}-paypal-checkout`} type="button" onClick={() => checkout(item.id, "paypal")}>PayPal</button>
            </div>
          </article>
        ))}
      </section>
      <section className={styles.security}>
        <strong>Pagamento seguro</strong>
        <p>Processado por Mercado Pago e PayPal. O PolarYix nao armazena dados do seu cartao.</p>
        <div className={styles.badges}><span>Secure Checkout</span><span>Protected Payment</span><span>SSL Secure</span></div>
      </section>
    </main>
  );
}
