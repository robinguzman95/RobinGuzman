// Grupo de rutas de las páginas internas (no cambia las URL): les da el mismo contenedor.
export default function LabLayout({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-6xl px-4 py-10 md:py-12">{children}</div>;
}
