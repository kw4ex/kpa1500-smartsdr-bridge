# KPA1500 SmartSDR Bridge (experimental)

**Experimental. Windows only for now.** The installer and helper files are Windows batch files. Versions for Mac, Linux and Raspberry Pi are being tested and are not released yet.

Makes a **FlexRadio running SmartSDR** show your **Elecraft KPA1500** as a **Power Genius XL** amplifier and a **Tuner Genius XL** tuner. No serial cable needed: the bridge talks to the amplifier and the radio over your network.

Design and on-air testing by KW4EX. Version 2.50.

## What it does
- **Amplifier (PGXL):** meters, Operate/Standby, and the amplifier follows the radio's transmit frequency by itself.
- **Tuner (TGXL):** Operate, Bypass and Tune buttons (press Tune again to cancel), return-loss and forward-power meters, and the C1, L and C2 bars of the KPA1500's tuner.
- Shows the connected radio's name in the bridge's small **Applet** window; browser control panel.
- Starting a new bridge closes one that is already running; `Stop_Bridge.bat` closes it cleanly.

## Download

**Start at the [Releases page](https://github.com/kw4ex/kpa1500-smartsdr-bridge/releases/latest).** The top entry marked **Latest** is the newest version. In the **Assets** list click **Install_KPA1500_SmartSDR_Bridge.bat** (not "Source code"). Step-by-step instructions are on the release page.

## Install (Windows)
1. Install Python 3.8 or newer from python.org (tick Add Python to PATH).
2. Download `Install_KPA1500_SmartSDR_Bridge.bat` from the Releases page and double-click it. It asks a few short questions and installs into its own `KPA1500_SmartSDR_Bridge` subfolder (suggested: `C:\RadioScripts`). It can also make a Desktop shortcut, open the firewall ports and run a self-test.
3. Start the bridge, then look for the **PGXL** and **TGXL** in SmartSDR.

A printable step-by-step guide is in [`docs/guides`](docs/guides/KPA1500-SmartSDR-Bridge-guide.pdf) (PDF) and is also installed with the program.

## Good to know
- Run **only one bridge at a time**. This one closes a running [KPA1500 SDR Bridge](https://github.com/kw4ex/kpa1500-sdr-bridge) (Thetis/NereusSDR) when it starts, and the reverse. Do not use it together with the Zeus KPA1500 add-on.
- One amplifier per radio connection: the bridge uses one link for the PGXL and one for the TGXL.
- Uninstall with `Uninstall_KPA1500_SmartSDR_Bridge.bat` in the install folder; it deletes only the bridge's own files.

## Status
Experimental. Tested against simulated amplifier and radio programs and on one station (SmartSDR). Reports are welcome: open an issue.

**No warranty. Use at your own risk.** Shared as is by one radio operator. Not made, approved or supported by Elecraft or FlexRadio.

## Licence
MIT, see `LICENSE`.
