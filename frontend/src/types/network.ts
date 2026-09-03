/** Сетевая информация киоска, возвращаемая GET /api/v1/network/info. */
export interface NetworkInfo {
  /** Имя компьютера (Windows hostname), резолвится по LAN (NetBIOS/LLMNR). */
  hostname: string;
  /** Порт HTTP-сервера бэкенда. */
  port: number;
  /** Локальные IPv4-адреса киоска (без loopback 127.x). */
  addresses: string[];
}
