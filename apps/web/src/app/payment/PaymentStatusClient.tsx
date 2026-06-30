"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { capturePayPalPayment, getPaymentStatus, sandboxApprovePayment, type PaymentRecord } from "@/lib/api";
import styles from "../payments.module.css";

export default function PaymentStatusClient({ mode }: { mode: "success" | "pending" | "cancelled" }) {
  const searchParams = useSearchParams();
  const paymentId = searchParams.get("payment_id") || "";
  const [payment, setPayment] = useState<PaymentRecord | null>(null);
  const [message, setMessage] = useState("Consultando pagamento...");

  useEffect(() => {
    let active = true;
    async function load() {
      if (!paymentId) {
        setMessage("Pagamento nao informado.");
        return;
      }
      try {
        if (mode === "success") {
          const current = await getPaymentStatus(paymentId);
          if (current.payment.provider === "paypal" && current.payment.status === "pending") {
            await capturePayPalPayment(paymentId).catch(() => current);
          }
        }
        const data = await getPaymentStatus(paymentId);
        if (!active) return;
        setPayment(data.payment);
        setMessage(statusMessage(data.payment.status));
      } catch (error) {
        if (active) setMessage(error instanceof Error ? error.message : "Nao foi possivel consultar o pagamento.");
      }
    }
    load();
    const interval = window.setInterval(load, mode === "pending" ? 5000 : 12000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [paymentId, mode]);

  async function approveSandbox() {
    if (!paymentId) return;
    setMessage("Simulando aprovacao sandbox...");
    try {
      const data = await sandboxApprovePayment(paymentId);
      setPayment(data.payment);
      setMessage(statusMessage(data.payment.status));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nao foi possivel aprovar no sandbox.");
    }
  }

  const title = mode === "success" ? "Pagamento recebido" : mode === "cancelled" ? "Pagamento cancelado" : "Aguardando pagamento";
  const sandbox = payment?.metadata?.sandbox_simulated === true;

  return (
    <main className={styles.page}>
      <section className={styles.statusPanel}>
        <p className={styles.eyebrow}>PolarYix Checkout</p>
        <h1>{title}</h1>
        <p>{message}</p>

        {payment ? (
          <div className={styles.qrBox}>
            <strong>Status: {payment.status}</strong>
            <p>Valor: {payment.currency} {Number(payment.amount).toFixed(2)}</p>
            {payment.qr_code_base64 ? <img alt="QR Code PIX" src={`data:image/png;base64,${payment.qr_code_base64}`} /> : null}
            {payment.qr_code ? (
              <>
                <p className={styles.qrCode}>{payment.qr_code}</p>
                <button className={styles.copyButton} type="button" onClick={() => navigator.clipboard.writeText(payment.qr_code || "")}>Copiar codigo PIX</button>
                <p>Apos o pagamento, a confirmacao pode levar alguns segundos.</p>
              </>
            ) : null}
          </div>
        ) : null}

        <div className={styles.statusActions}>
          {sandbox && payment?.status === "pending" ? <button className={styles.button} type="button" onClick={approveSandbox}>Aprovar sandbox</button> : null}
          <Link className={styles.ghostButton} href="/dashboard">Dashboard</Link>
          <Link className={styles.ghostButton} href="/premium">Premium</Link>
        </div>
      </section>
      <section className={styles.security}>
        <strong>Compra protegida</strong>
        <p>O PolarYix nao armazena numero de cartao, CVV ou validade. A confirmacao vem do provedor de pagamento.</p>
        <div className={styles.badges}><span>Secure Checkout</span><span>SSL Secure</span><span>Protected Payment</span></div>
      </section>
    </main>
  );
}

function statusMessage(status: PaymentRecord["status"]) {
  if (status === "approved") return "Pagamento aprovado. Beneficio liberado na sua conta.";
  if (status === "pending") return "Aguardando confirmacao do provedor.";
  if (status === "cancelled") return "Pagamento cancelado.";
  if (status === "rejected") return "Pagamento recusado pelo provedor.";
  if (status === "expired") return "Pagamento expirado.";
  if (status === "refunded") return "Pagamento reembolsado.";
  return "Pagamento falhou ou precisa de nova tentativa.";
}
