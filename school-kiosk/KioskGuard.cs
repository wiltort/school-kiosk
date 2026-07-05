using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace SchoolKiosk
{
    /// <summary>
    /// Класс для блокировки системных комбинаций клавиш
    /// </summary>
    public class KioskGuard
    {
        // Константы для Windows API
        private const int WM_SYSKEYDOWN = 0x0104;
        private const int WM_SYSKEYUP = 0x0105;
        private const int WM_KEYDOWN = 0x0100;
        private const int WM_KEYUP = 0x0101;
        private const int WM_CLOSE = 0x0010;
        private const int WM_DESTROY = 0x0002;
        private const int WM_QUIT = 0x0012;

        // Виртуальные коды клавиш
        private const int VK_F4 = 0x73;
        private const int VK_ESCAPE = 0x1B;
        private const int VK_RETURN = 0x0D;
        private const int VK_LWIN = 0x5B;
        private const int VK_RWIN = 0x5C;
        private const int VK_APPS = 0x5D; // Клавиша контекстного меню
        private const int VK_TAB = 0x09;
        private const int VK_CONTROL = 0x11;
        private const int VK_MENU = 0x12; // Alt
        private const int VK_DELETE = 0x2E;

        private readonly Window _window;
        private HwndSource _source;
        private bool _isClosed = false;

        public KioskGuard(Window window)
        {
            _window = window;
            _window.SourceInitialized += OnSourceInitialized;
            _window.Closed += OnWindowClosed;
        }

        private void OnSourceInitialized(object sender, EventArgs e)
        {
            _source = PresentationSource.FromVisual(_window) as HwndSource;
            if (_source != null)
            {
                _source.AddHook(HwndHook);

                // Устанавливаем стиль окна для предотвращения закрытия
                var handle = _source.Handle;
                var style = GetWindowLong(handle, GWL_STYLE);
                style &= ~WS_SYSMENU; // Убираем кнопку закрытия
                SetWindowLong(handle, GWL_STYLE, style);
            }
        }

        private void OnWindowClosed(object sender, EventArgs e)
        {
            _isClosed = true;
            if (_source != null)
            {
                _source.RemoveHook(HwndHook);
            }
        }

        private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            if (_isClosed) return IntPtr.Zero;

            switch (msg)
            {
                case WM_SYSKEYDOWN:
                case WM_SYSKEYUP:
                case WM_KEYDOWN:
                case WM_KEYUP:
                    handled = HandleKeyPress(msg, wParam, lParam);
                    break;

                case WM_CLOSE:
                case WM_DESTROY:
                case WM_QUIT:
                    // Блокируем закрытие окна
                    handled = true;
                    return IntPtr.Zero;
            }

            return IntPtr.Zero;
        }

        private bool HandleKeyPress(int msg, IntPtr wParam, IntPtr lParam)
        {
            int keyCode = wParam.ToInt32();
            int flags = lParam.ToInt32();
            bool altPressed = (flags & 0x20000000) != 0;

            // Проверяем нажатия
            bool isDown = (msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN);

            // Список блокируемых комбинаций
            // 1. Alt + F4
            if (altPressed && keyCode == VK_F4)
            {
                return true; // Блокируем
            }

            // 2. Alt + Tab
            if (altPressed && keyCode == VK_TAB)
            {
                return true;
            }

            // 3. Win (Windows key)
            if (keyCode == VK_LWIN || keyCode == VK_RWIN)
            {
                return true;
            }

            // 4. Ctrl + Alt + Delete
            if (keyCode == VK_DELETE &&
                (IsKeyDown(VK_CONTROL) && IsKeyDown(VK_MENU)))
            {
                return true;
            }

            // 5. Escape
            if (keyCode == VK_ESCAPE && !altPressed)
            {
                // Можно разрешить Escape в режиме администратора
                if (!IsAdminMode)
                {
                    return true;
                }
            }

            // 6. Контекстное меню (клавиша между Alt и Ctrl)
            if (keyCode == VK_APPS)
            {
                return true;
            }

            return false;
        }

        // Проверка состояния клавиш
        [DllImport("user32.dll")]
        private static extern short GetAsyncKeyState(int vKey);

        private bool IsKeyDown(int vKey)
        {
            return (GetAsyncKeyState(vKey) & 0x8000) != 0;
        }

        // Windows API для управления стилем окна
        private const int GWL_STYLE = -16;
        private const int WS_SYSMENU = 0x00080000;

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int GetWindowLong(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

        // Флаг для режима администратора
        public bool IsAdminMode { get; set; } = false;

        // Метод для разрешения выхода (например, по паролю)
        public void ExitKiosk()
        {
            // Закрываем приложение
            Application.Current.Shutdown();
        }
    }
}