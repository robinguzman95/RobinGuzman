// Datos del sitio: navegación, autor y enlaces. Un solo lugar para cambiarlos.

export const AUTHOR = "Robin Fernando Guzmán Pérez";
export const REPO_URL = "https://github.com/robinguzman95/RobinGuzman";
export const docUrl = (file: string) => `${REPO_URL}/blob/main/docs/${file}`;

export type NavItem = { href: string; label: string; description: string };
export type NavGroup = { label: string; items: NavItem[] };

export const NAV: NavGroup[] = [
  {
    label: "Laboratorio",
    items: [
      { href: "/baloto", label: "Estadísticas", description: "Frecuencias, parejas y pruebas de azar por juego" },
      { href: "/backtest", label: "Backtest", description: "¿Alguna estrategia le gana al azar?" },
      { href: "/ml", label: "Modelo de ML", description: "Machine learning evaluado sin mirar al futuro" },
      { href: "/vale-la-pena", label: "¿Vale la pena?", description: "Valor esperado real de cada tiquete" },
    ],
  },
  {
    label: "Herramientas",
    items: [
      { href: "/mi-jugada", label: "Revisar mi jugada", description: "Escribe tus números y ve su resumen" },
      { href: "/generador", label: "Generador", description: "Jugadas desde el histórico o el modelo" },
      { href: "/analizador", label: "Analizador", description: "Jugadas armadas y cómo les habría ido" },
    ],
  },
];

export const PROJECT_LINK: NavItem = {
  href: "/proyecto",
  label: "El proyecto",
  description: "Metodología, arquitectura y resultados",
};
