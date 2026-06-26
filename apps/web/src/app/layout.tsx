import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Polaryix",
  description: "Plataforma SaaS para análise de datasets e criação de dashboards.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}