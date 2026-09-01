@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title School Kiosk — Dev mode (Tauri)
cd /d "%~dp0..\src-tauri"

REM Добавляем MSVC-линкер в начало PATH (иначе в Git Bash конфликт
REM с GNU link.exe из MinGW и сборка падает).
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%VSWHERE%" (
    for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSINST=%%i"
    if defined VSINST (
        for /f %%d in ('dir /b /ad "%VSINST%\VC\Tools\MSVC" 2^>nul') do set "MSVCVER=%%d"
        if defined MSVCVER (
            set "MSVCBIN=%VSINST%\VC\Tools\MSVC\%MSVCVER%\bin\Hostx64\x64"
            if exist "%MSVCBIN%\link.exe" set "PATH=%MSVCBIN%;%PATH%"
        )
    )
)

REM Проверка: cargo tauri должен существовать (после установки tauri-cli).
where cargo-tauri >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [!] Tauri CLI не установлен. Запустите сначала scripts\setup.bat
    echo     или выполните: cargo install tauri-cli
    pause
    exit /b 1
)

REM cargo tauri dev сам поднимет Vite (beforeDevCommand) и откроет окно.
REM Python-бэкенд запускает Rust-ядро (process.rs) через Poetry.
call cargo tauri dev
endlocal
