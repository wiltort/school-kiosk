using Microsoft.Web.WebView2.Wpf;
using System;
using System.IO;
using System.Windows;
using System.Windows.Input;

namespace SchoolKiosk
{
    public partial class MainWindow : Window
    {
        private bool _isAdminMode = false;
        private string _reactAppPath;
        private KioskGuard _kioskGuard;

        public MainWindow()
        {
            InitializeComponent();

            // Путь к React приложению (сборка)
            _reactAppPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "react-build", "index.html");

            _kioskGuard = new KioskGuard(this);

            // Подписка на событие загрузки окна
            this.Loaded += MainWindow_Loaded;
        }

        private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                // 1. Инициализация WebView2
                await webView.EnsureCoreWebView2Async(null);

                // 2. Дополнительные настройки WebView2
                ConfigureWebView();

                // 3. Загрузка React приложения
                await LoadReactApp();

                // 4. Запуск киоск-режима (блокировка)
                InitializeKioskMode();
                this.KeyDown += OnKeyDown;

            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка инициализации: {ex.Message}",
                              "Ошибка",
                              MessageBoxButton.OK,
                              MessageBoxImage.Error);
            }
        }
        private void OnKeyDown(object sender, KeyEventArgs e)
        {
            // Секретная комбинация для администратора: Ctrl + Shift + A
            if (Keyboard.Modifiers == (ModifierKeys.Control | ModifierKeys.Shift) &&
                e.Key == Key.A)
            {
                ToggleAdminMode();
                e.Handled = true;
            }

            // Выход из киоска: Ctrl + Alt + X (только в режиме администратора)
            if (_isAdminMode &&
                Keyboard.Modifiers == (ModifierKeys.Control | ModifierKeys.Alt) &&
                e.Key == Key.X)
            {
                _kioskGuard.ExitKiosk();
                e.Handled = true;
            }
        }
        private void ConfigureWebView()
        {
            // Отключаем контекстное меню (правый клик)
            webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;

            // Отключаем DevTools (F12)
            webView.CoreWebView2.Settings.AreDevToolsEnabled = false;

            // Отключаем зум (Ctrl+колесо)
            webView.CoreWebView2.Settings.IsZoomControlEnabled = false;

            // Включаем поддержку JavaScript
            webView.CoreWebView2.Settings.IsScriptEnabled = true;
        }

        private async Task LoadReactApp()
        {
            // Проверяем, есть ли собранное React приложение
            if (File.Exists(_reactAppPath))
            {
                // Загружаем локальную сборку
                webView.Source = new Uri(_reactAppPath);
            }
            else
            {
                // Если сборки нет, используем режим разработки
                // (должен быть запущен npm start)
                webView.Source = new Uri("http://localhost:3000");

                // Показываем предупреждение на 5 секунд
                await ShowDevelopmentWarning();
            }
        }

        private async Task ShowDevelopmentWarning()
        {
            // Можно добавить индикатор, что приложение в режиме разработки
            AdminIndicator.Visibility = Visibility.Visible;
            AdminIndicator.Background = System.Windows.Media.Brushes.Orange;
            AdminIndicator.ToolTip = "Режим разработки (ожидается localhost:3000)";

            await Task.Delay(5000);
        }

        private void InitializeKioskMode()
        {
            // Фокус на окне
            this.Focus();

            // Скрываем курсор через 3 секунды бездействия
            var timer = new System.Timers.Timer(3000);
            timer.Elapsed += (s, e) =>
            {
                Dispatcher.Invoke(() =>
                {
                    if (!_isAdminMode)
                    {
                        Mouse.OverrideCursor = Cursors.None;
                    }
                });
            };
            timer.Start();

            // Показываем курсор при движении мыши
            this.MouseMove += (s, e) =>
            {
                Mouse.OverrideCursor = null;
                timer.Stop();
                timer.Start();
            };
        }

        // Метод для переключения в режим администратора
        public void ToggleAdminMode()
        {
            _isAdminMode = !_isAdminMode;
            _kioskGuard.IsAdminMode = _isAdminMode;
            // Визуальный индикатор
            AdminIndicator.Visibility = _isAdminMode ? Visibility.Visible : Visibility.Collapsed;

            if (_isAdminMode)
            {
                AdminIndicator.Background = System.Windows.Media.Brushes.Red;
                AdminIndicator.ToolTip = "Режим администратора активен";
                Mouse.OverrideCursor = null;

                // Показываем сообщение (опционально)
                MessageBox.Show("Режим администратора активирован.\n" +
                               "Для выхода нажмите Ctrl+Alt+X",
                               "Информация",
                               MessageBoxButton.OK,
                               MessageBoxImage.Information);
            }
            else
            {
                Mouse.OverrideCursor = Cursors.None;
                AdminIndicator.ToolTip = "Режим администратора";
            }
        }
    }
}