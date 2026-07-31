# Third-Party Notices

Flux bundles and depends on third-party software. This file lists the components,
their licenses, and their obligations. The full text of licenses referenced below
is available at the linked URLs; the license of the project itself is GPL-3.0
(see `LICENSE`).

## Bundled binaries

| Component | Version/source | License | Notes |
|---|---|---|---|
| [sing-box](https://github.com/SagerNet/sing-box) (`bin/sing-box.exe`) | official release build | GPL-3.0-or-later | Copyleft: source available upstream; the app is distributed under GPL-3.0 as well. |
| [Xray-core](https://github.com/XTLS/Xray-core) (`bin/xray.exe`) | official release build | MPL-2.0 | File-level license. Source: https://github.com/XTLS/Xray-core. This notice must be preserved. |
| [wintun](https://www.wintun.net/) (`bin/wintun.dll`) | official signed build, wintun 0.14.1 | WireGuard LLC Prebuilt Binaries License | Redistribution permitted only alongside software that uses wintun exclusively via its public API. Do not modify, reverse-engineer, or use the WireGuard/Wintun names to endorse this product. The license text is reproduced in `bin/wintun-license.txt`. |
| [AmneziaVPN / AmneziaWG](https://github.com/amnezia-vpn/amnezia-client) (`bin/AmneziaLib.dll`, `bin/tunnel.dll`, `bin/tunnel_service.exe`) | official release build | GPL-3.0 (amnezia-client) / GPL-2.0 (amneziawg, a WireGuard fork) | Copyleft; source available upstream. |

## Python dependencies

| Package | License |
|---|---|
| [PyQt6](https://pypi.org/project/PyQt6/) | GPL-3.0 (or commercial Qt license) — the application is therefore licensed under GPL-3.0 |
| [requests](https://pypi.org/project/requests/) | Apache-2.0 |
| [urllib3](https://pypi.org/project/urllib3/) | MIT |
| [cryptography](https://pypi.org/project/cryptography/) | Apache-2.0 / BSD |

## Build tooling

| Tool | License |
|---|---|
| [PyInstaller](https://pyinstaller.org/) | GPL-2.0 with a bootloader exception; does not impose GPL on the bundled application |

## Assets

- Country flag images (`assets/flags/*.png`) are sourced from
  [flagcdn.com](https://flagcdn.com/). Flag artwork is in the public domain
  (Wikimedia Commons) or distributed under the MIT License (flag-icons project).
- Application icon (`bin/flux.ico`) — project asset of Flux.

## wintun Prebuilt Binaries License (reproduced)

```
Prebuilt Binaries License
-------------------------

1. DEFINITIONS. "Software" means the precise contents of the "wintun.dll"
   files that are included in the .zip file that contains this document as
   downloaded from wintun.net/builds.

2. LICENSE GRANT. WireGuard LLC grants to you a non-exclusive and
   non-transferable right to use Software for lawful purposes under certain
   obligations and limited rights as set forth in this agreement.

3. RESTRICTIONS. Software is owned and copyrighted by WireGuard LLC. It is
   licensed, not sold. Title to Software and all associated intellectual
   property rights are retained by WireGuard. You must not:
   a. reverse engineer, decompile, disassemble, extract from, or otherwise
      modify the Software;
   b. modify or create derivative work based upon Software in whole or in
      parts, except insofar as only the API interfaces of the "wintun.h" file
      distributed alongside the Software (the "Permitted API") are used;
   c. remove any proprietary notices, labels, or copyrights from the Software;
   d. resell, redistribute, lease, rent, transfer, sublicense, or otherwise
      transfer rights of the Software without the prior written consent of
      WireGuard LLC, except insofar as the Software is distributed alongside
      other software that uses the Software only via the Permitted API;
   e. use the name of WireGuard LLC, the WireGuard project, the Wintun
      project, or the names of its contributors to endorse or promote products
      derived from the Software without specific prior written consent.

4. LIMITED WARRANTY.
THE SOFTWARE IS PROVIDED "AS IS" AND WITHOUT WARRANTY OF ANY KIND.
...

(full text: https://github.com/WireGuard/wintun/blob/master/prebuilt-binaries-license.txt)
```
