; ============================================================================
; School Kiosk — installer hooks (Tauri v2 / NSIS)
;
; Подключается через "bundle.windows.nsis.installerHooks" в tauri.conf.json.
; Это официальный механизм расширения установщика, который НЕ заменяет
; стандартный скрипт инсталлятора Tauri (в отличие от nsis.template).
;
; Что делает: позволяет задать каталог статики прямо при установке автономного
; установщика через параметр командной строки:
;
;   School-Kiosk-setup.exe /S /STATICDIR="D:\KioskStatic"
;   School-Kiosk-setup.exe /STATICDIR=C:\Static
;
; Если параметр не указан — ничего не пишется, и бэкенд использует каталог
; данных приложения по умолчанию. Выбранный путь сохраняется в
; %APPDATA%\com.schoolkiosk.app\settings.json — тот же файл, что читает
; Rust-оболочка (см. src-tauri/src/settings.rs).
;
; ВНИМАНИЕ: используются ТОЛЬКО штатные регистры NSIS ($0-$9, $R0-$R9),
; т.к. хук разворачивается внутри секции установщика, где нельзя объявлять
; собственные переменные директивой Var.
;
; Назначение регистров:
;   $R0 = подстрока-маркер "STATICDIR="
;   $R1 = длина маркера
;   $R2 = индекс поиска
;   $R3 = временный буфер (символ/подстрока)
;   $R4 = итоговый путь (значение STATICDIR)
;   $R5 = выходной буфер после замены '\' -> '/'
;   $R6 = длины/смещения
;   $R7 = индекс обрезки
; ============================================================================

!macro NSIS_HOOK_POSTINSTALL
  ; --------------------------------------------------------------------------
  ; Поиск подстроки "STATICDIR=" в $CMDLINE
  ; --------------------------------------------------------------------------
  StrCpy $R0 "STATICDIR="
  StrLen $R1 $R0
  StrCpy $R4 ""
  StrCpy $R2 0

  sk_find_loop:
    StrLen $R6 $CMDLINE
    IntCmp $R2 $R6 sk_done_write 0 sk_find_cont
  sk_find_cont:
    StrCpy $R3 $CMDLINE $R1 $R2
    StrCmp $R3 $R0 sk_found 0
    IntOp $R2 $R2 + 1
    Goto sk_find_loop

  sk_found:
    ; Значение начинается сразу после "STATICDIR="
    IntOp $R6 $R2 + $R1
    StrCpy $R4 $CMDLINE "" $R6

    ; Путь может быть в кавычках: /STATICDIR="D:\Static"
    StrCpy $R3 $R4 1
    StrCmp $R3 '$\"' 0 sk_no_open_quote

    ; Снимаем открывающую кавычку и режем до закрывающей.
    StrCpy $R4 $R4 "" 1
    StrLen $R6 $R4
    StrCpy $R7 0
    sk_quote_loop:
      IntCmp $R7 $R6 sk_after_parse 0 sk_quote_cont
    sk_quote_cont:
      StrCpy $R3 $R4 1 $R7
      StrCmp $R3 '$\"' sk_quote_found 0
      IntOp $R7 $R7 + 1
      Goto sk_quote_loop
    sk_quote_found:
      StrCpy $R4 $R4 $R7
      Goto sk_after_parse

    sk_no_open_quote:
      ; Без кавычек — обрезаем по первому пробелу / концу строки.
      StrLen $R6 $R4
      StrCpy $R7 0
      sk_space_loop:
        IntCmp $R7 $R6 sk_after_parse 0 sk_space_cont
      sk_space_cont:
        StrCpy $R3 $R4 1 $R7
        StrCmp $R3 " " sk_space_found 0
        IntOp $R7 $R7 + 1
        Goto sk_space_loop
      sk_space_found:
        StrCpy $R4 $R4 $R7

  sk_after_parse:
    StrCmp $R4 "" sk_done_write

    ; ------------------------------------------------------------------------
    ; Заменяем '\' на '/' — валидный JSON и понятный Windows-путь.
    ; ------------------------------------------------------------------------
    StrCpy $R5 ""
    sk_rep_loop:
      StrLen $R6 $R4
      IntCmp $R6 0 sk_rep_done 0 sk_rep_cont
    sk_rep_cont:
      StrCpy $R3 $R4 1
      StrCmp $R3 "\" sk_is_slash 0
      StrCpy $R5 "$R5$R3"
      Goto sk_rep_next
    sk_is_slash:
      StrCpy $R5 "$R5/"
    sk_rep_next:
      StrCpy $R4 $R4 "" 1
      Goto sk_rep_loop
    sk_rep_done:
      StrCpy $R4 $R5

    ; ------------------------------------------------------------------------
    ; Запись settings.json
    ; ------------------------------------------------------------------------
    CreateDirectory "$APPDATA\com.schoolkiosk.app"
    FileOpen $0 "$APPDATA\com.schoolkiosk.app\settings.json" w
    FileWrite $0 '{ "static_dir": "$R4" }$\r$\n'
    FileClose $0
    DetailPrint "Каталог статики сохранён: $R4"

  sk_done_write:
!macroend
