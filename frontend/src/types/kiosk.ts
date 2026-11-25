/** Сервис (плитка) киоска из реестра app_units. */
export interface AppUnit {
  /** Стабильный ключ сервиса. */
  key: string;
  /** Название плитки. */
  title: string;
  /** Показывать ли сервис на главном экране. */
  is_enabled: boolean;
  /** Порядок плитки. */
  order: number;
}

/** Известные ключи сервисов. */
export type AppUnitKey = "schedule" | "weather" | "announcements";
