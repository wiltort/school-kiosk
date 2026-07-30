# School Kiosk — Архитектура проекта (Python + Tauri + React)

## 1. Общая архитектура

```
+------------------------------------------------------------------+
|                     Локальная сеть школы                          |
|                                                                   |
|  +----------------------------+    +----------------------------+ |
|  |   ПК с киоском (Windows)   |    |  Ноутбук учителя           | |
|  |                            |    |  (браузер)                 | |
|  |  +----------------------+  |    |                            | |
|  |  |   Tauri Desktop App  |  |    |  http://192.168.1.X:      | |
|  |  |                      |  |    |      8765/admin           | |
|  |  |  +----------------+  |  |    |                            | |
|  |  |  |  WebView       |  |  |    |  - Редактор расписания    | |
|  |  |  |  (Kiosk View)  |  |  |    |  - Редактор новостей      | |
|  |  |  |  - Расписание  |  |  |    |  - Импорт Excel           | |
|  |  |  |  - Новости     |  |  |    |  - Парсинг VK/сайта       | |
|  |  |  |  - Слайдер     |  |  |    |  - Настройки              | |
|  |  |  +----------------+  |  |    |                            | |
|  |  |                      |  |    +----------------------------+ |
|  |  |  +----------------+  |  |                                   |
|  |  |  |  Rust Core     |  |  |    +----------------------------+ |
|  |  |  |  - Kiosk Guard |  |  |    | Смартфон завуча            | |
|  |  |  |  - Win API     |  |  |    | (браузер)                  | |
|  |  |  +-------+--------+  |  |    |                            | |
|  |  +----------+-----------+  |    | http://192.168.1.X:        | |
|  |             |              |    |     8765/admin             | |
|  |  +----------+-----------+  |    +----------------------------+ |
|  |  | Python FastAPI       |  |                                   |
|  |  | (0.0.0.0:8765)       |  |                                   |
|  |  |                      |  |                                   |
|  |  |  - Schedule API      |  |                                   |
|  |  |  - News API          |  |                                   |
|  |  |  - Admin API (JWT)   |  |                                   |
|  |  |  - VK Parser         |  |                                   |
|  |  |  - Site Parser       |  |                                   |
|  |  |  - Excel Import      |  |                                   |
|  |  |                      |  |                                   |
|  |  |  +----------------+  |  |                                   |
|  |  |  |   SQLite DB    |  |  |                                   |
|  |  |  +----------------+  |  |                                   |
|  |  +----------------------+  |                                   |
|  +----------------------------+                                   |
+------------------------------------------------------------------+
```

**Ключевое изменение:** Python FastAPI слушает на `0.0.0.0:8765` (все сетевые интерфейсы), а не только `localhost`. Это позволяет:
- Tauri WebView обращаться к API через localhost (без задержек)
- Устройства в локальной сети обращаться к админке через IP киоска

## 2. Технологический стек

### Desktop оболочка (Rust / Tauri)
| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Фреймворк | **Tauri v2** | Десктопная оболочка с WebView |
| Язык | **Rust** | Системные вызовы, киоск-режим |
| WebView | **WebView2** (Windows) | Отображение React SPA |
| Киоск-модуль | **Windows API** (user32.dll) | Блокировка Alt+F4, Win, Ctrl+Alt+Del |

### Backend (Python)
| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Web-фреймворк | **FastAPI** | REST API сервер |
| База данных | **SQLite** (через SQLAlchemy + Alembic) | Хранение данных |
| Парсинг Excel | **openpyxl** | Импорт расписания |
| Парсинг VK | **vk-api** | Получение новостей из VK |
| Парсинг сайта | **httpx + BeautifulSoup4** | Парсинг новостей с сайта |
| Фоновые задачи | **APScheduler** | Периодический парсинг новостей |
| Аутентификация | **python-jose + passlib** | JWT для админки |

### Frontend (React / TypeScript)
| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Фреймворк | **React 18 + TypeScript** | UI |
| Сборка | **Vite** | Быстрая сборка |
| Роутинг | **React Router v6** | Навигация |
| UI Kit | **Material UI** или **Ant Design** | Готовые компоненты |
| HTTP клиент | **TanStack Query (React Query)** | Работа с API |
| Слайдер | **Swiper.js** | Карусель новостей |
| Таблица | **TanStack Table** | Редактирование расписания |
| Формы | **React Hook Form** | Управление формами |

## 3. Структура проекта

```
school-kiosk/
│
├── src-tauri/                    # Tauri Rust core
│   ├── src/
│   │   ├── main.rs              # Точка входа, запуск Python
│   │   ├── kiosk.rs             # Киоск-режим (Win API)
│   │   ├── admin.rs             # IPC: админ-режим
│   │   └── process.rs           # Управление Python процессом
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── icons/                   # Иконки приложения
│
├── backend/                      # Python FastAPI
│   ├── app/                     # Основной пакет приложения
│   │   ├── __init__.py
│   │   ├── main.py              # Точка входа FastAPI (uvicorn)
│   │   ├── config.py            # Настройки из env/config файла
│   │   ├── database.py          # Подключение к БД (SQLAlchemy async)
│   │   │
│   │   ├── models/              # SQLAlchemy ORM модели
│   │   │   ├── __init__.py      # Экспорт всех моделей + Base
│   │   │   ├── base.py          # Базовый класс (id, created_at, updated_at)
│   │   │   ├── schedule.py      # Class, Subject, Teacher, ScheduleEntry
│   │   │   ├── news.py          # News
│   │   │   └── admin.py         # Admin, Settings
│   │   │
│   │   ├── schemas/             # Pydantic схемы (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── common.py        # Пагинация, статус-ответы
│   │   │   ├── schedule.py      # ClassCreate, ClassRead, ScheduleEntryCreate, ...
│   │   │   ├── news.py          # NewsCreate, NewsRead, NewsUpdate
│   │   │   └── admin.py         # LoginRequest, TokenResponse, SettingsUpdate
│   │   │
│   │   ├── routers/             # API роутеры (endpoints)
│   │   │   ├── __init__.py      # Подключение всех роутеров к app
│   │   │   ├── health.py        # GET /health (для Tauri health check)
│   │   │   ├── kiosk.py         # Публичные endpoint'ы киоска
│   │   │   ├── schedule.py      # /api/v1/schedule/*
│   │   │   ├── news.py          # /api/v1/news/*
│   │   │   └── admin.py         # /api/v1/admin/* (auth, settings)
│   │   │
│   │   ├── services/            # Бизнес-логика
│   │   │   ├── __init__.py
│   │   │   ├── schedule_service.py   # CRUD + week logic
│   │   │   ├── news_service.py       # CRUD + caching
│   │   │   ├── auth_service.py       # JWT, пароли, токены
│   │   │   ├── excel_importer.py     # Парсинг Excel -> schedule
│   │   │   ├── vk_parser.py          # Парсинг VK API -> news
│   │   │   └── site_parser.py        # Парсинг HTML сайта -> news
│   │   │
│   │   ├── middleware/          # Middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # JWT проверка для админ-роутов
│   │   │   ├── cors.py          # CORS настройки
│   │   │   └── logging.py       # Логирование запросов
│   │   │
│   │   ├── tasks/               # Фоновые задачи (APScheduler)
│   │   │   ├── __init__.py
│   │   │   ├── scheduler.py     # Настройка планировщика
│   │   │   ├── news_sync.py     # Периодический парсинг новостей
│   │   │   └── cache_cleanup.py # Очистка кэша
│   │   │
│   │   ├── utils/               # Вспомогательные утилиты
│   │   │   ├── __init__.py
│   │   │   ├── date_utils.py    # Работа с датами, неделями
│   │   │   ├── hash_utils.py    # Хеширование паролей
│   │   │   └── file_utils.py    # Работа с файлами (Excel upload)
│   │   │
│   │   └── static/              # Статика для админ-панели
│   │       └── admin/           # Сюда копируется React build
│   │           └── index.html
│   │
│   ├── alembic/                 # Миграции БД
│   │   ├── env.py               # Настройка Alembic
│   │   ├── script.py.mako       # Шаблон миграций
│   │   └── versions/            # Файлы миграций
│   │       └── .gitkeep
│   │
│   ├── tests/                   # Тесты
│   │   ├── __init__.py
│   │   ├── conftest.py          # Фикстуры pytest (test DB, client)
│   │   ├── test_health.py
│   │   ├── test_schedule.py
│   │   ├── test_news.py
│   │   ├── test_auth.py
│   │   ├── test_excel_import.py
│   │   └── test_parsers.py
│   │
│   ├── scripts/                 # Вспомогательные скрипты
│   │   ├── seed_data.py         # Наполнение тестовыми данными
│   │   ├── create_admin.py      # Создание администратора
│   │   └── reset_db.py          # Сброс БД
│   │
│   ├── alembic.ini              # Конфиг Alembic
│   ├── pyproject.toml           # Зависимости + метаданные
│   ├── requirements.txt         # pip freeze (для CI/CD)
│   └── requirements-dev.txt     # Зависимости для разработки
│
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/
│   │   │   ├── KioskView.tsx    # Публичный экран
│   │   │   └── AdminView.tsx    # Админ-панель
│   │   ├── components/
│   │   │   ├── kiosk/
│   │   │   │   ├── ScheduleBoard.tsx
│   │   │   │   ├── NewsSlider.tsx
│   │   │   │   ├── Clock.tsx
│   │   │   │   └── Weather.tsx (опционально)
│   │   │   └── admin/
│   │   │       ├── ScheduleEditor.tsx
│   │   │       ├── NewsEditor.tsx
│   │   │       ├── ExcelImport.tsx
│   │   │       └── Settings.tsx
│   │   ├── api/
│   │   │   ├── client.ts        # Axios/Fetch клиент
│   │   │   ├── schedule.ts
│   │   │   └── news.ts
│   │   ├── hooks/
│   │   ├── types/
│   │   └── styles/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── scripts/                     # Скрипты для сборки/запуска
│   ├── build.bat                # Полная сборка проекта
│   ├── dev.bat                  # Запуск в режиме разработки
│   └── setup.bat                # Первоначальная настройка окружения
│
├── .env.example                 # Пример переменных окружения
├── .gitignore
├── LICENSE
└── README.md
```

## 4. Детальное описание Python-модулей

### 4.1. `app/main.py` — точка входа

```python
# Назначение: запуск FastAPI приложения через uvicorn
# - Создаёт экземпляр FastAPI
# - Подключает все роутеры
# - Инициализирует БД (create_all)
# - Запускает APScheduler для фоновых задач
# - Настраивает middleware (CORS, логирование)
# - Раздаёт статику админ-панели

# Запуск: uvicorn app.main:app --host 0.0.0.0 --port 8765
```

### 4.2. `app/config.py` — конфигурация

```python
# Назначение: все настройки приложения в одном месте
# Источник: переменные окружения + .env файл

class Settings(BaseSettings):
    # --- Общие ---
    APP_NAME: str = "School Kiosk"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # --- Сервер ---
    HOST: str = "0.0.0.0"
    PORT: int = 8765

    # --- База данных ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./school_kiosk.db"

    # --- JWT ---
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_HOURS: int = 24
    ALGORITHM: str = "HS256"

    # --- Парсинг новостей ---
    VK_ACCESS_TOKEN: str = ""
    VK_GROUP_ID: str = ""
    SCHOOL_SITE_URL: str = ""
    NEWS_SYNC_INTERVAL_MINUTES: int = 60

    # --- Киоск ---
    CURSOR_HIDE_TIMEOUT_SECONDS: int = 3
    SCREEN_REFRESH_INTERVAL_SECONDS: int = 300

    # --- Админка ---
    ADMIN_SESSION_TIMEOUT_MINUTES: int = 15
    ALLOWED_IPS: list[str] = ["192.168.1.0/24", "10.0.0.0/8"]
```

### 4.3. `app/database.py` — подключение к БД

```python
# Назначение: настройка SQLAlchemy async engine + session

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### 4.4. `app/models/` — ORM модели

#### `models/base.py` — базовый класс
```python
# Добавляет id, created_at, updated_at во все модели
class TimestampMixin:
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )
```

#### `models/schedule.py` — 4 модели расписания
```python
class Class(TimestampMixin, Base):
    __tablename__ = "classes"
    name: str           # "10A", "11Б"
    grade_level: int    # 10, 11
    entries: list[ScheduleEntry] = relationship(back_populates="class_")

class Subject(TimestampMixin, Base):
    __tablename__ = "subjects"
    name: str           # "Математика"
    short_name: str     # "Мат"
    entries: list[ScheduleEntry] = relationship(back_populates="subject")

class Teacher(TimestampMixin, Base):
    __tablename__ = "teachers"
    full_name: str      # "Иванова М.И."
    short_name: str     # "Иванова"
    entries: list[ScheduleEntry] = relationship(back_populates="teacher")

class ScheduleEntry(TimestampMixin, Base):
    __tablename__ = "schedule_entries"
    class_id: int = ForeignKey("classes.id")
    subject_id: int = ForeignKey("subjects.id")
    teacher_id: int = ForeignKey("teachers.id")
    day_of_week: int    # 1=пн ... 5=пт
    lesson_number: int  # 1..8
    week_type: int      # 0=всегда, 1=числитель, 2=знаменатель
    room: str           # "Каб. 301"

    class_: Class = relationship(back_populates="entries")
    subject: Subject = relationship(back_populates="entries")
    teacher: Teacher = relationship(back_populates="entries")
```

#### `models/news.py` — новости
```python
class News(TimestampMixin, Base):
    __tablename__ = "news"
    title: str
    content: str        # HTML или Markdown
    image_url: str | None
    source: str         # "vk", "site", "manual"
    source_url: str | None
    published_at: datetime
    is_active: bool = True
```

#### `models/admin.py` — админы и настройки
```python
class Admin(TimestampMixin, Base):
    __tablename__ = "admins"
    username: str       # Уникальный логин
    password_hash: str  # bcrypt hash
    role: str           # "admin" или "editor"

class Settings(Base):
    __tablename__ = "settings"
    key: str = Column(String, primary_key=True)   # "vk_group_id"
    value: str = Column(String)                   # "-123456789"
```

### 4.5. `app/schemas/` — Pydantic схемы

```python
# Назначение: валидация входящих данных и форматирование ответов

# --- Common ---
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 50

class StatusResponse(BaseModel):
    status: str = "ok"
    message: str | None = None

# --- Schedule ---
class ClassCreate(BaseModel):
    name: str           # "10A"
    grade_level: int    # 10

class ClassRead(ClassCreate):
    id: int
    created_at: datetime

class ScheduleEntryCreate(BaseModel):
    class_id: int
    subject_id: int
    teacher_id: int
    day_of_week: int    # 1-5
    lesson_number: int  # 1-8
    week_type: int = 0  # 0=both, 1=числитель, 2=знаменатель
    room: str = ""

class ScheduleEntryRead(ScheduleEntryCreate):
    id: int
    subject_name: str   # Денормализовано для удобства
    teacher_name: str

# --- News ---
class NewsCreate(BaseModel):
    title: str
    content: str
    image_url: str | None = None
    source: str = "manual"
    source_url: str | None = None
    published_at: datetime = None
    is_active: bool = True

# --- Admin ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
```

### 4.6. `app/routers/` — API endpoints

#### `routers/health.py`
```python
# GET /health -> {"status": "ok", "version": "1.0.0"}
# Используется Tauri для проверки, что Python backend запущен
```

#### `routers/kiosk.py` — публичные endpoint'ы
```python
# GET  /api/v1/schedule/today?class_id=X  -> расписание на сегодня
# GET  /api/v1/schedule/now?class_id=X    -> какой урок сейчас идёт
# GET  /api/v1/schedule/week?class_id=X   -> расписание на неделю
# GET  /api/v1/schedule/classes           -> список классов
# GET  /api/v1/news/active                -> активные новости
# GET  /api/v1/kiosk/settings             -> настройки отображения
```

#### `routers/schedule.py` — админ CRUD расписания
```python
# Все endpoint'ы защищены JWT (Depends(get_current_admin))
# GET    /api/v1/admin/schedule/classes        -> список классов
# POST   /api/v1/admin/schedule/classes        -> создать класс
# PUT    /api/v1/admin/schedule/classes/:id    -> обновить класс
# DELETE /api/v1/admin/schedule/classes/:id    -> удалить класс
# ...аналогично для subjects, teachers, entries
# POST   /api/v1/admin/schedule/import-excel   -> импорт Excel
```

#### `routers/news.py` — админ CRUD новостей
```python
# GET    /api/v1/admin/news                    -> все новости (с пагинацией)
# POST   /api/v1/admin/news                    -> создать новость
# PUT    /api/v1/admin/news/:id                -> обновить новость
# DELETE /api/v1/admin/news/:id                -> удалить новость
# POST   /api/v1/admin/news/parse-vk           -> запустить парсинг VK
# POST   /api/v1/admin/news/parse-site         -> запустить парсинг сайта
```

#### `routers/admin.py` — аутентификация и настройки
```python
# POST /api/v1/admin/auth/login       -> вход, получение JWT
# POST /api/v1/admin/auth/refresh     -> обновление токена
# GET  /api/v1/admin/settings         -> получить настройки
# PUT  /api/v1/admin/settings         -> обновить настройки
```

### 4.7. `app/services/` — бизнес-логика

#### `services/schedule_service.py`
```python
# - get_today_schedule(class_id) -> расписание на сегодня
# - get_week_schedule(class_id) -> расписание на неделю
# - get_current_lesson(class_id) -> какой урок сейчас
# - create_entry(data) -> создать запись
# - update_entry(id, data) -> обновить запись
# - delete_entry(id) -> удалить запись
# - import_from_excel(file) -> импорт из Excel
```

#### `services/news_service.py`
```python
# - get_active_news() -> активные новости
# - create_news(data) -> создать
# - update_news(id, data) -> обновить
# - delete_news(id) -> удалить
```

#### `services/auth_service.py`
```python
# - authenticate(username, password) -> Admin | None
# - create_access_token(admin) -> JWT строка
# - create_refresh_token(admin) -> JWT строка
# - verify_token(token) -> Admin | None
# - hash_password(password) -> hash
# - verify_password(password, hash) -> bool
```

#### `services/excel_importer.py`
```python
# - parse_excel(file_path) -> list[ScheduleEntryCreate]
#   Ожидаемый формат Excel:
#   Колонки: Класс | Предмет | Учитель | День | Урок | Кабинет | Тип_недели
# - validate_data(entries) -> list[ValidationError]
# - import_to_db(entries) -> int (сколько импортировано)
```

#### `services/vk_parser.py`
```python
# - fetch_news(count=10) -> list[NewsCreate]
#   Использует VK API (wall.get) для получения постов из группы
# - parse_post(post) -> NewsCreate
#   Извлекает: текст, картинки, дату
```

#### `services/site_parser.py`
```python
# - fetch_news(url) -> list[NewsCreate]
#   Парсит HTML школьного сайта
# - parse_html(html) -> list[NewsCreate]
#   Ищет: заголовки, текст, изображения
```

### 4.8. `app/middleware/` — middleware

```python
# auth.py:  JWTBearer middleware для защиты админ-роутов
# cors.py:  CORS middleware (разрешаем всё для локальной сети)
# logging.py: Логирование всех HTTP запросов (method, path, status, duration)
```

### 4.9. `app/tasks/` — фоновые задачи

```python
# scheduler.py: Настройка APScheduler
#   - Запускается при старте приложения
#   - Регистрирует задачи

# news_sync.py: Периодический парсинг новостей
#   - Раз в N минут проверяет VK и сайт
#   - Добавляет новые новости в БД
#   - Не дублирует существующие (по source_url)

# cache_cleanup.py: Очистка устаревших данных
#   - Удаляет неактивные новости старше 30 дней
#   - Оптимизирует SQLite (VACUUM)
```

### 4.10. `app/utils/` — утилиты

```python
# date_utils.py:
#   - get_current_week_type() -> 1|2 (числитель/знаменатель)
#   - get_day_of_week() -> 1-7
#   - get_lesson_time(lesson_number) -> (start, end)
#   - is_lesson_now(lesson_number) -> bool

# hash_utils.py:
#   - hash_password(password) -> str (bcrypt)
#   - verify_password(password, hash) -> bool

# file_utils.py:
#   - save_uploaded_file(file) -> str (путь к сохранённому файлу)
#   - cleanup_temp_files()
```

### 4.11. `tests/` — тесты

```python
# conftest.py:
#   - test_db: отдельная SQLite БД для тестов
#   - test_client: AsyncClient для FastAPI
#   - seed_test_data: наполнение тестовыми данными

# test_health.py:       GET /health -> 200
# test_schedule.py:     CRUD расписания
# test_news.py:         CRUD новостей
# test_auth.py:         логин, токены, защита роутов
# test_excel_import.py: импорт Excel
# test_parsers.py:      парсинг VK и сайта (с моками)
```

### 4.12. `scripts/` — вспомогательные скрипты

```python
# seed_data.py:
#   - Создаёт тестовые классы (10А, 11Б, ...)
#   - Создаёт тестовые предметы (Математика, Физика, ...)
#   - Создаёт тестовое расписание на неделю
#   - Создаёт тестовые новости
#   - Создаёт администратора (admin/admin123)

# create_admin.py:
#   - Создаёт нового администратора
#   - Запрашивает логин/пароль/роль

# reset_db.py:
#   - Удаляет БД
#   - Создаёт новую
#   - Применяет миграции
```

## 5. Модели данных (SQLite)

### schedule (расписание)
```mermaid
erDiagram
    CLASSES {
        int id PK
        string name "10A, 11B..."
        int grade_level
    }
    SUBJECTS {
        int id PK
        string name "Математика, Физика..."
        string short_name "Мат, Физ..."
    }
    TEACHERS {
        int id PK
        string full_name
        string short_name
    }
    SCHEDULE_ENTRIES {
        int id PK
        int class_id FK
        int subject_id FK
        int teacher_id FK
        int day_of_week "1-5 (пн-пт)"
        int lesson_number "1-8"
        int week_type "0=both, 1=числитель, 2=знаменатель"
        string room "кабинет"
    }
    CLASSES ||--o{ SCHEDULE_ENTRIES : has
    SUBJECTS ||--o{ SCHEDULE_ENTRIES : has
    TEACHERS ||--o{ SCHEDULE_ENTRIES : has
```

### news (новости)
```mermaid
erDiagram
    NEWS {
        int id PK
        string title
        string content
        string image_url
        string source "vk, site, manual"
        string source_url
        datetime published_at
        datetime created_at
        bool is_active
    }
```

### admin (администраторы)
```mermaid
erDiagram
    ADMINS {
        int id PK
        string username
        string password_hash
        string role "admin, editor"
        datetime created_at
    }
    SETTINGS {
        int id PK
        string key UK
        string value
    }
```

## 6. API Endpoints

### Публичные (киоск) - доступны без авторизации
| Method | Path | Описание |
|--------|------|----------|
| GET | `/api/v1/schedule/today?class_id=X` | Расписание на сегодня |
| GET | `/api/v1/schedule/week?class_id=X` | Расписание на неделю |
| GET | `/api/v1/schedule/classes` | Список классов |
| GET | `/api/v1/news/active` | Активные новости |
| GET | `/api/v1/kiosk/settings` | Настройки киоска |

### Админ (требуют JWT) - доступны и с киоска, и из локальной сети
| Method | Path | Описание |
|--------|------|----------|
| POST | `/api/v1/admin/auth/login` | Вход (логин/пароль -> JWT) |
| POST | `/api/v1/admin/auth/refresh` | Обновление токена |
| GET | `/api/v1/admin/schedule/classes` | CRUD классы |
| POST | `/api/v1/admin/schedule/classes` | Создать класс |
| PUT | `/api/v1/admin/schedule/classes/:id` | Обновить класс |
| DELETE | `/api/v1/admin/schedule/classes/:id` | Удалить класс |
| GET | `/api/v1/admin/schedule/subjects` | CRUD предметы |
| POST | `/api/v1/admin/schedule/subjects` | Создать предмет |
| PUT | `/api/v1/admin/schedule/subjects/:id` | Обновить предмет |
| DELETE | `/api/v1/admin/schedule/subjects/:id` | Удалить предмет |
| GET | `/api/v1/admin/schedule/teachers` | CRUD учителя |
| POST | `/api/v1/admin/schedule/teachers` | Создать учителя |
| PUT | `/api/v1/admin/schedule/teachers/:id` | Обновить учителя |
| DELETE | `/api/v1/admin/schedule/teachers/:id` | Удалить учителя |
| GET | `/api/v1/admin/schedule/entries?class_id=X` | Получить расписание для класса |
| POST | `/api/v1/admin/schedule/entries` | Создать запись |
| PUT | `/api/v1/admin/schedule/entries/:id` | Обновить запись |
| DELETE | `/api/v1/admin/schedule/entries/:id` | Удалить запись |
| POST | `/api/v1/admin/schedule/import-excel` | Импорт Excel |
| GET | `/api/v1/admin/news` | Список новостей |
| POST | `/api/v1/admin/news` | Создать новость |
| PUT | `/api/v1/admin/news/:id` | Обновить новость |
| DELETE | `/api/v1/admin/news/:id` | Удалить новость |
| POST | `/api/v1/admin/news/parse-vk` | Парсинг VK |
| POST | `/api/v1/admin/news/parse-site` | Парсинг сайта |
| GET | `/api/v1/admin/settings` | Получить настройки |
| PUT | `/api/v1/admin/settings` | Обновить настройки |

## 7. Киоск-режим (Rust)

Tauri Rust core будет реализовывать тот же функционал, что сейчас в C#:

```rust
// src-tauri/src/kiosk.rs
struct KioskGuard {
    // Блокировка клавиш через Windows API (SetWindowsHookEx)
    // - Alt+F4
    // - Alt+Tab
    // - Win (левая/правая)
    // - Ctrl+Alt+Del
    // - Escape
    // - Context Menu

    // Режим администратора:
    // - Ctrl+Shift+A -> toggle admin mode
    // - Ctrl+Alt+X -> exit kiosk (только в admin mode)

    // Управление окном:
    // - Fullscreen (без рамки)
    // - Topmost (поверх всех окон)
    // - Скрытие курсора при бездействии
}
```

## 8. План реализации (поэтапный)

### Этап 1: Backend (Python FastAPI)
1. Инициализация Python проекта, структура папок
2. Модели БД (SQLAlchemy) + миграции (Alembic)
3. API для расписания (CRUD + Excel import)
4. API для новостей (CRUD + VK parser + site parser)
5. Админ API (JWT auth, настройки)
6. Тестирование API (через Swagger/Postman)

### Этап 2: Frontend (React)
1. Инициализация React + Vite + TypeScript
2. KioskView: расписание (таблица на день/неделю)
3. KioskView: слайдер новостей
4. KioskView: часы, дата, оформление
5. AdminView: авторизация
6. AdminView: редактор расписания
7. AdminView: редактор новостей + импорт
8. AdminView: настройки

### Этап 3: Tauri оболочка
1. Инициализация Tauri проекта
2. Перенос KioskGuard из C# в Rust
3. Запуск Python backend как child process
4. Интеграция React frontend в Tauri
5. Сборка и тестирование

### Этап 4: Сборка и деплой
1. Скрипты сборки (build.bat)
2. Инсталлятор (NSIS или WiX)
3. Документация

## 9. Ключевые решения

| Решение | Выбор | Обоснование |
|---------|-------|-------------|
| База данных | SQLite | Не требуется сервер, файл БД рядом с приложением |
| Парсинг VK | vk-api (официальный API) | Стабильнее парсинга HTML |
| Парсинг сайта | BeautifulSoup4 | Гибкий парсинг HTML |
| Аутентификация | JWT (access + refresh) | Без сессий, подходит для SPA |
| Запуск Python | Tauri spawn + health check | Автоматический старт/стоп с приложением |
| Сборка React | Vite | Быстрая, современная |
| UI Kit | Material UI | Популярный, много компонентов |
| **Сеть API** | **0.0.0.0:8765** | **Доступ из локальной сети для админки** |
| **CORS** | **Разрешён с любых origin** | **Админка открывается с разных устройств** |
| **Фронтенд админки** | **Отдельный SPA build** | **Можно хостить отдельно или через FastAPI** |

## 10. Диаграмма последовательности (запуск приложения)

```mermaid
sequenceDiagram
    participant User
    participant Tauri as Tauri (Rust)
    participant Python as Python Backend
    participant React as React Frontend
    participant DB as SQLite

    User->>Tauri: Запуск приложения
    Tauri->>Tauri: Полноэкранный режим
    Tauri->>Tauri: Блокировка клавиш (Win API)
    Tauri->>Python: spawn python backend
    Python->>DB: Инициализация БД
    Python-->>Tauri: Health check OK (port 8765)
    Tauri->>React: Загрузка WebView (localhost:5173 / build)
    React->>Python: GET /api/v1/schedule/today
    Python->>DB: SELECT schedule
    DB-->>Python: Данные расписания
    Python-->>React: JSON расписание
    React->>Python: GET /api/v1/news/active
    Python->>DB: SELECT news
    DB-->>Python: Новости
    Python-->>React: JSON новости
    React->>React: Отрисовка киоск-экрана
    Note over React: Автообновление каждые N минут
```

## 11. Диаграмма последовательности (удалённая админка)

```mermaid
sequenceDiagram
    participant Teacher as Учитель (ноутбук)
    participant Browser as Браузер
    participant Python as Python FastAPI (киоск)
    participant DB as SQLite

    Teacher->>Browser: Открыть http://192.168.1.100:8765/admin
    Browser->>Python: GET /admin/index.html
    Python-->>Browser: React SPA (админка)
    Browser->>Browser: Загрузка React приложения

    Teacher->>Browser: Ввод логина/пароля
    Browser->>Python: POST /api/v1/admin/auth/login
    Python->>DB: SELECT admin WHERE username=?
    DB-->>Python: Хеш пароля
    Python->>Python: Проверка bcrypt
    Python-->>Browser: JWT access + refresh токены

    Teacher->>Browser: Открыть редактор расписания
    Browser->>Python: GET /api/v1/admin/schedule/entries?class_id=1
    Note over Browser,Python: JWT в Authorization header
    Python->>DB: SELECT schedule entries
    DB-->>Python: Данные
    Python-->>Browser: JSON с расписанием

    Teacher->>Browser: Изменить урок
    Browser->>Python: PUT /api/v1/admin/schedule/entries/42
    Python->>DB: UPDATE schedule_entries
    DB-->>Python: OK
    Python-->>Browser: {"status": "ok"}

    Note over Browser,Python: Киоск на экране обновит данные автоматически
    Note over Browser,Python: (polling каждые N секунд или WebSocket)
```

## 12. Варианты доставки админ-панели

Есть два варианта, как пользователь получает админку в браузере:

### Вариант A: FastAPI раздаёт статику (рекомендуется)
```
http://192.168.1.100:8765/admin  ->  FastAPI static files -> index.html
```
- **Плюсы:** Проще, один порт, не нужно настраивать отдельный сервер
- **Минусы:** Нужно пересобрать React при изменении админки

### Вариант B: Отдельный dev-сервер для админки
```
http://192.168.1.100:5173/admin  ->  Vite dev server
```
- **Плюсы:** Hot reload при разработке
- **Минусы:** Два порта, сложнее деплой

**Рекомендация:** Вариант A для продакшна, Вариант B для разработки.

## 13. Безопасность при удалённом доступе

1. **JWT токены** с ограниченным сроком (access: 1h, refresh: 24h)
2. **Пароли** хранятся в bcrypt
3. **CORS** настроен для доступа с любых устройств в локальной сети
4. **HTTPS** не требуется (всё в локальной сети)
5. **IP-фильтрация** (опционально) — можно ограничить доступ по IP-адресам
6. **Логирование** всех действий админа (кто, когда, что изменил)
7. **Автоматический logout** при бездействии (15 минут)
8. **API ключ** для внутренней коммуникации Tauri -> Python (защита от внешних запросов к публичным API)

## 14. Сборка и единый установщик

### Общая схема сборки

```
Исходники                          Сборка                    Установщик
──────────────────────────────────────────────────────────────────────────

frontend/                         frontend/dist/
  src/                              index.html       ─┐
  package.json    ── Vite build ──> assets/*.js      ─┤
                                    assets/*.css     ─┤
                                                     ─┤
backend/                          backend/dist/       ─┤
  app/                              python-backend/   ─┤
  requirements.txt ─ PyInstaller ─> python-backend.exe─┤
                                                     ─┤
src-tauri/                        src-tauri/target/   ─┤
  src/                              release/          ─┤
  Cargo.toml     ── cargo build ─> kiosk.exe         ─┤
  tauri.conf.json                   bundle/           ─┤
                                    school-kiosk.msi  ─┘
                                    school-kiosk.exe (NSIS)
```

### Этап 1: Сборка React (Vite)

```bash
cd frontend
npm install
npm run build
# Результат: frontend/dist/  (статический HTML+JS+CSS)
```

Tauri автоматически встраивает папку `frontend/dist/` в бинарник на этапе компиляции (через `tauri.conf.json` → `build.distDir`).

### Этап 2: Упаковка Python (PyInstaller)

```bash
cd backend
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile ^
    --name python-backend ^
    --hidden-import uvicorn ^
    --hidden-import sqlalchemy ^
    --add-data "app:app" ^
    app/main.py
# Результат: backend/dist/python-backend.exe  (~30-50MB)
```

**Параметр `--onefile`** создаёт один .exe, который при запуске распаковывается во временную папку. Это самодостаточный Python со всеми зависимостями.

### Этап 3: Сборка Tauri + создание установщика

```bash
cd src-tauri
cargo tauri build
# Результат:
#   src-tauri/target/release/kiosk.exe  (~5MB, сам Tauri)
#   src-tauri/target/release/bundle/msi/school-kiosk-1.0.0.msi
#   src-tauri/target/release/bundle/nsis/school-kiosk-1.0.0.exe
```

**Tauri bundler** делает следующее:
1. Компилирует Rust-код в `kiosk.exe`
2. Встраивает React-статику (`frontend/dist/`) внутрь `kiosk.exe`
3. Копирует `python-backend.exe` рядом с `kiosk.exe`
4. Создаёт установщик (MSI или NSIS), который включает оба файла

### Что входит в установщик

```
C:\Program Files\School Kiosk\
├── kiosk.exe              # Tauri + React (встроена статика)
├── python-backend.exe     # Python FastAPI (PyInstaller bundle)
├── school_kiosk.db        # SQLite (создаётся при первом запуске)
└── config.json            # Настройки (порт, автозапуск и т.д.)
```

**Итоговый размер установщика:** ~40-60 MB
- Python + зависимости: ~30-50 MB (PyInstaller)
- Tauri + React: ~5-8 MB
- Установщик (сжатие): ~20-30 MB

### Что НЕ нужно устанавливать на ПК пользователя

| Компонент | Где находится |
|-----------|--------------|
| Python 3.11 | Встроен в `python-backend.exe` |
| FastAPI + Uvicorn | Встроен в `python-backend.exe` |
| SQLAlchemy + SQLite | Встроен в `python-backend.exe` |
| Node.js / npm | Не нужен |
| Rust / Cargo | Не нужен |
| WebView2 Runtime | Уже есть на Windows 10/11 |

### Процесс запуска приложения

```
Пользователь запускает kiosk.exe
         │
         ▼
Tauri стартует
         │
         ├── 1. Запускает python-backend.exe как child process
         │         │
         │         ▼
         │    Python инициализирует БД (если нет — создаёт)
         │    Python запускает FastAPI на 0.0.0.0:8765
         │
         ├── 2. Ждёт health check от Python (GET /health)
         │
         ├── 3. Открывает WebView с React SPA
         │
         └── 4. Активирует киоск-режим (блокировка клавиш)
```

### Скрипт полной сборки (build.bat)

```batch
@echo off
echo === School Kiosk Build Script ===

echo [1/4] Installing frontend dependencies...
cd frontend
call npm install

echo [2/4] Building React frontend...
call npm run build

echo [3/4] Building Python backend...
cd ../backend
call pyinstaller --onefile --name python-backend app/main.py

echo [4/4] Building Tauri app + installer...
cd ../src-tauri
call cargo tauri build

echo === Build complete! ===
echo Installer: src-tauri/target/release/bundle/nsis/school-kiosk-*.exe
```

### Автоматизация через GitHub Actions (CI/CD)

```yaml
# .github/workflows/build.yml
name: Build and Release
on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Rust
        uses: actions-rust-lang/setup-rust-toolchain@v1

      - name: Build React
        run: |
          cd frontend
          npm install
          npm run build

      - name: Build Python
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pyinstaller
          pyinstaller --onefile --name python-backend app/main.py

      - name: Build Tauri
        run: |
          cd src-tauri
          cargo tauri build

      - name: Upload installer
        uses: actions/upload-artifact@v4
        with:
          name: school-kiosk-installer
          path: src-tauri/target/release/bundle/nsis/*.exe
```

## 15. Требования к окружению

### Для разработки
- **Python 3.11+** + pip
- **Node.js 18+** + npm/yarn
- **Rust** (rustup + cargo)
- **Tauri CLI** (`cargo install tauri-cli`)
- **WebView2 Runtime** (предустановлен на Win10/11)

### Для сборки (продакшн)
- Python bundled с приложением (PyInstaller)
- React собран в статику (Vite build)
- Tauri bundler создаёт единый .msi/.exe установщик
- Всё работает из коробки на чистой Windows 10/11