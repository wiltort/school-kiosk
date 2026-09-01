@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title School Kiosk — Setup Environment
cd /d "%~dp0.."

echo ============================================
echo  School Kiosk — Первоначальная настройка
echo ============================================
echo.

REM ---------- 0. MSVC linker в начало PATH ----------
REM Важно! В Git Bash / MINGW64 на PATH стоит GNU-версия link.exe из MinGW,
REM которая конфликтует с MSVC-линкером. Добавляем MSVC-линкер первым.
call :setup_msvc
echo.

REM ---------- 1. Rust (rustup + cargo) ----------
where rustc >nul 2>nul
if %errorlevel%==0 (
    echo [OK] Rust:
    rustc --version
) else (
    echo [1/5] Rust не найден. Установите rustup с https://rustup.rs
    pause
)

REM ---------- 2. Проверка MSVC linker ----------
echo [2/5] Проверка MSVC linker...
if defined MSVCBIN (
    echo       Найден: %MSVCBIN%\link.exe
) else (
    echo       [!] MSVC linker не найден. Установите "Visual Studio Build Tools 2022"
    echo           с нагрузкой "Desktop development with C++".
    echo           winget install Microsoft.VisualStudio.2022.BuildTools --override "--wait --quiet --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64"
    pause
)

REM ---------- 3. WebView2 Runtime ----------
echo [3/5] WebView2 Runtime обычно предустановлен на Windows 10/11.
echo       Если нет: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

REM ---------- 4. Tauri CLI ----------
where cargo-tauri >nul 2>nul
if %errorlevel%==0 (
    echo [OK] Tauri CLI уже установлен.
) else (
    echo [4/5] Устанавливаем Tauri CLI ^(долго, ~5 мин^)...
    cargo install tauri-cli
    if %errorlevel% neq 0 (
        echo.
        echo [FAIL] Не удалось установить tauri-cli.
        echo        Проверьте, что MSVC-линкер найден ^(см. выше^).
        echo        Повторно запустите этот скрипт или:
        echo        call "%%VSINST%%\VC\Auxiliary\Build\vcvars64.bat" ^&^& cargo install tauri-cli
        pause
        exit /b 1
    )
)

REM ---------- 5. Frontend (npm) ----------
echo [5/5] Зависимости frontend (React/Vite)...
cd /d "%~dp0..\frontend"
if exist node_modules (
    echo [OK] node_modules уже есть.
) else (
    call npm install
)

REM ---------- Backend (Poetry) ----------
echo.
echo Зависимости backend (Poetry)...
cd /d "%~dp0..\backend"
where poetry >nul 2>nul
if %errorlevel%==0 (
    call poetry install
) else (
    echo [WARN] Poetry не найден. pip install poetry, затем poetry install
)

echo.
echo ============================================
echo  Готово! Запуск: scripts\dev.bat
echo ============================================
pause
endlocal
exit /b

REM ============================================================================
REM Находит папку MSVC-линкера (Hostx64\x64) через vswhere и добавляет её в PATH.
REM Устанавливает переменную MSVCBIN при успехе.
REM ============================================================================
:setup_msvc
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
    echo [!] vswhere не найден. MSVC, видимо, не установлен.
    exit /b 0
)
for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSINST=%%i"
if not defined VSINST (
    echo [!] Visual Studio Build Tools с C++ workload не найден.
    exit /b 0
)
for /f %%d in ('dir /b /ad "%VSINST%\VC\Tools\MSVC" 2^>nul') do set "MSVCVER=%%d"
if not defined MSVCVER exit /b 0
set "MSVCBIN=%VSINST%\VC\Tools\MSVC\%MSVCVER%\bin\Hostx64\x64"
if exist "%MSVCBIN%\link.exe" (
    set "PATH=%MSVCBIN%;%PATH%"
    echo [MSVC] Добавлен линкер в PATH: %MSVCBIN%
) else (
    echo [!] link.exe не найден в %MSVCBIN%
    set "MSVCBIN="
)
exit /b 0
