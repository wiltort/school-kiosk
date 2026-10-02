import { useEffect, useState } from "react";
import { getKioskConfig } from "../config/kioskConfig";
import type { NetworkInfo } from "../types/network";

/**
 * Панель «подключиться по локальной сети»: показывает адрес киоска (по имени
 * компьютера и по IP)
 */
export default function LanInfoPanel() {
  const [info, setInfo] = useState<NetworkInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    const { apiBaseUrl } = getKioskConfig();
    fetch(`${apiBaseUrl}/network/info`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json() as Promise<NetworkInfo>;
      })
      .then((data) => {
        if (!cancelled) {
          setInfo(data);
        }
      })
      .catch(() => {
        /* сеть недоступна — панель просто не покажем */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!info || info.addresses.length === 0) {
    return null;
  }

  // Основной адрес — по сетевому имени (стабилен при динамическом IP).
  const primaryUrl = `http://${info.hostname}:${info.port}`;
  const alternateUrls = info.addresses.map((ip) => `http://${ip}:${info.port}`);

  return (
    <aside className="lan-panel">
      <div className="lan-panel__text">
        <span className="lan-panel__label">Подключиться по сети</span>
        <code className="lan-panel__url">{primaryUrl}</code>
        {alternateUrls.map((url) => (
          <code className="lan-panel__alt" key={url}>
            {url}
          </code>
        ))}
      </div>
    </aside>
  );
}
