import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CookieConsent } from "@/components/CookieConsent";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Polaryix - Conversoes futuristas",
  description: "Converta arquivos e prepare midias autorizadas em uma experiencia premium, rapida e futurista.",
  icons: {
    icon: [
      { url: "/assets/favicon.svg", type: "image/svg+xml" },
      { url: "/assets/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/assets/favicon-64.png", sizes: "64x64", type: "image/png" },
    ],
    shortcut: "/assets/favicon.svg",
    apple: "/assets/favicon-64.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className={inter.className}>
        {children}
        <CookieConsent />
      </body>
    </html>
  );
}
