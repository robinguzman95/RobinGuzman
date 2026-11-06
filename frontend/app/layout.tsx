import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { SiteFooter } from "@/components/SiteFooter";
import { Suspense } from "react";
import { HeaderContent, SiteHeader } from "@/components/SiteHeader";
import { AUTHOR } from "@/lib/site";
import "./globals.css";

const sans = Geist({ subsets: ["latin"], variable: "--font-sans" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: { default: "LotoLab — laboratorio estadístico de loterías", template: "%s · LotoLab" },
  description:
    "Ciencia de datos aplicada a Baloto, Revancha, MiLoto y ColorLoto: pruebas estadísticas, backtesting, valor esperado y machine learning evaluados sin mirar al futuro.",
  authors: [{ name: AUTHOR }],
  openGraph: {
    title: "LotoLab — ¿se le puede ganar al azar?",
    description:
      "Un laboratorio de ciencia de datos que pone a prueba las estrategias populares de lotería con datos reales de Colombia.",
    locale: "es_CO",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen">
        <a href="#main" className="sr-only focus:not-sr-only">
          Saltar al contenido
        </a>
        <Suspense fallback={<HeaderContent />}>
          <SiteHeader />
        </Suspense>
        <main id="main">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
