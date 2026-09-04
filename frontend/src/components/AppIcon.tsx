import type { ReactNode } from "react";

interface AppIconProps {
  /** Подпись под иконкой. */
  label: string;
  /** Иконка (обычно inline-SVG). */
  icon: ReactNode;
  /** Обработчик нажатия. */
  onClick: () => void;
}

/**
 * Большая "плитка-приложение" главного экрана киоска.
 * Рассчитана на управление касанием, имеет заметную зону нажатия.
 */
export default function AppIcon({ label, icon, onClick }: AppIconProps) {
  return (
    <button type="button" className="app-icon" onClick={onClick}>
      <span className="app-icon__icon" aria-hidden="true">
        {icon}
      </span>
      <span className="app-icon__label">{label}</span>
    </button>
  );
}
