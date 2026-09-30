import type { IconProps } from "./types";

/** Иконка «Домой» для кнопки возврата на главный экран. */
export default function HomeIcon({ size = 28 }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3l9-8z" />
    </svg>
  );
}
