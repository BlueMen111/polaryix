"use client";

import { useState } from "react";
import { createPayment, type PaymentProvider } from "@/lib/api";
import styles from "./page.module.css";

const suggestions = [5, 10, 25, 50];

export default function DonatePage() {
  const [amount, setAmount] = useState(10);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState("");

  async function donate(provider: PaymentProvider, method: "checkout" | "pix" = "checkout") {
    const safeAmount = Math.max(1, Math.min(Number(amount) || 10, 10000));
    setAmount(safeAmount);
    setLoading(`${provider}-${method}`);
    setMessage("Criando doacao segura...");

    try {
      const { payment } = await createPayment({ provider, type: "donation", amount: safeAmount, currency: "BRL", method });
      window.localStorage.setItem("polaryix:last-payment-id", payment.id);
      window.location.href = payment.checkout_url || `/payment/pending?payment_id=${payment.id}`;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nao foi possivel iniciar a doacao.");
    } finally {
      setLoading("");
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <p>Apoie o PolarYix</p>
        <h1>Faca uma doacao</h1>
        <span>Sua doacao ajuda a manter conversoes, ferramentas de imagem e infraestrutura do projeto.</span>
      </section>

      <section className={styles.panel}>
        <h2>Valor</h2>
        <div className={styles.suggestions}>
          {suggestions.map((value) => (
            <button key={value} className={amount === value ? styles.active : undefined} type="button" onClick={() => setAmount(value)}>
              R$ {value}
            </button>
          ))}
        </div>

        <label className={styles.amountField}>
          <span>Valor personalizado</span>
          <input min={1} max={10000} type="number" value={amount} onChange={(event) => setAmount(Number(event.target.value))} />
        </label>

        <div className={styles.actions}>
          <button disabled={loading === "mercadopago-checkout"} type="button" onClick={() => donate("mercadopago")}>Mercado Pago</button>
          <button disabled={loading === "mercadopago-pix"} type="button" onClick={() => donate("mercadopago", "pix")}>PIX</button>
          <button disabled={loading === "paypal-checkout"} type="button" onClick={() => donate("paypal")}>PayPal</button>
        </div>

        {message ? <p className={styles.message}>{message}</p> : null}
      </section>

      <section className={styles.security}>
        <strong>Pagamento seguro</strong>
        <p>Compra protegida e processada por Mercado Pago e PayPal. Nenhum dado de cartao fica salvo no PolarYix.</p>
        <div>
          <span>Secure Checkout</span>
          <span>SSL Secure</span>
          <span>Protected Payment</span>
        </div>
      </section>
    </main>
  );
}
