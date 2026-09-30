import HomeIcon from "./icons/HomeIcon";

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
      <HomeIcon />
      <span>{label}</span>
    </button>
  );
}
