interface AdminPersonIconProps {
  /** Размер иконки в пикселях. */
  size?: number;
  /** Подпись для скринридеров. */
  title?: string;
  /** CSS-класс для управления цветом (по умолчанию — currentColor). */
  className?: string;
}

/**
 * Иконка «человечек в фуражке».
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
      {/* Плечи */}
      <path d="M4 21c0-3.87 3.58-6.5 8-6.5s8 2.63 8 6.5H4z" />
      {/* Голова */}
      <circle cx="12" cy="8.7" r="3.3" />
      {/* Тулья фуражки */}
      <path d="M8.4 8.6C8.6 6.6 10.1 4.9 12 4.9s3.4 1.7 3.6 3.7a3.3 3.3 0 0 0-7.2 0z" />
      {/* Козырёк */}
      <path d="M8.3 8.4 4.9 9.3c-.56.14-.56.94 0 1.08l3.4.92c.16.04.34-.01.44-.12V8.55c0-.06-.02-.11-.05-.15-.07-.07-.24-.06-.39 0z" />
    </svg>
  );
}
