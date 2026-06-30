import { Suspense } from "react";
import PaymentStatusClient from "../PaymentStatusClient";

export default function PaymentPendingPage() {
  return (
    <Suspense fallback={null}>
      <PaymentStatusClient mode="pending" />
    </Suspense>
  );
}
