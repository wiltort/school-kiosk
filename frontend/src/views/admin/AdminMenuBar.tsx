import AdminPersonIcon from "../../components/AdminPersonIcon";
import type { AdminSection } from "./constants";

interface AdminMenuBarProps {
  /** Активный раздел (подсвечивается); null — на главном экране. */
  activeSection: AdminSection | null;
  /** Открытие раздела. */
  onSectionChange: (section: AdminSection) => void;
  /** Выход из режима админа. */
  onExit: () => void;
}

/** Верхняя строка меню админки: «Настройки», «Расписания», «О проекте» и выход. */
export function AdminMenuBar({
  activeSection,
  onSectionChange,
  onExit,
}: AdminMenuBarProps) {
  const items: { id: AdminSection; label: string }[] = [
    { id: "settings", label: "Настройки" },
    { id: "schedules", label: "Расписания" },
    { id: "about", label: "О проекте" },
  ];

  return (
    <nav className="admin-menu admin-menu--top">
      <div className="admin-menu__nav">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={
              activeSection === item.id
                ? "admin-menu__item admin-menu__item--active"
                : "admin-menu__item"
            }
            onClick={() => onSectionChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="admin-menu__exit"
        aria-label="Выйти из админки"
        title="Выйти из админки"
        onClick={onExit}
      >
        <AdminPersonIcon size={30} isAdmin title="Выйти из админки" />
      </button>
    </nav>
  );
}
