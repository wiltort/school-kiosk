/**
 * Настройки киоск-режима.
 *
 * Здесь собраны параметры, которые в будущем должны управляться через админку
 * (например, таймаут возврата на главный экран). Пока значения берутся из
 * значений по умолчанию, но архитектура уже готова к загрузке настроек
 * с бэкенда через `loadKioskConfig`.
 */

export interface KioskConfig {
  /** Время бездействия пользователя, после которого происходит возврат на главный экран. */
  inactivityTimeoutMs: number;
  /** Базовый URL API бэкенда. */
  apiBaseUrl: string;
}

const DEFAULT_CONFIG: KioskConfig = {
  // 2 минуты (по ТЗ). Значение станет настраиваемым из админки.
  inactivityTimeoutMs: 2 * 60 * 1000,
  // В dev-режиме относительный путь проксируется Vite на бэкенд.
  apiBaseUrl: "/api/v1",
};

const config: KioskConfig = { ...DEFAULT_CONFIG };

export function getKioskConfig(): KioskConfig {
  return config;
}

/**
 * Загружает актуальные настройки киоска.
 *
 * Сейчас это "плейсхолдер": возвращает значения по умолчанию. В дальнейшем
 * здесь будет запрос к админ-API (например, GET /api/v1/settings) с подменой
 * сохранённых параметров.
 *
 * @returns Копия актуальной конфигурации киоска.
 */
export async function loadKioskConfig(): Promise<KioskConfig> {
  // TODO(admin): заменить на реальную загрузку настроек с бэкенда.
  return { ...DEFAULT_CONFIG };
}
