import HomeButton from "../components/HomeButton";
import { useActiveAnnouncements } from "../hooks/useAnnouncements";

interface AnnouncementsViewProps {
  onHome: () => void;
}

/** Экран ленты активных объявлений школы. */
export default function AnnouncementsView({ onHome }: AnnouncementsViewProps) {
  const { data = [], isLoading, isError } = useActiveAnnouncements("feed");

  return (
    <section className="announcements">
      <header className="announcements__topbar">
        <HomeButton onHome={onHome} />
      </header>

      <div className="announcements__body">
        {isLoading && (
          <p className="announcements__message">Загрузка объявлений…</p>
        )}

        {isError && !isLoading && (
          <p className="announcements__message">
            Не удалось загрузить объявления
          </p>
        )}

        {!isLoading && !isError && data.length === 0 && (
          <p className="announcements__message">Объявлений пока нет</p>
        )}

        {data.length > 0 && (
          <ul className="announcements__list">
            {data.map((item) => (
              <li key={item.id} className="announcements__card">
                <h2 className="announcements__title">{item.title}</h2>
                <p className="announcements__text">{item.body}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
