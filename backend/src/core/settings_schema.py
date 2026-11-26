"""Реестр ключей и схема настроек приложения.

Настройки хранятся в таблице ``app_settings`` в формате key-value: ключ —
стабильная строка с точечным пространством имён, значение — JSON-совместимый
тип. Реестр :data:`SETTINGS_SCHEMA` описывает все известные ключи: тип,
значение по умолчанию, принадлежность сервису (``unit``), заголовок и правила
валидации.

Реестр используется:

* :class:`~src.apps.settings.managers.SettingsManager` — для типизированного
  чтения/записи и валидации значений;
* админской панелью — для построения формы настроек;
* seed-ом при первом запуске — для переноса значений из legacy
  ``settings.json`` и заполнения значений по умолчанию.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.enums.schedule_modes import ScheduleMode
from src.enums.weather_api import WeatherAPIEnum


class SettingsKey(StrEnum):
    """Стабильные ключи настроек (пространства имён ``unit.key``)."""

    SYSTEM_STATIC_DIR = "system.static_dir"
    SYSTEM_LOCAL_IMAGE_DIR = "system.local_image_dir"
    SYSTEM_AUTOSTART = "system.autostart"

    SCHEDULE_MODE = "schedule.mode"
    SCHEDULE_CURRENT_LOCAL_IMAGE = "schedule.current_local_image_filename"

    UI_WELCOME_MESSAGE = "ui.welcome_message"

    WEATHER_ENABLED = "weather.enabled"
    WEATHER_API = "weather.api"
    WEATHER_LOCATION = "weather.location"
    WEATHER_REFRESH_INTERVAL = "weather.refresh_interval_minutes"

    ANNOUNCEMENTS_ENABLED = "announcements.enabled"
    ANNOUNCEMENTS_TICKER_ENABLED = "announcements.ticker_enabled"


class SettingType(StrEnum):
    """Тип значения настройки."""

    STR = "str"
    BOOL = "bool"
    INT = "int"
    ENUM = "enum"
    JSON = "json"


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """Описание одной настройки приложения."""

    key: SettingsKey
    type: SettingType
    default: Any
    title: str
    unit: str
    description: str = ""
    enum_type: type[StrEnum] | None = None
    nullable: bool = False
    min_value: int | None = None
    max_value: int | None = None

    @property
    def options(self) -> tuple[str, ...]:
        """Допустимые значения для enum-настроек."""
        if self.enum_type is None:
            return ()
        return tuple(str(item.value) for item in self.enum_type)

    def coerce(self, value: Any) -> Any:
        """Приводит значение к типу настройки и валидирует его.

        Raises:
            ValueError: если значение не соответствует типу или ограничениям.
        """
        if value is None:
            if self.nullable:
                return None
            raise ValueError(f"Настройка {self.key.value!r} не может быть пустой")

        if self.type is SettingType.BOOL:
            return self._coerce_bool(value)
        if self.type is SettingType.INT:
            return self._coerce_int(value)
        if self.type is SettingType.STR:
            return self._coerce_str(value)
        if self.type is SettingType.ENUM:
            return self._coerce_enum(value)
        return value

    def _coerce_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off", ""}:
                return False
        raise ValueError(
            f"Настройка {self.key.value!r} должна быть логическим значением"
        )

    def _coerce_int(self, value: Any) -> int:
        try:
            result = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Настройка {self.key.value!r} должна быть целым числом"
            ) from exc
        if self.min_value is not None and result < self.min_value:
            raise ValueError(
                f"Настройка {self.key.value!r} не может быть меньше {self.min_value}"
            )
        if self.max_value is not None and result > self.max_value:
            raise ValueError(
                f"Настройка {self.key.value!r} не может быть больше {self.max_value}"
            )
        return result

    def _coerce_str(self, value: Any) -> str | None:
        text = str(value).strip()
        if not text:
            if self.nullable:
                return None
            raise ValueError(f"Настройка {self.key.value!r} не может быть пустой")
        return text

    def _coerce_enum(self, value: Any) -> str:
        if self.enum_type is None:
            raise ValueError(f"Для настройки {self.key.value!r} не задан enum-тип")
        try:
            return str(self.enum_type(value).value)
        except ValueError as exc:
            options = ", ".join(self.options)
            raise ValueError(
                f"Недопустимое значение {value!r} для {self.key.value!r}. "
                f"Допустимо: {options}"
            ) from exc


SETTINGS_SCHEMA: tuple[SettingSpec, ...] = (
    SettingSpec(
        key=SettingsKey.SYSTEM_STATIC_DIR,
        type=SettingType.STR,
        default=None,
        title="Каталог статики",
        unit="system",
        description="Каталог загруженных изображений расписания.",
        nullable=True,
    ),
    SettingSpec(
        key=SettingsKey.SYSTEM_LOCAL_IMAGE_DIR,
        type=SettingType.STR,
        default=None,
        title="Папка локальных расписаний",
        unit="system",
        description="Путь на диске киоска с локальными изображениями расписания.",
        nullable=True,
    ),
    SettingSpec(
        key=SettingsKey.SYSTEM_AUTOSTART,
        type=SettingType.BOOL,
        default=False,
        title="Автозапуск",
        unit="system",
        description="Запускать киоск при входе в систему.",
    ),
    SettingSpec(
        key=SettingsKey.SCHEDULE_MODE,
        type=SettingType.ENUM,
        default=ScheduleMode.SINGLE.value,
        title="Режим расписания",
        unit="schedule",
        description="Как показывать расписание: одним изображением или по дням.",
        enum_type=ScheduleMode,
    ),
    SettingSpec(
        key=SettingsKey.SCHEDULE_CURRENT_LOCAL_IMAGE,
        type=SettingType.STR,
        default=None,
        title="Текущее локальное изображение",
        unit="schedule",
        description="Имя файла текущего локального изображения расписания. Устаревшее.",
        nullable=True,
    ),
    SettingSpec(
        key=SettingsKey.UI_WELCOME_MESSAGE,
        type=SettingType.STR,
        default=None,
        title="Приветственное сообщение",
        unit="ui",
        description="Показывается на главном экране под заголовком.",
        nullable=True,
    ),
    SettingSpec(
        key=SettingsKey.WEATHER_ENABLED,
        type=SettingType.BOOL,
        default=False,
        title="Показывать погоду",
        unit="weather",
        description="Включает плитку и экран прогноза погоды.",
    ),
    SettingSpec(
        key=SettingsKey.WEATHER_API,
        type=SettingType.ENUM,
        default=WeatherAPIEnum.WTTR.value,
        title="Сервис погоды",
        unit="weather",
        description="Провайдер прогноза погоды.",
        enum_type=WeatherAPIEnum,
    ),
    SettingSpec(
        key=SettingsKey.WEATHER_LOCATION,
        type=SettingType.STR,
        default="Москва",
        title="Населённый пункт",
        unit="weather",
        description="Локация для прогноза погоды.",
    ),
    SettingSpec(
        key=SettingsKey.WEATHER_REFRESH_INTERVAL,
        type=SettingType.INT,
        default=60,
        title="Интервал обновления, мин",
        unit="weather",
        description="Как часто обновлять прогноз погоды.",
        min_value=5,
        max_value=1440,
    ),
    SettingSpec(
        key=SettingsKey.ANNOUNCEMENTS_ENABLED,
        type=SettingType.BOOL,
        default=True,
        title="Показывать объявления",
        unit="announcements",
        description="Включает плитку и экран объявлений.",
    ),
    SettingSpec(
        key=SettingsKey.ANNOUNCEMENTS_TICKER_ENABLED,
        type=SettingType.BOOL,
        default=True,
        title="Бегущая строка",
        unit="announcements",
        description="Показывать активные объявления бегущей строкой на главном экране.",
    ),
)

SETTINGS_BY_KEY: dict[str, SettingSpec] = {
    spec.key.value: spec for spec in SETTINGS_SCHEMA
}


#: Сервисы киоска, создаваемые при первом запуске (реестр ``app_units``).
DEFAULT_APP_UNITS: tuple[dict[str, Any], ...] = (
    {"key": "schedule", "title": "Расписание", "is_enabled": True, "order": 1},
    {"key": "weather", "title": "Погода", "is_enabled": True, "order": 2},
    {"key": "announcements", "title": "Объявления", "is_enabled": True, "order": 3},
)
