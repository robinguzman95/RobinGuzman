/** Marca de LotoLab: tres balotas que se superponen (los números) sobre una línea de base (el azar). */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="10" cy="17" r="7.5" fill="#86b6ef" />
      <circle cx="16" cy="12" r="7.5" fill="#3987e5" />
      <circle cx="22" cy="17" r="7.5" fill="#184f95" />
      <rect x="3" y="27" width="26" height="2" rx="1" fill="currentColor" opacity="0.35" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2 text-lg font-bold tracking-tight">
      <LogoMark />
      LotoLab
    </span>
  );
}
