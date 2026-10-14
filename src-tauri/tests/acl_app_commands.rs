//! Регрессионный тест: кастомные IPC-команды приложения разрешены из
//! remote-origin (`http://127.0.0.1:8765`), который использует WebView в
//! release-сборке.
//!
//! Без разрешений из `src-tauri/permissions/` команды (`is_admin_active`,
//! `clear_admin_mode`, `set_exit_allowed` и т.д.) блокируются ACL Tauri для
//! remote-origin (см. `Webview::on_message` в tauri 2.11):
//! `(plugin_command.is_some() || has_app_acl_manifest || !is_local)
//!  && invoke.acl.is_none()` → reject. В dev WebView грузится с
//! `http://localhost:5173` (local origin), поэтому несоответствие незаметно,
//! а в release страницу раздаёт Python-бэкенд (`http://127.0.0.1:8765`) — и
//! админка по Ctrl+Shift+A не открывается.

use std::collections::BTreeMap;
use std::path::PathBuf;

use tauri_utils::acl::capability::{Capability, CapabilityFile};
use tauri_utils::acl::manifest::{Manifest, PermissionFile};
use tauri_utils::acl::resolved::Resolved;
use tauri_utils::acl::{ExecutionContext, APP_ACL_KEY};
use tauri_utils::platform::Target;
use url::Url;

/// Кастомные команды, зарегистрированные в `generate_handler!` (см. lib.rs).
const APP_COMMANDS: [&str; 7] = [
    "exit_app",
    "restart_app",
    "is_admin_active",
    "clear_admin_mode",
    "set_exit_allowed",
    "get_update_channel",
    "get_update_status",
];

/// Origin WebView в release: SPA раздаёт Python-бэкенд на этом адресе.
const REMOTE_ORIGIN: &str = "http://127.0.0.1:8765/";

/// Окно, к которому привязана capability `default`.
const WINDOW: &str = "main";

/// Собирает ACL-манифест приложения из TOML-файлов в `src-tauri/permissions/`.
fn load_app_manifest() -> Manifest {
    let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("permissions");
    let mut permission_files = Vec::new();
    for entry in std::fs::read_dir(&dir).expect("каталог permissions должен существовать")
    {
        let path = entry.expect("read_dir entry").path();
        if path.extension().is_some_and(|ext| ext == "toml") {
            let content = std::fs::read_to_string(&path).expect("read permission file");
            permission_files
                .push(toml::from_str::<PermissionFile>(&content).expect("parse permission file"));
        }
    }
    Manifest::new(permission_files, None)
}

/// Загружает `src-tauri/capabilities/default.json`, оставляя только разрешения
/// приложения (`default`). Манифесты `core:`/`opener:` принадлежат крейтам
/// Tauri и в этом тесте не нужны — проверяем именно кастомные команды.
fn load_capability() -> Capability {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("capabilities")
        .join("default.json");
    let content = std::fs::read_to_string(&path).expect("read capability file");
    let mut capability =
        match serde_json::from_str::<CapabilityFile>(&content).expect("parse capability file") {
            CapabilityFile::Capability(capability) => capability,
            _ => panic!("ожидался одиночный capability"),
        };
    capability
        .permissions
        .retain(|p| p.identifier().as_ref() == "default");
    capability
}

/// Все кастомные команды должны резолвиться в `allowed_commands` с контекстом
/// Remote, матчащим реальный origin release-сборки.
#[test]
fn custom_commands_allowed_from_remote_origin() {
    let mut acl: BTreeMap<String, Manifest> = BTreeMap::new();
    acl.insert(APP_ACL_KEY.to_string(), load_app_manifest());

    let mut capabilities = BTreeMap::new();
    let capability = load_capability();
    capabilities.insert(capability.identifier.clone(), capability);

    let resolved = Resolved::resolve(&acl, capabilities, Target::current())
        .expect("ACL должен резолвиться из permissions и capabilities");
    let origin = Url::parse(REMOTE_ORIGIN).expect("валидный origin");

    for command in APP_COMMANDS {
        let entries = resolved
            .allowed_commands
            .get(command)
            .unwrap_or_else(|| panic!("команда {command} отсутствует в allowed_commands"));

        let remote_ok = entries.iter().any(|cmd| {
            cmd.windows.iter().any(|w| w.matches(WINDOW))
                && matches!(
                    &cmd.context,
                    ExecutionContext::Remote { url } if url.test(&origin)
                )
        });
        assert!(
            remote_ok,
            "команда {command} должна быть разрешена из remote-origin \
             {REMOTE_ORIGIN} для окна {WINDOW} — проверьте src-tauri/permissions/ \
             и capability default.json"
        );
    }
}

/// Команды должны сохранять доступ и из local-контекста (dev/Vite), т.к. после
/// появления app-ACL-манифеста проверка ACL включается и для local-origin.
#[test]
fn custom_commands_keep_local_access() {
    let mut acl: BTreeMap<String, Manifest> = BTreeMap::new();
    acl.insert(APP_ACL_KEY.to_string(), load_app_manifest());

    let mut capabilities = BTreeMap::new();
    let capability = load_capability();
    capabilities.insert(capability.identifier.clone(), capability);

    let resolved = Resolved::resolve(&acl, capabilities, Target::current())
        .expect("ACL должен резолвиться из permissions и capabilities");

    for command in APP_COMMANDS {
        let entries = resolved
            .allowed_commands
            .get(command)
            .unwrap_or_else(|| panic!("команда {command} отсутствует в allowed_commands"));
        let local_ok = entries
            .iter()
            .any(|cmd| matches!(cmd.context, ExecutionContext::Local));
        assert!(
            local_ok,
            "команда {command} должна быть доступна и из local-origin (dev)"
        );
    }
}
