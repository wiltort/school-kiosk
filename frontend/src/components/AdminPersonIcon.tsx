interface AdminPersonIconProps {
  /** Размер иконки в пикселях. */
  size?: number;
  /** Подпись для скринридеров. */
  title?: string;
  /** CSS-класс для управления цветом (по умолчанию — currentColor). */
  className?: string;
  /** Флаг активированного админа */
  isAdmin?: boolean;
}

/**
 * Иконка «Щит».
 *
 * Используется как:
 *   - иконка входа в админку на главном экране (приглушённый цвет);
 *   - цветная кнопка выхода из режима админа справа в строке меню.
 *
 * Цвет задаётся через `fill="currentColor"`, поэтому управляется только
 * CSS-классом родителя.
 */
export default function AdminPersonIcon({
  size = 24,
  title,
  className,
  isAdmin = false,
}: AdminPersonIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="currentColor"
      className={className}
      role="img"
      aria-hidden={title ? undefined : true}
    >
      {title && <title>{title}</title>}
      {/* Щит */}
      <path
        d="M12 2L4 6v6c0 5 3.5 8.5 8 10 4.5-1.5 8-5 8-10V6l-8-4z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Галочка или крестик */}
      {isAdmin ? (
        <path
          d="M9 12l2 2 4-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <path
          d="M10 10l4 4M14 10l-4 4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}
