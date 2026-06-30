"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { capturePayPalPayment, getPaymentStatus, type PaymentRecord } from "@/lib/api";
import styles from "../payments.module.css";

export default function PaymentStatusClient({ mode }: { mode: "success" | "pending" | "cancelled" }) {
  const searchParams = useSearchParams();
  const paymentId = searchParams.get("payment_id") || "";
  const [payment, setPayment] = useState<PaymentRecord | null>(null);
  const [message, setMessage] = useState("Consultando pagamento...");
  const [now, setNow] = useState(Date.now());

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
      window.localStorage.removeItem("polaryix:last-payment-id");
    };
  }, [paymentId, mode]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  const title = mode === "success" ? "Pagamento recebido" : mode === "cancelled" ? "Pagamento cancelado" : "Aguardando pagamento";
  const countdown = payment?.expires_at ? expiryCountdown(payment.expires_at, now) : null;

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
            {payment.status === "pending" ? (
              <p className={styles.expiryNotice}>
                Este checkout expira em 5 minutos sem confirmacao de pagamento{countdown ? ` (${countdown})` : ""}.
              </p>
            ) : null}
            {payment.qr_code_base64 ? (
              <div className={styles.qrCodePanel}>
                <strong>QR Code PIX</strong>
                <img alt="QR Code PIX" src={`data:image/png;base64,${payment.qr_code_base64}`} />
              </div>
            ) : null}
            {payment.qr_code ? (
              <>
                <strong>Codigo PIX copia e cola</strong>
                <p className={styles.qrCode}>{payment.qr_code}</p>
                <button className={styles.copyButton} type="button" onClick={() => navigator.clipboard.writeText(payment.qr_code || "")}>Copiar codigo PIX</button>
                <p>Apos o pagamento, a confirmacao pode levar alguns segundos.</p>
              </>
            ) : null}
            {!payment.qr_code && !payment.qr_code_base64 && payment.status === "pending" ? (
              <p>Finalize o pagamento na janela segura do provedor. Se o checkout expirar, gere uma nova tentativa.</p>
            ) : null}
          </div>
        ) : null}
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

function expiryCountdown(expiresAt: string, now: number) {
  const remaining = Math.max(0, new Date(expiresAt).getTime() - now);
  const minutes = Math.floor(remaining / 60000);
  const seconds = Math.floor((remaining % 60000) / 1000);
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
