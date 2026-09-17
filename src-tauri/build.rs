use std::env;
use std::fs;
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
    fs::create_dir_all(&web_dist).expect("не удалось создать каталог ресурса web/dist");

    // `bundle.externalBin` объявляет `binaries/python-backend`, а tauri-build
    // требует, чтобы файл `binaries/python-backend-<target-triple>` существовал
    // на этапе компиляции (в т.ч. при `cargo check`/`clippy`/`dev` на свежем
    // клоне, где реального бинарника ещё нет). Создаём пустой placeholder.
    // Реальный бинарник кладёт `make build-backend`
    // (binaries/python-backend-<host>[.exe]).
    let target = env::var("TARGET").expect("cargo должен задавать переменную TARGET");
    let exe_suffix = if target.contains("windows") {
        ".exe"
    } else {
        ""
    };
    let bin_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("binaries")
        .join(format!("python-backend-{target}{exe_suffix}"));
    if !bin_path.exists() {
        fs::create_dir_all(bin_path.parent().expect("binaries path has parent"))
            .expect("не удалось создать каталог binaries");
        fs::write(&bin_path, []).expect("не удалось создать placeholder externalBin");
    }

    // Генерирует код-контекст Tauri из tauri.conf.json на этапе компиляции.
    tauri_build::build()
}
