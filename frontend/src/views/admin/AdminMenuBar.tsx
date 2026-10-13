import { useEffect, useRef, useState } from "react";
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

/** Верхняя строка меню админки: «Настройки», «Расписания», «О проекте» и меню пользователя. */
export function AdminMenuBar({
  activeSection,
  onSectionChange,
  onExit,
}: AdminMenuBarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const items: { id: AdminSection; label: string }[] = [
    { id: "settings", label: "Настройки" },
    { id: "schedules", label: "Расписания" },
    { id: "about", label: "О проекте" },
  ];

  // Закрываем выпадающее меню по клику вне его и по Escape.
  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    const handlePointerDown = (event: PointerEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  const handleProfile = () => {
    setMenuOpen(false);
    onSectionChange("profile");
  };

  const handleExit = () => {
    setMenuOpen(false);
    onExit();
  };

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

      <div className="admin-menu__user" ref={userMenuRef}>
        <button
          type="button"
          className={
            menuOpen
              ? "admin-menu__user-button admin-menu__user-button--open"
              : "admin-menu__user-button"
          }
          aria-label="Меню администратора"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          title="Меню администратора"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <AdminPersonIcon size={30} isAdmin title="Меню администратора" />
        </button>

        {menuOpen && (
          <div className="admin-menu__dropdown" role="menu">
            <button
              type="button"
              role="menuitem"
              className="admin-menu__dropdown-item"
              onClick={handleProfile}
            >
              Профиль
            </button>
            <button
              type="button"
              role="menuitem"
              className="admin-menu__dropdown-item"
              onClick={handleExit}
            >
              Выход
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
