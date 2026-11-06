import Link from "next/link";
import { Logo } from "@/components/Logo";
import { AUTHOR, NAV, PROJECT_LINK, REPO_URL, docUrl } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t text-sm" style={{ borderColor: "var(--border)" }}>
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-4">
        <div className="space-y-3 md:col-span-2">
          <Logo />
          <p className="max-w-md text-secondary">
            Laboratorio estadístico de las loterías de Baloto, Revancha, MiLoto y ColorLoto: datos reales, pruebas de
            hipótesis, backtesting, valor esperado y machine learning, evaluados sin mirar al futuro.
          </p>
          <p className="text-secondary">
            Desarrollado por <strong className="text-[color:var(--text-primary)]">{AUTHOR}</strong> · Proyecto académico
            y de portafolio.
          </p>
        </div>
        {NAV.map((g) => (
          <div key={g.label} className="space-y-2">
            <p className="eyebrow">{g.label}</p>
            <ul className="space-y-1">
              {g.items.map((it) => (
                <li key={it.href}>
                  <Link href={it.href} className="text-secondary hover:underline">
                    {it.label}
                  </Link>
                </li>
              ))}
              {g.label === "Herramientas" && (
                <>
                  <li>
                    <Link href={PROJECT_LINK.href} className="text-secondary hover:underline">
                      {PROJECT_LINK.label}
                    </Link>
                  </li>
                  <li>
                    <a href={REPO_URL} className="text-secondary hover:underline" rel="noopener noreferrer">
                      Código fuente
                    </a>
                  </li>
                  <li>
                    <a
                      href={docUrl("resultados_backtest.md")}
                      className="text-secondary hover:underline"
                      rel="noopener noreferrer"
                    >
                      Informes técnicos
                    </a>
                  </li>
                </>
              )}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t" style={{ borderColor: "var(--border)" }}>
        <div className="mx-auto max-w-6xl space-y-1 px-4 py-5 text-xs text-muted">
          <p>
            Datos:{" "}
            <a className="link" href="https://baloto.com" rel="noopener noreferrer">
              baloto.com
            </a>{" "}
            (Operador Nacional de Juegos S.A.S.). Proyecto no comercial y sin afiliación con el operador. La app no
            predice resultados: cada sorteo es independiente.
          </p>
          <p>
            Los juegos de azar son solo para mayores de 18 años. Si el juego deja de ser entretenimiento, busca ayuda:{" "}
            <a className="link" href="https://baloto.com" rel="noopener noreferrer">
              juego responsable
            </a>
            .
          </p>
        </div>
      </div>
    </footer>
  );
}
