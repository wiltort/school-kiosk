import { useActiveAnnouncements } from "../hooks/useAnnouncements";

/**
 * Бегущая строка активных объявлений на главном экране.
 *
 * Показывается только если включена настройка и есть хотя бы одно
 * объявление с видом `ticker` или `both`.
 */
export default function AnnouncementTicker() {
  const { data = [], isLoading } = useActiveAnnouncements("ticker");

  if (isLoading || data.length === 0) {
    return null;
  }

  const text = data
    .map((item) => `${item.title}: ${item.body}`)
    .join("   •   ");

  return (
    <div className="announcement-ticker" role="status" aria-live="polite">
      <div className="announcement-ticker__track">
        <span className="announcement-ticker__item">{text}</span>
        <span className="announcement-ticker__item" aria-hidden="true">
          {text}
        </span>
      </div>
    </div>
  );
}
