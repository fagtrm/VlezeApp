# VlezeApp

<div align="center">

**VLESS VPN Manager** — Desktop application for managing VLESS configurations and working with Xray

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GTK](https://img.shields.io/badge/GTK-4.0+-green.svg)](https://www.gtk.org/)
[![Libadwaita](https://img.shields.io/badge/Libadwaita-1.0+-purple.svg)](https://gnome.pages.gitlab.gnome.org/libadwaita/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 About

VlezeApp is a modern desktop GUI application for managing VLESS configurations and working with the Xray proxy server. Built with GTK4 and Libadwaita, it provides a native look and feel in GNOME and other Linux desktop environments.

## ✨ Features

- 🔗 **VLESS Link Parsing** — full support for `vless://` format with all parameters (TLS, Reality, WebSocket, gRPC, HTTP header, flow)
- ⚙️ **Xray Config Generation** — automatic JSON config creation for launching Xray
- 🚀 **Connection Management** — start, stop, and monitor Xray status in real-time
- 📡 **Latency Check** — ping via SOCKS5 proxy to verify VPN connectivity
- 📥 **Config Loading** — download base64 subscriptions from the internet or select local files
- 📋 **System Tray** — tray icon with context menu (D-Bus StatusNotifierItem)
- 🌍 **Localization** — Russian 🇷🇺 and English 🇬🇧 language support
- ⚡ **Auto-start** — automatic connection on application launch
- 💾 **Server Memory** — restore the last selected server

## 📦 Installation

### System Dependencies

| Dependency | Description |
|------------|-------------|
| **Python 3.10+** | Programming language |
| **GTK4** | GUI framework |
| **Libadwaita 1.0+** | GNOME components |
| **PyGObject** | GTK bindings for Python |
| **Xray-core** | Proxy server for VLESS |
| **curl** | Latency checking |

### Installing Dependencies

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

### Clone the Repository

```bash
git clone https://github.com/fagtrm/VlezeApp.git
cd VlezeApp
```

## 🚀 Usage

```bash
python3 main.py
```

## 🌐 Localization

The application automatically detects the system language.

### Compile Translations (after cloning)

```bash
bash scripts/compile_locale.sh
```

> **Important:** `.mo` files are not stored in the repository. After cloning, always run the compilation script.

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit an Issue or Pull Request.

1. Fork the repository
2. Create a branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<div align="center">

**VlezeApp** © 2026

</div>
