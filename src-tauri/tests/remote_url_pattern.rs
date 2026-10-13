//! Регрессионный тест: сопоставление remote-URL из `capabilities/default.json`
//! с реальным origin WebView.
//!
//! В release-сборке WebView грузит SPA с `http://127.0.0.1:8765` (бэкенд),
//! и IPC (`invoke`/`listen`) разрешён только если origin попадает под
//! `capabilities[].remote.urls` (URLPattern, см. tauri-utils
//! `RemoteUrlPattern::from_str`).
//!
//! Ключевой момент: паттерн `http://127.0.0.1` БЕЗ порта НЕ матчит
//! `http://127.0.0.1:8765` (порт в URLPattern по умолчанию — пустая строка,
//! т.е. только дефолтный порт 80). Поэтому в старых сборках IPC из WebView
//! молча блокировался и админка по Ctrl+Shift+A не открывалась. Рабочий
//! паттерн — `http://127.0.0.1:*`.

use urlpattern::{UrlPattern, UrlPatternInit, UrlPatternMatchInput};

/// Воспроизводит логику `tauri_utils::acl::RemoteUrlPattern::from_str`.
fn compile_pattern(s: &str) -> UrlPattern {
    let mut init = UrlPatternInit::parse_constructor_string::<regex::Regex>(s, None)
        .unwrap_or_else(|e| panic!("невалидный URLPattern {s:?}: {e}"));
    if init.search.as_ref().map(|p| p.is_empty()).unwrap_or(true) {
        init.search.replace("*".to_string());
    }
    if init.hash.as_ref().map(|p| p.is_empty()).unwrap_or(true) {
        init.hash.replace("*".to_string());
    }
    if init
        .pathname
        .as_ref()
        .map(|p| p.is_empty() || p == "/")
        .unwrap_or(true)
    {
        init.pathname.replace("*".to_string());
    }
    UrlPattern::parse(init, Default::default())
        .unwrap_or_else(|e| panic!("не удалось собрать URLPattern {s:?}: {e}"))
}

fn matches(pattern: &str, url: &str) -> bool {
    let pattern = compile_pattern(pattern);
    let url = url::Url::parse(url).expect("валидный URL");
    pattern
        .test(UrlPatternMatchInput::Url(url))
        .unwrap_or_default()
}

/// Старый (сломанный) паттерн без порта НЕ должен матчить бэкенд-порт.
#[test]
fn pattern_without_port_does_not_match_backend_port() {
    assert!(!matches("http://127.0.0.1", "http://127.0.0.1:8765/"));
    assert!(!matches("http://localhost", "http://localhost:8765/"));
}

/// Рабочий паттерн с wildcard-портом матчит бэкенд (release) и Vite (dev).
#[test]
fn pattern_with_port_wildcard_matches_backend_and_vite() {
    assert!(matches("http://127.0.0.1:*", "http://127.0.0.1:8765/"));
    assert!(matches(
        "http://127.0.0.1:*",
        "http://127.0.0.1:8765/?v=0.1.0-dev.14"
    ));
    assert!(matches("http://localhost:*", "http://localhost:5173/"));
}

/// Паттерн без порта матчит только дефолтный порт (80) — sanity check.
#[test]
fn pattern_without_port_matches_default_port() {
    assert!(matches("http://127.0.0.1", "http://127.0.0.1/"));
}

/// Чужой хост не должен матчить.
#[test]
fn other_host_is_not_matched() {
    assert!(!matches("http://127.0.0.1:*", "http://192.168.1.10:8765/"));
}
