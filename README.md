# Flux

**Flux** — быстрый и бесплатный VPN-клиент для Windows. Шесть протоколов: VLESS, VMess, Shadowsocks, Trojan, Hysteria2, AmneziaWG; системный TUN-туннель, тест скорости и пинг серверов встроены. Тёмный интерфейс, без аккаунтов, открытый исходный код..

## Features

- **All major protocols**: VLESS, VMess, Shadowsocks, Trojan, Hysteria2, and AmneziaWG (AWG).
- Two tunnel cores: [sing-box](https://github.com/SagerNet/sing-box) and [Xray-core](https://github.com/XTLS/Xray-core).
- System-wide TUN adapter (wintun) — all traffic goes through the tunnel.
- Subscription import (base64 / URI lists) and manual AWG `.conf` import.
- Server list with country flags, latency check (TCP ping) and active-server highlighting.
- Speed test (download/upload via Cloudflare's public speedtest endpoints).
- Built-in traffic monitoring, log viewer, dark UI, tray icon, RU/EN localization.
- Single-file distribution: PyInstaller bundles Python runtime, both cores and all assets.

## Возможности

- **Все основные протоколы**: VLESS, VMess, Shadowsocks, Trojan, Hysteria2 и AmneziaWG (AWG).
- Два ядра туннелирования: [sing-box](https://github.com/SagerNet/sing-box) и [Xray-core](https://github.com/XTLS/Xray-core).
- Системный TUN-адаптер (wintun) — весь трафик идёт через туннель.
- Импорт подписок (base64 / списки URI) и ручной импорт AWG-конфигов (`.conf`).
- Список серверов с флагами стран, проверкой задержки (TCP ping) и подсветкой активного сервера.
- Тест скорости (скачивание/отправка через публичные эндпоинты Cloudflare).
- Мониторинг трафика, просмотр логов, тёмный интерфейс, иконка в трее, локализация RU/EN.
- Распространение одним файлом: PyInstaller упаковывает рантайм Python, оба ядра и все ресурсы.

## Requirements / Требования

- Windows 10/11 (x64)
- Administrator rights (TUN driver installation and the AmneziaWG service)
- Права администратора (установка TUN-драйвера и службы AmneziaWG)

## Building from source / Сборка из исходников

```bash
pip install -r requirements.txt
pip install pyinstaller
# place sing-box.exe, xray.exe, wintun.dll, AmneziaLib.dll, tunnel.dll,
# tunnel_service.exe, flux.ico into bin/ (official release builds)
python -m PyInstaller build_v2.spec
```

The resulting `Flux.exe` is a fully self-contained single file.

## Support / Поддержка

If you find Flux useful, you can support the development with a one-time donation:

[Donate on DonationAlerts](https://www.donationalerts.com/r/armchflow)

Если проект вам полезен, вы можете поддержать разработку разовым донатом:

[Донат на DonationAlerts](https://www.donationalerts.com/r/armchflow)

## License / Лицензия

Flux is free software released under the **GNU General Public License v3.0**
(`LICENSE`). Third-party components and their licenses are listed in
`THIRD_PARTY_NOTICES.md`.

## Disclaimer

This software is provided "as is", for lawful purposes. You are responsible
for complying with the laws and regulations applicable in your jurisdiction.
The author does not provide any proxy or VPN service, does not operate any
servers, and is not liable for how the software is used.

Отказ от ответственности: ПО предоставляется «как есть» для законных целей.
Вы несёте ответственность за соблюдение законодательства вашей юрисдикции.
Автор не предоставляет услуг прокси или VPN, не управляет серверами и не
несёт ответственности за способ использования программы.
