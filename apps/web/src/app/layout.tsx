import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppProviders } from "@/components/AppProviders";
import { CookieConsent } from "@/components/CookieConsent";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://polaryix.com"),
  title: "PolarYix - File Converter, DDS to PNG, PNG to DDS, YouTube to MP3",
  description:
    "Convert images, videos, audio and documents online. Use PolarYix for DDS to PNG, PNG to DDS, YouTube to MP3, YouTube to MP4, image optimization and background removal.",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    siteName: "PolarYix",
    title: "PolarYix - File Converter, DDS to PNG, PNG to DDS, YouTube to MP3",
    description: "Convert images, videos, audio and documents online with PolarYix.",
    url: "https://polaryix.com",
    type: "website",
    images: ["/assets/polaryix-logo.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "PolarYix - File Converter, DDS to PNG, PNG to DDS, YouTube to MP3",
    description: "Convert images, videos, audio and documents online with PolarYix.",
    images: ["/assets/polaryix-logo.png"],
  },
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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function () {
                try {
                  var theme = localStorage.getItem("polaryix:theme") || (document.cookie.match(/(?:^|; )polaryix_theme=([^;]+)/) || [])[1] || "system";
                  var dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
                  document.documentElement.dataset.theme = dark ? "dark" : "light";
                  document.documentElement.classList.toggle("dark", dark);
                  var language = localStorage.getItem("polaryix:language") || (document.cookie.match(/(?:^|; )polaryix_language=([^;]+)/) || [])[1];
                  if (!language) language = (navigator.language || "").toLowerCase().indexOf("pt") === 0 ? "pt-BR" : "en-US";
                  document.documentElement.lang = language;
                } catch (error) {}
              })();
            `,
          }}
        />
      </head>
      <body className={inter.className}>
        <AppProviders>
          <Header />
          {children}
          <Footer />
          <CookieConsent />
        </AppProviders>
      </body>
    </html>
  );
}
