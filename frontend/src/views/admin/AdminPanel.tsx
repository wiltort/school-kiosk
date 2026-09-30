import HomeButton from "../../components/HomeButton";
import { SECTION_TITLES, type AdminSection } from "./constants";
import { SettingsPanel } from "./SettingsPanel";
import { SchedulesPanel } from "./SchedulesPanel";
import { AboutPanel } from "./AboutPanel";

interface AdminPanelProps {
  /** Выбранный раздел. */
  section: AdminSection;
  /** Возврат на главный экран киоска. */
  onHome: () => void;
  /** Вызывается после сохранения настроек (для обновления главного экрана). */
  onSettingsSaved?: () => void;
}

/** Контейнер выбранного раздела админки под строкой меню. */
export function AdminPanel({
  section,
  onHome,
  onSettingsSaved,
}: AdminPanelProps) {
  return (
    <div className="admin-view">
      <div className="admin-header">
        <HomeButton onHome={onHome} label="Киоск" />
        <h1 className="admin-title">{SECTION_TITLES[section]}</h1>
      </div>

      {section === "settings" && <SettingsPanel onSaved={onSettingsSaved} />}
      {section === "schedules" && <SchedulesPanel />}
      {section === "about" && <AboutPanel />}
    </div>
  );
}
