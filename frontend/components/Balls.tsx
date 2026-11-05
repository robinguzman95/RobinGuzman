// Balotas de un sorteo o jugada. En ColorLoto el color ES el dato, así que se pinta con el color
// real de la balota y además se nombra (aria-label y texto oculto): nunca solo color.
const BALL_COLORS: Record<string, { bg: string; fg: string }> = {
  amarillo: { bg: "#f2c200", fg: "#0b0b0b" },
  azul: { bg: "#2a63c4", fg: "#ffffff" },
  rojo: { bg: "#d03b3b", fg: "#ffffff" },
  verde: { bg: "#1a8a3a", fg: "#ffffff" },
  blanco: { bg: "#ffffff", fg: "#0b0b0b" },
  negro: { bg: "#1b1b1b", fg: "#ffffff" },
};

type Ball = { number: number; color?: string | null };

export function Balls({ balls, extra, size = "md" }: { balls: Ball[]; extra?: number | null; size?: "sm" | "md" }) {
  const dim = size === "sm" ? "h-8 w-8 text-sm" : "h-10 w-10 text-base";
  return (
    <ul className="flex flex-wrap items-center gap-2" aria-label="balotas">
      {balls.map((b, i) => {
        const c = b.color ? BALL_COLORS[b.color] : undefined;
        const label = b.color ? `${b.number} ${b.color}` : String(b.number);
        return (
          <li
            key={i}
            aria-label={label}
            title={label}
            className={`${dim} ball-ring grid place-items-center rounded-full font-semibold tabular-nums`}
            style={c ? { background: c.bg, color: c.fg } : undefined}
          >
            <span aria-hidden>{b.color ? b.number : String(b.number).padStart(2, "0")}</span>
          </li>
        );
      })}
      {extra != null && (
        <li
          aria-label={`superbalota ${extra}`}
          title={`superbalota ${extra}`}
          className={`${dim} grid place-items-center rounded-full font-semibold tabular-nums ball-extra`}
        >
          <span aria-hidden>{String(extra).padStart(2, "0")}</span>
        </li>
      )}
    </ul>
  );
}
