import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "LotoLab — laboratorio estadístico de loterías",
  description:
    "Analiza el histórico de Baloto, Revancha, MiLoto y ColorLoto y prueba si las estrategias populares le ganan al azar. No predice resultados.",
};

const NAV = [
  { href: "/", label: "Inicio" },
  { href: "/baloto", label: "Estadísticas" },
  { href: "/backtest", label: "Backtest" },
  { href: "/generador", label: "Generador" },
  { href: "/vale-la-pena", label: "¿Vale la pena?" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen">
        <a href="#main" className="sr-only focus:not-sr-only">
          Saltar al contenido
        </a>
        <header className="border-b" style={{ borderColor: "var(--border)" }}>
          <nav
            className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3"
            aria-label="principal"
          >
            <Link href="/" className="mr-auto text-lg font-bold">
              LotoLab
            </Link>
            {NAV.slice(1).map((n) => (
              <Link key={n.href} href={n.href} className="text-secondary hover:underline">
                {n.label}
              </Link>
            ))}
          </nav>
        </header>
        <main id="main" className="mx-auto max-w-5xl px-4 py-8">
          {children}
        </main>
        <footer className="border-t text-sm text-secondary" style={{ borderColor: "var(--border)" }}>
          <div className="mx-auto max-w-5xl space-y-2 px-4 py-6">
            <p>
              Datos:{" "}
              <a className="link" href="https://baloto.com" rel="noopener noreferrer">
                baloto.com
              </a>{" "}
              (Operador Nacional de Juegos S.A.S.). Proyecto académico, no comercial y sin afiliación con el operador.
            </p>
            <p>
              Los juegos de azar son solo para mayores de 18 años. Si el juego deja de ser entretenimiento, busca ayuda:{" "}
              <a className="link" href="https://baloto.com" rel="noopener noreferrer">
                juego responsable en baloto.com
              </a>
              .
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
