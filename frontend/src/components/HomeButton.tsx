interface HomeButtonProps {
  /** Обработчик возврата на главный экран. */
  onHome: () => void;
  /** Подпись кнопки (по умолчанию «Домой»). */
  label?: string;
}

/** Кнопка возврата на главный экран киоска. */
export default function HomeButton({
  onHome,
  label = "Домой",
}: HomeButtonProps) {
  return (
    <button type="button" className="home-button" onClick={onHome}>
      <svg
        viewBox="0 0 24 24"
        width="28"
        height="28"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3l9-8z" />
      </svg>
      <span>{label}</span>
    </button>
  );
}
