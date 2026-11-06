/** Encabezado común de las páginas internas: sección, título y una frase que explica la página. */
export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="space-y-3">
      <p className="eyebrow">{eyebrow}</p>
      <h1 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
      {children && <div className="max-w-3xl text-lg text-secondary">{children}</div>}
    </header>
  );
}
