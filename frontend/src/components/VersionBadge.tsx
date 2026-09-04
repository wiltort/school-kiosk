/**
 * Строка внизу экрана с версией приложения.
 *
 * Версия подставляется на этапе сборки Vite из `src-tauri/tauri.conf.json`
 * (константа `__APP_VERSION__` определена в vite.config.ts). Она совпадает
 * с версией релиза, которую проставляет scripts/set_release_version.py
 * перед сборкой, поэтому работает одинаково и в десктопном киоске (Tauri),
 * и в браузере по LAN.
 */
export default function VersionBadge() {
  const version = __APP_VERSION__;

  return <div className="version-badge">v{version}</div>;
}
