"use client";

import { useState } from "react";
import { createPayment, type PaymentProvider } from "@/lib/api";
import styles from "../payments.module.css";

const suggestions = [5, 10, 25, 50];

export default function DonatePage() {
  const [amount, setAmount] = useState(10);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState("");

  async function donate(provider: PaymentProvider, method: "checkout" | "pix" = "checkout") {
    setLoading(`${provider}-${method}`);
    setMessage("Criando doacao segura...");
    try {
      const { payment } = await createPayment({ provider, type: "donation", amount, currency: "BRL", method });
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
        <p className={styles.eyebrow}>Apoie o PolarYix</p>
        <h1>Faca uma doacao</h1>
        <p>Sua doacao ajuda a manter conversoes, ferramentas de imagem e infraestrutura do projeto.</p>
      </section>
      <section className={styles.panel}>
        <h2>Valor</h2>
        <div className={styles.statusActions}>
          {suggestions.map((value) => (
            <button key={value} className={amount === value ? styles.button : styles.ghostButton} type="button" onClick={() => setAmount(value)}>R$ {value}</button>
          ))}
        </div>
        <input className={styles.amountInput} min={1} max={10000} type="number" value={amount} onChange={(event) => setAmount(Number(event.target.value))} />
        <div className={styles.statusActions}>
          <button className={styles.button} disabled={loading === "mercadopago-checkout"} type="button" onClick={() => donate("mercadopago")}>Mercado Pago</button>
          <button className={styles.ghostButton} disabled={loading === "mercadopago-pix"} type="button" onClick={() => donate("mercadopago", "pix")}>PIX</button>
          <button className={styles.ghostButton} disabled={loading === "paypal-checkout"} type="button" onClick={() => donate("paypal")}>PayPal</button>
        </div>
        {message ? <p className={styles.message}>{message}</p> : null}
      </section>
      <section className={styles.security}>
        <strong>Pagamento seguro</strong>
        <p>Compra protegida e processada por Mercado Pago e PayPal. Nenhum dado de cartao fica salvo no PolarYix.</p>
        <div className={styles.badges}><span>Secure Checkout</span><span>SSL Secure</span><span>Protected Payment</span></div>
      </section>
    </main>
  );
}
