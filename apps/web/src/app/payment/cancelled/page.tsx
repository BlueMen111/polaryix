import { Suspense } from "react";
import PaymentStatusClient from "../PaymentStatusClient";

export default function PaymentCancelledPage() {
  return (
    <Suspense fallback={null}>
      <PaymentStatusClient mode="cancelled" />
    </Suspense>
  );
}
