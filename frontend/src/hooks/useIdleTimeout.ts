import { useEffect, useRef } from "react";

/** События, считающиеся "пользовательской активностью". */
const ACTIVITY_EVENTS: (keyof WindowEventMap)[] = [
  "pointerdown",
  "pointermove",
  "keydown",
  "wheel",
  "touchstart",
];

/**
 * Вызывает `callback`, если пользователь не взаимодействует с окном
 * дольше `timeoutMs` миллисекунд. Любое действие сбрасывает таймер.
 *
 * Если `timeoutMs` меньше или равно нулю — таймаут отключён.
 *
 * @param callback Действие по истечении времени бездействия.
 * @param timeoutMs Порог бездействия в миллисекундах.
 */
export function useIdleTimeout(callback: () => void, timeoutMs: number): void {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!timeoutMs || timeoutMs <= 0) {
      return undefined;
    }

    let timerId: ReturnType<typeof setTimeout> | undefined;

    const resetTimer = (): void => {
      if (timerId !== undefined) {
        clearTimeout(timerId);
      }
      timerId = setTimeout(() => callbackRef.current(), timeoutMs);
    };

    ACTIVITY_EVENTS.forEach((eventName) =>
      window.addEventListener(eventName, resetTimer),
    );
    resetTimer();

    return () => {
      if (timerId !== undefined) {
        clearTimeout(timerId);
      }
      ACTIVITY_EVENTS.forEach((eventName) =>
        window.removeEventListener(eventName, resetTimer),
      );
    };
  }, [timeoutMs]);
}
