"use client";

import { useState } from "react";

export function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "ok" | "error">("idle");
  return (
    <button
      type="button"
      className="btn-ghost text-sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setState("ok");
        } catch {
          setState("error");
        }
        setTimeout(() => setState("idle"), 1500);
      }}
    >
      {state === "ok" ? "¡Copiado!" : state === "error" ? "Selecciónalo a mano" : "Copiar"}
    </button>
  );
}
