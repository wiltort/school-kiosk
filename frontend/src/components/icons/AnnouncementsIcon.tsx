import type { IconProps } from "./types";

/** Иконка «Объявления» — плитка главного экрана и лента новостей. */
export default function AnnouncementsIcon({ size = 96 }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M3 10v4a1 1 0 0 0 1 1h2l4 4V5L6 9H4a1 1 0 0 0-1 1zm12.5-3.5a1 1 0 0 1 1.4 0A8 8 0 0 1 19 12a8 8 0 0 1-2.1 5.5 1 1 0 1 1-1.5-1.3A6 6 0 0 0 17 12a6 6 0 0 0-1.6-4.2 1 1 0 0 1 .1-1.3zM13 8.5a1 1 0 0 1 1.4.1A5 5 0 0 1 16 12a5 5 0 0 1-1.6 3.4A1 1 0 0 1 13 14a3 3 0 0 0 1-2 3 3 0 0 0-1-2 1 1 0 0 1 0-1.5z" />
    </svg>
  );
}
