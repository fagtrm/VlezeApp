# VlezeApp

<div align="center">

**VLESS VPN Manager** — десктопное приложение для управления VLESS конфигурациями и работы с Xray

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GTK](https://img.shields.io/badge/GTK-4.0+-green.svg)](https://www.gtk.org/)
[![Libadwaita](https://img.shields.io/badge/Libadwaita-1.0+-purple.svg)](https://gnome.pages.gitlab.gnome.org/libadwaita/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 Описание

VlezeApp — это современное десктопное приложение с графическим интерфейсом для управления VLESS конфигурациями и работы с прокси-сервером Xray. Построено на GTK4 и Libadwaita, обеспечивает нативный внешний вид в окружениях GNOME и других десктопных средах Linux.

## ✨ Возможности

- 🔗 **Парсинг VLESS ссылок** — полная поддержка формата `vless://` со всеми параметрами (TLS, Reality, WebSocket, gRPC, HTTP header, flow)
- ⚙️ **Генерация конфигов Xray** — автоматическое создание JSON конфигурации для запуска Xray
- 📑 **Табы конфигураций** — до 5 конфигураций с переключением по табам и удалением каждой
- 🚀 **Управление подключением** — кнопка старт/стоп в боковой панели, запуск, остановка и мониторинг состояния Xray в реальном времени
- 📡 **Проверка задержки** — пинг через SOCKS5 прокси для проверки работоспособности VPN
- 📥 **Загрузка конфигов** — скачивание base64 подписок из интернета или выбор локальных файлов
- 📋 **Системный трей** — иконка в трее с контекстным меню (D-Bus StatusNotifierItem)
- 🌍 **Локализация** — поддержка русского 🇷🇺 и английского 🇬🇧 языков
- ⚡ **Автозапуск** — автоматическое подключение при запуске приложения
- 💾 **Запоминание сервера** — восстановление последнего выбранного сервера

## 📦 Установка

### Системные зависимости

| Зависимость | Описание |
|-------------|----------|
| **Python 3.10+** | Язык программирования |
| **GTK4** | Графический фреймворк |
| **Libadwaita 1.0+** | Компоненты GNOME |
| **PyGObject** | Привязки GTK для Python |
| **Xray-core** | Прокси-сервер для VLESS |
| **curl** | Проверка задержки |

### Установка зависимостей

#### Arch Linux / Manjaro
```bash
sudo pacman -S python python-gobject gtk4 libadwaita xray curl
```

#### Fedora
```bash
sudo dnf install python3 python3-gobject gtk4 libadwaita curl
```

#### Ubuntu / Debian
```bash
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 curl
```

### Клонирование репозитория

```bash
git clone https://github.com/fagtrm/VlezeApp.git
cd VlezeApp
```

## 🚀 Запуск

```bash
python3 main.py
```

## 🌐 Локализация

Приложение определяет язык системы автоматически. Для переключения измените системную локаль.

### Компиляция переводов (после клонирования)

```bash
bash scripts/compile_locale.sh
```

> **Важно:** `.mo` файлы не хранятся в репозитории. После клонирования обязательно запустите компиляцию.

## 📄 Лицензия

MIT License — подробности в файле [LICENSE](LICENSE)

## 🤝 Вклад в проект

Приветствуется! Пожалуйста, создайте Issue или Pull Request.

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

<div align="center">

**VlezeApp** © 2026

</div>
