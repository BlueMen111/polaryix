import { Suspense } from "react";
import PaymentStatusClient from "../PaymentStatusClient";

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={null}>
      <PaymentStatusClient mode="success" />
    </Suspense>
  );
}
