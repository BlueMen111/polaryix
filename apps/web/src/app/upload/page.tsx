"use client";

import { AnalysisSessionForm } from "@/components/AnalysisSessionForm";
import { useRouter } from "next/navigation";

export default function UploadPage() {
  const router = useRouter();

  const handleSessionCreated = (sessionId: string) => {
    // TODO: Navigate to session details page
    console.log("Session created:", sessionId);
  };

  return (
    <main style={{ minHeight: "100vh", background: "#f5f5f5", paddingTop: "1rem" }}>
      <AnalysisSessionForm onSessionCreated={handleSessionCreated} />
    </main>
  );
}