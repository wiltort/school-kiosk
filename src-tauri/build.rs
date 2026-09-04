use std::path::Path;

fn main() {
    // `bundle.resources` ссылается на `web/dist`. tauri-build требует, чтобы
    // ресурс существовал на этапе компиляции — в т.ч. при `cargo check`/
    // `clippy`/`dev` на свежем клоне, где этого каталога ещё нет. Создаём его
    // здесь. Реальные файлы SPA кладёт `scripts/copy-web.mjs` в рамках
    // `beforeBuildCommand` релизной сборки (`cargo tauri build`).
    let web_dist = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("web")
        .join("dist");
    std::fs::create_dir_all(&web_dist).expect("не удалось создать каталог ресурса web/dist");

    // Генерирует код-контекст Tauri из tauri.conf.json на этапе компиляции.
    tauri_build::build()
}
