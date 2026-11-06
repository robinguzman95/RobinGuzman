"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/Logo";
import { NAV, PROJECT_LINK, REPO_URL } from "@/lib/site";

/** Encabezado con la ruta actual: al cambiar de página la navegación se vuelve a montar
 *  (key = ruta), así los menús abiertos se cierran solos. Con Cache Components la ruta es un dato
 *  de petición: en el layout va dentro de <Suspense>, con <HeaderContent /> como respaldo. */
export function SiteHeader() {
  const pathname = usePathname();
  return <HeaderContent navKey={pathname} />;
}

/** Encabezado fijo. Menús desplegables con <details>; en móvil, un solo menú. */
export function HeaderContent({ navKey }: { navKey?: string }) {
  const pathname = navKey;
  return (
    <header
      className="sticky top-0 z-30 border-b backdrop-blur"
      style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--page) 85%, transparent)" }}
    >
      <nav key={pathname} className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3" aria-label="principal">
        <Link href="/" aria-label="LotoLab, inicio">
          <Logo />
        </Link>

        <ul className="ml-auto hidden items-center gap-1 text-sm md:flex">
          {NAV.map((g) => (
            <li key={g.label} className="relative">
              <details className="menu group">
                <summary className="rounded-md px-3 py-2 text-secondary hover:text-[color:var(--text-primary)]">
                  {g.label} <span aria-hidden>▾</span>
                </summary>
                <div className="card absolute right-0 mt-2 w-80 p-2">
                  {g.items.map((it) => (
                    <Link
                      key={it.href}
                      href={it.href}
                      className="block rounded-lg px-3 py-2 hover:bg-[color:var(--accent-soft)]"
                    >
                      <span className="block font-semibold">{it.label}</span>
                      <span className="block text-xs text-muted">{it.description}</span>
                    </Link>
                  ))}
                </div>
              </details>
            </li>
          ))}
          <li>
            <Link
              href={PROJECT_LINK.href}
              className="rounded-md px-3 py-2 text-secondary hover:text-[color:var(--text-primary)]"
            >
              {PROJECT_LINK.label}
            </Link>
          </li>
          <li>
            <a href={REPO_URL} className="btn-secondary ml-2 inline-block text-sm" rel="noopener noreferrer">
              Código
            </a>
          </li>
        </ul>

        <details className="menu ml-auto md:hidden">
          <summary className="btn-secondary text-sm" aria-label="Abrir menú">
            Menú
          </summary>
          <div className="card absolute right-4 mt-2 w-[min(22rem,calc(100vw-2rem))] space-y-3 p-3">
            {NAV.map((g) => (
              <div key={g.label}>
                <p className="eyebrow px-2">{g.label}</p>
                {g.items.map((it) => (
                  <Link key={it.href} href={it.href} className="block rounded-lg px-2 py-1.5">
                    {it.label}
                  </Link>
                ))}
              </div>
            ))}
            <div className="border-t pt-2" style={{ borderColor: "var(--border)" }}>
              <Link href={PROJECT_LINK.href} className="block rounded-lg px-2 py-1.5">
                {PROJECT_LINK.label}
              </Link>
              <a href={REPO_URL} className="block rounded-lg px-2 py-1.5" rel="noopener noreferrer">
                Código en GitHub
              </a>
            </div>
          </div>
        </details>
      </nav>
    </header>
  );
}
