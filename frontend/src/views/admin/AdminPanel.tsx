import HomeButton from "../../components/HomeButton";
import { SECTION_TITLES, type AdminSection } from "./constants";
import { SettingsPanel } from "./SettingsPanel";
import { SchedulesPanel } from "./SchedulesPanel";
import { AboutPanel } from "./AboutPanel";
import { ProfilePanel } from "./ProfilePanel";

interface AdminPanelProps {
  /** Выбранный раздел. */
  section: AdminSection;
  /** Возврат на главный экран киоска. */
  onHome: () => void;
  /** Вызывается после сохранения настроек (для обновления главного экрана). */
  onSettingsSaved?: () => void;
  /** Вызывается после удаления собственного профиля или смены пароля. */
  onAdminDeleted?: () => void;
  /** Автоматически открыть форму создания администратора в разделе «Профиль». */
  autoOpenCreate?: boolean;
  /** Вызывается после обработки autoOpenCreate (для сброса флага). */
  onAutoOpenConsumed?: () => void;
}

/** Контейнер выбранного раздела админки под строкой меню. */
export function AdminPanel({
  section,
  onHome,
  onSettingsSaved,
  onAdminDeleted,
  autoOpenCreate = false,
  onAutoOpenConsumed,
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
      {section === "profile" && (
        <ProfilePanel
          onDeleted={onAdminDeleted ?? (() => {})}
          autoOpenCreate={autoOpenCreate}
          onAutoOpenConsumed={onAutoOpenConsumed}
        />
      )}
    </div>
  );
}
