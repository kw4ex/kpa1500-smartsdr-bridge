#!/usr/bin/env python3
"""
kpa1500_sdr_bridge.py  v2.51  -  Thetis or NereusSDR (TCI) <-> Elecraft KPA1500 <-> LP-100A
==============================================================================
Concept, design and on-air testing: KW4EX.

What it does
  * Follows your Thetis (or Zeus) TX frequency and tells the KPA1500 over the
    LAN (^FR;) so the amp selects the band and recalls its ATU setting.
  * Standby on Tune: TUNE in the radio -> amp STANDBY, then back to what it was.
  * Polls the amp: power, SWR, drive, temperature, volts/amps, fault, ATU mode,
    antenna, ATU-tuning state.
  * NEW: a control panel in your web browser (buttons for Operate/Standby, ATU
    Inline/Bypass, ATU Tune/Cancel, Antenna 1/2/Next, Clear Fault, Power On/Off,
    the Standby-on-Tune switch, and LP-100A alarm/mode).
  * NEW: optional Telepost LP-100A telemetry (true power, SWR, reflected power,
    return loss, impedance R+jX, dBm) over its serial port.

Needs Python 3.8+. The amp/Thetis parts use only the standard library.
The LP-100A needs one extra package:   py -m pip install pyserial

Safety rules built in
  * The bridge NEVER keys your transmitter. ATU Tune starts the amp's own
    full-search tune; you press TUNE in the radio (low power) to give it a carrier.
  * ATU inline/bypass, antenna changes and power-off are refused while the
    radio or amp is transmitting (power-off only while the option "Block
    power off while transmitting" is on - turn it off for emergency shutdown).
  * The web panel listens on this computer only (127.0.0.1) unless you pass
    --web-bind 0.0.0.0 (then use --web-token to require a password).

Revision history
  2.40 (2026-10-31)  NereusSDR support. One bridge now works with Thetis OR NereusSDR (one at a time;
                     it finds out which by itself, or choose in the panel / --radio). NereusSDR has no
                     TCI command run_cat_ex, so the FlexControl knob's CAT commands go to NereusSDR's
                     TCP/IP CAT port instead (--nereus-cat-port, default 13013). Telemetry is also sent
                     to NereusSDR as JSON over UDP (--nereus-mmio-port, default 50110) for meters inside
                     NereusSDR containers. New "Applet window" (browser page /applet, opens as its own
                     small window) with meters, control buttons and the knob info; its look (colours,
                     sizes, what is shown, order) is edited from the window itself. New --replace
                     (close an already running bridge first) and --stop-running. Plain TCI
                     rx_sensors is accepted for the no-antenna check. NereusSDR: frequency and
                     meters over TCI; the knob and TUNE over TCP/IP CAT (CAT 1 bound to Slice A).
                     Applet: Operate/Standby, power and frequency on the top line, selectable
                     sections (Telemetry, Controls, FlexControl, LP-100A), shrink-to-fit, no-antenna
                     check option, Quit bridge button, version shown. The Thetis Controls window
                     has a Title line item (like the Telemetry window). The bridge window closes
                     with the bridge. New files: kpa1500_sdr_bridge.py, start_kpa_sdr_bridge.bat,
                     Open_Applet.bat, Stop_Bridge.bat and an installer. The older
                     kpa1500_thetis_bridge.py is not changed and can stay.
  2.16 (2026-10-26)  Thetis buttons can now power the amplifier OFF (KPA_POWER_OFF) for a
                     fast shutdown. Two new options (panel, keys K and B): "Allow Thetis to
                     power off the amp" and "Block power off while transmitting" - turn the
                     second one off for an emergency shutdown when the radio is stuck in TX.
                     New Thetis variable amp_sot_text (ON / OFF) for display.
                     SWR (amp and LP-100A) reads 1.0 when there is no forward power,
                     instead of holding the last value after transmitting.
                     Browser panel: one-button toggles like the Thetis container (AMP power,
                     OPR/STBY, ATU IN/BYP, ATU TUNE/STOP, ANT 1/2, SoT, FAULT), a FAN -/+
                     tile, and a 4-second peak band on the meters. Saved layouts switch to
                     the new tiles once; the old separate buttons are still under Layout.
                     Help: new section on the ready-made Thetis windows, with pictures, and
                     the one-click setup (Setup_Thetis_Containers.bat).
                     Heartbeat variable bridge_time so Thetis can show "BRIDGE NOT RUNNING".
  2.15 (2026-10-25)  Standby-on-Tune always reads the amp mode fresh when tune starts;
                     Wake-on-LAN also sends via the default network interface.
  2.14 (2026-10-25)  Windows fix: the panel server now reads a POST body before replying, so
                     a refused request (403/404) no longer resets the connection.
  2.13 (2026-10-25)  When the amp is off, every amp reading is cleared (panel shows "-",
                     Thetis variables go to 0 / "--"), not just power and mode.
  2.12 (2026-10-25)  Start-up shows OFF (not "not found") when the amp was seen at this
                     address before, or is still visible on the network but silent.
  2.11 (2026-10-25)  Amplifier power indicator: ON / OFF / NO LINK in the panel (badge and
                     red banner), the console and Thetis (amp_mode shows OFF, new
                     amp_power variable). Readings are cleared when the amp goes silent.
  2.10 (2026-10-25)  One-click installer support: --probe IP (is a KPA1500 answering
                     there?, works across subnets) and --wol-broadcast ADDR
                     (send Wake-on-LAN to a chosen broadcast address).
  2.9  (2026-10-22)  Finds the KPA1500 on the network: --discover, --amp-ip auto,
                     "Find amplifier" in the panel, key D in the bridge window.
  2.8  (2026-10-22)  Fan speed control: current fan speed and minimum fan speed
                     (0-5) on the panel, keys F + - in the bridge window, and
                     KPA_FAN_* strings for Thetis buttons.
  2.7  (2026-10-21)  Built-in help: Help button in the panel, keys W and I in the
                     bridge window, --write-help / --print-help.
                     Log file is size-limited and can be switched off.
  2.6  (2026-10-20)  Revision number shown in the window and the panel.
                     Keyboard commands in the bridge window (press H).
                     "Ask before Power OFF" is now one bridge-wide setting.
  2.5               LP-100A port can be changed while running; single-instance
                     guard; start_kpa_bridge.bat launcher (now start_kpa_sdr_bridge.bat).
  2.0 - 2.4         Browser panel, ATU/antenna/power controls, LP-100A,
                     Wake-on-LAN, drive from the radio in standby, layout
                     editor, Thetis Multi Meter I/O feed.

How to change the SHORT LABELS used on the panel tiles (e.g. FWD, DRV, SWR)
  1. Close the bridge, make a backup copy of this file, then open it in
     Notepad (Notepad++ is nicer).
  2. Press Ctrl+F and search for:   const WIDGETS=[
  3. Each tile is one line like this:
         mk('fwd','meter','FWD','Amp forward power'),
     The 3rd quoted text ('FWD') is the SHORT label; the 4th ('Amp forward
     power') is the FULL label. The 1st ('fwd') is the tile's internal name:
     never change it, or saved layouts and buttons will stop working.
  4. Change only the text between the quote marks. Keep the quote marks, the
     commas and the closing bracket and comma at the end of the line.
     Example: to show PWR instead of FWD change  'FWD'  into  'PWR'.
  5. Save, restart the bridge, then press Ctrl+F5 in the browser.
  Labels in the Thetis container are separate: edit those in Thetis itself
  (Setup > Appearance > Meters/Gadgets).

Quick start
  py kpa1500_sdr_bridge.py --selftest     (no hardware needed)
  py kpa1500_sdr_bridge.py --dry-run      (reads only; buttons only print)
  py kpa1500_sdr_bridge.py                (live; open http://127.0.0.1:8080)
  py kpa1500_sdr_bridge.py --lp100-port COM5
"""
import argparse
import base64
import datetime
import hashlib
import hmac
import html
import ipaddress
import json
import math
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import escape as xml_escape

VERSION = "2.51"
BUILD_DATE = "2026-11-11"

# Optional add-on (v2.50): shows the KPA1500 to FlexRadio SmartSDR as a PGXL amplifier
# and TGXL tuner. Lives in its own file; nothing happens unless --flex-emulate is given.
try:
    import kpa1500_flex_emulation as flexemu
except Exception as _e:          # file missing or broken: the rest of the bridge works as before
    flexemu = None
    _FLEX_IMPORT_ERROR = str(_e)

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# kHz ranges -> KPA1500 band number (^BN)
BANDS = [
    (1800, 2000, 0), (3500, 4000, 1), (5250, 5450, 2), (7000, 7300, 3),
    (10100, 10150, 4), (14000, 14350, 5), (18068, 18168, 6),
    (21000, 21450, 7), (24890, 24990, 8), (28000, 29700, 9), (50000, 54000, 10),
]

# band number (as in BANDS) -> band name used for the no-antenna check
BAND_NAMES = ["160", "80", "60", "40", "30", "20", "17", "15", "12", "10", "6"]
# "No antenna?" check: receive level (dBm, Thetis average signal) below which the
# band is suspected to have no antenna. None = check off for that band. Quiet high
# bands can read low with a real antenna, so their limit is lower.
NOANT_DEFAULTS = {"160": -105, "80": -105, "60": -105, "40": -105, "30": -112, "20": -112,
                  "17": -115, "15": -115, "12": -115, "10": -115, "6": None}
NOANT_HYST = 3.0          # dB above the limit needed to clear the warning
DG_ACTIONS = ("ignore", "warn", "limit")   # over-drive protection: do nothing / warn / hold the drive at the limit
DG_TOL = 1.10             # measured drive must exceed the limit by this factor (+1 W) before it counts
DG_SPIKE_S = 0.8          # s the measured drive must stay over the limit before it counts (short peaks are ignored)
DG_SHOW_S = 3.0           # s the over-drive warning stays visible after the last confirmed over-drive
DG_STANDBY_S = 1.2        # s of confirmed over-drive (after the drive was pulled back) before the amp goes to STANDBY
NOANT_SETTLE = 1.5        # s ignored after a band change or after transmit
NOANT_WINDOW = 2.5        # s of receive level averaged (median)
NOANT_LEARN_MARGIN = 6    # learn: limit = level measured with no antenna + this many dB


# Thetis Controls window buttons (ids shared with kpa1500_thetis_setup.py)
TB_DEFAULT = ["title", "opr", "atu", "ant", "amp", "tune", "atutune", "sot", "dummy",
              "fault", "lpalarm", "lpmode", "fandn", "fanup"]
TB_IDS = set(TB_DEFAULT) | {"gap"}


# Thetis Telemetry window items (ids shared with kpa1500_thetis_setup.py)
TM_DEFAULT = ["status", "freq", "fwd", "swr", "drive", "refl", "pa", "fault", "lpp", "lps", "lptext"]
TM_IDS = set(TM_DEFAULT) | {"title", "gap"}
TITLE_TELE = "KPA1500 {ver} Telemetry"
TITLE_CTRL = "KPA1500 {ver} Controls"


def clean_title(s, default):
    """window title text: plain characters only ('%' has a meaning in Thetis); {ver} = bridge version"""
    if not isinstance(s, str):
        return default
    s = "".join(c for c in s if 32 <= ord(c) < 127 and c not in "%|<>&").strip()[:48]
    return s or default


def clean_thetis_meters(tm):
    """settings value -> {"order": [...], "title": text}"""
    order = list(TM_DEFAULT)
    if isinstance(tm, dict) and isinstance(tm.get("order"), list):
        o = [x for x in tm["order"] if isinstance(x, str) and x in TM_IDS]
        o = [x for i, x in enumerate(o) if x == "gap" or x not in o[:i]][:40]
        if [x for x in o if x != "gap"]:
            order = o
    return {"order": order, "title": clean_title(tm.get("title") if isinstance(tm, dict) else None, TITLE_TELE)}


def clean_thetis_buttons(tb):
    """settings value -> {"order": [...], "columns": n, "title": text} (standard layout if not usable)"""
    order, cols = list(TB_DEFAULT), 4
    if isinstance(tb, dict) and isinstance(tb.get("order"), list):
        o = [x for x in tb["order"] if isinstance(x, str) and x in TB_IDS]
        o = [x for i, x in enumerate(o) if x == "gap" or x not in o[:i]][:31]
        if not tb.get("tv") and "title" not in o:
            o.insert(0, "title")      # windows saved before the title became a list item keep their title
        if [x for x in o if x not in ("gap", "title")]:
            order = o
        try:
            cols = max(2, min(6, int(tb.get("columns", 4))))
        except (TypeError, ValueError):
            cols = 4
    return {"order": order, "columns": cols, "tv": 1,
            "title": clean_title(tb.get("title") if isinstance(tb, dict) else None, TITLE_CTRL)}


def fit_status(s):
    """status line cut to the console width, so the next one overwrites it (no wrapping)"""
    try:
        import shutil as _sh
        w = _sh.get_terminal_size((120, 25)).columns - 1
    except Exception:
        w = 119
    w = max(40, w)
    return (s if len(s) <= w else s[:w - 1] + "~").ljust(w)


def setup_launch_cmd(bat, settings_file=""):
    """Command line that opens Setup_Thetis_Containers.bat in its own window.
    cmd /c strips the outer pair of quotes when the line has several quoted parts,
    so the whole command is wrapped in one extra pair:  cmd /c ""x.bat" --settings "y""
    (paths with spaces work)."""
    inner = '"%s"' % bat
    if settings_file:
        inner += ' --settings "%s"' % os.path.abspath(settings_file)
    return 'cmd.exe /c "%s"' % inner


def band_of(khz):
    for lo, hi, bn in BANDS:
        if khz and lo <= khz <= hi:
            return BAND_NAMES[bn]
    return None


def clean_dg_num(x, default, lo, hi):
    """a number for the over-drive settings (kept inside lo..hi); default when it is not a number"""
    try:
        v = float(str(x).strip().lower().replace("w", ""))
    except (TypeError, ValueError):
        return default
    if v != v:
        return default
    return round(max(lo, min(hi, v)), 1)


def clean_limits(d):
    """settings value -> complete {band: limit or None}"""
    lim = dict(NOANT_DEFAULTS)
    if isinstance(d, dict):
        for k, v in d.items():
            k = str(k)
            if k not in lim:
                continue
            if v is None:
                lim[k] = None
            elif isinstance(v, (int, float)) and not isinstance(v, bool) and -150 <= v <= -30:
                lim[k] = int(round(v))
    return lim


FAULTS = {
    0x00: "none", 0x10: "watchdog reset", 0x20: "PA current high",
    0x40: "temperature high", 0x60: "input power high", 0x61: "gain low",
    0x70: "invalid frequency", 0x80: "50V supply", 0x81: "5V supply",
    0x82: "10V supply", 0x83: "12V supply", 0x84: "-12V supply",
    0x85: "LPF supply", 0x90: "reflected power high", 0x91: "SWR very high",
    0x92: "ATU no match", 0xB0: "dissipation high", 0xC0: "forward power high",
    0xC1: "fwd power too high for ATU", 0xF0: "gain high",
}

LP_ALARM = {0: "OFF", 1: "1.5", 2: "2.0", 3: "2.5", 4: "3.0", 5: "USER"}
LP_MODE = {0: "AVG", 1: "PEAK", 2: "TUNE"}
LP_RANGE = {0: "HIGH", 1: "MID", 2: "LOW"}


# --------------------------------------------------------------------------
# Minimal WebSocket (RFC 6455) so no extra packages are needed
# --------------------------------------------------------------------------
class WebSocket:
    def __init__(self, sock, client=True, leftover=b""):
        self.sock = sock
        self.client = client
        self.buf = bytearray(leftover)
        self.frag = bytearray()

    @classmethod
    def connect(cls, host, port, path="/", timeout=5.0):
        s = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
               "Sec-WebSocket-Version: 13\r\n\r\n" % (path, host, port, key))
        s.sendall(req.encode())
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                raise ConnectionError("closed during WebSocket handshake")
            data += chunk
        head, _, rest = data.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise ConnectionError("WebSocket upgrade refused: %r" % head[:60])
        s.settimeout(1.0)
        return cls(s, True, rest)

    def _send_frame(self, opcode, payload=b""):
        hdr = bytearray([0x80 | opcode])
        n = len(payload)
        mbit = 0x80 if self.client else 0
        if n < 126:
            hdr.append(mbit | n)
        elif n < 65536:
            hdr.append(mbit | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(mbit | 127)
            hdr += struct.pack(">Q", n)
        if self.client:
            mask = os.urandom(4)
            hdr += mask
            payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
        self.sock.sendall(bytes(hdr) + payload)

    def send_text(self, text):
        self._send_frame(1, text.encode("utf-8"))

    def _parse(self):
        b = self.buf
        if len(b) < 2:
            return None
        fin, op = b[0] & 0x80, b[0] & 0x0F
        masked, ln, pos = b[1] & 0x80, b[1] & 0x7F, 2
        if ln == 126:
            if len(b) < 4:
                return None
            ln, pos = struct.unpack(">H", bytes(b[2:4]))[0], 4
        elif ln == 127:
            if len(b) < 10:
                return None
            ln, pos = struct.unpack(">Q", bytes(b[2:10]))[0], 10
        mask = b""
        if masked:
            if len(b) < pos + 4:
                return None
            mask, pos = bytes(b[pos:pos + 4]), pos + 4
        if len(b) < pos + ln:
            return None
        payload = bytes(b[pos:pos + ln])
        if masked:
            payload = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
        del b[:pos + ln]
        return fin, op, payload

    def recv_message(self):
        """Return next text message. Raises socket.timeout if idle (fine)."""
        while True:
            fr = self._parse()
            if fr is None:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("connection closed")
                self.buf += chunk
                continue
            fin, op, payload = fr
            if op == 9:
                self._send_frame(10, payload)
            elif op == 8:
                raise ConnectionError("closed by peer")
            elif op in (0, 1):
                self.frag += payload
                if fin:
                    msg = bytes(self.frag).decode("utf-8", "replace")
                    self.frag = bytearray()
                    return msg
            # binary (op 2) and pong (op 10) are ignored

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Thetis Multi Meter I/O (MMIO): telemetry out to Thetis, button commands in
# --------------------------------------------------------------------------
# Strings a Thetis container button can send (Multi Meter I/O "Out" entry) ->
# bridge action. KPA_POWER_OFF acts at once (no question asked) if the option
# "Allow Thetis to power off the amp" is on; under RF only if "Block power off
# while transmitting" is off.
MMIO_COMMANDS = {
    "KPA_OPERATE": "operate", "KPA_STANDBY": "standby",
    "KPA_OPERATE_TOGGLE": "toggle_operate",
    "KPA_ATU_INLINE": "atu_inline", "KPA_ATU_BYPASS": "atu_bypass",
    "KPA_ATU_TOGGLE": "toggle_atu", "KPA_ATU_TUNE": "atu_tune",
    "KPA_ATU_CANCEL": "atu_cancel", "KPA_ANT1": "ant1", "KPA_ANT2": "ant2",
    "KPA_ANT_NEXT": "ant_next", "KPA_ANT_TOGGLE": "toggle_ant",
    "KPA_CLEAR_FAULT": "clear_fault", "KPA_SOT_ON": "sot_on",
    "KPA_SOT_OFF": "sot_off", "KPA_SOT_TOGGLE": "toggle_sot",
    "KPA_POWER_ON": "power_on", "KPA_POWER_OFF": "power_off", "KPA_LP_ALARM": "lp_alarm",
    "KPA_LP_MODE": "lp_mode",
    "KPA_FAN_0": ("fan_min", {"speed": 0}), "KPA_FAN_1": ("fan_min", {"speed": 1}),
    "KPA_FAN_2": ("fan_min", {"speed": 2}), "KPA_FAN_3": ("fan_min", {"speed": 3}),
    "KPA_FAN_4": ("fan_min", {"speed": 4}), "KPA_FAN_5": ("fan_min", {"speed": 5}),
    "KPA_FAN_UP": "fan_up", "KPA_FAN_DOWN": "fan_down",
    "KPA_DUMMY_OK": "dummy_ok",
    "KPA_RADIO_TUNE": "radio_tune", "KPA_RADIO_TUNE_STOP": "radio_tune_stop",
}
TERMS = {"none": "", "cr": "\r", "lf": "\n", "crlf": "\r\n"}


def _mmio_str(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return ("%.2f" % v).rstrip("0").rstrip(".") or "0"
    return str(v)


def mmio_encode(values, fmt, term, root="kpa"):
    """Return a list of UDP datagrams (bytes) carrying the variables.
    json/xml: one datagram holding everything. raw: one 'name:value' each."""
    t = TERMS.get(term, "")
    if fmt == "json":
        return [(json.dumps(values, separators=(",", ":")) + t).encode()]
    if fmt == "xml":
        body = "".join("<%s>%s</%s>" % (k, xml_escape(_mmio_str(v)), k)
                       for k, v in values.items())
        return [("<%s>%s</%s>" % (root, body, root) + t).encode()]
    return [("%s:%s" % (k, _mmio_str(v)) + t).encode() for k, v in values.items()]


def mmio_test(a):
    """Send a tiny fixed set of variables so you can see in Thetis' Variables
    list which format it understands. No amp or radio needed."""
    print("MMIO test: sending to %s:%d  format=%s  terminator=%s"
          % (a.mmio_host, a.mmio_port, a.mmio_format, a.mmio_term))
    print("In Thetis: Setup > Serial/Network/Midi CAT > Multi Meter I/O: the entry "
          "must be UDP, Direction In, Active + Enabled, matching this port/format.")
    print("Look for kpa_test, kpa_hello, kpa_flag in its Variables list. Ctrl+C to stop.\n")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    n = 0
    try:
        while True:
            vals = {"kpa_test": n, "kpa_hello": "hello", "kpa_flag": bool(n % 2)}
            for dg in mmio_encode(vals, a.mmio_format, a.mmio_term, a.mmio_root):
                sock.sendto(dg, (a.mmio_host, a.mmio_port))
            if n < 3:
                print("sent:", mmio_encode(vals, a.mmio_format, a.mmio_term,
                                           a.mmio_root)[0].decode().replace("\r", "\\r").replace("\n", "\\n"))
            n += 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")


# --------------------------------------------------------------------------
# Wake-on-LAN (the KPA1500 can only be powered on over the LAN this way when it
# is asleep; it needs menu NET WAKE on LAN = ON)
# --------------------------------------------------------------------------
def norm_mac(text):
    """'54-10-ec-14-75-2' / '54:10:EC:14:75:22' -> '54:10:EC:14:75:22' or None"""
    parts = re.split(r"[:\-]", text.strip())
    if len(parts) != 6:
        return None
    try:
        return ":".join("%02X" % int(p, 16) for p in parts)
    except ValueError:
        return None


def build_magic(mac):
    """Magic packet: 6 x 0xFF then the MAC address 16 times (102 bytes)."""
    raw = bytes.fromhex(mac.replace(":", ""))
    return b"\xff" * 6 + raw * 16


def local_ipv4s(amp_ip):
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((amp_ip, 9))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(i for i in ips if not i.startswith("127.")) or [""]


def arp_lookup(ip):
    """Find a MAC for ip in the OS ARP table (works if the amp was seen recently)."""
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True,
                             timeout=5).stdout
    except Exception:
        return None
    for line in out.splitlines():
        if re.search(r"(?<![0-9.])%s(?![0-9.])" % re.escape(ip), line):
            m = re.search(r"([0-9a-fA-F]{1,2}[-:]){5}[0-9a-fA-F]{1,2}", line)
            if m:
                return norm_mac(m.group(0))
    return None


# --------------------------------------------------------------------------
# Finding the amplifier on the network
# --------------------------------------------------------------------------
DEFAULT_AMP_IP = "192.168.0.175"


def resolve_amp_ip(flag, saved):
    """Which address to use at start. An explicit --amp-ip always wins; 'auto'
    and 'nothing given' use the address saved from an earlier search."""
    if flag and flag.lower() != "auto":
        return flag, "flag"
    if flag:
        return saved or DEFAULT_AMP_IP, "auto"
    if saved:
        return saved, "saved"
    return DEFAULT_AMP_IP, "default"


def discovery_networks(text, hint_ip):
    """Networks to search: the ones given, or this PC's own /24 networks plus
    the /24 of the address we already know."""
    nets = []
    if text and text.strip():
        for part in re.split(r"[,\s]+", text.strip()):
            if not part:
                continue
            n = ipaddress.ip_network(part, strict=False)
            if n.version != 4:
                continue
            if n.prefixlen < 20:
                raise ValueError("%s is too large to search (use /20 or smaller)" % part)
            nets.append(n)
    else:
        for ip in local_ipv4s(hint_ip):
            if ip and not ip.startswith("169.254."):
                nets.append(ipaddress.ip_network(ip + "/24", strict=False))
        try:
            nets.append(ipaddress.ip_network(hint_ip + "/24", strict=False))
        except ValueError:
            pass
    out = []
    for n in nets:
        if n not in out:
            out.append(n)
    return out


def _probe(ip, port, cmd, prefix, wait=0.6):
    """Ask one amplifier one question. Returns the value part of the answer
    (possibly an empty string), or None if it did not answer."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.15)
    try:
        s.sendto(cmd.encode("ascii"), (ip, port))
        end = time.time() + wait
        while time.time() < end:
            try:
                data, _ = s.recvfrom(256)
            except socket.timeout:
                continue
            except OSError:
                continue
            t = data.decode("ascii", "replace").strip()
            if t.upper().startswith(prefix.upper()):
                return t[len(prefix):].rstrip(";").strip()
    except OSError:
        pass
    finally:
        s.close()
    return None


def discover_amps(nets, port=1500, passes=3, wait=0.8):
    """Send the amplifier's 'identify' command (^I;) to every address on the
    networks and collect the ones that answer ^KPA1500;. Returns a list of
    dicts: ip, boot (True if in boot block), serial, firmware, mac."""
    targets = []
    for n in nets:
        targets.extend(str(h) for h in n.hosts())
        if n.num_addresses > 2:
            targets.append(str(n.broadcast_address))
    targets = list(dict.fromkeys(targets))[:4096]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except OSError:
        pass
    sock.settimeout(0.05)
    seen = {}
    try:
        for _ in range(passes):
            for i, t in enumerate(targets):
                try:
                    sock.sendto(b"^I;", (t, port))
                except OSError:
                    pass
                if i % 64 == 63:
                    time.sleep(0.005)
            end = time.time() + wait
            while time.time() < end:
                try:
                    data, addr = sock.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError:               # e.g. Windows 'connection reset' from ICMP
                    continue
                t = data.decode("ascii", "replace").strip()
                if t.upper().startswith("^KPA1500;"):
                    seen[addr[0]] = t.startswith("^kpa")
    finally:
        sock.close()
    out = []
    for ip in sorted(seen, key=lambda x: tuple(int(p) for p in x.split("."))):
        out.append({"ip": ip, "boot": seen[ip],
                    "serial": _probe(ip, port, "^SN;", "^SN") or "",
                    "firmware": _probe(ip, port, "^RV;", "^RV") or "",
                    "mac": _probe(ip, port, "^MA;", "^MA") or ""})
    return out


def describe_amp(f):
    bits = []
    if f.get("serial"):
        bits.append("serial %s" % f["serial"])
    if f.get("firmware"):
        bits.append("firmware %s" % f["firmware"])
    if f.get("boot"):
        bits.append("boot block")
    return "%s (%s)" % (f["ip"], ", ".join(bits) if bits else "no details")


# --------------------------------------------------------------------------
# KPA1500 over UDP
# --------------------------------------------------------------------------
class Amp:
    def __init__(self, ip, port, dry_run, log):
        self.addr = (ip, port)
        self.dry_run = dry_run
        self.log = log
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.4)
        self.lock = threading.Lock()

    def set_addr(self, ip, port=None):
        self.addr = (ip, port or self.addr[1])

    def _flush(self):
        self.sock.settimeout(0)
        try:
            while True:
                self.sock.recvfrom(1024)
        except (BlockingIOError, socket.timeout, OSError):
            pass
        self.sock.settimeout(0.4)

    def get(self, cmd):
        """Send a GET command, return the matching response text or None."""
        prefix = cmd[:-1].upper()
        with self.lock:
            self._flush()
            try:
                self.sock.sendto(cmd.encode("ascii"), self.addr)
                deadline = time.time() + 0.5
                while time.time() < deadline:
                    data, _ = self.sock.recvfrom(1024)
                    text = data.decode("ascii", "replace").strip()
                    if text.upper().startswith(prefix):
                        return text
            except (socket.timeout, OSError):
                pass
        return None

    def set(self, cmd):
        """Send a SET command (no reply expected). Honors --dry-run."""
        if self.dry_run:
            self.log("DRY-RUN: would send %s" % cmd)
            return
        try:
            self.sock.sendto(cmd.encode("ascii"), self.addr)
            self.log("-> amp: %s" % cmd, verbose=True)
        except OSError as e:
            self.log("ERROR sending %s: %s" % (cmd, e))


# --------------------------------------------------------------------------
# Telepost LP-100A (serial, poll-only: send "P", meter answers one frame)
# --------------------------------------------------------------------------
def parse_lp100(text):
    """Parse the reply to 'P'. Frame starts with ';'. Fields (per Telepost
    manual): Power(W), Z(ohm), Phase(deg), AlarmIdx, Callsign, PowerRange,
    MeterMode, dBm, SWR.  Returns a dict or None if it does not look right."""
    text = text.replace("\r", "").replace("\n", "")
    for frame in reversed([f for f in text.split(";") if f.strip()]):
        parts = [p.strip() for p in (frame.split(",") if "," in frame
                                     else frame.split())]
        if len(parts) < 9:
            continue
        try:
            pwr, z, ph = float(parts[0]), float(parts[1]), float(parts[2])
            alarm, rng = int(float(parts[3])), int(float(parts[5]))
            mode, dbm, swr = int(float(parts[6])), float(parts[7]), float(parts[8])
        except ValueError:
            continue
        if swr < 1.0:
            swr = 1.0
        rad = math.radians(ph)
        refl = pwr * ((swr - 1) / (swr + 1)) ** 2 if swr > 1 else 0.0
        rl = 20 * math.log10((swr + 1) / (swr - 1)) if swr > 1.0001 else None
        return {"pwr": pwr, "z": z, "phase": ph, "r": z * math.cos(rad),
                "x": z * math.sin(rad), "alarm": alarm,
                "alarm_txt": LP_ALARM.get(alarm, str(alarm)), "call": parts[4],
                "rng": rng, "rng_txt": LP_RANGE.get(rng, str(rng)), "mode": mode,
                "mode_txt": LP_MODE.get(mode, str(mode)), "dbm": dbm, "swr": swr,
                "refl": refl, "rl": rl}
    return None


def load_settings(path):
    """Small JSON file next to the script remembering choices made in the panel."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def list_serial_ports():
    """(list of {device, desc}, note). Needs pyserial."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return [], "pyserial is not installed (py -m pip install pyserial)"
    try:
        return [{"device": p.device, "desc": p.description or ""}
                for p in list_ports.comports()], ""
    except Exception as e:
        return [], str(e)


VALID_BAUDS = (9600, 19200, 38400, 57600, 115200)
PORT_RE = re.compile(r"COM\d{1,3}|/dev/(tty|cu)[\w.\-]+", re.I)


def default_serial_opener(port, baud):
    import serial  # pyserial
    return serial.Serial(port, baud, timeout=0.1)


# --------------------------------------------------------------------------
# FlexRadio FlexControl tuning knob (USB serial: VID 0x2192 PID 0x0010)
#   knob -> PC:  U; D; (one click)  U03; D05; (several clicks when spun fast)
#                S; C; L;  knob press tap / double / long
#                X1S; X2C; X3L; ...  buttons 1-3 tap / double / long
#   PC -> knob:  Ixyz;  LEDs 1-3 on (1) / off (0)
# Thetis is controlled over TCI; Thetis CAT commands run through TCI run_cat_ex.
# --------------------------------------------------------------------------
KNOB_VID, KNOB_PID = 0x2192, 0x0010
KNOB_EVENTS = [
    ("knob_tap", "Knob press: tap"), ("knob_double", "Knob press: double tap"), ("knob_long", "Knob press: long"),
    ("b1_tap", "Button 1: tap"), ("b1_double", "Button 1: double tap"), ("b1_long", "Button 1: long"),
    ("b2_tap", "Button 2: tap"), ("b2_double", "Button 2: double tap"), ("b2_long", "Button 2: long"),
    ("b3_tap", "Button 3: tap"), ("b3_double", "Button 3: double tap"), ("b3_long", "Button 3: long"),
]
KNOB_EVENT_IDS = [e for e, _ in KNOB_EVENTS]
_KNOB_PRESS = {"S": "tap", "C": "double", "L": "long"}
# what turning the knob does: id -> (name, LEDs, kind, details)
#   step:  one Thetis CAT command per click (up, down)
#   value: read a value, change it, write it back (read, write, min, max)
KNOB_MODES = {
    "vfoa": ("VFO A tuning", "000", "step", ("ZZSB", "ZZSA")),
    "vfob": ("VFO B tuning", "101", "step", ("ZZSH", "ZZSG")),
    "af": ("AF volume (master)", "100", "value", ("cat:ZZAG", "cat:ZZAG%03d", 0, 100)),
    "agc": ("AGC gain (RX1)", "010", "value", ("tci:agc_gain:0", "tci:agc_gain:0,%d", -20, 120)),
    "rit": ("RIT (10 Hz per click)", "001", "step", ("ZZRU", "ZZRD")),
    "xit": ("XIT (10 Hz per click)", "011", "step", ("ZZXU", "ZZXD")),
    "step": ("Tuning step size", "110", "step", ("ZZSU", "ZZSD")),
    "drive": ("TX drive", "111", "value", ("cat:ZZPC", "cat:ZZPC%03d", 0, 100)),
}
KNOB_CYCLE = ["vfoa", "af", "agc"]
# what a press does: id -> (name, group, how)
#   mode:X / toggle_mode:X / cycle   change what turning does
#   cat_toggle:ZZxx  0/1 switch (read, then set the other)   cat:ZZxx  one CAT command
#   bridge:action    a bridge function (same safety checks as the panel)
KNOB_ACTIONS = [
    ("none", "(nothing)", "", ""),
    ("mode_af_toggle", "Knob: AF volume <-> VFO A (toggle)", "Knob mode", "toggle_mode:af"),
    ("mode_agc_toggle", "Knob: AGC gain <-> VFO A (toggle)", "Knob mode", "toggle_mode:agc"),
    ("mode_vfob_toggle", "Knob: VFO B <-> VFO A (toggle)", "Knob mode", "toggle_mode:vfob"),
    ("mode_rit_toggle", "Knob: RIT <-> VFO A (toggle)", "Knob mode", "toggle_mode:rit"),
    ("mode_xit_toggle", "Knob: XIT <-> VFO A (toggle)", "Knob mode", "toggle_mode:xit"),
    ("mode_step_toggle", "Knob: tuning step size <-> VFO A (toggle)", "Knob mode", "toggle_mode:step"),
    ("mode_drive_toggle", "Knob: TX drive <-> VFO A (toggle)", "Knob mode", "toggle_mode:drive"),
    ("mode_cycle", "Knob: next mode (VFO A > AF volume > AGC gain)", "Knob mode", "cycle"),
    ("mode_vfoa", "Knob: back to VFO A tuning", "Knob mode", "mode:vfoa"),
    ("mute", "Mute on / off", "Thetis", "cat_toggle:ZZMA"),
    ("vox", "VOX on / off", "Thetis", "cat_toggle:ZZVE"),
    ("lock", "VFO A lock on / off", "Thetis", "cat_toggle:ZZUX"),
    ("split", "Split on / off", "Thetis", "cat_toggle:ZZSP"),
    ("rit_onoff", "RIT on / off", "Thetis", "cat_toggle:ZZRT"),
    ("rit_clear", "RIT clear (to 0)", "Thetis", "cat:ZZRC"),
    ("xit_onoff", "XIT on / off", "Thetis", "cat_toggle:ZZXS"),
    ("nr", "Noise reduction (NR) on / off", "Thetis", "cat_toggle:ZZNR"),
    ("nb", "Noise blanker (NB) on / off", "Thetis", "cat_toggle:ZZNA"),
    ("anf", "Auto notch (ANF) on / off", "Thetis", "cat_toggle:ZZNT"),
    ("step_up", "Tuning step: larger", "Thetis", "cat:ZZSU"),
    ("step_down", "Tuning step: smaller", "Thetis", "cat:ZZSD"),
    ("band_up", "Band up", "Thetis", "cat:ZZBU"),
    ("band_down", "Band down", "Thetis", "cat:ZZBD"),
    ("mox", "MOX on / off (TRANSMITS!)", "Thetis", "cat_toggle:ZZTX"),
    ("radio_tune", "TUNE the safe way (amp STANDBY first) / stop", "Bridge / amplifier", "bridge:radio_tune_toggle"),
    ("amp_operate", "Amp OPERATE / STANDBY", "Bridge / amplifier", "bridge:toggle_operate"),
    ("atu_tune", "Amp ATU tune", "Bridge / amplifier", "bridge:atu_tune"),
    ("ant_toggle", "Amp antenna 1 / 2", "Bridge / amplifier", "bridge:toggle_ant"),
    ("dummy_ok", "DUMMY OK (no-antenna warning)", "Bridge / amplifier", "bridge:dummy_ok"),
    ("sot_toggle", "Standby-on-Tune on / off", "Bridge / amplifier", "bridge:toggle_sot"),
    ("custom", "Custom command (type it below)", "Custom", "custom"),
]
KNOB_ACTION_MAP = {a[0]: a for a in KNOB_ACTIONS}
# short names for the Thetis "KPA1500 Knob" window
KNOB_MODE_SHORT = {"vfoa": "VFO A", "vfob": "VFO B", "af": "AF", "agc": "AGC", "rit": "RIT",
                   "xit": "XIT", "step": "Step", "drive": "Drive"}
KNOB_SHORT = {"none": "-", "mute": "Mute", "vox": "VOX", "lock": "Lock", "split": "Split", "rit_onoff": "RIT",
              "rit_clear": "RIT clr", "xit_onoff": "XIT", "nr": "NR", "nb": "NB", "anf": "ANF",
              "step_up": "Step +", "step_down": "Step -", "band_up": "Band +", "band_down": "Band -",
              "mox": "MOX!", "radio_tune": "TUNE", "amp_operate": "OPR/STBY", "atu_tune": "ATU tune",
              "ant_toggle": "ANT", "dummy_ok": "DUMMY OK", "sot_toggle": "SoT"}
# Thetis "KPA1500 Knob" window: items (ids shared with kpa1500_thetis_setup.py)
KW_DEFAULT = ["title", "now", "knob", "b1", "b2", "b3", "status"]
KW_IDS = set(KW_DEFAULT) | {"gap"}
TITLE_KNOB = "FlexControl Knob {ver}"


def clean_knob_window(kw):
    kw = kw if isinstance(kw, dict) else {}
    order = list(KW_DEFAULT)
    if isinstance(kw.get("order"), list):
        o = [x for x in kw["order"] if isinstance(x, str) and x in KW_IDS]
        o = [x for i, x in enumerate(o) if x == "gap" or x not in o[:i]][:20]
        if [x for x in o if x != "gap"]:
            order = o
    return {"enabled": kw.get("enabled", True) is not False, "order": order,
            "title": clean_title(kw.get("title"), TITLE_KNOB)}
KNOB_DEFAULT_TABLE = {
    "knob_tap": "mode_af_toggle", "knob_double": "mute", "knob_long": "mode_vfoa",
    "b1_tap": "mode_af_toggle", "b1_double": "mode_agc_toggle", "b1_long": "mute",
    "b2_tap": "vox", "b2_double": "step_up", "b2_long": "step_down",
    "b3_tap": "radio_tune", "b3_double": "band_up", "b3_long": "band_down",
}
CUSTOM_RE = re.compile(r"^(ZZ[A-Z0-9]{2}[^;]{0,20};?|[a-z_]{2,30}:[^;]{0,60};?)$")


def clean_knob(k):
    """settings value -> complete knob settings"""
    k = k if isinstance(k, dict) else {}
    port = k.get("port", "auto")
    if not isinstance(port, str) or not (port in ("", "auto") or PORT_RE.fullmatch(port)):
        port = "auto"
    table = dict(KNOB_DEFAULT_TABLE)
    for e, a in (k.get("table") or {}).items() if isinstance(k.get("table"), dict) else []:
        if e in table and a in KNOB_ACTION_MAP:
            table[e] = a
    custom = {}
    for e, c in (k.get("custom") or {}).items() if isinstance(k.get("custom"), dict) else []:
        if e in table and isinstance(c, str) and CUSTOM_RE.match(c.strip()):
            custom[e] = c.strip()

    def num(key, default, lo, hi):
        try:
            return max(lo, min(hi, int(k.get(key, default))))
        except (TypeError, ValueError):
            return default
    return {"port": port, "table": table, "custom": custom, "speed": num("speed", 2, 1, 8),
            "af_step": num("af_step", 1, 1, 10), "return_s": num("return_s", 0, 0, 600)}


def find_knob_port():
    """COM port of a connected FlexControl (by its USB id), or None"""
    try:
        from serial.tools import list_ports
        for p in list_ports.comports():
            if getattr(p, "vid", None) == KNOB_VID and getattr(p, "pid", None) == KNOB_PID:
                return p.device
    except Exception:
        pass
    return None


def parse_knob_code(code):
    """'U03' -> ('turn', 3)   'D' -> ('turn', -1)   'X2C' -> ('event', 'b2_double')   else (None, None)"""
    code = code.strip().upper()
    m = re.fullmatch(r"([UD])(\d{0,3})", code)
    if m:
        n = int(m.group(2) or 1) or 1
        return "turn", n if m.group(1) == "U" else -n
    if code in _KNOB_PRESS:
        return "event", "knob_" + _KNOB_PRESS[code]
    m = re.fullmatch(r"X([1-3])([SCL])", code)
    if m:
        return "event", "b%s_%s" % (m.group(1), _KNOB_PRESS[m.group(2)])
    return None, None


class FlexKnob(threading.Thread):
    """Reads the FlexControl; calls on_code('U03') for each message. Reconnects by itself."""
    def __init__(self, port, opener, on_code, log, finder=find_knob_port):
        super().__init__(daemon=True)
        self.port, self.opener, self.on_code, self.log, self.finder = port, opener, on_code, log, finder
        self.stop = threading.Event()
        self.ser, self.connected, self.device, self.error = None, False, "", ""
        self.out = []
        self._reconnect = False

    def set_port(self, port):
        self.port = port
        self._reconnect = True

    def send(self, text):
        self.out.append(text.encode("ascii"))

    def _close(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser, self.connected = None, False

    def run(self):
        buf = b""
        while not self.stop.is_set():
            if self._reconnect:
                self._reconnect = False
                self._close()
                self.error = ""
            if not self.port:
                self._close()
                self.device, self.error = "", ""
                self.stop.wait(0.5)
                continue
            if self.ser is None:
                dev = self.finder() if self.port == "auto" else self.port
                if not dev:
                    self.device, self.error = "", "not found (is it plugged in?)"
                    self.stop.wait(2.0)
                    continue
                try:
                    self.ser = self.opener(dev, 9600)
                    self.connected, self.device, self.error, buf = True, dev, "", b""
                    self.log("FlexControl knob connected on %s" % dev)
                    self.on_code("__connected__")
                except Exception as e:
                    msg = str(e)
                    if "denied" in msg.lower() or "busy" in msg.lower() or "PermissionError" in msg:
                        msg = "%s is in use by another program (DDUtil?) - close it there first" % dev
                    if msg != self.error:
                        self.log("FlexControl knob: %s" % msg)
                    self.device, self.error = dev, msg
                    self.ser = None
                    self.stop.wait(3.0)
                    continue
            try:
                while self.out:
                    self.ser.write(self.out.pop(0))
                n = self.ser.in_waiting
                if n:
                    buf += self.ser.read(n)
                    while b";" in buf:
                        code, buf = buf.split(b";", 1)
                        code = code.decode("ascii", "replace").strip()
                        if code:
                            self.on_code(code)
                    buf = buf[-64:]
                else:
                    self.stop.wait(0.01)
            except Exception as e:
                self.log("FlexControl knob disconnected: %s" % e)
                self._close()
                self.error = "disconnected"
                self.stop.wait(1.0)
        self._close()


class FakeKnobSerial:
    """Stands in for pyserial in the self-test: feed() what the knob would send."""
    def __init__(self):
        self.buf, self.written = b"", []

    def feed(self, s):
        self.buf += s.encode("ascii")

    def write(self, b):
        self.written.append(b)

    @property
    def in_waiting(self):
        return len(self.buf)

    def read(self, n):
        d, self.buf = self.buf[:n], self.buf[n:]
        return d

    def close(self):
        pass


class LP100(threading.Thread):
    def __init__(self, port, baud, opener, log, debug=False, interval=0.12):
        super().__init__(daemon=True)
        self.port, self.baud, self.opener = port, baud, opener
        self.log, self.debug, self.interval = log, debug, interval
        self.stop = threading.Event()
        self.queue = []
        self.reading, self.read_time, self.raw = None, 0.0, ""
        self.frames, self.bad = 0, 0
        self.ser = None
        self.connected = False
        self.last_error = ""
        self._reconnect = False

    def set_port(self, port, baud):
        """Change port/baud while running (empty port = disconnect)."""
        self.port, self.baud = port, baud
        self.reading, self.read_time, self.raw = None, 0.0, ""
        self.last_error = ""
        self._reconnect = True

    def _close(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        self.connected = False

    def send(self, b):
        self.queue.append(b)

    def snapshot(self):
        if (self.port and not self._reconnect and self.reading
                and time.time() - self.read_time < 1.5):
            return dict(self.reading)
        return None

    def run(self):
        warned = False
        while not self.stop.is_set():
            try:
                if self._reconnect:
                    self._close()
                    self.reading, self.read_time, self.raw = None, 0.0, ""
                    self._reconnect = False
                    warned = False
                if not self.port:                      # not configured / disconnected
                    self.stop.wait(0.3)
                    continue
                if self.ser is None:
                    self.ser = self.opener(self.port, self.baud)
                    self.connected = True
                    self.last_error = ""
                    warned = False
                    self.log("LP-100A connected on %s @ %d baud"
                             % (self.port, self.baud))
                while self.queue:
                    self.ser.write(self.queue.pop(0))
                    time.sleep(0.02)
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)      # drop stale bytes
                self.ser.write(b"P")
                data, deadline = b"", time.time() + 0.3
                while time.time() < deadline and not data:
                    if self.ser.in_waiting:
                        time.sleep(0.03)
                        data = self.ser.read(self.ser.in_waiting)
                    else:
                        time.sleep(0.005)
                text = data.decode("ascii", "replace")
                self.raw = text
                rd = parse_lp100(text) if text else None
                if rd and not self._reconnect:
                    self.reading, self.read_time = rd, time.time()
                    self.frames += 1
                    if self.debug and self.frames <= 5:
                        self.log("LP-100A raw frame: %r" % text)
                elif text:
                    self.bad += 1
                    if self.debug or self.bad <= 3:
                        self.log("LP-100A unreadable frame: %r (is the meter on "
                                 "its Watts screen?)" % text)
            except ImportError:
                self.log("LP-100A needs pyserial:  py -m pip install pyserial")
                return
            except Exception as e:
                self.last_error = str(e)
                if not warned:
                    self.log("LP-100A error on %s: %s (retrying)" % (self.port, e))
                    warned = True
                self._close()
                self.stop.wait(2.0)
            self.stop.wait(self.interval)


# --------------------------------------------------------------------------
# The bridge
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# NereusSDR support (new in 2.40)
# --------------------------------------------------------------------------
RADIO_KINDS = ("auto", "thetis", "nereus")
RADIO_NAMES = {"thetis": "Thetis", "nereus": "NereusSDR"}


class CatLink(threading.Thread):
    """TCP connection to a NereusSDR 'TCP/IP CAT' channel. NereusSDR does not have the TCI command
    run_cat_ex, so the knob's Thetis-style CAT commands (ZZSB; ZZAG; ...) go here instead.
    Replies look like  ZZAG050;  and are handed to on_reply(code, value)."""
    REPLY = re.compile(r"(ZZ[A-Z0-9]{2})([^;]*);")

    def __init__(self, host, port, on_reply, log):
        super().__init__(daemon=True)
        self.host, self.port = host, port
        self.on_reply, self.log = on_reply, log
        self.sock = None
        self.connected = False
        self.stop = threading.Event()
        self.send_lock = threading.Lock()
        self.error = ""
        self._warned = False
        self.raw = []                 # last few raw things seen/sent, for the 'no answer' report

    def note(self, s):
        self.raw.append(s)
        del self.raw[:-6]

    def run(self):
        while not self.stop.is_set():
            s = None
            try:
                s = socket.create_connection((self.host, self.port), timeout=2.0)
                s.settimeout(0.5)
                self.sock = s
                self.connected = True
                self.error = ""
                self._warned = False
                self.log("Connected to the NereusSDR CAT port at %s:%d" % (self.host, self.port))
                buf = ""
                idle_t = time.time()
                while not self.stop.is_set():
                    if time.time() - idle_t > 10:       # NereusSDR hangs up an idle CAT link after ~30 s
                        idle_t = time.time()
                        self.send("ZZVN;")
                    try:
                        data = s.recv(4096)
                    except socket.timeout:
                        continue
                    if not data:
                        raise ConnectionError("closed by NereusSDR")
                    buf += data.decode("ascii", "replace")
                    self.note("<- " + repr(data.decode("ascii", "replace"))[:80])
                    if len(buf) > 8192:
                        buf = buf[-2048:]
                    while True:
                        m = self.REPLY.search(buf)
                        if not m:
                            break
                        buf = buf[m.end():]
                        self.on_reply(m.group(1), m.group(2).strip())
            except (OSError, ConnectionError) as e:
                if self.connected:
                    self.log("Lost the NereusSDR CAT connection: %s" % e)
                elif not self._warned:
                    self.log("Waiting for the NereusSDR CAT port %s:%d (%s). In NereusSDR turn on "
                             "File > Settings > CAT & Network > TCP/IP CAT > Enable TCP CAT."
                             % (self.host, self.port, e))
                    self._warned = True
                self.error = str(e)
            finally:
                self.connected = False
                self.sock = None
                if s:
                    try:
                        s.close()
                    except OSError:
                        pass
            self.stop.wait(2.0)

    def send(self, text):
        s = self.sock
        if not (s and self.connected):
            return False
        try:
            with self.send_lock:
                s.sendall(text.encode("ascii"))
            self.note("-> " + text)
            return True
        except OSError:
            return False

    def close(self):
        self.stop.set()
        s = self.sock
        if s:
            try:
                s.close()
            except OSError:
                pass


APPLET_SECTIONS = ("telemetry", "controls", "knob", "lp100")
APPLET_ITEMS = ("fwd", "drv", "swr", "refl", "temp", "volts", "amps", "lpwr", "lswr",
                "opr", "atu", "ant", "amp", "tune", "atutune", "sot", "dummy", "fault",
                "fandn", "fanup", "lpalarm", "lpmode", "hfreq", "hopr", "hpwr")
APPLET_COLORS = ("bg", "panel", "text", "dim", "accent", "ok", "warn", "bad", "meter")
APPLET_THEMES = ("dark", "light", "contrast", "nereus", "amber")


def clean_applet_skin(d):
    """The look of the Applet window, checked so a damaged settings file can do no harm."""
    d = d if isinstance(d, dict) else {}

    def num(key, lo, hi, default):
        try:
            return int(max(lo, min(hi, float(d.get(key, default)))))
        except (TypeError, ValueError):
            return default
    theme = d.get("theme") if d.get("theme") in APPLET_THEMES else "dark"
    colors = {}
    if isinstance(d.get("colors"), dict):
        for k, v in d["colors"].items():
            if k in APPLET_COLORS and isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v):
                colors[k] = v.lower()
    order = [x for x in (d.get("order") if isinstance(d.get("order"), list) else []) if x in APPLET_SECTIONS]
    order = list(dict.fromkeys(order))
    order += [x for x in APPLET_SECTIONS if x not in order]
    hide = [x for x in (d.get("hide") if isinstance(d.get("hide"), list) else []) if x in APPLET_SECTIONS]
    hide_items = [x for x in (d.get("hide_items") if isinstance(d.get("hide_items"), list) else [])
                  if x in APPLET_ITEMS]
    title = re.sub(r"[<>&\"'\\\x00-\x1f]", "", str(d.get("title", "KPA1500")))[:30].strip() or "KPA1500"
    return {"theme": theme, "colors": colors, "font": num("font", 10, 28, 14), "cols": num("cols", 1, 3, 2),
            "bar": num("bar", 6, 36, 16), "radius": num("radius", 0, 22, 8), "gap": num("gap", 2, 20, 8),
            "title": title, "width": num("width", 240, 1600, 460), "height": num("height", 240, 1600, 780),
            "zoom": num("zoom", 50, 150, 100), "fit": d.get("fit") is not False, "caps": d.get("caps") is not False,
            "order": order, "hide": list(dict.fromkeys(hide)), "hide_items": list(dict.fromkeys(hide_items))}


def pid_from_netstat(text, port):
    """Process id that is LISTENING on a local port, from the text of  netstat -ano  (Windows)."""
    for line in text.splitlines():
        p = line.split()
        if (len(p) >= 5 and p[0].upper() == "TCP" and p[3].upper() == "LISTENING"
                and p[1].endswith(":%d" % port)):
            try:
                return int(p[4])
            except ValueError:
                pass
    return None


def find_listener_pid(port):
    try:
        if os.name == "nt":
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=15,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            return pid_from_netstat(out, port)
        try:
            out = subprocess.run(["lsof", "-nP", "-iTCP:%d" % port, "-sTCP:LISTEN", "-t"],
                                 capture_output=True, text=True, timeout=15).stdout.split()
            return int(out[0]) if out else None
        except FileNotFoundError:
            # small Linux systems (Raspberry Pi OS Lite) often have no lsof: ask 'ss' instead
            out = subprocess.run(["ss", "-H", "-ltnp", "sport = :%d" % port],
                                 capture_output=True, text=True, timeout=15).stdout
            m = re.search(r"pid=(\d+)", out)
            return int(m.group(1)) if m else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def parent_console_pid(pid):
    """Windows: the cmd.exe window that started the bridge process (so it can be closed with it).
    Only a cmd.exe whose command line names a KPA1500 bridge program is returned."""
    if os.name != "nt" or not pid:
        return None
    try:
        ps = ("$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%d'; if($p){$q=Get-CimInstance Win32_Process "
              "-Filter ('ProcessId='+$p.ParentProcessId); if($q -and $q.Name -eq 'cmd.exe' -and "
              "$q.CommandLine -like '*kpa1500_*bridge*'){$q.ProcessId}}" % pid)
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                             timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
        return int(out.split()[0]) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def stop_running_bridge(lock_port, web_port, log=print, wait=10.0):
    """Close a running bridge. On Mac and Linux the old bridge gives up its lock a moment before its
    other ports are released, so after it is gone we also wait until its panel and Flex ports are free."""
    probe = acquire_lock(lock_port)
    was_running = probe is None
    if probe is not None:
        probe.close()
    ok = _stop_running_bridge(lock_port, web_port, log, wait)
    if ok and was_running and os.name != "nt":
        def listening(port):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.3).close()
                return True
            except OSError:
                return False
        end = time.time() + 8.0
        while time.time() < end and any(listening(pt) for pt in (web_port, 8080, 9008, 9010) if pt):
            time.sleep(0.25)
    return ok


def _stop_running_bridge(lock_port, web_port, log=print, wait=10.0):
    """Close a bridge that is already running, then return True when its lock port is free.
    First it is asked politely through its own panel (no password is needed on this computer);
    if that does not work, its process is ended."""
    import urllib.request

    def free():
        s = acquire_lock(lock_port)
        if s is None:
            return False
        s.close()
        return True

    def wait_free(t):
        end = time.time() + t
        while time.time() < end:
            if free():
                return True
            time.sleep(0.2)
        return free()
    if free():
        return True
    log("Closing the bridge that is already running ...")
    for port in dict.fromkeys([p for p in (web_port, 8080) if p]):
        try:
            rq = urllib.request.Request("http://127.0.0.1:%d/api/cmd" % port,
                                        json.dumps({"action": "quit_bridge"}).encode(),
                                        {"Content-Type": "application/json", "X-KPA": "1"}, method="POST")
            urllib.request.urlopen(rq, timeout=2).read()
            break
        except Exception:
            continue
    if wait_free(wait / 2):
        return True
    pid = find_listener_pid(lock_port)
    if pid and pid != os.getpid():
        log("It did not answer - ending its process (%d)." % pid)
        con = parent_console_pid(pid)
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=15,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if con:
                    subprocess.run(["taskkill", "/PID", str(con), "/F"], capture_output=True, timeout=15,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
        except (OSError, subprocess.SubprocessError) as e:
            log("Could not end it: %s" % e)
    return wait_free(wait / 2)


def find_app_browser():
    """A Chrome-style browser that can open a page as a small window of its own (--app)."""
    cands = []
    if os.name == "nt":
        for env in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
            base = os.environ.get(env)
            if base:
                cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    elif sys.platform == "darwin":
        cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                 "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    else:
        import shutil
        cands = [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium",
                                                  "chromium-browser", "microsoft-edge")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None


APPLET_PROC = [None]


def applet_window_open():
    p = APPLET_PROC[0]
    return bool(p and p.poll() is None)


def close_applet_window():
    """Close the Applet window this bridge opened (it runs in its own browser process)."""
    p = APPLET_PROC[0]
    APPLET_PROC[0] = None
    if not (p and p.poll() is None):
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, timeout=15,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            p.terminate()
    except (OSError, subprocess.SubprocessError):
        pass


def open_applet_window(url, width, height, log):
    """Open the Applet page as a small window of its own (no tabs, no address bar)."""
    if applet_window_open():
        return True, "The Applet window is already open"
    exe = find_app_browser()
    try:
        if exe:
            import tempfile
            prof = os.path.join(tempfile.gettempdir(), "kpa1500_applet_profile")
            APPLET_PROC[0] = subprocess.Popen([exe, "--app=" + url, "--window-size=%d,%d" % (width, height),
                                               "--user-data-dir=" + prof, "--no-first-run",
                                               "--no-default-browser-check"])
            log("Applet window opened (%s)" % os.path.basename(exe))
            return True, "The Applet window is open on the bridge computer"
        import webbrowser
        webbrowser.open(url)
        log("Applet opened in your normal browser (no Edge or Chrome found for a small window)")
        return True, "The Applet opened in your browser (Edge or Chrome would give it a window of its own)"
    except (OSError, ValueError) as e:
        return False, "Could not open the Applet window: %s" % e


APPLET_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KPA1500 Applet</title>
<style>
:root{--bg:#10141a;--panel:#1a212b;--text:#e6edf3;--dim:#8b98a8;--accent:#3aa0ff;--ok:#2fbf71;--warn:#f2b134;--bad:#ef4f4f;--meter:#2fbf71;
 --font:14px;--cols:2;--radius:8px;--gap:8px;--bar:16px}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text)}
body{font-family:"Segoe UI",system-ui,-apple-system,sans-serif;font-size:var(--font);line-height:1.35;padding:var(--gap)}
#app{display:flex;flex-direction:column;gap:var(--gap)}
.sec{background:var(--panel);border-radius:var(--radius);padding:calc(var(--gap) + 2px)}
.sec>h2{margin:0 0 6px;font-size:.78em;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);font-weight:600}
.hdr{display:flex;align-items:center;gap:6px;flex-wrap:wrap;background:var(--panel);border-radius:var(--radius);padding:6px calc(var(--gap) + 2px)}
.hdr .t{font-weight:700;font-size:1.15em;min-width:4em}
.hdr .sp{flex:1}
.vr{color:var(--dim);font-size:.72em;margin-left:-2px}
.hf{font-weight:700;font-size:1.15em;color:var(--accent);font-variant-numeric:tabular-nums}
.hb{padding:.2em .7em !important;width:auto !important}
.nocap .sec>h2{display:none}
.badge{display:inline-flex;align-items:center;gap:4px;border-radius:99px;padding:1px 7px;font-size:.72em;white-space:nowrap;background:rgba(127,127,127,.18)}
.dot{width:.7em;height:.7em;border-radius:50%;background:var(--bad);display:inline-block}
.dot.on{background:var(--ok)}
.ib{border:0;background:transparent;color:var(--dim);cursor:pointer;font-size:.95em;padding:2px 4px;border-radius:6px}
.ib:hover{background:rgba(127,127,127,.2);color:var(--text)}
.big{font-size:1.5em;font-weight:700;color:var(--accent)}
.sub{color:var(--dim);font-size:.9em}
.ban{border-radius:calc(var(--radius) - 2px);padding:5px 9px;font-weight:700;margin-top:6px;display:none}
.ban.bad{background:var(--bad);color:#fff}.ban.warn{background:var(--warn);color:#000}
.ban.show{display:block}
.grid{display:grid;grid-template-columns:repeat(var(--cols),minmax(0,1fr));gap:var(--gap)}
.m .mh{display:flex;justify-content:space-between;font-size:.88em}
.m .ml{color:var(--dim)}.m .mv{font-variant-numeric:tabular-nums;font-weight:600}
.bar{position:relative;height:var(--bar);background:rgba(127,127,127,.22);border-radius:calc(var(--radius) / 2);overflow:hidden;margin-top:2px}
.bar i{position:absolute;top:0;bottom:0;left:0}
.bar .f1{background:var(--meter)}.bar .f2{background:var(--bad)}
.bar .pk{width:2px;background:var(--text);opacity:.85}
.btns{display:grid;grid-template-columns:repeat(var(--cols),minmax(0,1fr));gap:calc(var(--gap) - 2px)}
.btn{border:1px solid rgba(127,127,127,.35);background:rgba(127,127,127,.14);color:var(--text);border-radius:calc(var(--radius) - 2px);padding:.55em .4em;font:inherit;font-weight:700;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.btn.lit{background:var(--ok);color:#000;border-color:var(--ok)}
.btn.lit.alert{background:var(--bad);color:#fff;border-color:var(--bad)}
.btn:disabled{opacity:.45;cursor:default}
.kn{font-variant-numeric:tabular-nums}
.kn div{padding:1px 0}
.kn .k{color:var(--dim);display:inline-block;min-width:3.2em}
body.stale #app>*{opacity:.45}
#toast{position:fixed;left:8px;right:8px;bottom:8px;background:var(--panel);border:1px solid var(--accent);border-radius:var(--radius);padding:6px 10px;display:none;z-index:9}
#ed{position:fixed;inset:0;background:var(--bg);overflow:auto;padding:var(--gap);display:none;z-index:8}
#ed.open{display:block}
#ed h3{margin:12px 0 4px;font-size:.85em;color:var(--dim);text-transform:uppercase;letter-spacing:.07em}
#ed label{display:flex;align-items:center;gap:8px;margin:3px 0}
#ed input[type=range]{flex:1}
#ed input[type=text],#ed select,#ed textarea{background:var(--panel);color:var(--text);border:1px solid rgba(127,127,127,.4);border-radius:6px;padding:4px 6px;font:inherit}
#ed textarea{width:100%;height:6em;font-family:ui-monospace,Consolas,monospace;font-size:.8em}
#ed .row{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
#ed .cols{display:grid;grid-template-columns:repeat(auto-fill,minmax(9.5em,1fr));gap:2px 10px}
</style></head><body>
<div id="app">
 <div class="hdr" id="hdr">
  <span class="t" id="ttl">KPA1500</span><span class="vr" id="vr"></span>
  <span class="hf" id="hFreq">---</span>
  <button class="btn hb" id="h_opr">OPERATE</button>
  <button class="btn hb" id="h_amp">AMP</button>
  <span class="sp"></span>
  <span class="badge"><i class="dot" id="dRadio"></i><span id="tRadio">radio ?</span></span>
  <span class="badge" id="bFlex" style="display:none" title="FlexRadio the amplifier and tuner are registered with"><i class="dot on"></i><span id="tFlex"></span></span>
  <span class="badge" id="bMode">--</span>
  <button class="ib" id="bSkin" title="Change how this window looks">&#9998; Look</button>
  <a class="ib" href="/" target="_blank" rel="noopener" title="Open the full bridge panel" style="text-decoration:none">Panel</a>
 </div>
 <div id="bans">
  <div class="ban warn" id="bFollow"></div>
  <div class="ban bad" id="bFault"></div>
  <div class="ban warn" id="bNoAnt"></div>
  <div class="ban bad" id="bDrive"></div>
  <div class="ban bad" id="bDown">BRIDGE NOT RUNNING - data frozen</div>
 </div>
 <div class="sec" id="s_telemetry" data-sec="telemetry"><h2>Telemetry</h2><div class="grid" id="gTel"></div></div>
 <div class="sec" id="s_controls" data-sec="controls"><h2>Controls</h2><div class="btns" id="gBtn"></div></div>
 <div class="sec" id="s_knob" data-sec="knob"><h2>FlexControl knob</h2>
  <div class="big" id="kNow">--</div>
  <div class="kn" id="kLines"></div>
  <div class="sub" id="kStat">--</div>
 </div>
 <div class="sec" id="s_lp100" data-sec="lp100"><h2>LP-100A</h2><div class="grid" id="gLp"></div><div class="sub" id="lpTxt">--</div></div>
</div>
<div id="toast"></div>
<div id="ed"></div>
<script>
const VER='__VERSION__';
const T=new URLSearchParams(location.search).get('t');const Q=T?('?t='+encodeURIComponent(T)):'';
const $=id=>document.getElementById(id);
const COLORS=['bg','panel','text','dim','accent','ok','warn','bad','meter'];
const THEMES={
 dark:{bg:'#10141a',panel:'#1a212b',text:'#e6edf3',dim:'#8b98a8',accent:'#3aa0ff',ok:'#2fbf71',warn:'#f2b134',bad:'#ef4f4f',meter:'#2fbf71'},
 light:{bg:'#eef1f5',panel:'#ffffff',text:'#17202a',dim:'#5c6b7a',accent:'#0b6bcb',ok:'#1f9d57',warn:'#d98e04',bad:'#d93636',meter:'#1f9d57'},
 contrast:{bg:'#000000',panel:'#101010',text:'#ffffff',dim:'#c0c0c0',accent:'#00e5ff',ok:'#00ff66',warn:'#ffe000',bad:'#ff3030',meter:'#00ff66'},
 nereus:{bg:'#07182a',panel:'#0e2b47',text:'#e8f4ff',dim:'#7fa6c9',accent:'#38bdf8',ok:'#34d399',warn:'#fbbf24',bad:'#f87171',meter:'#38bdf8'},
 amber:{bg:'#141006',panel:'#201a0a',text:'#ffd98a',dim:'#a88a45',accent:'#ffb000',ok:'#9be564',warn:'#ffcf40',bad:'#ff5a3c',meter:'#ffb000'}};
const SECTIONS=[['telemetry','Telemetry'],['controls','Controls'],['knob','FlexControl knob'],['lp100','LP-100A']];
const METERS=[['fwd','Amp forward','amp_fwd','W',0,1750,1500,'tel'],['drv','Drive','amp_drive','W',0,100,80,'tel'],
 ['swr','Amp SWR','amp_swr',':1',1,3,2,'tel'],['refl','Reflected','amp_refl','W',0,300,200,'tel'],
 ['temp','Temperature','amp_temp','°C',0,100,80,'tel'],['volts','Supply','amp_volts','V',0,70,65,'tel'],
 ['amps','Current','amp_amps','A',0,60,50,'tel'],
 ['lpwr','LP-100A power','lp_pwr','W',0,1750,1500,'lp'],['lswr','LP-100A SWR','lp_swr',':1',1,3,2,'lp']];
const BUTTONS=[
 ['opr','OPERATE','STANDBY',m=>m.amp_operate==1,'toggle_operate','toggle_operate'],
 ['atu','ATU IN','ATU BYP',m=>m.amp_atu_inline==1,'toggle_atu','toggle_atu'],
 ['ant','ANT 1','ANT 2',m=>m.amp_ant==1,'toggle_ant','toggle_ant'],
 ['amp','AMP ON','AMP OFF',m=>m.amp_online==1,'power_off','power_on'],
 ['tune','STOP TUNE','TUNE',m=>m.amp_tune_active==1,'radio_tune_stop','radio_tune'],
 ['atutune','STOP ATU','ATU TUNE',m=>m.amp_atu_tuning==1,'atu_cancel','atu_tune'],
 ['sot','SoT ON','SoT OFF',m=>m.amp_sot==1,'toggle_sot','toggle_sot'],
 ['dummy','DUMMY OK','DUMMY OK',m=>m.dummy_ok==1,'dummy_ok','dummy_ok'],
 ['fault','FAULT - CLR','NO FAULT',m=>m.amp_fault!=0,'clear_fault','clear_fault'],
 ['fandn','FAN -','FAN -',null,'fan_down','fan_down'],
 ['fanup','FAN +','FAN +',null,'fan_up','fan_up'],
 ['lpalarm','LP ALARM','LP ALARM',null,'lp_alarm','lp_alarm'],
 ['lpmode','LP MODE','LP MODE',null,'lp_mode','lp_mode']];
const DEF={theme:'dark',colors:{},font:14,cols:2,bar:16,radius:8,gap:8,title:'KPA1500',width:460,height:780,zoom:100,fit:true,caps:true,
 order:SECTIONS.map(s=>s[0]),hide:[],hide_items:[]};
let skin=JSON.parse(JSON.stringify(DEF)),S=null,loaded=false,dirty=false,peakMs=4000;
function effColors(k){return Object.assign({},THEMES[k.theme]||THEMES.dark,k.colors||{});}
function fitWin(){
 const b=document.body,z0=(skin.zoom||100)/100;
 b.style.zoom=1;
 let z=z0;
 if(skin.fit!==false){const h=b.offsetHeight+2*parseFloat(getComputedStyle(b).marginTop||0);if(h>0)z=Math.min(z0,innerHeight/h);}
 b.style.zoom=Math.max(0.4,Math.min(2,z));
}
addEventListener('resize',()=>fitWin());
let fitT=0;
function fitSoon(){const n=Date.now();if(n-fitT>1500){fitT=n;fitWin();}}
function applySkin(){
 const r=document.documentElement.style,c=effColors(skin);
 COLORS.forEach(n=>r.setProperty('--'+n,c[n]));
 r.setProperty('--font',skin.font+'px');r.setProperty('--cols',skin.cols);r.setProperty('--bar',skin.bar+'px');
 r.setProperty('--radius',skin.radius+'px');r.setProperty('--gap',skin.gap+'px');
 $('ttl').textContent=skin.title||'KPA1500';document.title=(skin.title||'KPA1500')+' Applet v'+VER;$('vr').textContent='v'+VER;
 SECTIONS.forEach(([id])=>{const e=$('s_'+id);e.style.display=skin.hide.includes(id)?'none':'';e.style.order=String(skin.order.indexOf(id)+1||9);});
 $('hdr').style.order='0';
 document.body.classList.toggle('nocap',skin.caps===false);
 [['hfreq','hFreq'],['hopr','h_opr'],['hpwr','h_amp']].forEach(a=>{const e=$(a[1]);if(e)e.style.display=skin.hide_items.includes(a[0])?'none':'';});
 fitWin();
 METERS.forEach(m=>{const e=$('m_'+m[0]);if(e)e.style.display=skin.hide_items.includes(m[0])?'none':'';});
 BUTTONS.forEach(b=>{const e=$('b_'+b[0]);if(e)e.style.display=skin.hide_items.includes(b[0])?'none':'';});
}
// ---- build once
const PK={};
METERS.forEach(m=>{
 const d=document.createElement('div');d.className='m';d.id='m_'+m[0];
 d.innerHTML='<div class="mh"><span class="ml"></span><span class="mv">--</span></div><div class="bar"><i class="f1"></i><i class="f2"></i><i class="pk"></i></div>';
 d.querySelector('.ml').textContent=m[1];$(m[7]==='lp'?'gLp':'gTel').appendChild(d);PK[m[0]]=[];
});
BUTTONS.forEach(b=>{
 const e=document.createElement('button');e.className='btn';e.id='b_'+b[0];e.textContent=b[2];
 e.onclick=()=>press(b);$('gBtn').appendChild(e);
});
function toast(t){const e=$('toast');e.textContent=t;e.style.display='block';clearTimeout(toast.h);toast.h=setTimeout(()=>e.style.display='none',/^Refused|Could not|not /i.test(t)?9000:2500);}
async function post(action,params){
 try{const r=await fetch('/api/cmd'+Q,{method:'POST',headers:{'Content-Type':'application/json','X-KPA':'1'},body:JSON.stringify({action:action,params:params||{}})});
  const j=await r.json();return j;}catch(e){return {ok:false,message:'Could not reach the bridge'};}
}
async function press(b){
 const m=(S&&S.mm)||{};const lit=b[3]?b[3](m):false;const act=lit?b[4]:b[5];
 if(act==='power_off'&&S&&S.confirm_off&&!confirm('Switch the amplifier OFF?'))return;
 const j=await post(act);toast((j.ok?'':'Refused: ')+(j.message||act));
}
const pct=(m,v)=>Math.max(0,Math.min(100,(v-m[4])/(m[5]-m[4])*100));
function setMeter(m,v){
 const e=$('m_'+m[0]);if(!e)return;v=+v||0;const now=Date.now(),h=PK[m[0]];h.push([now,v]);
 while(h.length&&now-h[0][0]>peakMs)h.shift();let pk=v;h.forEach(x=>{if(x[1]>pk)pk=x[1];});
 const p=pct(m,v),ph=pct(m,m[6]),pp=pct(m,pk);
 e.querySelector('.f1').style.width=Math.min(p,ph)+'%';
 const f2=e.querySelector('.f2');f2.style.left=ph+'%';f2.style.width=Math.max(0,p-ph)+'%';
 e.querySelector('.pk').style.left=Math.min(98.5,pp)+'%';
 e.querySelector('.mv').textContent=(m[4]===1&&m[5]===3?v.toFixed(1):(Math.abs(v)<100&&m[3]!=='W'?v.toFixed(1):Math.round(v)))+' '+m[3];
}
function render(s){
 S=s;fitSoon();const m=s.mm||{};
 $('bDown').classList.remove('show');document.body.classList.remove('stale');
 const rn={thetis:'Thetis',nereus:'NereusSDR'}[s.radio]||'radio program';
 $('tRadio').textContent=s.tci?rn:(s.radio?rn+' - waiting':'waiting');$('dRadio').className='dot'+(s.tci?' on':'');
 {const fr=s.flex&&s.flex.radio,fi=fr&&fr.info||{},ft=[fi.name,fi.model,fi.callsign].filter(Boolean).join(' ');
  $('bFlex').style.display=(fr&&fr.state==='registered')?'':'none';$('tFlex').textContent='Flex: '+(ft||fr&&fr.ip||'');}
 $('bMode').textContent=(m.amp_power&&m.amp_power!=='ON')?m.amp_power:(m.amp_mode||'--');
 $('hFreq').textContent=m.amp_freq||'---';const bw=$('bFollow');if(m.amp_following===0&&/!/.test(m.amp_freq_line||'')){bw.textContent='Amp frequency: '+m.amp_freq_line;bw.classList.add('show');}else bw.classList.remove('show');
 const bf=$('bFault');if(m.amp_fault){bf.textContent='FAULT: '+(m.amp_fault_text||m.amp_fault);bf.classList.add('show');}else bf.classList.remove('show');
 const bn=$('bNoAnt');if(m.noant==1){bn.textContent=m.noant_text||'ANTENNA?';bn.classList.add('show');}else bn.classList.remove('show');
 const bdr=$('bDrive');if(m.drvlim==1){bdr.textContent=m.drvlim_text||'OVER-DRIVE';bdr.classList.add('show');}else bdr.classList.remove('show');
 METERS.forEach(x=>setMeter(x,m[x[2]]));
 BUTTONS.forEach(b=>{const e=$('b_'+b[0]);if(!e)return;const lit=b[3]?!!b[3](m):false;
  const hh=$('h_'+b[0]);if(hh){hh.textContent=lit?b[1]:b[2];hh.classList.toggle('lit',lit);}
  e.textContent=lit?b[1]:b[2];e.classList.toggle('lit',lit);e.classList.toggle('alert',lit&&b[0]==='fault');
  e.disabled=(b[0]==='lpalarm'||b[0]==='lpmode')&&!s.lp_enabled;});
 $('kNow').textContent=m.knob_now||'--';
 $('kLines').innerHTML='';[['Knob','knob_k'],['B1','knob_b1'],['B2','knob_b2'],['B3','knob_b3']].forEach(a=>{
  const d=document.createElement('div');const k=document.createElement('span');k.className='k';k.textContent=a[0];
  d.appendChild(k);d.appendChild(document.createTextNode(m[a[1]]||'--'));$('kLines').appendChild(d);});
 $('kStat').textContent=m.knob_status||'--';
 $('lpTxt').textContent=m.lp_online==1?('Z '+m.lp_z+' Ω   R '+m.lp_r+'  X '+m.lp_x+'   Refl '+m.lp_refl+' W   RL '+m.lp_rl+' dB'):'LP-100A not connected';
 if(!loaded&&s.applet_skin){skin=Object.assign(JSON.parse(JSON.stringify(DEF)),s.applet_skin);loaded=true;applySkin();}
 const rs=$('edRadio');if(rs&&document.activeElement!==rs)rs.value=s.radio_pref||'auto';
}
async function poll(){
 try{const r=await fetch('/api/state'+Q,{cache:'no-store'});if(!r.ok)throw 0;render(await r.json());}
 catch(e){$('bDown').classList.add('show');document.body.classList.add('stale');}
 setTimeout(poll,250);
}
// ---- the "Look" editor
function el(tag,props,kids){const e=document.createElement(tag);Object.assign(e,props||{});(kids||[]).forEach(k=>e.appendChild(typeof k==='string'?document.createTextNode(k):k));return e;}
function slider(label,key,min,max,step){
 const v=el('span',{textContent:String(skin[key])}),i=el('input',{type:'range',min:min,max:max,step:step,value:skin[key]});
 i.oninput=()=>{skin[key]=+i.value;v.textContent=i.value;dirty=true;applySkin();};
 return el('label',{},[el('span',{textContent:label,style:'min-width:7em'}),i,v]);
}
function openEd(){
 const ed=$('ed');ed.innerHTML='';
 const row=(a)=>el('div',{className:'row'},a);
 ed.appendChild(row([el('b',{textContent:'How this window looks',style:'flex:1;font-size:1.1em'}),
  el('button',{className:'btn',textContent:'Save',onclick:saveSkin}),el('button',{className:'btn',textContent:'Close',onclick:()=>ed.classList.remove('open')})]));
 ed.appendChild(el('h3',{textContent:'Radio program'}));
 const rs=el('select',{id:'edRadio'},[['auto','Detect automatically'],['thetis','Thetis'],['nereus','NereusSDR']].map(a=>el('option',{value:a[0],textContent:a[1]})));
 rs.value=(S&&S.radio_pref)||'auto';rs.onchange=async()=>{const j=await post('radio_set',{radio:rs.value});toast(j.message||'');};
 ed.appendChild(row([rs]));
 ed.appendChild(el('h3',{textContent:'Colours'}));
 const th=el('select',{},Object.keys(THEMES).map(k=>el('option',{value:k,textContent:k})));th.value=skin.theme;
 th.onchange=()=>{skin.theme=th.value;skin.colors={};dirty=true;applySkin();openEd();};
 ed.appendChild(row([el('span',{textContent:'Theme'}),th]));
 const cg=el('div',{className:'cols'});const eff=effColors(skin);
 const names={bg:'Background',panel:'Panels',text:'Text',dim:'Quiet text',accent:'Accent',ok:'Lit / OK',warn:'Warning',bad:'Alarm',meter:'Meter bars'};
 COLORS.forEach(n=>{const i=el('input',{type:'color',value:eff[n]});i.oninput=()=>{skin.colors[n]=i.value;skin.theme=th.value;dirty=true;applySkin();};
  cg.appendChild(el('label',{},[i,names[n]]));});
 ed.appendChild(cg);
 ed.appendChild(el('h3',{textContent:'Size and spacing'}));
 ed.appendChild(slider('Text size','font',10,28,1));ed.appendChild(slider('Bar height','bar',6,36,1));
 ed.appendChild(slider('Zoom %','zoom',50,150,5));
 const ft=el('input',{type:'checkbox',checked:skin.fit!==false});ft.onchange=()=>{skin.fit=ft.checked;dirty=true;applySkin();};
 ed.appendChild(row([ft,el('span',{textContent:'Shrink to fit the window height (nothing is cut off)'})]));
 ed.appendChild(slider('Corner radius','radius',0,22,1));ed.appendChild(slider('Spacing','gap',2,20,1));
 const cs=el('select',{},[1,2,3].map(n=>el('option',{value:n,textContent:n+(n===1?' column':' columns')})));cs.value=skin.cols;
 cs.onchange=()=>{skin.cols=+cs.value;dirty=true;applySkin();};
 ed.appendChild(row([el('span',{textContent:'Meters and buttons in',style:'min-width:9em'}),cs]));
 const ti=el('input',{type:'text',value:skin.title,maxLength:30});ti.oninput=()=>{skin.title=ti.value;dirty=true;applySkin();};
 ed.appendChild(row([el('span',{textContent:'Window title',style:'min-width:9em'}),ti]));
 const wi=el('input',{type:'text',value:skin.width,size:5}),hi=el('input',{type:'text',value:skin.height,size:5});
 const ap=el('button',{className:'btn',textContent:'Resize window',onclick:()=>{skin.width=Math.max(240,Math.min(1600,+wi.value||460));skin.height=Math.max(240,Math.min(1600,+hi.value||780));dirty=true;try{window.resizeTo(skin.width,skin.height);}catch(e){}}});
 ed.appendChild(row([el('span',{textContent:'Window size',style:'min-width:9em'}),wi,'×',hi,ap]));
 ed.appendChild(el('h3',{textContent:'Top line: show'}));
 const tg=el('div',{className:'cols'});
 [['hfreq','Frequency'],['hopr','Operate / Standby button'],['hpwr','Power on / off button']].forEach(a=>{
  const cb=el('input',{type:'checkbox',checked:!skin.hide_items.includes(a[0])});
  cb.onchange=()=>{skin.hide_items=skin.hide_items.filter(x=>x!==a[0]);if(!cb.checked)skin.hide_items.push(a[0]);dirty=true;applySkin();};
  tg.appendChild(el('label',{},[cb,a[1]]));});
 ed.appendChild(tg);
 ed.appendChild(el('h3',{textContent:'Sections: show and order'}));
 const cc=el('input',{type:'checkbox',checked:skin.caps!==false});cc.onchange=()=>{skin.caps=cc.checked;dirty=true;applySkin();};
 ed.appendChild(row([cc,el('span',{textContent:'Show the section captions (Status, Telemetry, ...)'})]));
 skin.order.forEach((id,ix)=>{
  const nm=(SECTIONS.find(s=>s[0]===id)||[id,id])[1];
  const cb=el('input',{type:'checkbox',checked:!skin.hide.includes(id)});
  cb.onchange=()=>{skin.hide=skin.hide.filter(x=>x!==id);if(!cb.checked)skin.hide.push(id);dirty=true;applySkin();};
  const mv=(d)=>()=>{const j=ix+d;if(j<0||j>=skin.order.length)return;const o=skin.order;[o[ix],o[j]]=[o[j],o[ix]];dirty=true;applySkin();openEd();};
  ed.appendChild(row([cb,el('span',{textContent:nm,style:'flex:1'}),el('button',{className:'btn',textContent:'▲',onclick:mv(-1)}),el('button',{className:'btn',textContent:'▼',onclick:mv(1)})]));
 });
 ed.appendChild(el('h3',{textContent:'Meters'}));
 const mg=el('div',{className:'cols'});
 METERS.forEach(m=>{const cb=el('input',{type:'checkbox',checked:!skin.hide_items.includes(m[0])});
  cb.onchange=()=>{skin.hide_items=skin.hide_items.filter(x=>x!==m[0]);if(!cb.checked)skin.hide_items.push(m[0]);dirty=true;applySkin();};
  mg.appendChild(el('label',{},[cb,m[1]]));});
 ed.appendChild(mg);
 ed.appendChild(el('h3',{textContent:'Buttons'}));
 const bg=el('div',{className:'cols'});
 BUTTONS.forEach(b=>{const cb=el('input',{type:'checkbox',checked:!skin.hide_items.includes(b[0])});
  cb.onchange=()=>{skin.hide_items=skin.hide_items.filter(x=>x!==b[0]);if(!cb.checked)skin.hide_items.push(b[0]);dirty=true;applySkin();};
  bg.appendChild(el('label',{},[cb,b[1]===b[2]?b[1]:b[1]+' / '+b[2]]));});
 ed.appendChild(bg);
 ed.appendChild(el('h3',{textContent:'Safety: no-antenna check'}));
 const na=(S&&S.noant)||{};
 const nc=el('input',{type:'checkbox',checked:!!na.enabled});
 nc.onchange=async()=>{const j=await post(nc.checked?'noant_on':'noant_off');toast(j.message||'Done');};
 ed.appendChild(row([nc,el('span',{textContent:'Refuse TUNE and warn when the receive level looks like no antenna'})]));
 const nsel=el('select',{},[el('option',{value:'warn',textContent:'Only warn'}),el('option',{value:'standby',textContent:'Warn and put the amp in STANDBY'})]);nsel.value=na.action||'warn';
 nsel.onchange=async()=>{const j=await post('noant_action',{action:nsel.value});toast(j.message||'Done');};
 ed.appendChild(row([el('span',{textContent:'When it triggers',style:'min-width:9em'}),nsel]));
 ed.appendChild(el('div',{className:'sub',textContent:'The limit for each band is set in the full panel (Panel button, Settings). This setting is saved by the bridge, not by this look.'}));
 ed.appendChild(el('h3',{textContent:'Safety: over-drive protection'}));
 const dgs=(S&&S.drive_guard)||{};
 const dgl=el('input',{type:'text',size:5,value:dgs.limit>0?String(dgs.limit):'',placeholder:'off'});
 dgl.onchange=async()=>{const j=await post('drive_guard',{limit:dgl.value});toast(j.message||'Done');};
 ed.appendChild(row([el('span',{textContent:'Limit (W into the amp)',style:'min-width:9em'}),dgl]));
 const dga=el('select',{},[el('option',{value:'ignore',textContent:'Ignore'}),el('option',{value:'warn',textContent:'Warn'}),el('option',{value:'limit',textContent:'Hold at the limit'})]);dga.value=dgs.action||'warn';
 dga.onchange=async()=>{const j=await post('drive_guard',{action:dga.value});toast(j.message||'Done');};
 ed.appendChild(row([el('span',{textContent:'If it goes over',style:'min-width:9em'}),dga]));
 const dgw=el('input',{type:'text',size:5,value:String(dgs.radio_w||100)});
 dgw.onchange=async()=>{const j=await post('drive_guard',{radio_w:dgw.value});toast(j.message||'Done');};
 ed.appendChild(row([el('span',{textContent:'Radio full power (W)',style:'min-width:9em'}),dgw]));
 ed.appendChild(el('div',{className:'sub',textContent:'Only judged while the amp is in OPERATE. This helps; it does not replace care. The amplifier keeps its own protection as the last line of defence.'}));
 ed.appendChild(el('h3',{textContent:'Bridge'}));
 ed.appendChild(row([el('button',{className:'btn',textContent:'Quit bridge',onclick:async()=>{if(!confirm('Close the bridge and this window? The amplifier is not changed.'))return;const j=await post('quit_bridge');toast(j.message||'Closing');}}),
  el('span',{className:'sub',textContent:'Closes the bridge, its COM ports and this window. Only works on the bridge computer.'})]));
 ed.appendChild(el('h3',{textContent:'Share or restore a look'}));
 const ta=el('textarea',{value:JSON.stringify(skin)});
 ed.appendChild(ta);
 ed.appendChild(row([el('button',{className:'btn',textContent:'Use the text above',onclick:()=>{try{skin=Object.assign(JSON.parse(JSON.stringify(DEF)),JSON.parse(ta.value));dirty=true;applySkin();openEd();}catch(e){toast('That text is not a saved look');}}}),
  el('button',{className:'btn',textContent:'Back to the standard look',onclick:()=>{skin=JSON.parse(JSON.stringify(DEF));dirty=true;applySkin();openEd();}})]));
 ed.classList.add('open');
}
async function saveSkin(){const j=await post('applet_skin',{skin:skin});if(j.ok)dirty=false;toast(j.message||'Saved');}
$('bSkin').onclick=openEd;
['opr','amp'].forEach(id=>{const b=BUTTONS.find(x=>x[0]===id);$('h_'+id).onclick=()=>press(b);});
applySkin();poll();
</script></body></html>
'''


class Bridge:
    def __init__(self, a, quiet=False):
        self.a = a
        self.quiet = quiet
        self.stop = threading.Event()
        self.print_lock = threading.Lock()
        self._saved_settings = load_settings(a.settings_file) if a.settings_file else {}
        ip0, self.amp_ip_source = resolve_amp_ip(a.amp_ip, self._saved_settings.get("amp_ip"))
        self.amp = Amp(ip0, a.amp_port, a.dry_run, self.log)
        self.found_amps = []
        self.finding = False
        self._t0 = time.time()
        self._hinted = False
        self.lp = None
        self.web = None
        self.last_msg = ""
        self.settings = load_settings(a.settings_file) if a.settings_file else {}
        # --- log file management (a choice saved from the panel wins over flags)
        self._log_lock = threading.Lock()
        self._log_fh = None
        self._log_size = 0
        if "log_enabled" in self.settings:
            self.log_enabled = bool(self.settings["log_enabled"]) and bool(a.logfile)
        else:
            self.log_enabled = bool(a.logfile) and not a.no_log
        try:
            self.log_max_mb = float(self.settings.get("log_max_mb", a.log_max_mb))
        except (TypeError, ValueError):
            self.log_max_mb = 2.0
        self.confirm_power_off = bool(self.settings.get("confirm_power_off", True))
        if isinstance(self.settings.get("web_token"), str):     # set or removed in the panel
            a.web_token = self.settings["web_token"]
        self.local_no_token = True     # the bridge computer itself never needs the panel password
        # may a Thetis button (KPA_POWER_OFF) switch the amp off?
        self.allow_thetis_off = bool(self.settings.get("allow_thetis_power_off", True))
        # refuse power off while RF is present? (off = emergency shutdown allowed under TX)
        self.block_off_tx = bool(self.settings.get("block_power_off_in_tx", True))
        # "no antenna?" check (receive level from Thetis)
        na = self.settings.get("noant") if isinstance(self.settings.get("noant"), dict) else {}
        self.noant_enabled = bool(na.get("enabled", True))
        self.noant_action = na.get("action") if na.get("action") in ("warn", "standby") else "warn"
        self.noant_limits = clean_limits(na.get("limits"))
        self.noant_lock = threading.RLock()
        self.rx_samples = []          # (time, dBm) while receiving
        self.rx_msg_t = 0.0           # last receive-level message from Thetis
        self.rx_quiet_until = 0.0     # ignore readings until (band change / after TX)
        self.rx_band = None
        self.rx_ex_seen = False
        self.rx_ch_seen = False
        self.noant_low = False
        self.dummy_ok = set()         # bands where DUMMY OK was pressed
        self.noant_held = False       # amp put in STANDBY by the check
        self._noant_tx_logged = False
        self._noant_low_logged = False
        # over-drive protection: one limit in watts at the amplifier input (0 = off)
        dg = self.settings.get("drive_guard") if isinstance(self.settings.get("drive_guard"), dict) else {}
        self.dg_action = dg.get("action") if dg.get("action") in DG_ACTIONS else "warn"
        self.dg_limit = clean_dg_num(dg.get("limit"), 0.0, 0.0, 1500.0)
        self.dg_radio_w = clean_dg_num(dg.get("radio_w"), 100.0, 1.0, 1500.0)
        self.dg_slider = None         # the radio's RF power setting, 0-100 (from the FlexRadio)
        self.dg_slider_t = 0.0
        self.dg_last_tx = False
        self.dg_clamp_t = 0.0
        self.dg_over_since = None     # when measured over-drive began (raw, before the spike filter)
        self.dg_hot_t = 0.0           # last time over-drive was confirmed (lasted longer than a short peak)
        self.dg_held = False          # amp put in STANDBY by the over-drive protection
        self.dg_logged = ""
        # bridge-started radio TUNE (amp to STANDBY first, then key)
        try:
            self.tune_timeout = max(0, min(600, int(self.settings.get("tune_timeout", 20))))
        except (TypeError, ValueError):
            self.tune_timeout = 20
        self.thetis_buttons = clean_thetis_buttons(self.settings.get("thetis_buttons"))
        # FlexControl tuning knob
        self.knob_cfg = clean_knob(self.settings.get("knob"))
        self.knob = None
        self.knob_mode = "vfoa"
        self.knob_vals = {}           # value modes: mode -> [value, time last used]
        self.knob_last = ("", "", 0.0)  # last message: code, meaning, time
        self.knob_t = 0.0             # last knob activity
        self.cat_replies = {}         # Thetis CAT answers via TCI run_cat_ex: code -> (value, time)
        self.cat_events = {}
        self.agc_val = {}
        self.tci_cat_ok = None        # do the knob's CAT commands get through? (run_cat_ex, or NereusSDR's CAT port)
        rp = self.settings.get("radio")
        self.radio_pref = rp if rp in RADIO_KINDS else (getattr(a, "radio", "auto") if getattr(a, "radio", "auto") in RADIO_KINDS else "auto")
        self.radio_kind = {"thetis": "thetis", "nereus": "nereus"}.get(self.radio_pref)   # None until found (auto)
        self.cat_via = "tcp" if self.radio_pref == "nereus" else "tci"
        self.cat_link = None
        self.cat_noans = {}
        self.cat_check_lock = threading.Lock()
        self.applet_skin = clean_applet_skin(self.settings.get("applet_skin"))
        self.thetis_meters = clean_thetis_meters(self.settings.get("thetis_meters"))
        self.thetis_knobwin = clean_knob_window(self.settings.get("thetis_knobwin"))
        self.tci_ws = None
        self.tci_send_lock = threading.Lock()
        self.tune_t = 0.0             # when the current tune started
        self.bridge_tune = False      # the current tune was started by the bridge
        self.prompting = False
        self.quit = False

        # radio state
        self.freq_hz = {0: None, 1: None}
        self.split = False
        self.tx = False
        self.tci_ok = False
        self.want_khz = None
        self.last_khz = None
        self.last_band = None
        self.amp_khz = None       # frequency the amp reports (^FR;), kHz
        self.fr_miss = 0          # unanswered ^FR; queries (3 = amp does not report it)
        self.fr_due = 0.0         # time to read the amp frequency back
        # amp state
        self.mode = None          # 0 standby / 1 operate
        self.mode_time = 0
        self.fwd = 0
        self.refl = 0
        self.swr = 1.0
        self.pin = 0
        self.temp = None
        self.volts = None
        self.amps = None
        self.fault = None
        self.atu = None           # 'I' inline / 'B' bypass
        self.ant = None
        self.atu_tuning = None
        self.atu_c = self.atu_l = None   # ATU capacitor / inductor relay bitmasks (^CR; ^LR;)
        self.atu_side = None             # "T" capacitor on the transmitter side, "A" on the antenna side
        self.fan_speed = None     # current fan speed 0-5 (^FS)
        self.fan_min = None       # minimum fan speed 0-5 (^FC)
        self.amp_ok = False
        # True once the amp has answered at this address (remembered between runs)
        self.ever_ok = self.settings.get("amp_seen_ip") == self.amp.addr[0]
        self.presence = None        # amp visible in the ARP table while it is silent?
        self.flex = None            # FlexRadio PGXL/TGXL emulation (optional add-on)
        self.presence_match = False  # ... and it is our amp (same MAC as learned earlier)
        self.miss = 0
        self.radio_fwd = 0.0      # radio's own measured TX power (TCI tx_sensors)
        self.radio_swr = None
        self.radio_t = 0.0
        self.wol = None           # amp setting NET WAKE on LAN (True/False)
        self.mac = norm_mac(a.amp_mac) if a.amp_mac else None
        if not self.mac and a.mac_file and os.path.exists(a.mac_file):
            try:
                self.mac = norm_mac(open(a.mac_file).read())
            except OSError:
                pass
        self.power_thread = None
        # tune handling
        self.tune_active = False
        self.saved_mode = None
        self.standby_on_tune = not a.no_standby_on_tune

    # ---- logging ---------------------------------------------------------
    def _log_limit_bytes(self):
        return int(self.log_max_mb * 1048576) if self.log_max_mb > 0 else 0

    def _write_log(self, text):
        with self._log_lock:
            try:
                if self._log_fh is None:
                    if os.path.exists(self.a.logfile):
                        self._log_size = os.path.getsize(self.a.logfile)
                    else:
                        self._log_size = 0
                    self._log_fh = open(self.a.logfile, "a", encoding="utf-8")
                self._log_fh.write(text)
                self._log_fh.flush()
                self._log_size += len(text.encode("utf-8"))
                lim = self._log_limit_bytes()
                if lim and self._log_size > lim:
                    self._trim_log(lim)
            except OSError as e:
                self.log_enabled = False
                self._close_log()
                if not self.quiet:
                    print("\nLog file problem (%s) - file logging turned off." % e)

    def _close_log(self):
        try:
            if self._log_fh:
                self._log_fh.close()
        except OSError:
            pass
        self._log_fh = None

    def _trim_log(self, lim):
        """Keep only the newest part of the log (a quarter of the limit)."""
        keep = max(1024, lim // 4)
        path = self.a.logfile
        self._close_log()
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - keep))
            data = f.read()
        i = data.find(b"\n")
        if 0 <= i < len(data) - 1:
            data = data[i + 1:]
        head = ("--- log trimmed %s: kept the newest %d KB (limit %.1f MB) ---\n" % (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            len(data) // 1024, self.log_max_mb)).encode()
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(head + data)
        os.replace(tmp, path)
        self._log_fh = open(path, "a", encoding="utf-8")
        self._log_size = os.path.getsize(path)

    def log_info(self):
        size = 0
        if self.a.logfile and os.path.exists(self.a.logfile):
            try:
                size = os.path.getsize(self.a.logfile)
            except OSError:
                pass
        return {"log_enabled": self.log_enabled, "log_max_mb": self.log_max_mb,
                "log_kb": size // 1024, "log_file": self.a.logfile or ""}

    def log(self, msg, verbose=False):
        line = "%s  %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
        if self.log_enabled and (not verbose or self.a.verbose):
            self._write_log(line + "\n")
        if self.quiet or (verbose and not self.a.verbose):
            return
        with self.print_lock:
            sys.stdout.write("\r" + line.ljust(120) + "\n")
            sys.stdout.flush()

    # ---- TCI side --------------------------------------------------------
    def tci_loop(self):
        while not self.stop.is_set():
            ws = None
            try:
                ws = WebSocket.connect(self.a.tci_host, self.a.tci_port,
                                       self.a.tci_path)
                self.tci_ws = ws
                self.tci_ok = True
                self.last_khz = None          # force resend after reconnect
                self.log("Connected to TCI at %s:%d"
                         % (self.a.tci_host, self.a.tci_port))
                ws.send_text("tx_sensors_enable:true;")   # radio TX power/SWR
                ws.send_text("rx_sensors_enable:true,250;")   # receive level (no-antenna check)
                threading.Thread(target=self.check_tci_cat, daemon=True).start()
                while not self.stop.is_set():
                    try:
                        msg = ws.recv_message()
                    except socket.timeout:
                        continue
                    self.on_tci(msg)
            except Exception as e:
                if self.tci_ok:
                    self.log("Lost TCI connection: %s" % e)
                    if self.tune_active:
                        self.log("WARNING: TCI lost during TUNE - amp left in "
                                 "STANDBY (fail-safe). Set OPERATE manually.")
                        self.tune_active = False
                        self.saved_mode = None
                elif not getattr(self, "_warned", False):
                    self.log("Waiting for TCI server (%s) ..." % e)
                    self._warned = True
                self.tci_ok = False
                self.bridge_tune = False
            finally:
                self.tci_ws = None
                if ws:
                    ws.close()
            self.stop.wait(2.0)

    CAT_REPLY_RE = re.compile(r"run_cat_ex:(ZZ[A-Z0-9]{2})[^;,]*;?,\s*(?:ZZ[A-Z0-9]{2})?([^;]*);?")

    def on_tci(self, msg):
        for m in self.CAT_REPLY_RE.finditer(msg):      # answers to Thetis CAT questions
            code, val = m.group(1), m.group(2).strip()
            self.cat_replies[code] = (val, time.time())
            ev = self.cat_events.get(code)
            if ev:
                ev.set()
        for tok in msg.split(";"):
            tok = tok.strip()
            if not tok:
                continue
            name, _, rest = tok.partition(":")
            args = [x.strip() for x in rest.split(",")] if rest else []
            self.log("<- TCI: %s" % tok, verbose=True)
            try:
                rx = int(args[0]) if args else None
                if name == "vfo" and rx == self.a.rx and len(args) >= 3:
                    self.freq_hz[int(args[1])] = int(args[2])
                    self.update_freq()
                elif name == "split_enable" and rx == self.a.rx:
                    self.split = args[1].lower() == "true"
                    self.update_freq()
                elif name == "trx" and rx == self.a.rx:
                    self.tx = args[1].lower() == "true"
                    if not self.tx:
                        self.radio_fwd, self.radio_swr = 0.0, None
                        self.rx_quiet_until = time.time() + NOANT_SETTLE
                elif (name in ("tx_sensors", "tx_sensor") and rx == self.a.rx
                      and len(args) >= 5):
                    # tx_sensors:trx,mic_dbm,fwd_watts,peak_or_rev_watts,swr[,alc]
                    self.radio_fwd = max(0.0, float(args[2]))
                    self.radio_swr = float(args[4])
                    self.radio_t = time.time()
                elif name == "tune" and rx == self.a.rx:
                    self.handle_tune(args[1].lower() == "true")
                elif name == "agc_gain" and len(args) >= 2:
                    self.agc_val[rx] = (int(float(args[1])), time.time())
                    ev = self.cat_events.get("agc_gain")
                    if ev:
                        ev.set()
                elif name == "rx_channel_sensors_ex" and rx == self.a.rx and len(args) >= 4:
                    # rx_channel_sensors_ex:rx,channel,signal,average_signal,peak_bin
                    self.rx_ex_seen = True
                    if int(args[1]) == 0:
                        self.rx_level(float(args[3]))
                elif (name == "rx_channel_sensors" and rx == self.a.rx and len(args) >= 3
                      and not self.rx_ex_seen):
                    self.rx_ch_seen = True
                    if int(args[1]) == 0:
                        self.rx_level(float(args[2]))
                elif (name == "rx_sensors" and rx == self.a.rx and len(args) >= 2
                      and not self.rx_ex_seen and not self.rx_ch_seen):
                    self.rx_level(float(args[1]))
            except (ValueError, IndexError):
                pass

    def update_freq(self):
        hz = self.freq_hz[1] if (self.split and self.freq_hz[1]) \
            else self.freq_hz[0]
        if hz:
            self.want_khz = int(round(hz / 1000.0))
            b = band_of(self.want_khz)
            if b != self.rx_band:
                with self.noant_lock:
                    self.rx_band = b
                    self.rx_samples = []
                    self.noant_low = False
                    self.rx_quiet_until = time.time() + NOANT_SETTLE

    # ---- "no antenna?" check ------------------------------------------------
    def rx_level(self, dbm):
        now = time.time()
        with self.noant_lock:
            self.rx_msg_t = now
            if self.transmitting() or now < self.rx_quiet_until or not -200 < dbm < 50:
                return
            self.rx_samples.append((now, dbm))
            while self.rx_samples and now - self.rx_samples[0][0] > NOANT_WINDOW:
                self.rx_samples.pop(0)

    def rx_dbm(self):
        with self.noant_lock:
            v = sorted(x[1] for x in self.rx_samples)
        if not v:
            return None
        n = len(v)
        return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0

    def noant_state(self):
        """state: off | na (no level from Thetis) | nolimit | ok | low | dummy | tx
        Messages are logged AFTER the lock is released (logging waits for the screen;
        holding this lock meanwhile could stop the whole bridge)."""
        msgs = []
        st = self._noant_state(msgs)
        for m, beep in msgs:
            self.log(m)
            if beep and not self.quiet:
                sys.stdout.write("\a")
        return st

    def _noant_state(self, msgs):
        with self.noant_lock:
            band = self.rx_band
            lim = self.noant_limits.get(band) if band else None
            dbm = self.rx_dbm()
            tx = self.transmitting()
            live = self.tci_ok and (tx or time.time() - self.rx_msg_t < 3.0)
            st = {"enabled": self.noant_enabled, "action": self.noant_action, "band": band,
                  "limit": lim, "dbm": None if dbm is None else round(dbm, 1), "live": live,
                  "tx": tx, "held": self.noant_held, "dummy": False, "state": "off"}
            if not self.noant_enabled:
                self.noant_low = False
            elif not live or dbm is None:
                st["state"] = "na"
            elif lim is None:
                st["state"] = "nolimit"
            else:
                if not tx:     # judge only from receive; keep the last verdict while transmitting
                    self.noant_low = dbm < (lim + NOANT_HYST if self.noant_low else lim)
                if not self.noant_low:
                    self.dummy_ok.discard(band)          # a real signal is back: forget DUMMY OK
                st["dummy"] = band in self.dummy_ok
                st["state"] = ("ok" if not self.noant_low else "dummy" if st["dummy"]
                               else "tx" if tx else "low")
            warn = st["state"] in ("low", "tx")
            st["warn"] = warn
            st["hold"] = warn and self.noant_action == "standby"
            if warn and not self._noant_low_logged:
                self._noant_low_logged = True
                msgs.append(("NO ANTENNA? Receive level %.0f dBm on %s m is below the limit %d dBm. "
                             "Check the antenna, or press DUMMY OK (key M) if a dummy load is connected."
                             % (dbm, band, lim), False))
            elif not warn:
                self._noant_low_logged = False
            if st["state"] == "tx" and not self._noant_tx_logged:
                self._noant_tx_logged = True
                msgs.append(("WARNING: TRANSMITTING while 'no antenna?' is showing (receive level was "
                             "%.0f dBm on %s m). Check the antenna / dummy load!" % (dbm, band), True))
            elif not tx:
                self._noant_tx_logged = False
            st["text"] = self.noant_text(st)
            return st

    @staticmethod
    def noant_text(st):
        s = st["state"]
        if s == "tx":
            return "!! TX - NO ANTENNA? CHECK DUMMY LOAD !!"
        if s == "low":
            if st["action"] == "standby":
                return "AMP HELD STBY - ANTENNA? RX %.0f dBm" % st["dbm"]
            return "ANTENNA? RX %.0f dBm (%sm limit %d)" % (st["dbm"], st["band"], st["limit"])
        if s == "dummy":
            return "DUMMY OK on %sm (RX %.0f dBm)" % (st["band"], st["dbm"])
        return ""

    def noant_enforce(self):
        """Option 'keep the amp in STANDBY': called from the amp poll loop."""
        st = self.noant_state()
        if st["hold"]:
            if (self.amp_ok and self.mode == 1 and not st["tx"] and not self.tune_active
                    and not self.a.dry_run):
                self.amp.set("^OS0;")
                self.ingest("^OS;", self.amp.get("^OS;"))
                if not self.noant_held:
                    self.log("Amp put in STANDBY: no antenna? (receive %.0f dBm on %s m). Press "
                             "DUMMY OK if a dummy load is connected." % (st["dbm"], st["band"]))
                self.noant_held = True
        elif self.noant_held and not st["tx"]:
            self.noant_held = False
            if self.amp_ok and self.mode == 0 and not self.tune_active and not self.a.dry_run:
                self.amp.set("^OS1;")
                self.ingest("^OS;", self.amp.get("^OS;"))
                self.log("No-antenna hold cleared - amp back to OPERATE")
            else:
                self.log("No-antenna hold cleared")

    def save_noant(self):
        self.save_setting("noant", {"enabled": self.noant_enabled, "action": self.noant_action,
                                    "limits": dict(self.noant_limits)})

    # ---- over-drive protection -------------------------------------------
    def flex_rfpower(self):
        """the radio's RF power setting (0-100) from the FlexRadio, or None when it is not known"""
        L = getattr(self.flex, "link", None) if self.flex else None
        if L is None or L.state != "registered":
            return None
        return L.rfpower

    def flex_set_rfpower(self, pct):
        """ask the FlexRadio to set its RF power (0-100); True when the request was sent"""
        L = getattr(self.flex, "link", None) if self.flex else None
        if L is None or L.state != "registered":
            return False
        L.todo.append(("rfpower", int(pct)))
        return True

    def dg_pct(self):
        """the radio drive setting (0-100) that equals the limit"""
        return max(0, min(100, int(self.dg_limit / self.dg_radio_w * 100.0 + 1e-6)))

    def drive_guard_state(self):
        """state: off | idle (amp not in OPERATE) | ok | slider (the radio's drive setting is over the limit)
        | tx (measured drive is over the limit) | held (amp put in STANDBY)"""
        enabled = self.dg_action != "ignore" and self.dg_limit > 0
        slider_w = None if self.dg_slider is None else self.dg_slider * self.dg_radio_w / 100.0
        fresh = self.dg_slider is not None and time.time() - self.dg_slider_t < 6.0
        measured, msrc = self.drive_info()
        tx = self.transmitting()
        # not while the amp is in STANDBY or its own ATU is tuning (the amp passes the full radio power through then)
        active = enabled and self.amp_ok and self.mode == 1 and not self.atu_tuning
        st = {"action": self.dg_action, "limit": self.dg_limit, "radio_w": self.dg_radio_w,
              "slider": self.dg_slider if fresh else None,
              "slider_w": round(slider_w, 1) if (slider_w is not None and fresh) else None,
              "drive_w": round(measured, 1), "tx": tx, "state": "off", "warn": False, "held": self.dg_held}
        if not enabled:
            st["state"] = "off"
        elif self.dg_held and not active:
            st["state"] = "held"
        elif not active:
            st["state"] = "idle"
        else:
            over_tx = tx and time.time() - self.dg_hot_t < DG_SHOW_S
            over_sl = fresh and slider_w > self.dg_limit + 0.5
            st["state"] = "tx" if over_tx else "slider" if over_sl else "ok"
        st["warn"] = st["state"] in ("tx", "slider", "held")
        st["text"] = self.dg_text(st)
        return st

    @staticmethod
    def dg_text(st):
        s = st["state"]
        if s == "tx":
            return "!! OVER-DRIVE: %.0f W (limit %.0f W) !!" % (st["drive_w"], st["limit"])
        if s == "held":
            return "AMP HELD STBY - drive was over %.0f W. Press OPERATE" % st["limit"]
        if s == "slider":
            if st["action"] == "limit":
                return "DRIVE SETTING %.0f W over limit %.0f W - holding at limit" % (st["slider_w"], st["limit"])
            return "DRIVE SETTING %.0f W is over the limit %.0f W" % (st["slider_w"], st["limit"])
        return ""

    def drive_guard_loop(self):
        while True:
            time.sleep(0.25)
            try:
                self.drive_guard_tick()
            except Exception as e:
                if self.dg_logged != "err":
                    self.dg_logged = "err"
                    self.log("Over-drive protection error: %s" % e)

    def drive_guard_tick(self):
        """read the radio's drive setting, compare it and the measured drive with the limit, act"""
        if self.dg_action == "ignore" or self.dg_limit <= 0:
            self.dg_held = False if not (self.amp_ok and self.mode == 0) else self.dg_held
            return
        now = time.time()
        tx = self.transmitting()
        pct = self.flex_rfpower()
        if pct is not None:
            self.dg_slider = max(0, min(100, int(pct)))
            self.dg_slider_t = now
        self.dg_last_tx = tx
        if self.dg_held and self.mode == 1:
            self.dg_held = False                       # the operator pressed OPERATE again
        # measured drive: only the amp's own input reading counts, and only when it lasts (short peaks are ignored)
        meas, msrc = self.drive_info()
        raw_over = (self.amp_ok and self.mode == 1 and not self.atu_tuning and tx and msrc == "amp"
                    and meas > self.dg_limit * DG_TOL + 1.0)
        if raw_over:
            if self.dg_over_since is None:
                self.dg_over_since = now
            if now - self.dg_over_since >= DG_SPIKE_S:
                self.dg_hot_t = now
        else:
            self.dg_over_since = None
        st = self.drive_guard_state()
        s = st["state"]
        if s in ("slider", "tx", "held"):
            if self.dg_logged != s:
                self.dg_logged = s
                if s == "slider":
                    self.log("DRIVE SETTING %.0f W (radio RF power %d) is over the limit %.0f W%s"
                             % (st["slider_w"], st["slider"], st["limit"],
                                " - holding it at the limit" if st["action"] == "limit" else ""))
                elif s == "tx":
                    self.log("OVER-DRIVE: %.0f W measured, limit %.0f W%s" % (
                        st["drive_w"], st["limit"], " - pulling the drive back" if st["action"] == "limit" else ""))
        elif s in ("ok", "idle", "off"):
            self.dg_logged = ""
        if st["action"] != "limit" or s not in ("slider", "tx"):
            return
        # hold at the limit: put the radio's RF power setting back to the limit (not more than once per 1.5 s)
        if now - self.dg_clamp_t >= 1.5 and not self.a.dry_run:
            self.dg_clamp_t = now
            pct = self.dg_pct()
            if self.flex_set_rfpower(pct):
                self.dg_slider = pct
                self.dg_slider_t = now
                self.log("RF power put back to %d (limit %.0f W of the radio's %.0f W)"
                         % (pct, self.dg_limit, self.dg_radio_w))
        if s == "tx":
            if (raw_over and self.dg_over_since is not None
                    and now - self.dg_over_since >= DG_SPIKE_S + DG_STANDBY_S and now - self.dg_clamp_t >= 0.3
                    and self.amp_ok and self.mode == 1 and not self.a.dry_run):
                self.amp.set("^OS0;")
                self.ingest("^OS;", self.amp.get("^OS;"))
                self.dg_held = True
                self.dg_over_since = None
                self.dg_hot_t = 0.0
                self.log("Amp put in STANDBY: drive stayed over the limit (%.0f W measured, limit %.0f W). "
                         "Lower the drive, then press OPERATE." % (st["drive_w"], st["limit"]))

    def save_drive_guard(self):
        self.save_setting("drive_guard", {"action": self.dg_action, "limit": self.dg_limit,
                                          "radio_w": self.dg_radio_w})

    def send_pending_freq(self):
        khz = self.want_khz
        if khz is None or khz == self.last_khz:
            return
        if self.a.send_band:
            for lo, hi, bn in BANDS:
                if lo <= khz <= hi and bn != self.last_band:
                    self.amp.set("^BN%02d;" % bn)
                    self.last_band = bn
        self.amp.set("^FR%05d;" % khz)
        self.last_khz = khz
        self.fr_due = time.time() + 0.15      # read it back shortly to confirm the amp followed
        self.log("Frequency %.3f MHz sent to amp" % (khz / 1000.0))

    # ---- FlexControl knob ----------------------------------------------------
    def radio_label(self):
        return RADIO_NAMES.get(self.radio_kind, "Thetis")

    def tci_cat(self, cmd):
        """run one Thetis-style CAT command (e.g. ZZSB): Thetis takes it through TCI (run_cat_ex),
        NereusSDR through its TCP/IP CAT port"""
        cmd = cmd.strip().rstrip(";")
        if self.cat_via == "tcp":
            link = self.cat_link
            return bool(link and link.send(cmd + ";"))
        return self.tci_send("run_cat_ex:%s;" % cmd)

    def start_cat_link(self):
        if self.cat_link or not getattr(self.a, "nereus_cat_port", 0):
            return
        self.cat_link = CatLink(self.a.nereus_cat_host, self.a.nereus_cat_port, self.on_cat_reply, self.log)
        self.cat_link.start()

    def on_cat_reply(self, code, val):
        """an answer from NereusSDR's CAT port (same job as CAT_REPLY_RE for Thetis)"""
        if not val:
            return
        self.cat_replies[code] = (val, time.time())
        if self.cat_via == "tcp":
            self.tci_cat_ok = True
        ev = self.cat_events.get(code)
        if ev:
            ev.set()

    def cat_query(self, code, timeout=0.6):
        """ask Thetis a CAT value (e.g. ZZMA -> '1'); None if no answer"""
        ev = threading.Event()
        self.cat_events[code] = ev
        t0 = time.time()
        if self.cat_via == "tcp":
            timeout = max(timeout, 1.5)
        try:
            if not self.tci_cat(code):
                return None
            ev.wait(timeout)
        finally:
            self.cat_events.pop(code, None)
        v = self.cat_replies.get(code)
        if v and v[1] >= t0:
            return v[0]
        if self.cat_via == "tcp" and self.cat_link and time.time() - self.cat_noans.get(code, 0) > 20:
            self.cat_noans[code] = time.time()
            self.log("NereusSDR gave no answer to %s; - last CAT traffic: %s"
                     % (code, " | ".join(self.cat_link.raw) or "nothing"))
        return None

    def agc_query(self, timeout=0.6):
        ev = threading.Event()
        self.cat_events["agc_gain"] = ev
        t0 = time.time()
        try:
            if not self.tci_send("agc_gain:%d;" % self.a.rx):
                return None
            ev.wait(timeout)
        finally:
            self.cat_events.pop("agc_gain", None)
        v = self.agc_val.get(self.a.rx)
        return v[0] if v and v[1] >= t0 else None

    def check_tci_cat(self):
        # one check at a time (a panel change can start a second one while the first is still waiting)
        with self.cat_check_lock:
            self._check_tci_cat()

    def _check_tci_cat(self):
        """Find out how the knob's CAT commands get to the radio program. Thetis runs them through the
        TCI command run_cat_ex; NereusSDR has no run_cat_ex, so they go to its TCP/IP CAT port."""
        time.sleep(0.5)
        pref = self.radio_pref
        if pref == "auto":
            self.radio_kind = None
            self.cat_via = "tci"
        if pref in ("auto", "thetis"):
            self.cat_via = "tci"
            for _ in range(2):
                v = self.cat_query("ZZVN", 1.5)
                if v is not None:
                    if self.tci_cat_ok is not True:
                        self.log("Thetis runs CAT commands over TCI (version %s) - knob functions available" % v, verbose=True)
                    self.radio_kind = "thetis"
                    self.tci_cat_ok = True
                    return
            if pref == "thetis":
                if self.tci_cat_ok is not False:
                    self.log("Thetis did not answer a CAT command over TCI (run_cat_ex). The knob's CAT functions "
                             "(VFO steps, VOX, mute, AF volume ...) need a newer Thetis.")
                self.tci_cat_ok = False
                return
        # NereusSDR (chosen, or found because Thetis' run_cat_ex did not answer)
        self.cat_via = "tcp"
        self.start_cat_link()
        for i in range(3):
            v = self.cat_query("ZZVN", 1.5)
            if v is not None:
                if self.radio_kind != "nereus":
                    self.log("NereusSDR answers CAT commands on %s:%d (version %s) - knob functions available"
                             % (self.a.nereus_cat_host, self.a.nereus_cat_port, v))
                self.radio_kind = "nereus"
                self.tci_cat_ok = True
                return
            time.sleep(1.0)
        if pref == "auto":
            self.cat_via = "tci"
        if self.tci_cat_ok is not False:
            self.log("No CAT answer: Thetis did not answer run_cat_ex and the NereusSDR CAT port %s:%d did not "
                     "answer either. The knob's CAT functions (VFO steps, VOX, mute, AF volume ...) need one of "
                     "them. NereusSDR: File > Settings > CAT & Network > TCP/IP CAT > Enable TCP CAT."
                     % (self.a.nereus_cat_host, self.a.nereus_cat_port))
        self.tci_cat_ok = False

    def knob_set_mode(self, mode, why=""):
        if mode not in KNOB_MODES:
            return
        if mode != self.knob_mode:
            self.knob_mode = mode
            self.log("Knob: %s%s" % (KNOB_MODES[mode][0], why), verbose=True)
        if self.knob:
            self.knob.send("I%s;" % KNOB_MODES[mode][1])

    def knob_code(self, code):
        """one message from the knob"""
        now = time.time()
        if code == "__connected__":
            self.knob_set_mode(self.knob_mode)
            return
        kind, val = parse_knob_code(code)
        if kind is None:
            return
        self.knob_t = now
        if kind == "turn":
            self.knob_last = (code, "turn %s %d" % ("up" if val > 0 else "down", abs(val)), now)
            self.knob_turn(val)
        else:
            act = self.knob_cfg["table"].get(val, "none")
            self.knob_last = (code, dict(KNOB_EVENTS).get(val, val), now)
            ok, msg = self.knob_action(val, act)
            if act != "none":
                self.log("Knob %s -> %s%s" % (dict(KNOB_EVENTS).get(val, val), "" if ok else "REFUSED: ", msg))

    def knob_turn(self, n):
        if not self.tci_ok:
            return
        name, _led, kind, det = KNOB_MODES[self.knob_mode]
        if kind == "step":
            up, down = det
            steps = abs(n) if abs(n) < 3 else abs(n) * self.knob_cfg["speed"]
            for _ in range(min(steps, 40)):
                self.tci_cat(up if n > 0 else down)
            return
        rd, wr, lo, hi = det
        now = time.time()
        cur = self.knob_vals.get(self.knob_mode)
        if cur is None or now - cur[1] > 3.0:        # not turned lately: read the value now
            v = self.agc_query() if rd.startswith("tci:") else self.cat_query(rd[4:])
            try:
                v = int(str(v).replace("+", "")) if v is not None else None
            except ValueError:
                v = None
            if v is None:
                if cur is None:
                    self.log("Knob: Thetis did not tell the %s - try again" % name)
                    return
                v = cur[0]
            cur = [v, now]
        stepv = self.knob_cfg["af_step"] if self.knob_mode == "af" else 1
        v = max(lo, min(hi, cur[0] + (1 if n > 0 else -1) * min(abs(n), 10) * stepv))
        self.knob_vals[self.knob_mode] = [v, now]
        fmt = wr[4:]
        if wr.startswith("tci:"):
            self.tci_send(fmt % v + ";")
        else:
            self.tci_cat(fmt % v)

    def knob_action(self, event, act):
        """run the function assigned to a knob event (also used by the panel's Try button)"""
        spec = KNOB_ACTION_MAP.get(act)
        if not spec or act == "none":
            return True, "nothing assigned"
        how = spec[3]
        if how.startswith("toggle_mode:"):
            m = how.split(":", 1)[1]
            self.knob_set_mode("vfoa" if self.knob_mode == m else m)
            return True, "knob now: %s" % KNOB_MODES[self.knob_mode][0]
        if how.startswith("mode:"):
            self.knob_set_mode(how.split(":", 1)[1])
            return True, "knob now: %s" % KNOB_MODES[self.knob_mode][0]
        if how == "cycle":
            i = KNOB_CYCLE.index(self.knob_mode) if self.knob_mode in KNOB_CYCLE else -1
            self.knob_set_mode(KNOB_CYCLE[(i + 1) % len(KNOB_CYCLE)])
            return True, "knob now: %s" % KNOB_MODES[self.knob_mode][0]
        if how.startswith("bridge:"):
            return self.do_action(how.split(":", 1)[1])
        if not self.tci_ok:
            return False, "%s is not connected (TCI)" % self.radio_label()
        if how.startswith("cat_toggle:"):
            code = how.split(":", 1)[1]
            cur = self.cat_query(code)
            if cur not in ("0", "1"):
                return False, "Thetis did not answer %s" % code
            new = "0" if cur == "1" else "1"
            if code == "ZZTX" and new == "1":
                na = self.noant_state()
                if na["warn"]:
                    return False, "MOX refused: no antenna? (press DUMMY OK if a dummy load is connected)"
            self.tci_cat(code + new)
            return True, "%s %s" % (spec[1].replace(" on / off", ""), "ON" if new == "1" else "OFF")
        if how.startswith("cat:"):
            self.tci_cat(how.split(":", 1)[1])
            return True, spec[1]
        if how == "custom":
            c = self.knob_cfg["custom"].get(event, "")
            if not c:
                return False, "no custom command typed for this event"
            if c.upper().startswith("ZZ"):
                self.tci_cat(c)
            else:
                self.tci_send(c if c.endswith(";") else c + ";")
            return True, "custom: %s" % c
        return False, "unknown function"

    def knob_short(self, event):
        """what a press does, in a few characters (for the Thetis Knob window)"""
        act = self.knob_cfg["table"].get(event, "none")
        how = KNOB_ACTION_MAP.get(act, ("", "", "", ""))[3]
        if how.startswith("toggle_mode:"):
            m = how.split(":", 1)[1]
            return ">" + KNOB_MODE_SHORT["vfoa" if self.knob_mode == m else m]
        if how.startswith("mode:"):
            return ">" + KNOB_MODE_SHORT.get(how.split(":", 1)[1], "?")
        if how == "cycle":
            i = KNOB_CYCLE.index(self.knob_mode) if self.knob_mode in KNOB_CYCLE else -1
            return ">" + KNOB_MODE_SHORT[KNOB_CYCLE[(i + 1) % len(KNOB_CYCLE)]]
        if act == "custom":
            c = self.knob_cfg["custom"].get(event, "")
            return ("C:" + c.rstrip(";")[:9]) if c else "C:?"
        return KNOB_SHORT.get(act, act)

    def knob_line(self, prefix):
        return "tap %s   2x %s   hold %s" % (self.knob_short(prefix + "_tap"), self.knob_short(prefix + "_double"),
                                             self.knob_short(prefix + "_long"))

    def knob_watchdog(self):
        r = self.knob_cfg["return_s"]
        if r and self.knob_mode != "vfoa" and time.time() - self.knob_t > r:
            self.knob_set_mode("vfoa", " (back after %d s)" % r)

    # ---- radio TUNE started by the bridge (amp STANDBY first) -------------
    def tci_send(self, text):
        ws = self.tci_ws
        if not (ws and self.tci_ok):
            return False
        try:
            with self.tci_send_lock:
                ws.send_text(text)
            return True
        except Exception as e:
            self.log("Could not send to Thetis: %s" % e)
            return False

    def radio_tune_cmd(self, on):
        """key / unkey the radio's own TUNE. Thetis takes the TCI command tune:; NereusSDR does not
        accept that one, so its CAT command ZZTU1; / ZZTU0; is used."""
        if self.radio_kind == "nereus" and self.cat_via == "tcp":
            return self.tci_cat("ZZTU%d" % (1 if on else 0))
        return self.tci_send("tune:%d,%s;" % (self.a.rx, "true" if on else "false"))

    def radio_tune_start(self):
        if not (self.tci_ok and self.tci_ws):
            return False, "Refused: %s is not connected (TCI)" % self.radio_label()
        if self.tune_active:
            return False, "A tune is already running - press again to stop it"
        if self.transmitting():
            return False, "Refused: the radio is already transmitting"
        na = self.noant_state()
        if na["warn"]:
            return False, ("Refused: no antenna? Receive level %.0f dBm on %s m is below %d dBm. "
                           "Press DUMMY OK first if a dummy load is connected." % (na["dbm"], na["band"], na["limit"]))
        prior = None
        if self.standby_on_tune and self.amp_ok:
            self.ingest("^OS;", self.amp.get("^OS;"))
            prior = self.mode
            if prior is None:
                return False, "Refused: could not read the amp mode - nothing keyed"
            if prior == 1 and not self.a.dry_run:
                for _ in range(2):
                    self.amp.set("^OS0;")
                    time.sleep(0.05)
                    self.ingest("^OS;", self.amp.get("^OS;"))
                    if self.mode == 0:
                        break
                if self.mode != 0:
                    return False, "Refused: the amp did not confirm STANDBY - nothing keyed"
                time.sleep(0.1)                  # let the amp's relays settle before RF
        self.saved_mode = prior
        self.tune_active, self.tune_t, self.bridge_tune = True, time.time(), True
        if not self.radio_tune_cmd(True):
            self.tune_active, self.bridge_tune = False, False
            self.saved_mode = None
            if prior == 1:
                self.amp.set("^OS1;")
            return False, "Could not reach %s - tune not started (amp put back as it was)" % self.radio_label()
        msg = "TUNE started from the bridge%s%s" % (
            " - amp in STANDBY first (CONFIRMED)" if prior == 1 else
            (" - amp was already in STANDBY" if prior == 0 else
             (" - Standby-on-Tune is OFF: amp left as it is" if not self.standby_on_tune else "")),
            (", auto-stop after %d s" % self.tune_timeout) if self.tune_timeout else "")
        self.log(msg)
        return True, msg

    def radio_tune_stop(self, why="TUNE stopped from the bridge"):
        if not self.tune_active:
            return False, "No tune is running"
        sent = self.radio_tune_cmd(False)
        self.log(why)

        def fallback():           # Thetis normally answers tune:false; if not, finish anyway
            if self.tune_active and not self.tx:
                self.handle_tune(False)
        threading.Timer(1.5, fallback).start()
        return True, why + ("" if sent else " (Thetis not reachable)")

    def tune_watchdog(self):
        if (self.tune_active and self.bridge_tune and self.tune_timeout
                and time.time() - self.tune_t > self.tune_timeout):
            self.bridge_tune = False
            self.radio_tune_stop("TUNE auto-stopped after %d s" % self.tune_timeout)

    # ---- Standby on Tune -------------------------------------------------
    def handle_tune(self, active):
        if active and not self.tune_active:
            self.tune_active = True
            self.tune_t = time.time()
            self.bridge_tune = False
            self.log("TUNE started in radio")
            if not self.standby_on_tune:
                return
            # always ask the amp right now: a cached reading can be up to ~2 s old
            self.ingest("^OS;", self.amp.get("^OS;"))
            prior = self.mode
            self.amp.set("^OS0;")
            self.saved_mode = prior
            if prior is None:
                self.log("WARNING: could not read amp mode; will NOT auto-restore")
            if not self.a.dry_run:
                self.ingest("^OS;", self.amp.get("^OS;"))
                if self.mode != 0:
                    self.amp.set("^OS0;")      # one retry
                    self.ingest("^OS;", self.amp.get("^OS;"))
                self.log("Amp STANDBY for tune %s (was %s)" % (
                    "CONFIRMED" if self.mode == 0 else "NOT CONFIRMED!",
                    {1: "OPERATE", 0: "STANDBY", None: "unknown"}[prior]))
        elif not active and self.tune_active:
            self.tune_active = False
            self.bridge_tune = False
            self.log("TUNE ended in radio")
            saved, self.saved_mode = self.saved_mode, None
            if saved == 1 and self.noant_state()["hold"]:
                self.noant_held = True
                self.log("Amp left in STANDBY after tune: no antenna? (press DUMMY OK if a dummy "
                         "load is connected)")
            elif saved == 1:
                self.amp.set("^OS1;")
                if not self.a.dry_run:
                    self.ingest("^OS;", self.amp.get("^OS;"))
                    self.log("Amp restored to OPERATE %s" % (
                        "CONFIRMED" if self.mode == 1 else "NOT CONFIRMED!"))
            elif saved == 0:
                self.log("Amp was not in OPERATE before tune - leaving as is")

    # ---- amp polling -----------------------------------------------------
    POLL_SEQ = ["^WS;", "^OS;", "^WS;", "^PWI;", "^WS;", "^PWR;", "^WS;",
                "^TM;", "^WS;", "^FL;", "^WS;", "^VI;", "^WS;", "^AM;",
                "^WS;", "^AN;", "^WS;", "^TP;", "^WS;", "^FS;", "^WS;", "^FC;",
                "^WS;", "^CR;", "^WS;", "^LR;", "^WS;", "^SI;"]

    def poll_loop(self):
        i = 0
        while not self.stop.is_set():
            self.send_pending_freq()
            cmd = self.POLL_SEQ[i % len(self.POLL_SEQ)]
            i += 1
            self.ingest(cmd, self.amp.get(cmd))
            if self.amp_ok and (i % 20 == 0 or (self.fr_due and time.time() >= self.fr_due)):
                self.read_amp_freq()
            if i % 3 == 0:
                self.noant_enforce()
            self.tune_watchdog()
            if i % 10 == 0:
                self.knob_watchdog()
            if not self.amp_ok and not self._hinted and time.time() - self._t0 > 8:
                self._hinted = True
                self.log("No answer from the amplifier at %s. Press D to search the network, "
                         "or start with --amp-ip auto." % self.amp.addr[0])
            if self.amp_ok and i % 60 == 5 and (self.mac is None or self.wol is None):
                self.ingest("^MA;", self.amp.get("^MA;"))
                self.ingest("^WL;", self.amp.get("^WL;"))
            self.stop.wait(self.a.poll)

    def read_amp_freq(self):
        """Ask the amp which frequency it is set to. Never counts as the amp being
        offline: an amp that does not answer ^FR; just shows the frequency sent."""
        self.fr_due = 0.0
        if self.fr_miss >= 3:
            return
        r = self.amp.get("^FR;")
        m = re.match(r"\^FR\s*(\d+);", r or "", re.I)
        if m:
            self.amp_khz, self.fr_miss = int(m.group(1)), 0
        else:
            self.fr_miss += 1
            if self.fr_miss == 3:
                self.log("The amp does not report its frequency (^FR;): showing the frequency sent to it")

    def follow_state(self):
        """(amp kHz or None, text): does the amp follow the radio?"""
        if not self.amp_ok:
            return None, "--"
        want = self.want_khz
        if self.amp_khz is None:
            return None, "(sent)" if want else "--"
        if not want or abs(self.amp_khz - want) <= 1:
            return self.amp_khz, "= radio" if want else ""
        return self.amp_khz, "radio %.3f !" % (want / 1000.0)

    def ingest(self, cmd, r):
        if r is None:
            self.miss += 1
            if self.miss >= 5 and self.amp_ok:
                self.amp_ok = False
                # forget the last readings so nothing stale is shown as if live
                self.mode, self.tune_active = None, False
                self.fwd = self.refl = self.pin = 0
                self.swr = 1.0
                self.temp = self.volts = self.amps = self.fault = None
                self.atu = self.ant = self.atu_tuning = None
                self.atu_c = self.atu_l = self.atu_side = None
                self.fan_speed = self.fan_min = None
                self.amp_khz, self.fr_miss = None, 0
                self.log("Amp not responding at %s:%d - it is switched OFF, asleep, "
                         "unplugged or unreachable" % self.amp.addr)
            return
        if not self.amp_ok:
            self.log("Amp responding at %s:%d" % self.amp.addr)
        self.miss, self.amp_ok, self.ever_ok = 0, True, True
        if self.settings.get("amp_seen_ip") != self.amp.addr[0]:
            self.save_setting("amp_seen_ip", self.amp.addr[0])
        self.log("<- amp: %s" % r, verbose=True)
        m = None
        if cmd == "^WS;":
            m = re.match(r"\^WS\s*(\d+)\s+(\d+);", r, re.I)
            if m:
                self.fwd, self.swr = int(m.group(1)), int(m.group(2)) / 10.0
                if self.fwd == 0:
                    # the amp keeps showing the last SWR after RF stops; with no
                    # forward power there is no SWR to report, so show 1.0
                    self.swr = 1.0
        elif cmd == "^OS;":
            m = re.match(r"\^OS([01]);", r, re.I)
            if m:
                self.mode, self.mode_time = int(m.group(1)), time.time()
        elif cmd == "^PWI;":
            m = re.match(r"\^PWI\s*(\d+);", r, re.I)
            if m:
                self.pin = int(m.group(1))
        elif cmd == "^PWR;":
            m = re.match(r"\^PWR\s*(\d+);", r, re.I)
            if m:
                self.refl = int(m.group(1))
        elif cmd == "^TM;":
            m = re.match(r"\^TM\s*(\d+);", r, re.I)
            if m:
                self.temp = int(m.group(1))
        elif cmd == "^VI;":
            m = re.match(r"\^VI\s*(\d+)\s+(\d+);", r, re.I)
            if m:
                self.volts, self.amps = int(m.group(1)) / 10.0, int(m.group(2))
        elif cmd == "^AM;":
            m = re.match(r"\^AM([IB]);", r, re.I)
            if m:
                self.atu = m.group(1).upper()
        elif cmd == "^AN;":
            m = re.match(r"\^AN(\d+);", r, re.I)
            if m:
                self.ant = int(m.group(1))
        elif cmd == "^FS;":
            m = re.match(r"\^FS(\d);", r, re.I)
            if m:
                self.fan_speed = int(m.group(1))
        elif cmd == "^FC;":
            m = re.match(r"\^FC(\d);", r, re.I)
            if m:
                self.fan_min = int(m.group(1))
        elif cmd == "^TP;":
            m = re.match(r"\^TP([01]);", r, re.I)
            if m:
                self.atu_tuning = m.group(1) == "1"
        elif cmd == "^CR;":
            m = re.match(r"\^CR([0-9A-Fa-f]{2});", r, re.I)
            if m:
                self.atu_c = int(m.group(1), 16)
        elif cmd == "^LR;":
            m = re.match(r"\^LR([0-9A-Fa-f]{2});", r, re.I)
            if m:
                self.atu_l = int(m.group(1), 16)
        elif cmd == "^SI;":
            m = re.match(r"\^SI([TA]);", r, re.I)
            if m:
                self.atu_side = m.group(1).upper()
        elif cmd == "^MA;":
            m = re.match(r"\^MA\s*([0-9A-Fa-f:]{17});", r, re.I)
            if m:
                mac = norm_mac(m.group(1))
                if mac and mac != self.mac:
                    self.mac = mac
                    self.log("Amp MAC address learned: %s (needed for remote power-on)" % mac)
                    if self.a.mac_file:
                        try:
                            with open(self.a.mac_file, "w") as fh:
                                fh.write(mac + "\n")
                        except OSError:
                            pass
        elif cmd == "^WL;":
            m = re.match(r"\^WL([01]);", r, re.I)
            if m:
                new = m.group(1) == "1"
                if self.wol is None and not new:
                    self.log("NOTE: amp menu NET WAKE on LAN is OFF - remote "
                             "power-on needs it ON (button: Enable Wake-on-LAN)")
                self.wol = new
        elif cmd == "^FL;":
            m = re.match(r"\^FL\s*([0-9A-Fa-f]{2});", r, re.I)
            if m:
                code = int(m.group(1), 16)
                if code != self.fault and code != 0:
                    self.log("AMP FAULT %02X: %s" % (code, FAULTS.get(code, "unknown")))
                self.fault = code

    # ---- control actions (used by the web buttons) -----------------------
    def drive_info(self):
        """Exciter drive (W) and where it came from. The KPA1500 reports input
        power as 0 whenever its PA is bypassed (STANDBY or ATU tuning), so the
        radio's own measurement (TCI tx_sensors) is used in that case."""
        if self.mode == 1 and self.pin > 0:
            return float(self.pin), "amp"
        if self.radio_fwd > 0 and time.time() - self.radio_t < 1.5:
            return self.radio_fwd, "radio"
        return 0.0, "none"

    def transmitting(self):
        lp = self.lp.snapshot() if self.lp else None
        return bool(self.tx or self.fwd > 5 or (lp and lp["pwr"] > 5))

    def _confirm(self, getcmd, text):
        if self.a.dry_run:
            return True, "DRY-RUN: would send " + text
        time.sleep(0.08)
        self.ingest(getcmd, self.amp.get(getcmd))
        return True, text + " - sent"

    def do_action(self, name, params=None):
        a = self.amp
        if name == "toggle_operate":
            name = "standby" if self.mode == 1 else "operate"
        elif name == "toggle_atu":
            name = "atu_bypass" if self.atu == "I" else "atu_inline"
        elif name == "toggle_ant":
            name = "ant2" if self.ant == 1 else "ant1"
        elif name == "toggle_sot":
            name = "sot_off" if self.standby_on_tune else "sot_on"
        simple = {
            "operate": ("^OS1;", "^OS;"), "standby": ("^OS0;", "^OS;"),
            "atu_inline": ("^AMI;", "^AM;"), "atu_bypass": ("^AMB;", "^AM;"),
            "ant1": ("^AN1;", "^AN;"), "ant2": ("^AN2;", "^AN;"),
            "ant_next": ("^AN0;", "^AN;"), "clear_fault": ("^FLC;", "^FL;"),
        }
        needs_idle = {"atu_inline", "atu_bypass", "ant1", "ant2", "ant_next",
                      "power_off"}
        if name == "power_off" and not self.block_off_tx:
            needs_idle = needs_idle - {"power_off"}      # emergency shutdown allowed under RF
        if name in needs_idle and self.transmitting():
            msg = "Refused: transmitting - %s not allowed under RF" % name
            if name == "power_off":
                msg += " (option 'Block power off while transmitting' is on)"
            self.log(msg)
            return False, msg
        if name == "operate" and self.noant_enabled and self.noant_action == "standby":
            st = self.noant_state()
            if st["hold"]:
                return False, ("Refused: no antenna? Receive level %.0f dBm on %s m is below %d dBm. "
                               "Press DUMMY OK if a dummy load is connected." % (st["dbm"], st["band"], st["limit"]))
        if (name == "operate" and self.tune_active and self.standby_on_tune
                and self.saved_mode is not None):
            return False, ("Refused: TUNE in progress - the amp returns to its "
                           "prior mode automatically when TUNE ends")
        if name in simple:
            setc, getc = simple[name]
            self.log("Button: %s -> %s" % (name, setc))
            a.set(setc)
            ok, msg = self._confirm(getc, setc)
        elif name == "atu_tune":
            self.log("Button: ATU full-search tune (^FT;)")
            a.set("^FT;")
            ok, msg = True, ("ATU tune started on the amp. Press TUNE in the "
                             "radio at LOW power to supply the carrier.")
        elif name == "atu_cancel":
            a.set("^FE;")
            ok, msg = True, "Cancel-tune (^FE;) sent"
        elif name == "power_on":
            if self.a.dry_run:
                ok, msg = True, "DRY-RUN: would send Wake-on-LAN packet + ^ON1;"
                self.log(msg)
            elif self.power_thread and self.power_thread.is_alive():
                ok, msg = True, "Power-on already in progress"
            else:
                self.power_thread = threading.Thread(target=self.power_on_sequence,
                                                     daemon=True)
                self.power_thread.start()
                ok, msg = True, ("Power-on started: Wake-on-LAN packet + ^ON1; "
                                 "(takes up to ~15 s)")
        elif name == "enable_wol":
            a.set("^WL1;")
            ok, msg = self._confirm("^WL;", "^WL1; (Wake-on-LAN enable)")
        elif name == "power_off":
            under_rf = self.transmitting()
            a.set("^ON0;")
            ok, msg = True, "Power-off (^ON0;) sent"
            if under_rf:
                msg = "EMERGENCY power-off under RF (^ON0;) sent"
            self.log(msg)
        elif name == "amp_find":
            if self.finding:
                return False, "A search is already running"
            self.finding = True
            try:
                found, searched = self.find_amps()
            except ValueError as e:
                return False, "Search not possible: %s" % e
            finally:
                self.finding = False
            if found:
                ok, msg = True, "Found %d KPA1500: %s" % (
                    len(found), "; ".join(describe_amp(f) for f in found))
            else:
                ok, msg = False, ("No KPA1500 answered (searched %s). Check it is switched on "
                                  "and on this network." % searched)
            self.log(msg)
        elif name == "amp_ip":
            params = params if isinstance(params, dict) else {}
            ip = str(params.get("ip", "")).strip()
            try:
                addr = ipaddress.ip_address(ip)
                good = (addr.version == 4 and addr.is_private and not addr.is_multicast
                        and not addr.is_unspecified)
            except ValueError:
                good = False
            if not good:
                return False, "Not a usable local network address (use something like 192.168.0.175)"
            if self.transmitting() or self.tune_active:
                return False, "Refused: transmitting - the amplifier address cannot change under RF"
            self.set_amp_ip(ip)
            ok, msg = True, "Now talking to the amplifier at %s" % ip
            if self.amp_ip_source == "flag":
                msg += " (saved, but --amp-ip on the command line overrides it at the next start)"
        elif name in ("fan_min", "fan_up", "fan_down"):
            if name == "fan_min":
                params = params if isinstance(params, dict) else {}
                try:
                    target = int(params.get("speed"))
                except (TypeError, ValueError):
                    return False, "Fan speed must be a number from 0 to 5"
                if not 0 <= target <= 5:
                    return False, "Fan speed must be from 0 to 5"
            else:
                if not self.a.dry_run or self.fan_min is None:
                    self.ingest("^FC;", a.get("^FC;"))
                if self.fan_min is None:
                    return False, "Fan setting not read from the amplifier yet"
                target = max(0, min(5, self.fan_min + (1 if name == "fan_up" else -1)))
                if target == self.fan_min:
                    msg = "Fan minimum speed is already %d (%s)" % (
                        target, "highest" if target == 5 else "lowest")
                    self.last_msg = msg
                    return True, msg
            self.log("Fan minimum speed -> %d" % target)
            a.set("^FC%d;" % target)
            ok, msg = self._confirm("^FC;", "^FC%d; (fan minimum speed %d)" % (target, target))
        elif name in ("log_on", "log_off"):
            if name == "log_on":
                if not self.a.logfile:
                    return False, "No log file name is set (start the bridge with --logfile name)"
                self.log_enabled = True
                self.log("Log file turned ON")
                ok, msg = True, "Log file ON (limit %.1f MB)" % self.log_max_mb
            else:
                self.log("Log file turned OFF")
                with self._log_lock:
                    self.log_enabled = False
                    self._close_log()
                ok, msg = True, "Log file OFF - nothing more is written to disk"
            self.save_setting("log_enabled", self.log_enabled)
        elif name == "log_limit":
            params = params if isinstance(params, dict) else {}
            try:
                mb = float(params.get("mb"))
            except (TypeError, ValueError):
                return False, "Bad size"
            if mb not in (1.0, 2.0, 5.0, 10.0):
                return False, "Log limit must be 1, 2, 5 or 10 MB"
            self.log_max_mb = mb
            self.save_setting("log_max_mb", mb)
            ok, msg = True, "Log file limit: %g MB" % mb
        elif name in ("thetis_off_on", "thetis_off_off"):
            self.allow_thetis_off = (name == "thetis_off_on")
            self.save_setting("allow_thetis_power_off", self.allow_thetis_off)
            ok, msg = True, "Allow Thetis to power off the amp: %s" % (
                "YES" if self.allow_thetis_off else "NO")
            self.log(msg)
        elif name in ("block_off_tx_on", "block_off_tx_off"):
            self.block_off_tx = (name == "block_off_tx_on")
            self.save_setting("block_power_off_in_tx", self.block_off_tx)
            ok, msg = True, "Block power off while transmitting: %s" % (
                "ON" if self.block_off_tx else "OFF - power off works even under RF")
            self.log(msg)
        elif name in ("confirm_off_on", "confirm_off_off"):
            self.confirm_power_off = (name == "confirm_off_on")
            self.save_setting("confirm_power_off", self.confirm_power_off)
            ok, msg = True, "Ask before Power OFF: %s" % (
                "ON" if self.confirm_power_off else "OFF")
            self.log(msg)
        elif name in ("sot_on", "sot_off"):
            self.standby_on_tune = (name == "sot_on")
            ok, msg = True, "Standby-on-Tune %s" % (
                "ON" if self.standby_on_tune else "OFF")
            self.log(msg)
        elif name == "lp_port":
            params = params if isinstance(params, dict) else {}
            port = str(params.get("port", "")).strip()
            try:
                baud = int(params.get("baud", 115200))
            except (TypeError, ValueError):
                return False, "Bad baud rate"
            if port and not PORT_RE.fullmatch(port):
                return False, "Port name not allowed (use a name like COM5)"
            if baud not in VALID_BAUDS:
                return False, "Baud must be one of %s" % ", ".join(map(str, VALID_BAUDS))
            if not self.lp:
                return False, "LP-100A support is not running"
            self.lp.set_port(port, baud)
            self.save_setting("lp100_port", port)
            self.save_setting("lp100_baud", baud)
            ok = True
            msg = ("LP-100A connecting on %s @ %d baud" % (port, baud)) if port \
                else "LP-100A disconnected"
            self.log(msg)
        elif name == "radio_tune_toggle":
            ok, msg = self.radio_tune_stop() if self.tune_active else self.radio_tune_start()
        elif name == "radio_tune":
            ok, msg = self.radio_tune_start()
        elif name == "radio_tune_stop":
            ok, msg = self.radio_tune_stop()
        elif name in ("thetis_buttons", "thetis_buttons_default"):
            params = params if isinstance(params, dict) else {}
            if name == "thetis_buttons_default":
                tb = {"order": list(TB_DEFAULT), "columns": 4, "tv": 1, "title": self.thetis_buttons["title"]}
            else:
                params = dict(params)
                params.setdefault("order", self.thetis_buttons["order"])
                params.setdefault("columns", self.thetis_buttons["columns"])
                params.setdefault("title", self.thetis_buttons["title"])
                params["tv"] = 1
                if not isinstance(params.get("order"), list) or not [
                        x for x in params["order"] if x in TB_IDS and x not in ("gap", "title")]:
                    return False, "The button list needs at least one button"
                tb = clean_thetis_buttons(params)
            self.thetis_buttons = tb
            self.save_setting("thetis_buttons", tb)
            ok, msg = True, ("Thetis Controls buttons saved (%d buttons, %d columns). Press 'Rebuild Thetis "
                             "windows' (or run Setup_Thetis_Containers.bat) to put them into Thetis."
                             % (len([x for x in tb["order"] if x != "gap"]), tb["columns"]))
        elif name in ("thetis_meters", "thetis_meters_default"):
            params = params if isinstance(params, dict) else {}
            if name == "thetis_meters_default":
                tm = {"order": list(TM_DEFAULT), "title": self.thetis_meters["title"]}
            else:
                params = dict(params)
                params.setdefault("order", self.thetis_meters["order"])
                params.setdefault("title", self.thetis_meters["title"])
                if not isinstance(params.get("order"), list) or not [
                        x for x in params["order"] if x in TM_IDS and x != "gap"]:
                    return False, "The Telemetry window needs at least one line or bar"
                tm = clean_thetis_meters(params)
            self.thetis_meters = tm
            self.save_setting("thetis_meters", tm)
            ok, msg = True, ("Thetis Telemetry window saved (%d items, title '%s'). Press 'Rebuild Thetis "
                             "windows' to put it into Thetis." % (len([x for x in tm["order"] if x != "gap"]), tm["title"]))
        elif name in ("thetis_knobwin", "thetis_knobwin_default"):
            params = params if isinstance(params, dict) else {}
            cur = self.thetis_knobwin
            if name == "thetis_knobwin_default":
                kw = {"enabled": cur["enabled"], "order": list(KW_DEFAULT), "title": cur["title"]}
            else:
                merged = dict(cur)
                merged.update({k: v for k, v in params.items() if k in ("enabled", "order", "title")})
                if "order" in params and (not isinstance(params["order"], list) or not [
                        x for x in params["order"] if x in KW_IDS and x != "gap"]):
                    return False, "The Knob window needs at least one line"
                kw = clean_knob_window(merged)
            self.thetis_knobwin = kw
            self.save_setting("thetis_knobwin", kw)
            ok, msg = True, ("Thetis Knob window %s. Press 'Rebuild Thetis windows' to put it into Thetis."
                             % ("saved" if kw["enabled"] else "switched OFF (it is taken out at the next rebuild)"))
        elif name == "thetis_rebuild":
            here = os.path.dirname(os.path.abspath(__file__))
            bat = os.path.join(here, "Setup_Thetis_Containers.bat")
            if os.name != "nt":
                return False, ("Only on Windows: run  python3 kpa1500_thetis_setup.py  on the Thetis "
                               "computer (Thetis closed)")
            if not os.path.exists(bat):
                return False, "Setup_Thetis_Containers.bat is not in %s - run the installer again" % here
            if self.a.dry_run:
                ok, msg = True, "DRY-RUN: would open the Thetis setup window"
            else:
                cmd = setup_launch_cmd(bat, self.a.settings_file)
                self.log("Opening the Thetis setup: %s" % cmd, verbose=True)
                subprocess.Popen(cmd, cwd=here,
                                 creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
                ok, msg = True, ("The Thetis setup window is open on the bridge computer. Answer its "
                                 "questions there: it offers to close Thetis for you (the normal way, Thetis "
                                 "saves its settings), makes a backup, rebuilds the windows and offers to "
                                 "start Thetis again.")
            self.log(msg)
        elif name == "web_password":
            params = params if isinstance(params, dict) else {}
            tok = str(params.get("token", "")).strip()
            if tok and not re.fullmatch(r"[A-Za-z0-9_-]{4,32}", tok):
                return False, "Password: 4 to 32 letters, digits, - or _ (no spaces)"
            self.a.web_token = tok
            self.save_setting("web_token", tok)
            if tok:
                ok, msg = True, ("Panel password set. Other computers and phones open the panel with "
                                 "http://THIS-PC:%d/?t=%s" % (self.a.web_port, tok))
            else:
                ok, msg = True, "Panel password removed - anyone on your network who can reach the panel can use it"
            if self.a.web_bind in ("127.0.0.1", "localhost"):
                msg += " (the panel is only open on this computer right now, so it is not needed)"
            self.log(msg)
        elif name == "tune_timeout":
            params = params if isinstance(params, dict) else {}
            try:
                v = int(params.get("s"))
            except (TypeError, ValueError):
                return False, "Auto-stop time must be a number of seconds (0 = never)"
            if not 0 <= v <= 600:
                return False, "Auto-stop time must be 0 to 600 seconds"
            self.tune_timeout = v
            self.save_setting("tune_timeout", v)
            ok, msg = True, "Bridge TUNE auto-stop: %s" % ("never" if v == 0 else "%d s" % v)
            self.log(msg)
        elif name in ("knob_set", "knob_defaults"):
            params = params if isinstance(params, dict) else {}
            old = self.knob_cfg
            if name == "knob_defaults":
                new = clean_knob({"port": old["port"]})
            else:
                merged = {k: v for k, v in old.items()}
                for k in ("port", "speed", "af_step", "return_s"):
                    if k in params:
                        merged[k] = params[k]
                for k in ("table", "custom"):
                    if isinstance(params.get(k), dict):
                        d = dict(old[k])
                        d.update(params[k])
                        if k == "custom":
                            d = {e: c for e, c in d.items() if c}
                        merged[k] = d
                if "port" in params and not (params["port"] in ("", "auto") or PORT_RE.fullmatch(str(params["port"]))):
                    return False, "Port must be auto, empty (off) or a name like COM7"
                new = clean_knob(merged)
                if "custom" in params:
                    for e, c in params["custom"].items():
                        if c and new["custom"].get(e) != str(c).strip():
                            return False, ("Custom command not allowed: %r (use a Thetis CAT command like ZZMA1; "
                                           "or a TCI command like mute:true;)" % c)
            self.knob_cfg = new
            self.save_setting("knob", new)
            if self.knob and new["port"] != old["port"]:
                self.knob.set_port(new["port"])
            ok, msg = True, "FlexControl knob settings saved" + (
                "" if name == "knob_set" else " (functions back to the defaults)")
        elif name == "knob_try":
            params = params if isinstance(params, dict) else {}
            ev = params.get("event")
            if ev not in KNOB_EVENT_IDS:
                return False, "Unknown knob event"
            ok, msg = self.knob_action(ev, self.knob_cfg["table"][ev])
            msg = "Try %s: %s" % (dict(KNOB_EVENTS)[ev], msg)
        elif name == "dummy_ok":
            st = self.noant_state()
            band = st["band"]
            if not band:
                return False, "DUMMY OK: no band known yet (is Thetis running?)"
            with self.noant_lock:
                if band in self.dummy_ok:
                    self.dummy_ok.discard(band)
                    ok, msg = True, "DUMMY OK cleared on %s m" % band
                elif st["state"] in ("low", "tx"):
                    self.dummy_ok.add(band)
                    ok, msg = True, ("DUMMY OK on %s m: warning silenced until a normal receive "
                                     "level returns (antenna reconnected)" % band)
                else:
                    return False, "No 'no antenna?' warning on %s m now - DUMMY OK is not needed" % band
            self.log(msg)
        elif name == "drive_guard":
            params = params if isinstance(params, dict) else {}
            if "action" in params:
                if params["action"] not in DG_ACTIONS:
                    return False, "Action must be ignore, warn or limit"
                self.dg_action = params["action"]
            if "limit" in params:
                raw = str(params["limit"]).strip().lower()
                if raw in ("", "off", "0"):
                    self.dg_limit = 0.0
                else:
                    v = clean_dg_num(raw, None, 0.0, 1e9)
                    if v is None or not 1 <= v <= 1500:
                        return False, "The drive limit must be a number of watts from 1 to 1500 (or off)"
                    self.dg_limit = v
            if "radio_w" in params:
                v = clean_dg_num(params["radio_w"], None, 0.0, 1e9)
                if v is None or not 1 <= v <= 1500:
                    return False, "The radio's full power must be a number of watts from 1 to 1500"
                self.dg_radio_w = v
            self.dg_logged = ""
            self.save_drive_guard()
            lim = "off" if self.dg_limit <= 0 else "%g W" % self.dg_limit
            ok, msg = True, "Over-drive protection: %s, limit %s (radio full power %g W)" % (
                {"ignore": "ignore", "warn": "warn", "limit": "hold at the limit"}[self.dg_action], lim, self.dg_radio_w)
            if self.dg_action != "ignore" and self.dg_limit <= 0:
                msg += " - enter a limit in watts to switch it on"
            self.log(msg)
        elif name in ("noant_on", "noant_off"):
            self.noant_enabled = (name == "noant_on")
            self.save_noant()
            ok, msg = True, "No-antenna check %s" % ("ON" if self.noant_enabled else "OFF")
            self.log(msg)
        elif name == "noant_action":
            params = params if isinstance(params, dict) else {}
            act_ = params.get("action")
            if act_ not in ("warn", "standby"):
                return False, "Action must be warn or standby"
            self.noant_action = act_
            self.save_noant()
            ok, msg = True, ("No-antenna check: %s" % ("warn only" if act_ == "warn" else
                             "warn AND keep the amp in STANDBY until DUMMY OK or a normal level"))
            self.log(msg)
        elif name in ("noant_limit", "noant_learn"):
            params = params if isinstance(params, dict) else {}
            band = str(params.get("band") or self.rx_band or "")
            if band not in NOANT_DEFAULTS:
                return False, "Unknown band %r (use 160, 80, 60, 40, 30, 20, 17, 15, 12, 10 or 6)" % band
            if name == "noant_learn":
                st = self.noant_state()
                if band != st["band"] or st["dbm"] is None:
                    return False, ("Learn needs a live receive level on %s m: tune the radio to that "
                                   "band with the antenna disconnected, wait 3 s, try again" % band)
                if st["tx"]:
                    return False, "Learn: not while transmitting"
                val = int(round(st["dbm"])) + NOANT_LEARN_MARGIN
                note = " (measured %.0f dBm + %d dB)" % (st["dbm"], NOANT_LEARN_MARGIN)
            else:
                v = params.get("dbm")
                if v in (None, "", "off", "OFF", "-"):
                    val, note = None, ""
                else:
                    try:
                        val = int(round(float(v)))
                    except (TypeError, ValueError):
                        return False, "Limit must be a number of dBm, e.g. -105, or 'off'"
                    if not -150 <= val <= -30:
                        return False, "Limit must be between -150 and -30 dBm"
                    note = ""
            with self.noant_lock:
                self.noant_limits[band] = None if val is None else max(-150, min(-30, val))
                self.noant_low = False
            self.save_noant()
            lim = self.noant_limits[band]
            ok, msg = True, "No-antenna limit %s m: %s%s" % (band, "OFF" if lim is None else "%d dBm" % lim, note)
            self.log(msg)
        elif name == "noant_defaults":
            with self.noant_lock:
                self.noant_limits = dict(NOANT_DEFAULTS)
                self.noant_low = False
            self.save_noant()
            ok, msg = True, "No-antenna limits back to the defaults"
            self.log(msg)
        elif name in ("lp_alarm", "lp_mode"):
            if not (self.lp and self.lp.port):
                return False, "LP-100A not configured (choose a port under Settings)"
            self.lp.send(b"A" if name == "lp_alarm" else b"F")
            ok, msg = True, "LP-100A %s command sent" % (
                "alarm-cycle" if name == "lp_alarm" else "mode-cycle")
        elif name == "radio_set":
            params = params if isinstance(params, dict) else {}
            r = str(params.get("radio", "")).lower()
            if r not in RADIO_KINDS:
                return False, "Radio program: auto, thetis or nereus"
            self.radio_pref = r
            self.save_setting("radio", r)
            self.radio_kind = {"thetis": "thetis", "nereus": "nereus"}.get(r)
            self.cat_via = "tcp" if r == "nereus" else "tci"
            if r == "nereus":
                self.start_cat_link()
            self.tci_cat_ok = None
            threading.Thread(target=self.check_tci_cat, daemon=True).start()
            ok, msg = True, "Radio program: %s" % ("find it automatically" if r == "auto" else RADIO_NAMES[r])
            self.log(msg)
        elif name == "applet_skin":
            params = params if isinstance(params, dict) else {}
            self.applet_skin = clean_applet_skin(params.get("skin") if "skin" in params else params)
            self.save_setting("applet_skin", self.applet_skin)
            ok, msg = True, "Applet look saved"
        elif name == "applet_window":
            sk = self.applet_skin
            ok, msg = open_applet_window(self.applet_url(), sk["width"], sk["height"], self.log)
        elif name == "quit_bridge":
            self.log("Quit requested (panel or a newer copy of the bridge)")
            threading.Timer(0.5, lambda: setattr(self, "quit", True)).start()
            ok, msg = True, "The bridge is closing"
        else:
            return False, "Unknown action"
        self.last_msg = msg
        if not ok and str(name).startswith("radio_tune"):
            self.log("TUNE button refused: %s" % msg)
        return ok, msg

    def applet_url(self):
        host = self.a.web_bind
        if host in ("0.0.0.0", "", "localhost"):
            host = "127.0.0.1"
        port = self.web.server_address[1] if self.web else self.a.web_port
        return "http://%s:%d/applet" % (host, port)

    def resolve_mac(self):
        if not self.mac:
            self.mac = arp_lookup(self.amp.addr[0])
            if self.mac:
                self.log("Amp MAC found in ARP table: %s" % self.mac)
        return self.mac

    def send_wol(self, mac):
        pkt = build_magic(mac)
        amp_ip = self.amp.addr[0]
        a = amp_ip.split(".")
        targets = {"255.255.255.255", amp_ip}
        if len(a) == 4:
            targets.add(".".join(a[:3] + ["255"]))
        for extra in re.split(r"[\s,;]+", getattr(self.a, "wol_broadcast", "") or ""):
            if extra:
                targets.add(extra)
        sent = 0
        for src in local_ipv4s(self.amp.addr[0]):
            for dst in sorted(targets):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.bind((src, 0))
                    s.sendto(pkt, (dst, self.a.wol_port))
                    s.close()
                    sent += 1
                except OSError:
                    pass
        # also one send from whichever interface Windows/Linux picks by default
        for dst in sorted(targets):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(pkt, (dst, self.a.wol_port))
                s.close()
                sent += 1
            except OSError:
                pass
        return sent

    def power_on_sequence(self):
        mac = self.resolve_mac()
        if mac:
            n = self.send_wol(mac)
            self.log("Wake-on-LAN magic packet sent for %s (%d sends)" % (mac, n))
        else:
            self.log("No amp MAC known - skipping Wake-on-LAN. Give it with "
                     "--amp-mac 54:10:EC:xx:xx:xx (amp menu NET MAC, or the "
                     "Elecraft utility's Network tab)")
        for attempt in range(15):
            self.amp.set(";")
            self.amp.set(";")
            self.amp.set("^ON1;")
            time.sleep(1.0)
            r = self.amp.get("^ON;")
            if r and re.match(r"\^ON1;", r, re.I):
                self.last_msg = "Amplifier powered on"
                self.log("Power-on CONFIRMED (^ON1;)")
                return
            if mac and attempt in (4, 9):
                self.send_wol(mac)
        self.last_msg = "Power-on: no confirmation after 15 s"
        self.log("Power-on NOT confirmed. Check amp menu NET WAKE on LAN = ON, "
                 "the MAC address, and that the PC and amp are on the same LAN.")

    def open_help(self):
        import webbrowser
        try:
            if self.web and not self.a.no_web:
                host = self.a.web_bind
                if host in ("0.0.0.0", "", "localhost"):
                    host = "127.0.0.1"
                url = "http://%s:%d/help" % (host, self.web.server_address[1])
            else:
                import pathlib
                url = pathlib.Path(write_help_file()).as_uri()
            self.log("Opening the help in your browser: %s" % url)
            webbrowser.open(url)
        except Exception as e:
            self.log("Could not open the help (%s). Run with --write-help to make a file." % e)

    def set_amp_ip(self, ip, save=True):
        self.amp.set_addr(ip)
        self.amp_ok, self.miss = False, 0
        self.ever_ok = self.settings.get("amp_seen_ip") == ip
        self.presence, self.presence_match = None, False
        self.mac, self.wol, self.last_khz = None, None, None
        self.mode = self.fan_min = self.fan_speed = None
        self.log("Now talking to the amplifier at %s:%d" % self.amp.addr)
        if save:
            self.save_setting("amp_ip", ip)

    def find_amps(self):
        """Search the network. Returns (found list, text describing what was searched)."""
        nets = discovery_networks(self.a.discover_net, self.amp.addr[0])
        n_addr = sum(max(0, n.num_addresses - 2) for n in nets)
        found = discover_amps(nets, self.amp.addr[1])
        self.found_amps = found
        return found, "%d addresses on %s" % (n_addr, ", ".join(str(n) for n in nets))

    def startup_discovery(self):
        """--amp-ip auto: use the known address if it answers, otherwise search."""
        ip, port = self.amp.addr
        if _probe(ip, port, "^I;", "^KPA1500;", 1.0) is not None or \
                _probe(ip, port, "^I;", "^kpa1500;", 0.2) is not None:
            self.log("KPA1500 answered at %s - no search needed" % ip)
            return True
        self.log("Searching the network for the KPA1500 ...")
        try:
            found, searched = self.find_amps()
        except ValueError as e:
            self.log("Search failed: %s" % e)
            return False
        if not found:
            self.log("No KPA1500 answered (%s). Check it is on and on this network, "
                     "then press D in this window to search again." % searched)
            return False
        if len(found) > 1:
            self.log("Several KPA1500 amplifiers answered: %s - using the first. "
                     "Press D to choose another." % "; ".join(describe_amp(f) for f in found))
        self.set_amp_ip(found[0]["ip"])
        self.log("Found the KPA1500 at %s" % describe_amp(found[0]))
        return True

    def save_setting(self, key, value):
        self.settings[key] = value
        if not self.a.settings_file:
            return
        try:
            with open(self.a.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=1)
        except OSError as e:
            self.log("Could not save settings file: %s" % e)

    def power_text(self):
        """ON = answering; OFF = it was answering and has stopped (switched off or lost
        power); NO LINK = it has not answered at this address yet."""
        if self.amp_ok:
            return "ON"
        return "OFF" if (self.ever_ok or self.presence_match) else "NO LINK"

    def presence_loop(self):
        """While the amp is silent, look in the ARP table to see whether it is still
        on the network (a switched-off amp is usually still there, asleep)."""
        while not self.stop.is_set():
            if self.amp_ok or self.a.dry_run:
                self.presence, self.presence_match = None, False
            else:
                mac = arp_lookup(self.amp.addr[0])
                self.presence = bool(mac)
                self.presence_match = bool(mac and self.mac and mac == self.mac)
            self.stop.wait(5.0)

    def mode_text(self, unknown="UNKNOWN"):
        if not self.amp_ok:
            return self.power_text()
        return {1: "OPERATE", 0: "STANDBY"}.get(self.mode, unknown)

    def state(self):
        lp = self.lp.snapshot() if self.lp else None
        return {
            "tci": self.tci_ok, "amp": self.amp_ok, "dry_run": self.a.dry_run,
            "freq_khz": self.want_khz, "tx": self.tx,
            "amp_khz": self.follow_state()[0], "follow": self.follow_state()[1],
            "mode": self.mode_text(None), "power": self.power_text(),
            "on_network": self.presence,
            "tune_active": self.tune_active, "fwd": self.fwd, "refl": self.refl,
            "swr": self.swr, "pin": self.pin, "temp": self.temp,
            "drive": self.drive_info()[0], "drive_src": self.drive_info()[1],
            "radio_swr": self.radio_swr,
            "volts": self.volts, "amps": self.amps,
            "fault": self.fault or 0,
            "fault_text": FAULTS.get(self.fault or 0, "unknown"),
            "atu": self.atu, "ant": self.ant, "atu_tuning": self.atu_tuning,
            "fan": self.fan_speed, "fan_min": self.fan_min,
            "amp_ip": self.amp.addr[0], "amp_port": self.amp.addr[1],
            "amp_ip_source": self.amp_ip_source, "found": self.found_amps,
            "finding": self.finding,
            "standby_on_tune": self.standby_on_tune,
            "wol": self.wol, "mac": self.mac,
            "version": VERSION, "confirm_off": self.confirm_power_off,
            "thetis_off": self.allow_thetis_off, "block_off_tx": self.block_off_tx,
            "log": self.log_info(),
            "lp_enabled": bool(self.lp and self.lp.port), "lp": lp,
            "lp_port": self.lp.port if self.lp else "",
            "lp_baud": self.lp.baud if self.lp else 115200,
            "lp_connected": bool(self.lp and self.lp.connected),
            "lp_error": self.lp.last_error if self.lp else "",
            "lp_raw": self.lp.raw if self.lp else "",
            "transmitting": self.transmitting(), "msg": self.last_msg,
            "mm": self.mmio_vars(),
            "radio": self.radio_kind or "", "radio_pref": self.radio_pref,
            "radio_name": RADIO_NAMES.get(self.radio_kind, ""), "cat_via": self.cat_via,
            "cat_link": bool(self.cat_link and self.cat_link.connected),
            "applet_skin": self.applet_skin,
            "noant": self.noant_state(), "noant_limits": dict(self.noant_limits),
            "drive_guard": self.drive_guard_state(),
            "noant_defaults": dict(NOANT_DEFAULTS),
            "tune_timeout": self.tune_timeout, "bridge_tune": self.bridge_tune,
            "thetis_buttons": self.thetis_buttons, "thetis_buttons_default": TB_DEFAULT,
            "thetis_meters": self.thetis_meters, "thetis_meters_default": TM_DEFAULT,
            "thetis_knobwin": self.thetis_knobwin,
            "knob": dict(self.knob_cfg, connected=bool(self.knob and self.knob.connected),
                         device=self.knob.device if self.knob else "", error=self.knob.error if self.knob else "",
                         mode=self.knob_mode, mode_name=KNOB_MODES[self.knob_mode][0],
                         last=self.knob_last[0], last_text=self.knob_last[1],
                         last_age=round(time.time() - self.knob_last[2], 1) if self.knob_last[2] else None,
                         tci_cat=self.tci_cat_ok),
            "is_windows": os.name == "nt",
            "flex": self.flex.status() if self.flex else None,
            "web_password_set": bool(self.a.web_token), "web_bind": self.a.web_bind, "web_port": self.a.web_port,
            "tune_left": (max(0, int(self.tune_timeout - (time.time() - self.tune_t)))
                          if self.tune_active and self.bridge_tune and self.tune_timeout else None),
        }

    def freq_text(self):
        """amp frequency as text with 'MHz' (text, so Thetis shows all 3 decimals)"""
        k, _ = self.follow_state()
        if k is None and self.amp_ok and self.want_khz:
            k = self.want_khz
        return ("%.3f MHz" % (k / 1000.0)) if k else "--- MHz"

    # ---- Thetis Multi Meter I/O --------------------------------------------
    def mmio_vars(self):
        na = self.noant_state()
        d, src = self.drive_info()
        lp = self.lp.snapshot() if self.lp else None
        gain = (10 * math.log10(self.fwd / d)
                if (self.mode == 1 and d > 0 and self.fwd > 0) else 0.0)
        z = lambda key: lp[key] if lp else 0.0
        return {
            "amp_online": int(self.amp_ok),
            "amp_operate": int(self.mode == 1),
            "amp_mode": self.mode_text(),
            "amp_power": self.power_text(),
            "amp_tx": int(self.transmitting()),
            "amp_fwd": int(self.fwd), "amp_refl": int(self.refl),
            "amp_swr": round(self.swr, 1), "amp_drive": round(d, 1),
            "amp_drive_src": src, "amp_gain_db": round(gain, 1),
            "amp_temp": self.temp if self.temp is not None else 0,
            "amp_volts": self.volts if self.volts is not None else 0.0,
            "amp_amps": self.amps if self.amps is not None else 0,
            "amp_fault": self.fault or 0,
            "amp_fault_text": FAULTS.get(self.fault or 0, "unknown") if self.amp_ok else "--",
            "amp_atu_inline": int(self.atu == "I"),
            "amp_atu": {"I": "INLINE", "B": "BYPASS"}.get(self.atu, "UNKNOWN" if self.amp_ok else "--"),
            "amp_atu_tuning": int(bool(self.atu_tuning)),
            "amp_ant": self.ant or 0,
            "amp_fan": self.fan_speed if self.fan_speed is not None else 0,
            "amp_fan_min": self.fan_min if self.fan_min is not None else 0,
            "amp_sot": int(self.standby_on_tune),
            "amp_sot_text": "ON" if self.standby_on_tune else "OFF",
            "amp_freq": self.freq_text(),
            "amp_freq_khz": self.follow_state()[0] or (self.want_khz if self.amp_ok and self.want_khz else 0),
            "amp_follow": self.follow_state()[1],
            "amp_freq_line": self.freq_text() + ("" if self.follow_state()[1] in ("= radio", "", "--")
                                                 else "  " + self.follow_state()[1]),
            "bridge_version": "v" + VERSION,
            "amp_following": int(self.follow_state()[1] in ("= radio", "(sent)")),
            "bridge_time": int(time.time()),
            "amp_tune_active": int(self.tune_active),
            "rx_dbm": na["dbm"] if na["dbm"] is not None else 0.0,
            "rx_text": ("RX %.0f dBm" % na["dbm"]) if na["dbm"] is not None and na["live"] else "RX --",
            "noant": int(na["warn"]),
            "noant_tx": int(na["state"] == "tx"),
            "noant_held": int(self.noant_held),
            "dummy_ok": int(na["dummy"]),
            "noant_text": na["text"],
            "drvlim": int(self.drive_guard_state()["warn"]),
            "drvlim_text": self.drive_guard_state()["text"],
            "knob_mode": KNOB_MODES[self.knob_mode][0] if (self.knob and self.knob.connected) else "--",
            "knob_connected": int(bool(self.knob and self.knob.connected)),
            "knob_now": KNOB_MODES[self.knob_mode][0],
            "knob_k": self.knob_line("knob"), "knob_b1": self.knob_line("b1"),
            "knob_b2": self.knob_line("b2"), "knob_b3": self.knob_line("b3"),
            "knob_status": (("FlexControl on " + self.knob.device) if (self.knob and self.knob.connected)
                            else ("FlexControl: " + ((self.knob.error if self.knob else "") or "off")
                                  if self.knob_cfg["port"] else "FlexControl: off")),
            "lp_online": int(lp is not None),
            "lp_pwr": round(z("pwr"), 1), "lp_swr": round(lp["swr"], 2) if (lp and lp["pwr"] >= 1.0) else 1.0,
            "lp_refl": round(z("refl"), 1), "lp_rl": round(lp["rl"] or 0, 1) if lp else 0.0,
            "lp_z": round(z("z"), 1), "lp_phase": round(z("phase"), 1),
            "lp_r": round(z("r"), 1), "lp_x": round(z("x"), 1),
            "lp_dbm": round(z("dbm"), 1),
        }

    def mmio_targets(self):
        """where telemetry goes: Thetis (UDP XML, --mmio-port) and/or NereusSDR (UDP JSON, --nereus-mmio-port)"""
        t = []
        if self.a.mmio_port:
            t.append((self.a.mmio_host, self.a.mmio_port, self.a.mmio_format, self.a.mmio_term, self.a.mmio_root))
        if getattr(self.a, "nereus_mmio_port", 0):
            t.append((self.a.nereus_mmio_host, self.a.nereus_mmio_port, self.a.nereus_mmio_format,
                      self.a.nereus_mmio_term, self.a.mmio_root))
        return t

    def mmio_send_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        period = 1.0 / max(1.0, min(50.0, self.a.mmio_rate))
        while not self.stop.is_set():
            vals = self.mmio_vars()
            for host, port, fmt, term, root in self.mmio_targets():
                try:
                    for dg in mmio_encode(vals, fmt, term, root):
                        sock.sendto(dg, (host, port))
                except OSError:
                    pass
            self.stop.wait(period)

    def mmio_in_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.a.mmio_listen_bind, self.a.mmio_listen))
        except OSError as e:
            self.log("MMIO command listener could not bind %s:%d (%s)"
                     % (self.a.mmio_listen_bind, self.a.mmio_listen, e))
            return
        sock.settimeout(0.5)
        last = {}
        unknown_logged = 0
        while not self.stop.is_set():
            try:
                data, addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                return
            text = data.decode("utf-8", "replace")
            self.log("<- Thetis button message from %s: %r" % (addr[0], text), verbose=True)
            tokens = re.findall(r"KPA_[A-Z0-9_]+", text.upper())
            if not tokens and unknown_logged < 20:
                unknown_logged += 1
                self.log("Thetis sent a message with no KPA_ command in it: %r "
                         "(check the string typed into the Thetis macro button)" % text[:80])
            for tok in tokens:
                spec = MMIO_COMMANDS.get(tok)
                if not spec:
                    self.log("Ignored unknown Thetis command %s" % tok)
                    continue
                action, aparams = spec if isinstance(spec, tuple) else (spec, None)
                if action == "power_off" and not self.allow_thetis_off:
                    self.log("Thetis button %s -> REFUSED: option 'Allow Thetis to power off "
                             "the amp' is off" % tok)
                    break
                now = time.time()
                if now - last.get(tok, 0) < 0.25:      # debounce double-sends
                    break
                last[tok] = now
                ok, msg = self.do_action(action, aparams)
                self.log("Thetis button %s -> %s%s" % (tok, "" if ok else "REFUSED: ", msg))
                break

    def start_mmio(self):
        if self.mmio_targets():
            threading.Thread(target=self.mmio_send_loop, daemon=True).start()
        if self.a.mmio_listen:
            threading.Thread(target=self.mmio_in_loop, daemon=True).start()

    # ---- web panel -------------------------------------------------------
    def start_web(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, body, ctype="application/json"):
                data = body if isinstance(body, bytes) else body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _local(self):
                return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

            def _auth(self):
                tok = bridge.a.web_token
                if not tok:
                    return True
                if bridge.local_no_token and self._local():
                    return True        # on the bridge computer: no password needed
                got = parse_qs(urlparse(self.path).query).get("t", [""])[0]
                return hmac.compare_digest(got, tok)

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/":
                    self._send(200, PAGE_HTML.replace("__VERSION__", VERSION).replace(
                        "__KNOB_CATALOG__", json.dumps({"events": KNOB_EVENTS, "actions": [a[:3] for a in KNOB_ACTIONS],
                                                        "modes": {k: v[0] for k, v in KNOB_MODES.items()},
                                                        "defaults": KNOB_DEFAULT_TABLE})),
                               "text/html; charset=utf-8")
                elif path == "/api/state":
                    if not self._auth():
                        return self._send(403, '{"error":"token required"}')
                    st = bridge.state()
                    st["client_local"] = self._local()
                    self._send(200, json.dumps(st))
                elif path == "/flex":
                    if not self._auth():
                        return self._send(403, '{"error":"token required"}')
                    self._send(200, flexemu.STATUS_PAGE if flexemu else "Add-on file kpa1500_flex_emulation.py not found",
                               "text/html; charset=utf-8")
                elif path == "/help":
                    self._send(200, render_help_html(), "text/html; charset=utf-8")
                elif path == "/applet":
                    self._send(200, APPLET_HTML.replace("__VERSION__", VERSION), "text/html; charset=utf-8")
                elif path == "/api/ports":
                    if not self._auth():
                        return self._send(403, '{"error":"token required"}')
                    ports, note = list_serial_ports()
                    self._send(200, json.dumps({"ports": ports, "note": note}))
                else:
                    self._send(404, '{"error":"not found"}')

            def do_POST(self):
                # Always read the request body first. Answering (e.g. 403) while the body is
                # still unread makes Windows reset the connection (WinError 10053/10054).
                try:
                    n = max(0, min(int(self.headers.get("Content-Length", "0")), 65536))
                    raw = self.rfile.read(n) if n else b""
                except (ValueError, OSError):
                    raw = b""
                if urlparse(self.path).path != "/api/cmd":
                    return self._send(404, '{"error":"not found"}')
                if not self._auth():
                    return self._send(403, '{"error":"token required"}')
                if self.headers.get("X-KPA") != "1":       # blocks cross-site posts
                    return self._send(403, '{"error":"missing header"}')
                try:
                    body = json.loads(raw[:16384] or b"{}")
                    action = body.get("action", "")
                    params = body.get("params")
                except (ValueError, AttributeError):
                    return self._send(400, '{"error":"bad request"}')
                if str(action) in ("quit_bridge", "applet_window") and not self._local():
                    return self._send(200, json.dumps({"ok": False, "message":
                                      "That can only be done on the bridge computer itself"}))
                if str(action) == "web_password" and not self._local():
                    return self._send(200, json.dumps({"ok": False, "message":
                                      "The panel password can only be changed on the bridge computer itself"}))
                ok, msg = bridge.do_action(str(action), params)
                self._send(200, json.dumps({"ok": ok, "message": msg}))

        class QuietServer(ThreadingHTTPServer):
            daemon_threads = True

            def handle_error(self, request, client_address):
                # A browser that closes a page mid-reply (common on Windows:
                # WinError 10053/10054) is normal - do not print a traceback.
                if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError, BrokenPipeError)):
                    return
                super().handle_error(request, client_address)

        self.web = QuietServer((self.a.web_bind, self.a.web_port), Handler)
        self.web.daemon_threads = True
        threading.Thread(target=self.web.serve_forever, daemon=True).start()
        return self.web.server_address[1]

    # ---- console ---------------------------------------------------------
    def status_text(self):
        f = self.want_khz
        mode = self.mode_text("?")
        if self.tune_active:
            mode += "(tune)"
        fault = "--" if not self.fault else "%02X" % self.fault
        s = ("TCI:%s AMP:%s | %s | %s ATU:%s ANT:%s | Fwd %4dW SWR %.1f | "
             "Drive %3.0fW | %s C | Fault %s" % (
                 "ok" if self.tci_ok else "--", "ok" if self.amp_ok else self.power_text(),
                 ("%.3f MHz" % (f / 1000.0) if f else "no freq")
                 + {"= radio": " (amp ok)", "": ""}.get(self.follow_state()[1],
                     " (amp %.3f!)" % (self.amp_khz / 1000.0) if self.amp_khz else ""), mode,
                 self.atu or "?", self.ant or "?", self.fwd, self.swr,
                 self.drive_info()[0],
                 self.temp if self.temp is not None else "--", fault))
        if self.lp:
            lp = self.lp.snapshot()
            s += " | LP %s" % ("%.0fW SWR %.2f" % (lp["pwr"], lp["swr"])
                               if lp else "--")
        if self.knob and self.knob.connected and self.knob_mode != "vfoa":
            s += " | KNOB " + KNOB_MODES[self.knob_mode][0].split(" (")[0]
        na = self.noant_state()
        if na["state"] != "off" and na["dbm"] is not None and na["live"]:
            s += " | RX %.0f" % na["dbm"]
        s += {"low": " ANTENNA?" + (" (STBY)" if na["hold"] else ""), "tx": " !!TX NO ANTENNA?!!",
              "dummy": " DUMMY OK"}.get(na["state"], "")
        dg = self.drive_guard_state()
        if dg["warn"]:
            s += " | " + dg["text"]
        return s

    def run(self):
        if os.name == "nt":
            os.system("title KPA1500 SDR Bridge v%s" % VERSION)
        print("KPA1500 SDR bridge  v%s (%s)   amp %s:%d   TCI %s:%d%s%s" % (
            VERSION, BUILD_DATE,
            self.amp.addr[0], self.amp.addr[1], self.a.tci_host, self.a.tci_port,
            "   [DRY-RUN: nothing is sent to the amp]" if self.a.dry_run else "",
            "" if self.standby_on_tune else "   [standby-on-tune OFF]"))
        threading.Thread(target=self.presence_loop, daemon=True).start()
        if not self.a.no_web:
            try:
                port = self.start_web()
                host = "127.0.0.1" if self.a.web_bind in ("127.0.0.1", "localhost") \
                    else self.a.web_bind
                print("Control panel: http://%s:%d%s" % (
                    host, port, ("/?t=" + self.a.web_token) if self.a.web_token else ""))
            except OSError as e:
                print("Could not start control panel on port %d: %s"
                      % (self.a.web_port, e))
        saved = "lp100_port" in self.settings
        lp_port = self.settings["lp100_port"] if saved else self.a.lp100_port
        lp_baud = int(self.settings.get("lp100_baud", self.a.lp100_baud))
        self.lp = LP100(lp_port, lp_baud, default_serial_opener, self.log,
                        self.a.lp100_debug)
        self.lp.start()
        self.knob = FlexKnob(self.knob_cfg["port"], default_serial_opener, self.knob_code, self.log)
        self.knob.start()
        if lp_port:
            print("LP-100A: %s @ %d%s" % (lp_port, lp_baud,
                  "  (saved from the panel - overrides --lp100-port)"
                  if saved and self.a.lp100_port != lp_port else ""))
        else:
            print("LP-100A: no port set (choose one in the panel: Settings > LP-100A port)")
        if self.a.mmio_port:
            print("Thetis MMIO feed: -> %s:%d as %s (%.0f/s)" % (
                self.a.mmio_host, self.a.mmio_port, self.a.mmio_format.upper(),
                self.a.mmio_rate))
        if getattr(self.a, "nereus_mmio_port", 0):
            print("NereusSDR MMIO feed: -> %s:%d as %s (%.0f/s)" % (
                self.a.nereus_mmio_host, self.a.nereus_mmio_port, self.a.nereus_mmio_format.upper(),
                self.a.mmio_rate))
        print("Radio program: %s   (NereusSDR CAT port %s:%s)" % (
            {"auto": "found automatically (Thetis or NereusSDR)", "thetis": "Thetis",
             "nereus": "NereusSDR"}[self.radio_pref],
            self.a.nereus_cat_host, self.a.nereus_cat_port or "off"))
        if self.a.mmio_listen:
            print("Thetis button commands: listening on %s:%d" % (
                self.a.mmio_listen_bind, self.a.mmio_listen))
        self.start_mmio()
        if (self.a.amp_ip or "").lower() == "auto":
            self.startup_discovery()
        if flexemu and flexemu.wanted(self.a):
            try:
                self.flex = flexemu.FlexEmulation(self, self.a, log=self.log)
                self.flex.start()
                print("FlexRadio emulation: PGXL on TCP %d%s%s   (status page: /flex)" % (
                    self.flex.pgxl.port,
                    ", TGXL on TCP %d" % self.flex.tgxl.port if self.flex.tuner else "",
                    ", logging in to radio %s [EXPERIMENTAL]" % self.flex.radio_ip if self.flex.link else ""))
            except Exception as e:
                self.flex = None
                print("FlexRadio emulation could not start: %s" % e)
        elif flexemu is None and any(x.startswith("--flex") for x in sys.argv[1:]):
            print("FlexRadio emulation add-on not available: %s" % _FLEX_IMPORT_ERROR)
        print("Press H for keyboard commands, W to open the full help. Ctrl+C or Q to quit.")
        print("Log file: %s\n" % (
            ("%s (kept under %s)" % (self.a.logfile, ("%g MB" % self.log_max_mb)
                                     if self.log_max_mb > 0 else "no limit"))
            if self.log_enabled else "OFF"))
        if not self.a.no_keys:
            ConsoleKeys(self).start()
        threading.Thread(target=self.tci_loop, daemon=True).start()
        threading.Thread(target=self.poll_loop, daemon=True).start()
        threading.Thread(target=self.drive_guard_loop, daemon=True).start()
        if self.radio_pref == "nereus":
            self.start_cat_link()
        if getattr(self.a, "applet", False) and self.web and not self.a.no_web:
            sk = self.applet_skin
            open_applet_window(self.applet_url(), sk["width"], sk["height"], self.log)
        try:
            while not self.quit:
                time.sleep(0.5)
                if self.prompting:
                    continue
                line = fit_status(self.status_text())     # built BEFORE taking the print lock
                with self.print_lock:
                    sys.stdout.write("\r" + line)
                    sys.stdout.flush()
            print("\nStopping.")
            self.stop.set()
            close_applet_window()
            if self.cat_link:
                self.cat_link.close()
            if self.lp:
                self.lp.stop.set()
            if self.knob:
                self.knob.stop.set()
        except KeyboardInterrupt:
            print("\nStopping.")
            self.stop.set()
            close_applet_window()
            if self.lp:
                self.lp.stop.set()
            if self.knob:
                self.knob.stop.set()


# --------------------------------------------------------------------------
# Built-in help (browser: /help   window: keys W and I   file: --write-help)
# --------------------------------------------------------------------------
MMIO_VAR_HELP = {
    "amp_online": "1 if the amplifier is answering, otherwise 0",
    "amp_operate": "1 = OPERATE, 0 = STANDBY",
    "amp_mode": "text: OPERATE, STANDBY, UNKNOWN - or OFF / NO LINK when the amplifier is not answering",
    "amp_power": "text: ON, OFF (was answering, now silent: switched off or lost power) or NO LINK (never answered at this address)",
    "amp_tx": "1 while the radio or amplifier is transmitting",
    "amp_fwd": "amplifier forward power, watts",
    "amp_refl": "amplifier reflected power, watts",
    "amp_swr": "SWR at the amplifier output",
    "amp_drive": "drive power into the amplifier, watts (taken from the radio when the amp is in standby)",
    "amp_drive_src": "where the drive figure came from: amp, radio or none",
    "amp_gain_db": "amplifier gain in dB (only while in OPERATE and transmitting)",
    "amp_temp": "PA temperature, degrees C",
    "amp_volts": "PA supply voltage, volts",
    "amp_amps": "PA current, amps",
    "amp_fault": "fault code (0 = no fault)",
    "amp_fault_text": "fault description in words",
    "amp_atu_inline": "1 = ATU inline, 0 = ATU bypassed",
    "amp_atu": "text: INLINE, BYPASS or UNKNOWN",
    "amp_atu_tuning": "1 while the ATU is tuning",
    "amp_ant": "selected antenna number",
    "amp_fan": "current fan speed, 0 (off) to 5 (all fans, highest speed)",
    "amp_fan_min": "minimum fan speed you have set, 0 to 5",
    "amp_sot": "1 if Standby-on-Tune is switched on",
    "amp_freq": "frequency the amp is set to, as text, e.g. 14.025 MHz (read back from the amp)",
    "amp_freq_khz": "frequency the amp is set to, kHz (0 = unknown)",
    "amp_follow": "text: '= radio' when the amp is on the radio frequency, 'radio 7.150 !' when not, '(sent)' if the amp does not report it",
    "amp_freq_line": "amp frequency for the Thetis windows: '7.150 MHz' while it follows the radio, '7.150 MHz  radio 14.025 !' when it does not",
    "bridge_version": "bridge version as text, e.g. v2.23 (shown in the Thetis window titles)",
    "amp_following": "1 when the amp is on the radio frequency",
    "rx_dbm": "receive level from Thetis, dBm (average signal of RX1, judged only while receiving)",
    "rx_text": "receive level as text, e.g. RX -78 dBm",
    "noant": "1 when the 'no antenna?' warning is showing (receive level below the band limit, no DUMMY OK)",
    "noant_tx": "1 when transmitting while the 'no antenna?' warning is showing",
    "noant_held": "1 when the bridge is keeping the amp in STANDBY because of the 'no antenna?' check",
    "dummy_ok": "1 when DUMMY OK has been pressed for this band (dummy load connected on purpose)",
    "noant_text": "the 'no antenna?' warning text (empty when all is well)",
    "drvlim": "1 when the over-drive protection warning is showing (drive over the limit)",
    "drvlim_text": "the over-drive warning text (empty when all is well)",
    "knob_mode": "what the FlexControl knob does now, e.g. VFO A tuning or AF volume (master) ('--' = no knob)",
    "knob_connected": "1 when the FlexControl tuning knob is connected",
    "knob_now": "what turning the knob does now, e.g. VFO A tuning, AF volume (master), AGC gain (RX1)",
    "knob_k": "the knob press functions in short, e.g. tap >AF   2x Mute   hold >VFO A ('>' = switch the knob to)",
    "knob_b1": "button 1 functions in short (tap / double tap / hold)",
    "knob_b2": "button 2 functions in short (tap / double tap / hold)",
    "knob_b3": "button 3 functions in short (tap / double tap / hold)",
    "knob_status": "FlexControl connection, e.g. FlexControl on COM7",
    "amp_sot_text": "text: ON or OFF (Standby-on-Tune), for display",
    "bridge_time": "heartbeat: the time in seconds (Unix time). Thetis can warn when it stops changing (bridge not running)",
    "amp_tune_active": "1 while the radio's TUNE is active",
    "lp_online": "1 if the LP-100A is answering, otherwise 0",
    "lp_pwr": "LP-100A forward power, watts",
    "lp_swr": "SWR at the LP-100A (the real antenna SWR)",
    "lp_refl": "reflected power, watts (calculated)",
    "lp_rl": "return loss, dB",
    "lp_z": "impedance magnitude, ohms",
    "lp_phase": "impedance phase, degrees",
    "lp_r": "resistance part of the impedance, ohms",
    "lp_x": "reactance part of the impedance, ohms (negative = capacitive)",
    "lp_dbm": "power in dBm",
}

MMIO_CMD_HELP = {
    "KPA_OPERATE": "Put the amplifier in OPERATE",
    "KPA_STANDBY": "Put the amplifier in STANDBY",
    "KPA_OPERATE_TOGGLE": "Flip between OPERATE and STANDBY (best for one button)",
    "KPA_ATU_INLINE": "ATU inline (refused while transmitting)",
    "KPA_ATU_BYPASS": "ATU bypass (refused while transmitting)",
    "KPA_ATU_TOGGLE": "Flip ATU between inline and bypass (refused while transmitting)",
    "KPA_ATU_TUNE": "Start the amplifier's ATU tune search. Then press TUNE in Thetis at low power",
    "KPA_ATU_CANCEL": "Cancel an ATU tune in progress",
    "KPA_ANT1": "Select antenna 1 (refused while transmitting)",
    "KPA_ANT2": "Select antenna 2 (refused while transmitting)",
    "KPA_ANT_NEXT": "Select the next antenna (refused while transmitting)",
    "KPA_ANT_TOGGLE": "Flip between antenna 1 and 2 (refused while transmitting)",
    "KPA_CLEAR_FAULT": "Clear the amplifier fault",
    "KPA_SOT_ON": "Switch Standby-on-Tune on",
    "KPA_SOT_OFF": "Switch Standby-on-Tune off",
    "KPA_SOT_TOGGLE": "Flip Standby-on-Tune on or off",
    "KPA_POWER_ON": "Power the amplifier on (Wake-on-LAN)",
    "KPA_POWER_OFF": "Power the amplifier OFF at once, no question asked (needs 'Allow Thetis to power off the amp'; refused while transmitting unless 'Block power off while transmitting' is off)",
    "KPA_LP_ALARM": "Cycle the LP-100A alarm setting",
    "KPA_LP_MODE": "Cycle the LP-100A display mode",
    "KPA_FAN_0": "Minimum fan speed 0: fans stay off until the amp needs them",
    "KPA_FAN_1": "Minimum fan speed 1",
    "KPA_FAN_2": "Minimum fan speed 2",
    "KPA_FAN_3": "Minimum fan speed 3",
    "KPA_FAN_4": "Minimum fan speed 4",
    "KPA_FAN_5": "Minimum fan speed 5: all fans at the highest speed, always",
    "KPA_FAN_UP": "Raise the minimum fan speed by one (stops at 5)",
    "KPA_FAN_DOWN": "Lower the minimum fan speed by one (stops at 0)",
    "KPA_RADIO_TUNE": "Start the RADIO's tune the safe way: amp to STANDBY first (Standby-on-Tune), "
                      "confirmed, then Thetis TUNE on. Stops by itself after the auto-stop time",
    "KPA_RADIO_TUNE_STOP": "Stop the radio's tune (the amp returns to OPERATE if it was in OPERATE)",
    "KPA_DUMMY_OK": "DUMMY OK: a dummy load is connected on purpose - silences the 'no antenna?' "
                    "warning on this band (press again to undo)",
}


def _P(t):
    return ("p", t)


def _UL(*items):
    return ("ul", list(items))


def _OL(*items):
    return ("ol", list(items))


def _CODE(t):
    return ("code", t.strip("\n"))


def _NOTE(t):
    return ("note", t)


def _WARN(t):
    return ("warn", t)


def _TABLE(head, rows):
    return ("table", head, rows)


def _IMG(name, caption):
    """a picture from HELP_IMAGES (bottom of this file), shown in the HTML help"""
    return ("img", name, caption)


def help_sections():
    """The whole help document as a list of sections (id, title, blocks).
    The variable, button-string and flag tables are generated from the program
    itself, so they cannot get out of date."""
    flag_rows = []
    for act in build_parser()._actions:
        if not act.option_strings or act.option_strings == ["-h", "--help"]:
            continue
        flag = " ".join(act.option_strings)
        if act.nargs != 0 and not isinstance(act, argparse._VersionAction):
            flag += " " + (act.metavar or act.dest.upper())
        default = ""
        if act.nargs != 0 and act.default not in (None, "", argparse.SUPPRESS):
            default = str(act.default)
            if os.sep in default:
                default = "(next to the script)"
        flag_rows.append(["`%s`" % flag, act.help or "", default])
    var_rows = [["`%s`" % k, v] for k, v in MMIO_VAR_HELP.items()]
    cmd_rows = [["`%s`" % k, MMIO_CMD_HELP.get(k, "")] for k in MMIO_COMMANDS]

    S = []
    S.append(("overview", "1. What this is", [
        _P("The KPA1500 bridge is a small program that runs on the PC next to Thetis or NereusSDR. "
           "It connects Thetis, the Elecraft KPA1500 amplifier and (optionally) the "
           "Telepost LP-100A power meter over your network."),
        _UL("Follows your Thetis or NereusSDR frequency, so the amplifier changes band by itself.",
            "**Standby on Tune**: the amplifier drops to STANDBY while the radio tunes "
            "and goes back to what it was afterwards.",
            "Shows live readings: forward and reflected power, SWR, drive, gain, "
            "temperature, volts and amps, fault codes, plus LP-100A readings.",
            "Controls the amplifier: Operate/Standby, ATU inline/bypass/tune, antenna, "
            "clear fault, power on and off.",
            "A control panel you open in a web browser, on this PC or any device on your network.",
            "Keyboard commands in the bridge window.",
            "An **Applet window** (works with Thetis and NereusSDR) with the meters, control buttons, "
            "FlexControl knob lines and LP-100A readings in one small window you can restyle and resize "
            "(see {sec:nereus}).",
            "A FlexControl knob that works with both radio programs.",
            "Two ready-made Thetis windows (containers): **KPA1500 Telemetry** with meters, and "
            "**KPA1500 Controls** with buttons that light up. One double-click puts them into Thetis "
            "(see {sec:containers})."),
        _CODE("""
 Thetis or NereusSDR <--TCI (port 50001)--> BRIDGE <--LAN (UDP 1500)--> KPA1500 amplifier
   ^        (NereusSDR also: CAT port 13013)     |  ^
   |  containers (Multi Meter I/O / UDP)         |  +-- LP-100A (USB / COM port)
   +---------------------------------------------+
                                                 |
                   Browser panel (http://127.0.0.1:8080)   Applet window (/applet)
"""),
        _NOTE("The bridge never keys your transmitter. You press TUNE or PTT in Thetis as usual."),
    ]))
    S.append(("requirements", "2. What you need", [
        _TABLE(["Item", "Needed", "Notes"], [
            ["Amplifier", "Elecraft KPA1500 on your network",
             "Fixed IP address (default used here: 192.168.0.175). Firmware 01.84 or newer, "
             "which adds the UDP interface the bridge uses."],
            ["Radio software", "Thetis 2.10.3.12 or newer (2.10.3.15 recommended), or NereusSDR",
             "TCI server switched on (both programs). NereusSDR also needs TCP/IP CAT, see {sec:nereus}. The ready-made Thetis windows need 2.10.3.12+ (macro buttons, "
             "LED scripts); drive-in-standby needs 2.10.3.13+."],
            ["Computer", "Windows 10 or 11 PC running Thetis",
             "The bridge runs on the same PC. Other PCs, Macs and tablets can use the browser panel."],
            ["Python", "Python 3.8 or newer", "From python.org. Nothing else to install for the basics."],
            ["Network", "PC and amplifier on the same network",
             "Wired is best. The amplifier must be reachable on UDP port 1500."],
            ["LP-100A (optional)", "Telepost LP-100A on a USB or COM port",
             "Needs the pyserial add-on. Keep the meter on its Watts screen."],
            ["Wake-on-LAN (optional)", "Amp menu NET WAKE on LAN = ON",
             "Only needed to power the amplifier on from the panel."],
            ["Browser", "Edge, Chrome, Firefox or Safari", "For the control panel and this help."],
        ]),
    ]))
    S.append(("install", "3. Installing", [
        _P("**Easiest: the installer.** Double-click `Install_KPA1500_SDR_Bridge.bat`. It checks Python, "
           r"asks where to install (it makes its own subfolder, for example `C:\RadioScripts\KPA1500_SDR_Bridge`), "
           "installs pyserial for the LP-100A, finds the amplifier's address, asks for the LP-100A COM port, "
           "writes the start file, offers shortcuts, the firewall rule and a test, and can set up the Thetis "
           "windows. It leaves any older bridge folder alone."),
        _P("**By hand:**"),
        _OL("**Install Python.** Go to python.org/downloads, install the latest Python 3, and "
            "tick **Add python.exe to PATH** on the first screen. Check it: open Command "
            "Prompt and type `py --version`.",
            r"**Make a folder** `C:\RadioScripts\KPA1500_SDR_Bridge` and copy all the files from the package "
            r"into it (at least `kpa1500_sdr_bridge.py` and `start_kpa_sdr_bridge.bat`).",
            "**LP-100A only:** in Command Prompt type `py -m pip install pyserial`.",
            "**Test the program** (no radio or amplifier needed): "
            r"type `cd C:\RadioScripts\KPA1500_SDR_Bridge` then `py kpa1500_sdr_bridge.py --selftest`. "
            "The last line should say ALL TESTS PASSED.",
            "**Switch on the radio program's connections.** Thetis: Setup > Serial/Network/Midi CAT "
            "(Network tab), TCI server running, 127.0.0.1 port 50001. NereusSDR: the settings in {sec:nereus}.",
            "**First run in safe mode:** `py kpa1500_sdr_bridge.py --dry-run`. Nothing is "
            "sent to the amplifier. The status line should show `TCI:ok AMP:ok`.",
            "If Windows asks about the firewall, allow Python on **Private** networks.",
            "**Run it for real:** double-click `start_kpa_sdr_bridge.bat`, then open "
            "http://127.0.0.1:8080 in a browser."),
        _P("If your amplifier is not at 192.168.0.175, open `start_kpa_sdr_bridge.bat` in Notepad "
           "and add `--amp-ip 192.168.0.xxx` to the BRIDGE_FLAGS line (see Customizing). Not sure of the "
           "address? Use `--amp-ip auto`, or see Finding the amplifier on the network."),
        _NOTE("Only one bridge can run at a time (the amplifier and the knob allow one user). The older "
              "`kpa1500_thetis_bridge.py` can stay on the disk, but this bridge closes it when it starts."),
    ]))
    S.append(("start", "4. Starting and stopping", [
        _UL(r"Double-click `start_kpa_sdr_bridge.bat`. It starts the bridge in its own window. If a bridge "
            "(this one or the older Thetis-only one) is already running, it is closed first, so you never "
            "get two copies or leftover windows.",
            "That window is minimized by default: look for **KPA1500 SDR Bridge** on the taskbar.",
            "**Stop it cleanly:** double-click `Stop_Bridge.bat`, or in the Applet click **Look**, scroll to "
            "**Bridge** and press **Quit bridge**, or press **Q** in the bridge window. All of these close the "
            "bridge, its window and the Applet window. Ctrl+C also works.",
            "`Open_Applet.bat` opens the Applet window again if you closed it.",
            "**Start with Windows**, or **start Thetis and the bridge together**: the notes at "
            "the top of `start_kpa_sdr_bridge.bat` explain both, step by step."),
    ]))
    S.append(("find", "Finding the amplifier on the network", [
        _P("If you do not know the amplifier's IP address, the bridge can search for it. It sends the "
           "amplifier's own 'identify' command to every address on your network and lists the ones "
           "that answer. Each result shows the address, serial number and firmware."),
        _UL("**Once, from the command line:** `py kpa1500_sdr_bridge.py --discover`. It prints "
            "what it found and the address to use.",
            "**Every start:** use `--amp-ip auto`. If the amplifier answers at the last known "
            "address nothing is searched; otherwise the network is searched and the address is "
            "remembered.",
            "**While running, in the panel:** click Settings, then **Find amplifier**. Pick the one you "
            "want and press **Use this address**.",
            "**While running, in the bridge window:** press **D**."),
        _P("The address you pick is saved and used at the next start. An explicit `--amp-ip "
           "192.168.x.x` in the batch file always overrides the saved one, so remove it if you "
           "want the panel's choice to stick."),
        _P("By default it searches this PC's own network (the /24 around its address) and the "
           "network of the address it already knows. To search somewhere else give the network, for "
           "example `--discover 192.168.1.0/24` or `--discover-net 192.168.1.0/24`."),
        _NOTE("The amplifier must be on and on the same network, and Windows Firewall must allow "
              "Python on Private networks. A sleeping amplifier may not answer. The amplifier address "
              "cannot be changed while the radio or amplifier is transmitting."),
    ]))
    S.append(("panel", "5. Using the browser panel", [
        _P("Open http://127.0.0.1:8080 (the bridge prints the address when it starts). "
           "The panel shows tiles. A tile is either a reading, a status light or a button."),
        _TABLE(["Tile", "Meaning"], [
            ["TCI / AMP / LP", "Link status to Thetis, the amplifier and the LP-100A"],
            ["FWD / REF", "Amplifier forward and reflected power"],
            ["SWR", "SWR at the amplifier output"],
            ["DRV", "Drive power going into the amplifier. 'R' or '(radio)' means the figure "
                    "comes from Thetis because the amp reports 0 W in standby"],
            ["GAIN", "Forward power divided by drive, in dB (OPERATE only)"],
            ["TMP / V/A", "PA temperature, supply volts and amps"],
            ["AMP (frequency)", "The frequency the amp itself reports it is on. Green with a tick when it "
             "matches the radio; red with the radio frequency when it does not. \"sent\" means the amp does not "
             "report its frequency, so the panel shows what was sent to it"],
            ["RX", "Receive level from Thetis (dBm). Red when it is below the band's limit: no antenna? (see No antenna? check)"],
            ["DUMMY OK", "Lit when you have confirmed a dummy load on this band (see No antenna? check)"],
            ["FAN", "Current fan speed and your minimum fan speed. Press 0 to 5 to set the minimum (see Fan speed)"],
            ["FLT", "Fault code. Red when a fault is active"],
            ["OPR / STBY", "Operate and standby"],
            ["INL / BYP / TUNE / CNCL", "ATU inline, bypass, start tune, cancel tune"],
            ["A1 / A2 / NXT", "Antenna 1, antenna 2, next antenna"],
            ["SOT", "Standby-on-Tune switch"],
            ["ON / OFF / WOL", "Power on, power off, enable Wake-on-LAN in the amplifier"],
            ["LP PWR / LP SWR / ...", "LP-100A readings (appear once a port is set)"],
        ]),
        _WARN("Safety interlocks: ATU inline/bypass and antenna changes are refused while the "
              "radio, amplifier or LP-100A shows RF; this cannot be switched off. Power OFF is "
              "refused under RF too, unless you untick **Block power off while transmitting** "
              "(panel Settings, or key B) for emergency shutdown."),
        _P("**Customize the layout:** click **Settings** (top right). Drag tiles or use the arrows "
           "to reorder, the width button to make a tile wider, the x to hide a tile. Choose "
           "short or full labels, bars on or off, size, theme and title bar. The presets "
           "Full, Compact, Telemetry and Controls give quick starting points. **Save as...** "
           "keeps your own named layouts, and Export/Import copies one to another device."),
        _P("**Thetis look:** open `http://127.0.0.1:8080/?layout=Thetis` (or choose the preset "
           "**Thetis look**, or **Style: Thetis look** in Settings). The panel then shows the same two "
           "black windows as in Thetis - KPA1500 Telemetry with the blue bars and yellow peak band, "
           "and KPA1500 Controls with the lit buttons - and the buttons work right in the browser. "
           "Handy on a phone or tablet, or to try the look before setting up Thetis. If the bridge "
           "stops, the red BRIDGE NOT RUNNING line appears, just as in Thetis. **Size** in Settings "
           "makes it bigger or smaller."),
        _P("**Several windows:** open `http://127.0.0.1:8080/?layout=Compact` for a small "
           "window with just drive, output, SWR and Operate/Standby. Any layout name works "
           "(`?layout=Mine`)."),
        _P("**Small window beside Thetis:** start Edge as `msedge --app=http://127.0.0.1:8080/"
           "?layout=Compact`, size it, then press Win+Ctrl+T (PowerToys Always On Top) to keep it "
           "above Thetis."),
        _P("**From a phone, tablet or Mac:** answer Yes to network access in the installer (Step 6), or "
           "start the bridge with `--web-bind 0.0.0.0`, and browse to `http://PC-ADDRESS:8080`. A "
           "password is optional: with one, other devices see a password box (or use "
           "`http://PC-ADDRESS:8080/?t=yourpassword`)."),
        _P("**Panel password (Settings > Panel access):** the bridge computer itself never needs the "
           "password. There you can **Set password** or **Remove password** at any time - so a "
           "forgotten password is never a problem: open `http://127.0.0.1:8080` on the bridge computer "
           "and remove or change it. A password set or removed in the panel wins over `--web-token` in "
           "the start file."),
    ]))
    S.append(("window", "6. The bridge window", [
        _P("The window shows one status line that updates twice a second, for example:"),
        _CODE("TCI:ok AMP:ok | 14.025 MHz | OPERATE ATU:I ANT:1 | Fwd 0W SWR 1.0 | Drive 0W | 31 C | Fault --"),
        _P("Important events (frequency sent, tune started, faults, button presses) appear as "
           "time-stamped lines above it. The revision number is on the first line."),
        _P("Click inside the window and press a key:"),
        _TABLE(["Key", "Action"], [
            ["H", "Show the key list"], ["W", "Open this full help in your browser"],
            ["I", "Read the help in this window, topic by topic"],
            ["O", "Operate / Standby toggle"], ["A", "ATU inline / bypass toggle"],
            ["N", "Antenna 1 / 2 toggle"], ["C", "Clear the amplifier fault"],
            ["F", "Set the minimum fan speed (0 to 5)"], ["+ / -", "Raise / lower the minimum fan speed by one"],
            ["D", "Search the network for the amplifier and choose it"],
            ["S", "Standby-on-Tune on / off"], ["L", "Change the LP-100A COM port"],
            ["Y", "'Ask before Power OFF' on / off"], ["G", "Log file on / off"],
            ["K", "'Allow Thetis to power off the amp' yes / no"],
            ["B", "'Block power off while transmitting' on / off"],
            ["P", "Power the amplifier ON"], ["X", "Power the amplifier OFF"],
            ["V", "Show the version"], ["Q", "Quit the bridge"],
        ]),
    ]))
    S.append(("tune", "7. Standby on Tune", [
        _P("When you press TUNE in Thetis, the bridge puts the amplifier in STANDBY. When TUNE "
           "ends it puts the amplifier back as it was: OPERATE returns to OPERATE, and an "
           "amplifier that was already in STANDBY stays there. Each step is read back and "
           "confirmed in the window."),
        _UL("Switch it on or off with the **SOT** tile, the **S** key, or `--no-standby-on-tune`.",
            "If the connection to Thetis drops during a tune, the amplifier is left in STANDBY "
            "on purpose (fail-safe). Set OPERATE yourself afterwards."),
        _WARN("With Thetis' own TUNE button, the standby command is sent when Thetis announces TUNE. "
              "A few milliseconds of RF can reach the amplifier first. Use the bridge **TUNE** button "
              "below to avoid that, keep tune power low, and keep your usual hardware protection."),
        _P("**The bridge TUNE button (recommended)** - in the Thetis Controls window, the browser "
           "panel, or key **T** in the bridge window. It does things in the safe order:"),
        _OL("Checks: Thetis is connected, nothing is transmitting, and no 'no antenna?' warning is "
            "showing (press DUMMY OK first when a dummy load is connected).",
            "With Standby-on-Tune on and the amp in OPERATE: puts the amp in STANDBY and reads it "
            "back. If STANDBY is not confirmed, nothing is keyed and the reason is shown.",
            "Waits 0.1 s for the amp's relays, then tells Thetis to TUNE.",
            "The button lights and reads **STOP TUNE** (the panel also shows the seconds left). "
            "Press it to stop, or stop TUNE in Thetis.",
            "When the tune ends the amp goes back to OPERATE if it was in OPERATE (or stays in "
            "STANDBY if the 'no antenna?' hold applies)."),
        _P("**Auto-stop:** a tune started with the bridge TUNE button stops by itself after 20 s "
           "(change it in Settings > Safety; 0 = never). The bridge never changes the tune power: "
           "set it in Thetis as usual. With Standby-on-Tune off, TUNE leaves the amp as it is."),
    ]))
    S.append(("noant", "No antenna? check (receive level)", [
        _P("With no antenna connected (antenna switch in the wrong place, a cable off, a relay "
           "fault) the receiver hears almost nothing: on a typical setup about -119 dBm, while a real "
           "antenna on 80 m shows -78 dBm or more of band noise. The bridge watches the receive level "
           "that Thetis reports and warns you **before** you transmit into nothing."),
        _UL("Thetis sends its **average signal** level of RX1 over TCI. The bridge takes the middle "
            "value of the last 2.5 seconds of receive, ignores the first 1.5 seconds after a band "
            "change or after transmitting, and ignores everything while transmitting (the "
            "verdict from just before key-up is kept).",
            "If Thetis is not running, or it sends no level, the check does nothing and shows "
            "\"no level from Thetis\" in Settings. It never warns without a live reading.",
            "Each band has its own **limit**. Below the limit means \"no antenna?\". The warning "
            "clears when the level is 3 dB above the limit again."),
        _TABLE(["Band (m)", "Default limit"], [
            ["160, 80, 60, 40", "-105 dBm"], ["30, 20", "-112 dBm"],
            ["17, 15, 12, 10", "-115 dBm (quiet high bands read low even with a good antenna)"],
            ["6", "off (no check)"]]),
        _P("**What you see when the level is too low:**"),
        _UL("**Browser panel:** an orange bar across the top: NO ANTENNA? with the level, the band "
            "and the limit, and a **DUMMY OK** button. The **RX** tile turns red.",
            "**Thetis windows:** a red line near the bottom of both windows, for example "
            "`ANTENNA? RX -119 dBm (40m limit -105)`. The green AMP line also shows the receive level.",
            "**Bridge window:** the status line ends with `RX -119 ANTENNA?`, and the log says why.",
            "**If you transmit anyway:** the bar turns red and flashes, the Thetis line changes to "
            "`!! TX - NO ANTENNA? CHECK DUMMY LOAD !!`, and the bridge window beeps and logs a warning."),
        _P("**DUMMY OK** (panel button, Thetis Controls button, key **M**): press it when a dummy load "
           "is connected on purpose. The warning is silenced for that band. DUMMY OK switches itself "
           "off as soon as a normal receive level comes back (antenna reconnected), so it can never be "
           "left on by mistake. Press it again to undo."),
        _P("**Keep the amp in STANDBY** (optional): in Settings choose **Warn and keep the amp in "
           "STANDBY**. While the warning shows, the bridge puts the amplifier in STANDBY and refuses "
           "OPERATE. The radio can still transmit at low power straight through the amp. Pressing "
           "DUMMY OK, or a normal receive level returning, puts the amp back in OPERATE. The bridge "
           "never switches the amp while RF is present."),
        _P("**Settings** (browser panel > Settings > No antenna? check, or key **R** in the bridge "
           "window): switch the check on or off, choose warn only or keep STANDBY, type a limit for "
           "each band (empty = no check on that band), or **Learn this band**: disconnect the antenna "
           "(or switch the radio to no antenna), wait 3 seconds, press Learn. The limit becomes the "
           "measured level + 6 dB. **Default limits** puts them all back. Everything is saved in "
           "kpa1500_settings.json and kept when you update."),
        _NOTE("Things that lower the receive level and can give a false warning: the receive "
              "attenuator (ATT / step attenuator), preamp off on the high bands, a very narrow filter, "
              "a small receive antenna, or a dead band at night on 10-17 m. Use Learn or set a lower "
              "limit for that band. This check is a reminder, not a protection device: keep the "
              "amplifier's own SWR protection and your usual care."),
    ]))
    S.append(("drive", "Over-drive protection (drive limit)", [
        _P("Too much drive into the amplifier can damage it. This protection watches the drive going **into** "
           "the KPA1500 and acts when it is over a limit you set. It helps; it does not replace care. The "
           "amplifier's own protection stays the last line of defence."),
        _TABLE(["Setting", "Meaning"], [
            ["Limit (W)", "One overall limit for the drive into the amplifier. Empty, 0 or off = protection off."],
            ["If it goes over", "**Ignore** does nothing. **Warn** shows a red message (panel bar, Applet banner, "
             "status line, log) and changes nothing. **Hold at the limit** gives the same warning AND puts the "
             "radio's RF power setting back to the limit, so it is fixed before you transmit. If the measured drive "
             "still stays over the limit for about 1.2 s more, the amp is put in STANDBY and stays there until you "
             "lower the drive and press OPERATE."],
            ["Radio full power (W)", "The radio's RF power setting is a percent of its full power. Default 100 "
             "(most FlexRadios). The setting is turned into watts with this number."]]),
        _P("**Where to set it:** browser panel > Settings > Over-drive protection, or the Applet window > Look > "
           "Safety: over-drive protection. A new install starts with **Warn** and no limit, so nothing happens "
           "until you type a number."),
        _UL("The radio's RF power setting is read from the FlexRadio **before** you transmit, so a setting that is "
            "too high is caught before you key up. The measured drive is also watched while transmitting.",
            "The limit is **ignored while the amp is in STANDBY** (so you can tune the amp's ATU with full radio "
            "power) and while the amp's own ATU is tuning.",
            "Only the amp's own input-power reading is judged. Short peaks (under 0.8 s) are ignored, and the "
            "measured drive must be 10 % + 1 W over the limit before it counts: that margin is on purpose.",
            "Hold at the limit never changes the radio setting more than once every 1.5 s, so it does not fight "
            "SmartSDR or you.",
            "The TUNE power of the radio is not changed. A tune through the amp in OPERATE is still judged by the "
            "measured drive.")
    ]))
    S.append(("atu", "8. Tuning the amplifier's ATU", [
        _OL("Set the radio to the frequency you want and its power low.",
            "Press **ATU TUNE** (panel), or send `KPA_ATU_TUNE` from a Thetis button.",
            "Press **TUNE** in Thetis. That gives the amplifier a carrier to tune on.",
            "Release TUNE when the amplifier finishes. **Cancel tune** stops it early."),
        _P("The bridge starts the amplifier's own tuning only. It never keys the transmitter."),
    ]))
    S.append(("fan", "Fan speed", [
        _P("The amplifier's fans normally stay off (speed 0) and speed up as the heat sink warms. "
           "You can set a **minimum fan speed** from 0 to 5 so the fans never run slower than that, "
           "for example to keep the amplifier cooler during long digital sessions."),
        _TABLE(["Speed", "Meaning"], [
            ["0", "Automatic: fans off until the amplifier needs them (the normal setting)"],
            ["1 to 4", "Fans always run at least this fast; they still speed up if the amplifier heats up"],
            ["5", "All fans at the highest speed, always"],
        ]),
        _P("The **FAN** tile shows two numbers: the speed the fans are running now, and your minimum, "
           "for example `2 / min 1`. The current speed can be higher than your minimum because of "
           "temperature. To change the minimum:"),
        _UL("Panel: press **0** to **5** on the FAN tile.",
            "Bridge window: press **F** and type a number, or press **+** or **-** to step up or down.",
            "Thetis button: send `KPA_FAN_0` to `KPA_FAN_5`, `KPA_FAN_UP` or `KPA_FAN_DOWN`."),
        _NOTE("Fan changes are allowed at any time, including while transmitting. They are read "
              "back from the amplifier to confirm. Reading the fan speed needs firmware 01.47 or "
              "newer. The amplifier also has a fan dwell time (menu FAN SPEED DWELL) that stops the "
              "fans changing speed too quickly; the bridge does not change it."),
    ]))
    S.append(("lp100", "9. The LP-100A power meter", [
        _OL("Connect the meter to the PC by USB. In Device Manager > Ports note its COM number.",
            "Install the serial add-on once: `py -m pip install pyserial`.",
            "In the panel click **Settings**, type the port (for example COM5) in the "
            "**LP-100A port** box, and press **Connect**. Or press **L** in the bridge window.",
            "Leave the meter on its **Watts** screen, or no data is sent."),
        _UL("Baud rate: 115200 (use 38400 for LP-100A firmware older than 1.2.0.0).",
            "You can change the port at any time without restarting. The choice is remembered.",
            "**Disconnect** turns it off. The Alarm and Mode tiles press the meter's own buttons.",
            "First-time check: start with `--lp100-debug` to log the raw data the meter sends."),
        _P("The LP-100A shows the real antenna values: true power, SWR, reflected power, return "
           "loss and impedance. The amplifier's own readings sit beside them for comparison."),
    ]))
    S.append(("knob", "FlexControl tuning knob", [
        _P("The FlexRadio **FlexControl** (FlexKnob) is a USB tuning knob with a push switch and three "
           "buttons. The bridge reads it directly and controls Thetis through the same TCI link it already "
           "uses - no DDUtil and no virtual serial ports needed. It works with or without the amplifier."),
        _OL("Plug the knob in. If DDUtil (or another program) uses it, remove it there or close that "
            "program - only one program can use the knob.",
            "In the browser panel open **Settings > FlexControl tuning knob**. With **Find it automatically** "
            "the bridge finds the knob by its USB id; or choose a COM port yourself.",
            "The status line says 'Knob connected on COMx'. Press a button: 'last:' shows what arrived "
            "and that row lights up.",
            "Choose a function for each press, or keep the defaults. **Try** runs a function as if you "
            "pressed it."),
        _P("**Turning the knob** does what the knob's mode says. A press can switch the mode; the LEDs show "
           "it. Modes: " + "; ".join("**%s** (LEDs %s)" % (v[0], v[1]) for v in KNOB_MODES.values()) + ". "
           "VFO and RIT/XIT use Thetis' own tuning step; spun fast, the VFO moves faster (**Fast spin**). "
           "**Back to VFO A after** returns to VFO tuning by itself when the knob is not touched."),
        _TABLE(["Press", "Default function"], [[n, KNOB_ACTION_MAP[KNOB_DEFAULT_TABLE[e]][1]] for e, n in KNOB_EVENTS]),
        _P("**All functions:** " + "; ".join(a_[1] for a_ in KNOB_ACTIONS if a_[0] not in ("none", "custom")) + "."),
        _P("**Custom command:** choose 'Custom command' and type a Thetis CAT command (e.g. `ZZMA1;` = mute on, "
           "`ZZTU1;` = TUNE on) or a TCI command (e.g. `mute:true;`). Thetis' CAT command list is in its "
           "Setup > CAT Control help."),
        _P("**KPA1500 Knob window in Thetis:** a third Thetis window shows, at a glance, what the knob does: "
           "`KNOB: AF volume (master)` and one short line each for the knob press and buttons 1-3, for example "
           "`B1  tap >AF   2x >AGC   hold Mute` (`>AF` = the press switches the knob to AF volume; 2x = double "
           "tap; hold = long press). The lines change as the mode changes. Choose its title (`{ver}` = bridge "
           "version), its lines and their order, or switch it off, under **Settings > Thetis windows > Knob "
           "window**, then press **Rebuild Thetis windows**. The panel's Thetis look shows it too."),
        _NOTE("The CAT functions use Thetis' TCI command `run_cat_ex`. If Settings says 'Thetis does not run CAT "
              "commands over TCI', update Thetis. MOX on a knob button really transmits; it is refused while "
              "the 'no antenna?' warning shows."),
    ]))
    S.append(("poweron", "10. Powering the amplifier on remotely", [
        _P("A sleeping KPA1500 cannot be woken by an ordinary command. The bridge sends a "
           "Wake-on-LAN packet and then asks the amplifier to switch on."),
        _OL("In the amplifier menu set **NET WAKE on LAN** to ON, or press **Enable Wake-on-LAN** "
            "in the panel while the amplifier is awake.",
            "Run the bridge once while the amplifier is on. It learns the amplifier's MAC address "
            "and saves it. (Or give it with `--amp-mac`.)",
            "Press **ON** in the panel, **P** in the window, or send `KPA_POWER_ON`."),
        _P("The result appears in the window and in the log. If it fails, check the NET WAKE on "
           "LAN setting, the MAC address, and that the PC and amplifier are on the same network."),
    ]))
    S.append(("versions", "Thetis, Thetis HL2 and SDR-VST3", [
        _P("The bridge works with three versions of Thetis, one running at a time (they all use TCI "
           "port 50001 and the same radio): **Thetis**, **Thetis HL2** (MI0BOT's version for the "
           "Hermes Lite 2) and **SDR-VST3** (a Thetis version with VST plugin hosting). Nothing in the "
           "bridge has to be changed to switch between them: it connects to whichever one is running."),
        _P("**Getting each program ready (once)**"),
        _OL("Start the program the usual way. **Thetis HL2: always use its own shortcut.** It starts "
            "Thetis with `-dbid:HL2`, which keeps its settings separate from your normal Thetis.",
            "Open **Setup > Serial/Network/Midi CAT**, **Network** tab, **TCI Server** box: Bind IP:Port "
            "`127.0.0.1:50001` and tick **TCI Server Running**. Leave the other boxes as they are.",
            "Click **Apply**, then **OK**, and close the program normally (File > Exit) so it saves."),
        _P("The installer and `Setup_Thetis_Containers.bat` check this and print a note when the TCI "
           "server is switched off."),
        _P("**The KPA1500 windows in each program**"),
        _UL("`Setup_Thetis_Containers.bat` asks which program(s) to set up when more than one is "
            "installed: type a number, several like `1,3`, or `A` for all of them.",
            "Each program gets its own backup: `thetis_backups` (Thetis), `thetis_backups\\Thetis-HL2` and "
            "`thetis_backups\\SDR-VST3`. `Undo_Thetis_Containers.bat` also asks which program.",
            "SDR-VST3 keeps the windows in a newer format than Thetis. The setup writes that format "
            "for it automatically; nothing is different for you.",
            "From a command prompt: `py kpa1500_thetis_setup.py --program vst3` (or `thetis`, `hl2`, "
            "`thetis,hl2`, `all`)."),
        _P("**Where they live**"),
        _UL(r"Thetis: `C:\Program Files\OpenHPSDR\Thetis`, settings in `%APPDATA%\OpenHPSDR\Thetis-x64`",
            r"Thetis HL2: `C:\Program Files\OpenHPSDR\Thetis-HL2`, settings in the same `Thetis-x64\DB` "
            r"folder, as a separate database (`HL2_dbman_settings.json`)",
            r"SDR-VST3: `C:\Program Files\OpenHPSDR\SDR-VST3`, settings in `%APPDATA%\OpenHPSDR\SDR-VST3-x64`"),
        _NOTE("All three run as **Thetis.exe**, also in Task Manager. The setup and the installer tell "
              "them apart by their folders and close only the one being changed (always the normal way, "
              "never forced). Close them yourself with File > Exit too: a program ended in Task Manager "
              "does not save, and can leave the radio or the sound device stuck until the radio is "
              "switched off and on or the PC is restarted."),
        _NOTE(r"Before updating or adding a Thetis version, copy the folder `%APPDATA%\OpenHPSDR` "
              r"somewhere safe (for example `C:\RadioScripts\Thetis_Backups`). It holds the settings of all of them."),
    ]))
    S.append(("nereus", "NereusSDR settings and the Applet window", [
        _P("This version works with Thetis **or** NereusSDR, one at a time. By default it finds out "
           "which one is running (it asks Thetis a CAT question over TCI; if that is not answered it "
           "tries NereusSDR's CAT port). You can choose one under **Radio program** in the Applet's "
           "Look window, or start the bridge with `--radio thetis` or `--radio nereus`."),
        _P("**What the bridge uses in NereusSDR**"),
        _TABLE(["Connection", "Port", "Used for"], [
            ["TCI server", "50001", "Frequency, transmit state, power and SWR, receive level, drive. Always needed."],
            ["TCP/IP CAT (CAT 1)", "13013", "The FlexControl knob and the TUNE button. Needed for those two."],
            ["UDP data (optional)", "50110", "Readings sent to NereusSDR containers. Not available in every NereusSDR build."],
        ]),
        _P("**NereusSDR settings, step by step (once).** Everything is under **File > Settings... > "
           "CAT & Network**. Do these in NereusSDR, then start the bridge."),
        _OL("**TCI Server page.** Tick **Enable TCI Server**. **Listen on:** `127.0.0.1`. **Port:** `50001`. "
            "The **Status** line should say it is listening. Leave the Compatibility, VFO Quirks, IQ Stream "
            "and Sensors groups at their defaults (the bridge switches on the sensors it needs by itself). "
            "Only one program can use port 50001: close Thetis, or any other program that uses TCI, first.",
            "**TCP/IP CAT page, switch on.** Tick **Enable TCP CAT**. For channel **CAT 1** set **Listen on:** "
            "`127.0.0.1` and **Port:** `13013`.",
            "**TCP/IP CAT page, bind the slice (important).** For CAT 1 set **VFO A:** to **Slice A** (NereusSDR "
            "may list it as Slice ID 0). Leave **VFO B:** empty. Without this binding NereusSDR answers `?;` to "
            "the knob and TUNE commands and they do nothing.",
            "**Keep CAT 1 for the bridge.** If another program (a logger, WSJT-X) needs CAT, give it CAT 2, 3 or 4 "
            "or rigctld. Leave **CAT Options** at their defaults.",
            "**Transmit permission.** TUNE from the Applet or the knob keys the radio through CAT, which "
            "follows NereusSDR's normal transmit rules. This NereusSDR window must hold the station's "
            "transmit control (TXcontrol). If TUNE is refused, NereusSDR shows the reason and the bridge log says "
            "'TUNE refused'. Changing CAT settings cannot grant ownership.",
            "**Start the bridge.** Within about 10 seconds its window says 'NereusSDR answers CAT commands' "
            "and the Applet's top line shows NereusSDR."),
        _P("**Testing the CAT link without the bridge:** in NereusSDR open **CAT Options > CAT Tester**, "
           "choose CAT 1, send `ZZVN;`. You should get a version back. A reply of `?;` means VFO A is not bound "
           "to Slice A (step 3). No reply means TCP CAT is off or the port is different."),
        _P("**Good to know.** NereusSDR closes a CAT connection that stays silent for about 30 seconds; the "
           "bridge sends a small keep-alive every 10 seconds, so you do not need to do anything. TUNE uses "
           "the CAT command `ZZTU1;` (off: `ZZTU0;`), because NereusSDR's TCI has no tune command. "
           "Frequency, mode and band changes in NereusSDR reach the amplifier through TCI."),
        _P("**The Applet window** is a small window with the amplifier meters, control buttons, the knob "
           "lines and the LP-100A. It opens with `--applet`, with `Open_Applet.bat`, or in any browser at "
           "`http://127.0.0.1:8080/applet`. It is the same for Thetis and NereusSDR."),
        _UL("**Top line:** the radio program found, the frequency, the **Operate / Standby** button and the "
            "amplifier **Power on / off** button (each can be hidden under **Top line: show**). The version number is shown next to the title.",
            "**Sections:** Telemetry, Controls, FlexControl knob and LP-100A. Choose which to show, and their "
            "order, under **Look > Sections: show and order** (arrows move, a tick shows or hides).",
            "**Look** (the pencil button): **Theme**, **Colours**, **Size and spacing** (text size, columns, bar "
            "height, corner radius, spacing, zoom %), **Top line: show**, **Meters** and **Buttons** (which are "
            "shown and in what order), **Window title** and **Resize window**. **Shrink to fit the window "
            "height** (and the zoom box) make the whole Applet fit a small window or a small part of the "
            "screen; you can also just drag the window larger or smaller.",
            "**No-antenna protection:** under **Look > Safety: no-antenna check** choose 'Only warn', 'Warn and "
            "put the amp in STANDBY' or 'Refuse TUNE and warn'. It is the same setting as in the full panel. The limit "
            "for each band is set in the full panel (**Panel** button, Settings). With NereusSDR press "
            "**Learn this band** there: disconnect the antenna (or switch the radio to no antenna), wait 3 seconds, "
            "press Learn. Do it once per band.",
            "**Look > Bridge > Quit bridge** closes the bridge and its windows (only on the bridge computer). "
            "**Share or restore a look** copies the look as text, or loads one.",
            "The look is saved by the bridge in `kpa1500_settings.json` and comes back at every start."),
        _P("**The FlexControl knob** works with NereusSDR as in {sec:knob}. If the knob lines show `?;` or "
           "nothing happens, check step 3 above. The knob needs the TCP/IP CAT link; the amplifier functions do not."),
        _P("**Telemetry inside NereusSDR containers (optional):** the bridge also sends every reading as JSON "
           "over UDP to port 50110 (`--nereus-mmio-port`; 0 = off). NereusSDR's containers cannot send button "
           "clicks back, which is why the buttons are in the Applet. In some NereusSDR builds the **Meter Data "
           "Sources (MMIO)** button is switched off while a container is being edited, so a new data source cannot "
           "be added there yet. The Applet does not need it."),
        _P("**Starting a new bridge** closes one that is already running (this program or the older "
           "Thetis-only bridge): `--replace`. `--stop-running` closes it and exits; `Stop_Bridge.bat` does the "
           "same and also closes its window."),
        _NOTE("The no-antenna check uses the receive level the radio program reports. Its per-band limits were "
              "chosen for Thetis; with NereusSDR use **Learn this band** once per band (antenna disconnected, wait 3 seconds)."),
    ]))
    S.append(("containers", "11. The Thetis windows (meters and buttons)", [
        _P("The package includes two ready-made Thetis windows, called **containers**. They float "
           "on top of Thetis; drag them wherever you like or dock them into the Thetis screen."),
        _IMG("thetis_overview", "Thetis with the two KPA1500 windows (right): Controls on top, Telemetry below."),
        _P("**Put them into Thetis (one double-click):**"),
        _OL("Make sure the bridge is installed (the installer does this).",
            "Thetis must be closed while the windows are added, because it saves its own settings when "
            "it closes. If it is running, the setup offers to **close it for you** (the normal way, like "
            "File > Exit, so nothing is lost) and afterwards offers to **start it again**.",
            r"Open the bridge folder (normally `C:\RadioScripts\KPA1500_SDR_Bridge`) and double-click "
            "**Setup_Thetis_Containers.bat**.",
            "A black window shows what it found. Answer the questions: press **Enter** to accept the "
            "answer in brackets. It asks whether you use an LP-100A, then whether to make the changes.",
            "When it says **Done**, press a key to close the window.",
            "Start the bridge (if it is not running), then start Thetis. The two windows appear."),
        _P("What the setup does for you:"),
        _UL("Saves a **backup** of your Thetis settings first (folder `thetis_backups` next to the bridge).",
            "Makes the two **Multi Meter I/O** entries the bridge needs, if they are missing: "
            "readings in on 127.0.0.1:50100 and button presses out to 127.0.0.1:50101. If you already "
            "made them, it uses yours.",
            "Adds (or updates) the **KPA1500 Telemetry** and **KPA1500 Controls** windows. Running it "
            "again later updates them and keeps them where you put them."),
        _NOTE("To undo: double-click **Undo_Thetis_Containers.bat** (it offers to close Thetis for you). "
              "It puts back the settings saved just before the last setup."),
        _P("**KPA1500 Controls**"),
        _IMG("thetis_controls", "The Controls window. Blue (lit) buttons mean that function is ON."),
        _P("A lit (blue) button means that function is on, and its label shows the current state. "
           "When the amplifier is ready to go, **the whole top row is lit**: OPERATE, ATU IN, ANT 1, AMP ON. "
           "The second row keeps everything about tuning together: TUNE, ATU TUNE, SoT and DUMMY OK. "
           "Pressing a button sends a command to the bridge; the bridge applies its usual safety checks."),
        _TABLE(["Button", "Lit when", "Pressing it"], [
            ["OPERATE / STANDBY", "the amp is in OPERATE", "switches to the other mode"],
            ["ATU IN / ATU BYP", "the ATU is inline", "switches inline / bypass (refused while transmitting)"],
            ["ANT 1 / ANT 2", "antenna 1 is selected", "switches to the other antenna (refused while transmitting)"],
            ["AMP ON / AMP OFF", "the amp is switched on and answering",
             "lit: **switches the amp OFF at once** (no question asked); dark: wakes the amp (about 15 s)"],
            ["TUNE / STOP TUNE", "the radio is tuning",
             "starts the radio's tune the safe way (amp STANDBY first, confirmed) / stops it. "
             "Stops by itself after 20 s"],
            ["ATU TUNE / STOP ATU", "the amp's ATU is tuning",
             "starts the amp's ATU tune (then press TUNE at low power), or stops it"],
            ["SoT ON / SoT OFF", "Standby-on-Tune is on", "turns Standby-on-Tune off / on"],
            ["DUMMY OK", "you confirmed a dummy load on this band", "silences the 'no antenna?' warning on this band / undoes it"],
            ["NO FAULT / FAULT - CLR", "the amp reports a fault", "clears the fault"],
            ["LP ALARM, LP MODE", "-", "step through the LP-100A alarm and display settings"],
            ["FAN - / FAN +", "-", "lower / raise the amp's minimum fan speed (shown on the status line)"],
        ]),
        _P("**Your own layout:** in the browser panel open **Settings > Thetis windows**. For the "
           "**Telemetry window** choose which lines and bars it shows and in which order (status line, "
           "AMP frequency line, forward / SWR / drive bars, the text lines, the LP-100A bars and line, a "
           "**Title line** and blank lines). For the **Controls window** (it has a **Title line** item too) move buttons with the arrows, take "
           "out the ones you never use (x), put them back (+), add a blank space, and choose 3 to 6 columns. "
           "Each window has a **Title** you can type, for example `KW4EX {ver} Amp` - `{ver}` shows the "
           "bridge version (if the Telemetry title shows it, the AMP line leaves it out). "
           "The panel's Thetis look shows the result at once. "
           "To put it into Thetis press **Rebuild Thetis windows**: the setup window offers to close "
           "Thetis for you, makes a backup, rebuilds both windows (they keep their place) and offers to "
           "start Thetis again. Double-clicking **Setup_Thetis_Containers.bat** does the same. "
           "**Standard order** puts the layout above back."),
        _P("The line under the title shows the amp power, mode, fan speed (current and minimum) and fault."),
        _P("**No antenna? line** (red, near the bottom of both windows, blank when all is well): shows "
           "`ANTENNA? RX -119 dBm (40m limit -105)` when the receive level is too low, and "
           "`!! TX - NO ANTENNA? CHECK DUMMY LOAD !!` if you transmit anyway. See the section "
           "**No antenna? check**. The receive level itself is on the green AMP line."),
        _P("**Amp frequency line** (green, in both windows), for example `AMP  14.025 MHz  RX -78 dBm  v2.23`: the "
           "frequency the amplifier itself reports it is on, read back from the amp after every VFO change. "
           "Turn the VFO and watch it follow. Nothing extra is shown while the amp is on the radio "
           "frequency; `radio 7.150 !` means it is NOT (it shows where the radio is). The Telemetry line "
           "ends with the bridge version, and the Controls title shows it too (`KPA1500 v2.23 Controls`). `(sent)` means the amp does not "
           "report its frequency, so the line shows what the bridge sent. Thetis buttons cannot show "
           "changing text, so this is a text line rather than a button. If the windows were set up before "
           "this line existed, run **Setup_Thetis_Containers.bat** again (Thetis closed) to add it, and "
           "make the windows a little taller if the bottom is cut off."),
        _P("**KPA1500 Telemetry**"),
        _IMG("thetis_telemetry", "The Telemetry window while receiving (bars are at zero)."),
        _UL("**Top line**: amp power, mode, ATU and antenna. Under it, the green amp frequency line.",
            "**Bars**: KPA1500 forward power, KPA1500 SWR, drive power, LP-100A power and LP-100A SWR. "
            "The live reading is a **blue** bar that turns **red** past the limit (1500 W, or SWR 2.0).",
            "**Peak hold**: a **yellow** band beyond the blue bar shows the highest reading of the last "
            "4 seconds, with a red line at its end and the peak value on the right. On a steady carrier "
            "(TUNE) the peak equals the live reading, so there is no yellow band.",
            "**Text lines**: reflected power, gain, where the drive figure comes from; PA temperature, "
            "volts, amps and fan; fault and Standby-on-Tune; LP-100A R, X, |Z| and return loss.",
            "SWR reads 1.0 when there is no RF (the amp keeps its last SWR otherwise)."),
        _WARN("If the bridge stops, a red line **BRIDGE NOT RUNNING - data frozen** appears at the bottom "
              "of both windows within about 5 seconds, and the Controls buttons go dark. Readings shown "
              "are then old and the buttons do nothing. Start the bridge again and everything comes back. "
              "While all is well that bottom line is simply blank."),
        _P("**Safety options for the AMP button** are in the browser panel under **Settings** (or keys K and B "
           "in the bridge window): **Allow Thetis to power off the amp** and **Block power off while "
           "transmitting**. Untick the second one only if you want an emergency power-off to work even "
           "while the radio is stuck in transmit."),
        _P("**Changing the look:** Thetis lets you change colours, fonts and sizes in Setup > Appearance > "
           "Meters/Gadgets. Running the setup again resets the two windows to the standard design. "
           "Save your own version first with the container **Save** button there if you change them."),
    ]))
    S.append(("thetis", "12. Setting up Thetis by hand (advanced)", [
        _P("You do not need this section if you used **Setup_Thetis_Containers.bat**: it makes the "
           "entries below for you. It is here for building your own containers."),
        _P("Thetis can show outside data in a container (a small window of meters and buttons) "
           "using **Multi Meter I/O**. Set up two entries once."),
        _P("**Entry 1 - readings into Thetis.** In Thetis open Setup > Serial/Network/Midi CAT > "
           "Multi Meter I/O, click **Add UDP**, select the new entry and set:"),
        _TABLE(["Setting", "Enter"], [
            ["Direction", "In"], ["Format (in)", "XML"], ["Terminator (in)", "None"],
            ["Bind IP:Port", "127.0.0.1:50100"], ["Active / Enabled", "tick both, then Apply"]]),
        _P("**Entry 2 - button presses out of Thetis** (for the buttons in the next section). "
           "Click **Add UDP** again and set:"),
        _TABLE(["Setting", "Enter"], [
            ["Direction", "Out"], ["Format (out)", "Raw"], ["Terminator (out)", "None"],
            ["UDP Endpoint IP:Port", "127.0.0.1:50101"],
            ["Active / Enabled", "tick both, then Apply"]]),
        _P("Start the bridge with these flags (they are already in `start_kpa_sdr_bridge.bat`):"),
        _CODE("--mmio-port 50100 --mmio-format xml --mmio-listen 50101"),
        _P("Select the In entry in Thetis: its **Variables** list should fill with the values "
           "below. Each name starts with four letters Thetis gives that entry (the **4Char ID**, "
           "for example `tatg`), so you will see names like `tatg.amp_fwd`."),
        _TABLE(["Variable", "Meaning"], var_rows),
        _P("**Build a display.** Open Setup > Appearance > Meters/Gadgets, click **Add Container**, "
           "choose **Text Overlay** in the list and click the right arrow to add it. In its "
           "**RX Text** and **TX Text** boxes type words and insert variables with the **%** "
           "button (it opens a picker and copies the name; paste it with Ctrl+V). For example:"),
        _CODE("""
FWD %tatg.amp_fwd% W   DRV %tatg.amp_drive% W
%tatg.amp_mode%   ATU %tatg.amp_atu%   ANT %tatg.amp_ant%
SWR %tatg.amp_swr%   TMP %tatg.amp_temp% C   FLT %tatg.amp_fault_text%
"""),
        _P("Use one Text Overlay item per line. Use the arrows beside the item list to reorder "
           "them. A **Led Indicator** item can show a warning, for example with the condition "
           "`%tatg.amp_swr% > 2.0`. Copy the TX text into the TX Text box too."),
        _P("**Amplifier power:** `%tatg.amp_mode%` shows **OFF** when the amplifier stops answering "
           "(switched off or lost power) and **NO LINK** if it has never answered at the address. "
           "OFF is also shown at start-up if the amplifier was seen at this address on an earlier run. "
           "`%tatg.amp_power%` shows ON, OFF or NO LINK on its own. The browser panel shows a green or "
           "red AMP badge at the top and a red banner while the amplifier is not answering."),
        _NOTE("If a new container does not show, click **Recover Container**, tick **Auto height** "
              "so it grows to fit its items, and check the Show RX / Show TX boxes."),
    ]))
    S.append(("buttons", "13. Thetis button strings (for container buttons)", [
        _P("The ready-made Controls window already uses these. They are listed here for building "
           "your own buttons."),
        _P("A Thetis container can hold buttons that send a short text to the bridge. Each text "
           "below makes the bridge do one thing, using the same safety checks as the panel. "
           "Type the text exactly as shown, in capitals."),
        _TABLE(["String to send", "What the bridge does"], cmd_rows),
        _P("**Add a button to a container.**"),
        _OL("In Setup > Appearance > Meters/Gadgets select your container, choose **Other Buttons** "
            "in the item list and click the right arrow.",
            "Make the container tall enough to show it: tick **Auto height**, or drag the "
            "container's bottom edge. Put the Other Buttons item where you want it with the "
            "up/down arrows.",
            "In the Other Buttons panel scroll the checkbox list to the **macro** buttons, tick "
            "one, and click **Apply**. A button appears in the container.",
            "**Right-click the button** to open its setup (per the Thetis release notes). Choose "
            "the action that **sends an MMIO string**, pick the **Out** entry you made "
            "(127.0.0.1:50101), give the button a label such as ATU, and type the string, for "
            "example `KPA_ATU_TOGGLE`.",
            "Repeat for each button you want. Good starting set: `KPA_OPERATE_TOGGLE`, "
            "`KPA_ATU_TOGGLE`, `KPA_ATU_TUNE`, `KPA_ANT_TOGGLE`, `KPA_CLEAR_FAULT`."),
        _NOTE("The Thetis button setup screens may be worded differently from this description. "
              "What matters is: the action is 'send MMIO string', the target is the Out entry "
              "with 127.0.0.1:50101, and the text is one of the strings above."),
        _P("**Test a button:** run `py kpa1500_sdr_bridge.py --dry-run --mmio-listen 50101 "
           "--verbose`, press the button, and watch the window. It shows what Thetis sent. A "
           "line saying 'no KPA_ command' means the text in the button is wrong. "
           "`KPA_POWER_OFF` switches the amplifier off at once, without asking first, so it can "
           "be used as a fast shutdown. Two options control it (panel Settings, or keys "
           "K and B in the bridge window): **Allow Thetis to power off the amp** (on by default) "
           "and **Block power off while transmitting** (on by default). Turn the second one off "
           "if you want an emergency shutdown to work even while the radio is stuck in transmit."),
    ]))
    S.append(("customize", "13. Customizing", [
        _P("**Startup flags.** Open `start_kpa_sdr_bridge.bat` in Notepad and edit the "
           "`BRIDGE_FLAGS` line. Save it, close the bridge window and run the file again. "
           "Common changes:"),
        _TABLE(["To do this", "Add this to BRIDGE_FLAGS"], [
            ["Use a different amplifier address", "`--amp-ip 192.168.0.200`"],
            ["Find the amplifier by itself at every start", "`--amp-ip auto`"],
            ["Start with Standby-on-Tune off", "`--no-standby-on-tune`"],
            ["Test safely (nothing is sent to the amp)", "`--dry-run`"],
            ["Use the panel from other devices", "`--web-bind 0.0.0.0 --web-token PASSWORD`"],
            ["Change the panel port", "`--web-port 8090`"],
            ["Use the LP-100A", "`--lp100-port COM5`  (or set it in the panel)"],
            ["Turn the log file off", "`--no-log`"],
            ["Change the log size limit", "`--log-max-mb 5`"],
            ["Use JSON to Thetis instead of XML", "`--mmio-format json`  (and set Format (in) to JSON in Thetis)"],
            ["Try with Zeus", "`--tci-port 6060 --dry-run`  (experimental)"],
        ]),
        _P("**Settings made in the panel or window** (LP-100A port, log on/off and size, ask before "
           "Power OFF) are saved in `kpa1500_settings.json` next to the program. They are used at "
           "the next start instead of the matching flags. Delete that file to go back to the flags."),
        _P("**Panel layout:** click Settings. Everything about the tiles can be changed there "
           "and saved under a name (see section {sec:panel})."),
        _P("**Change the short labels** (FWD, DRV, SWR ...):"),
        _OL("Close the bridge, make a backup copy of `kpa1500_sdr_bridge.py`, and open it in "
            "Notepad.",
            "Press Ctrl+F and search for `const WIDGETS=[`.",
            "Each tile is one line, for example `mk('fwd','meter','FWD','Amp forward power'),`. "
            "The **third** quoted text is the short label and the **fourth** is the full label. "
            "Never change the first one.",
            "Change only the text between the quote marks, save, restart the bridge and press "
            "Ctrl+F5 in the browser."),
        _P("Labels inside a Thetis container are edited in Thetis itself."),
    ]))
    S.append(("flags", "14. All command-line flags", [
        _P("Run `py kpa1500_sdr_bridge.py --help` for the same list."),
        _TABLE(["Flag", "What it does", "Default"], flag_rows),
    ]))
    S.append(("files", "15. Files the bridge uses", [
        _TABLE(["File", "Purpose"], [
            ["kpa1500_sdr_bridge.py", "The program (revision shown at its top and in every window)"],
            ["start_kpa_sdr_bridge.bat", "Starts the bridge (closes an older one first; optionally starts Thetis). The flags are set inside it"],
            ["Open_Applet.bat", "Opens the Applet window of the running bridge"],
            ["Stop_Bridge.bat", "Closes the running bridge, its window and the Applet"],
            ["Install_KPA1500_SDR_Bridge.bat", "The installer (only in the download)"],
            ["KPA_Network_Check.bat", "Read-only network check (amplifier address, UDP port)"],
            ["kpa1500_bridge.log", "Event log, trimmed automatically (default 2 MB)"],
            ["kpa1500_settings.json", "Choices saved from the panel or window"],
            ["kpa1500_mac.txt", "The amplifier's MAC address, learned for remote power-on"],
            ["KPA1500_Bridge_Help.html", "This help as a file: `py kpa1500_sdr_bridge.py --write-help`"],
            ["Setup_Thetis_Containers.bat", "Puts the two KPA1500 windows into Thetis (close Thetis first)"],
            ["Undo_Thetis_Containers.bat", "Puts back the Thetis settings saved before the last setup"],
            ["kpa1500_thetis_setup.py", "The program behind those two files (`--check` only reports, `--remove` takes the windows out)"],
            ["thetis_backups", "Folder of Thetis settings backups made by the setup"],
        ]),
    ]))
    S.append(("trouble", "16. If something goes wrong", [
        _TABLE(["What you see", "Likely cause and fix"], [
            ["Over-drive protection says it is waiting", "It only works while the amp is in OPERATE. In STANDBY, and "
             "while the amp tunes its own ATU, the limit is ignored on purpose."],
            ["The drive (RF power) setting is never read", "The bridge must be logged in to the FlexRadio (Flex badge "
             "in the Applet). The measured-drive check still works without it."],
            ["Applet says 'not connected' or the radio badge shows no program", "The radio program's TCI server is off or on a "
             "different port. Thetis: Setup > Serial/Network/Midi CAT > Network > TCI Server Running. NereusSDR: File > "
             "Settings... > CAT & Network > TCI Server, Enable, port 50001."],
            ["'Waiting for the NereusSDR CAT port' or no CAT answer", "TCP CAT is off, or the port is not 13013. NereusSDR: "
             "File > Settings... > CAT & Network > TCP/IP CAT > Enable TCP CAT, CAT 1, port 13013."],
            ["Knob or TUNE does nothing; the log shows `?;`", "CAT 1 is not bound to a slice. Set VFO A to Slice A (Slice ID 0) "
             "on the TCP/IP CAT page."],
            ["TUNE button is refused", "This NereusSDR window does not hold transmit (TXcontrol), or another device keys. Read "
             "the reason NereusSDR shows. The bridge never keys by itself."],
            ["The amp does not follow the NereusSDR frequency", "TCI is not connected (see the first row) or another program "
             "holds port 50001."],
            ["Old bridge windows pile up", "Start with `start_kpa_sdr_bridge.bat` (it closes the old one) and stop with "
             "`Stop_Bridge.bat` or Quit bridge in the Applet."],
            ["TCI:-- in the status line", "Thetis is not running, its TCI server is off, or the port differs. "
                                          "Start Thetis, switch TCI on, check `--tci-port`."],
            ["AMP:-- in the status line", "Amplifier off or asleep, wrong `--amp-ip`, a different network, or "
                                          "firmware older than 01.84. Press D in the bridge window (or use "
                                          "Find amplifier under Settings) to search for it, or run `--discover`."],
            ["Panel will not open", "The bridge is not running, or the port is in use. Look in the "
                                    "bridge window for 'Could not start control panel'. Try `--web-port 8090`."],
            ["Panel looks old after an update", "Press Ctrl+F5. The panel warns you if its revision differs."],
            ["Drive is blank in standby", "Needs Thetis 2.10.3.13 or newer. It shows while transmitting only."],
            ["LP-100A will not connect", "Run `py -m pip install pyserial`, check the COM port in Device "
                                         "Manager, the baud rate, and that the meter is on the Watts screen. "
                                         "The reason shows under Settings."],
            ["Thetis Variables list is empty", "Bridge not started with `--mmio-port 50100`, the In entry is not "
                                               "Active/Enabled, or port/format differ. Try `--mmio-test --mmio-port 50100`."],
            ["A Thetis button does nothing", "Check the Out entry is Active/Enabled with 127.0.0.1:50101, the "
                                             "bridge has `--mmio-listen 50101`, and the text is a valid string. "
                                             "Use `--verbose` to see what arrives."],
            ["Command 'REFUSED - transmitting'", "By design. ATU, antenna and power-off changes are blocked while RF is present."],
            ["Power ON does not wake the amp", "Check NET WAKE on LAN, the MAC address (`--amp-mac`), and the "
                                               "network. See the log."],
            ["'The bridge is already running'", "Only one copy may run. Close the other one."],
            ["The bridge window flashes and closes", "Open Command Prompt, go to the folder and run "
                                                     "`start_kpa_sdr_bridge.bat` to read the message."],
            ["Container shows nothing in Thetis", "Click Recover Container, tick Auto height, check Show RX/Show TX "
                                                  "and the background colour."],
            ["'BRIDGE NOT RUNNING - data frozen' in Thetis", "The bridge is closed or stuck. Start it with "
                                                             "start_kpa_sdr_bridge.bat. The line goes away within seconds."],
            ["All Controls buttons dark, no warning line", "Normal for a moment after Thetis starts. If it stays, "
                                                           "check the bridge is running with `--mmio-port 50100`."],
            ["Setup says Thetis is running", "Answer Y to let the setup close it, or close Thetis yourself (it can take a few seconds), then press Enter. If Thetis shows a question when closing, answer it."],
            ["The KPA1500 windows did not appear", "Was Thetis closed while the setup ran? Run "
                                                   "Setup_Thetis_Containers.bat again with Thetis closed. "
                                                   "In Thetis, Setup > Appearance > Meters/Gadgets lists them."],
            ["Something in Thetis looks wrong after the setup", "Close Thetis, double-click "
                                                                "Undo_Thetis_Containers.bat, start Thetis."],
            ["Log file keeps growing", "Update to this revision. Use `--no-log`, or the Settings box, or the G key."],
            ["FAN tile shows a dash", "The fan setting has not been read yet, or the amplifier firmware is older "
                                      "than 01.47. Check the AMP link is ok."],
        ]),
    ]))
    S.append(("safety", "17. Safety notes", [
        _UL("The bridge never keys the transmitter and never presses TUNE for you.",
            "ATU and antenna changes are refused while RF is present. Power-off is too, unless "
            "**Block power off while transmitting** is turned off for emergency shutdown.",
            "Standby-on-Tune is a convenience, not a substitute for proper hardware protection.",
            "Test new settings with `--dry-run` first, and use a dummy load for first transmissions.",
            "Do not open the panel to your network without `--web-token`.",
            "The bridge is not made by or supported by Elecraft, Telepost or the Thetis authors."),
    ]))
    S.append(("about", "18. About this version", [
        _P("Revision %s (%s)." % (VERSION, BUILD_DATE)),
        _P("Concept, design and on-air testing: KW4EX."),
        _P("This is the SDR bridge, the successor of the Thetis-only bridge (`kpa1500_thetis_bridge.py`), "
           "with the same features plus NereusSDR and the Applet window. Both can be installed side by side; "
           "only one runs at a time."),
        _P("The revision is shown on the first line of the bridge window, in the window title, "
           "and in the panel (top right and under Settings)."),
    ]))
    # number the sections automatically and resolve {sec:id} references
    nums = {sid: n for n, (sid, _t, _b) in enumerate(S, 1)}

    def sub(t):
        return re.sub(r"\{sec:(\w+)\}", lambda m: str(nums[m.group(1)]), t)

    def fix(b):
        kind = b[0]
        if kind in ("p", "note", "warn"):
            return (kind, sub(b[1]))
        if kind in ("ul", "ol"):
            return (kind, [sub(i) for i in b[1]])
        if kind == "table":
            return (kind, [sub(h) for h in b[1]], [[sub(c) for c in r] for r in b[2]])
        if kind == "img":
            return (kind, b[1], sub(b[2]))
        return b
    return [(sid, "%d. %s" % (nums[sid], re.sub(r"^\d+\.\s*", "", t)), [fix(b) for b in blocks])
            for sid, t, blocks in S]


def help_section_number(sid):
    return [i for i, (x, _t, _b) in enumerate(help_sections(), 1) if x == sid][0]


def _help_inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)


def render_help_html():
    out = []
    secs = help_sections()
    out.append("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KPA1500 Bridge Help</title>
<style>
:root{--bg:#f4f6f8;--card:#fff;--fg:#14212b;--fg2:#4a5b68;--line:#c9d3db;--acc:#0f6a85;--code:#e8eef2;--warn:#fff3e0;--wl:#d98200;--note:#e6f3f7;--nl:#16708c}
@media (prefers-color-scheme:dark){:root{--bg:#0d1216;--card:#151e25;--fg:#e1e8ed;--fg2:#9fb0bc;--line:#26343d;--acc:#54b6d2;--code:#1f2d36;--warn:#33250f;--wl:#e8a33d;--note:#102a33;--nl:#54b6d2}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,Segoe UI,sans-serif}
.wrap{max-width:56rem;margin:0 auto;padding:1rem}
h1{font-size:1.6rem;margin:.2rem 0}h2{font-size:1.2rem;margin:2rem 0 .5rem;padding-top:.6rem;border-top:1px solid var(--line)}
a{color:var(--acc)}code{background:var(--code);padding:.05rem .3rem;border-radius:.25rem;font-family:ui-monospace,Consolas,monospace;font-size:.9em;word-break:break-word}
pre{background:var(--code);padding:.7rem;border-radius:.4rem;overflow-x:auto;font-size:.85rem;line-height:1.35}
nav{background:var(--card);border:1px solid var(--line);border-radius:.4rem;padding:.7rem 1rem;columns:2 18rem}
nav a{display:block;text-decoration:none;padding:.1rem 0}
.tw{overflow-x:auto;margin:.6rem 0}table{border-collapse:collapse;width:100%;background:var(--card);font-size:.92rem}
th,td{border:1px solid var(--line);padding:.35rem .5rem;text-align:left;vertical-align:top}th{background:var(--code)}
.note,.warn{padding:.6rem .8rem;border-radius:.4rem;margin:.7rem 0;border-left:4px solid}
.note{background:var(--note);border-color:var(--nl)}.warn{background:var(--warn);border-color:var(--wl)}
.top{font-size:.8rem;float:right}.sub{color:var(--fg2)}
li{margin:.25rem 0}
figure{margin:1rem 0;text-align:center}figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:.3rem}
figcaption{color:var(--fg2);font-size:.88rem;margin-top:.3rem}
@media print{nav,.top{display:none}body{background:#fff;color:#000}}
</style></head><body><div class="wrap">""")
    out.append("<h1>KPA1500 Bridge Help</h1>")
    out.append('<div class="sub">Revision %s (%s) &middot; Thetis &harr; Elecraft KPA1500 &harr; LP-100A'
               ' &middot; design by KW4EX</div>'
               % (html.escape(VERSION), html.escape(BUILD_DATE)))
    out.append('<p><b>Quick start:</b> double-click <code>start_kpa_sdr_bridge.bat</code>, then open '
               '<a href="http://127.0.0.1:8080">http://127.0.0.1:8080</a>. '
               'For the meters and buttons inside Thetis, close Thetis and double-click '
               '<code>Setup_Thetis_Containers.bat</code> - see <a href="#containers">section %d</a>.</p>'
               % help_section_number("containers"))
    out.append("<nav aria-label=\"Contents\">")
    for sid, title, _ in secs:
        out.append('<a href="#%s">%s</a>' % (sid, html.escape(title)))
    out.append("</nav>")
    for sid, title, blocks in secs:
        out.append('<h2 id="%s">%s<a class="top" href="#top">top</a></h2>' % (sid, html.escape(title)))
        for b in blocks:
            kind = b[0]
            if kind == "p":
                out.append("<p>%s</p>" % _help_inline(b[1]))
            elif kind in ("ul", "ol"):
                out.append("<%s>%s</%s>" % (kind, "".join("<li>%s</li>" % _help_inline(i) for i in b[1]), kind))
            elif kind == "code":
                out.append("<pre>%s</pre>" % html.escape(b[1], quote=False))
            elif kind in ("note", "warn"):
                out.append('<div class="%s">%s</div>' % (kind, _help_inline(b[1])))
            elif kind == "img":
                data = HELP_IMAGES.get(b[1], "")
                if data:
                    out.append('<figure><img src="data:image/jpeg;base64,%s" alt="%s"><figcaption>%s</figcaption></figure>'
                               % (data, html.escape(_help_plain(b[2])), _help_inline(b[2])))
            elif kind == "table":
                head = "".join("<th>%s</th>" % _help_inline(h) for h in b[1])
                rows = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % _help_inline(c) for c in r) for r in b[2])
                out.append('<div class="tw"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, rows))
    out.append("</div><a id=\"top\"></a></body></html>")
    return "\n".join(out)


def _help_plain(t):
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", t.replace("`", ""))


def render_help_text(sections=None, width=76):
    import textwrap
    out = []
    for sid, title, blocks in (sections or help_sections()):
        out.append("")
        out.append("=" * min(width, max(len(title), 20)))
        out.append(title)
        out.append("=" * min(width, max(len(title), 20)))
        for b in blocks:
            kind = b[0]
            if kind == "p":
                out.append(textwrap.fill(_help_plain(b[1]), width))
            elif kind in ("ul", "ol"):
                for n, i in enumerate(b[1], 1):
                    bullet = "  - " if kind == "ul" else "  %d. " % n
                    out.append(textwrap.fill(_help_plain(i), width, initial_indent=bullet,
                                             subsequent_indent=" " * len(bullet)))
            elif kind == "code":
                out.extend("    " + l for l in b[1].splitlines())
            elif kind in ("note", "warn"):
                out.append(textwrap.fill(("NOTE: " if kind == "note" else "WARNING: ") + _help_plain(b[1]),
                                         width, subsequent_indent="  "))
            elif kind == "img":
                out.append(textwrap.fill("[Picture in the HTML help: %s]" % _help_plain(b[2]), width))
            elif kind == "table":
                for r in b[2]:
                    cells = [_help_plain(c) for c in r]
                    line = "  " + cells[0] + ": " + "; ".join(c for c in cells[1:] if c)
                    out.append(textwrap.fill(line, width, subsequent_indent="      "))
            out.append("")
    return "\n".join(out).encode("ascii", "replace").decode("ascii")


def help_file_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "KPA1500_Bridge_Help.html")


def write_help_file(path=None):
    path = path or help_file_path()
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_help_html())
    return path


# --------------------------------------------------------------------------
# Keyboard commands in the bridge window
# --------------------------------------------------------------------------
KEY_HELP = """
Keyboard commands (click this window first, then press a key):
  H  this key list                  O  Operate / Standby toggle
  W  open the full help (browser)   A  ATU inline / bypass toggle
  I  read the help in this window   N  antenna 1 / 2 toggle
  L  change the LP-100A COM port    C  clear amp fault
  Y  toggle "ask before Power OFF"  S  Standby-on-Tune on / off
  G  log file on / off              P  Power ON the amplifier
  X  Power OFF the amplifier        V  show the version
  F  set minimum fan speed (0-5)    +  / -  fan speed up / down
  K  allow Thetis to power off: yes/no
  B  block power off while transmitting: on/off
  D  find the amplifier on the network
  T  TUNE the radio safely (amp STANDBY first), press again to stop
  M  DUMMY OK: dummy load on purpose (silences "no antenna?" on this band)
  R  "no antenna?" check: on/off, warn or keep STANDBY, limits per band, learn
  Q  quit the bridge
The same safety checks as the panel apply: nothing switches while transmitting
(power off too, unless B has turned "block power off while transmitting" off).
"""


class ConsoleKeys(threading.Thread):
    def __init__(self, bridge, read_line=None):
        super().__init__(daemon=True)
        self.b = bridge
        self.read_line = read_line or input
        self._cooked = None            # POSIX: callback(bool) to leave/enter raw mode

    # ---- real keyboard readers ----
    def run(self):
        try:
            if not sys.stdin or not sys.stdin.isatty():
                return
            if os.name == "nt":
                self._loop_windows()
            else:
                self._loop_posix()
        except Exception as e:
            self.b.log("Keyboard commands unavailable: %s" % e)

    def _loop_windows(self):
        import msvcrt
        while not self.b.stop.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):          # arrow / function key
                    msvcrt.getwch()
                    continue
                self.handle_key(ch)
            else:
                time.sleep(0.05)

    def _loop_posix(self):
        import select
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)

        def cooked(on):
            if on:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            else:
                tty.setcbreak(fd)
        self._cooked = cooked
        try:
            tty.setcbreak(fd)
            while not self.b.stop.is_set():
                if select.select([sys.stdin], [], [], 0.2)[0]:
                    self.handle_key(sys.stdin.read(1))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # ---- helpers ----
    def ask(self, prompt):
        self.b.prompting = True
        if self._cooked:
            self._cooked(True)
        try:
            sys.stdout.write("\r" + " " * 120 + "\r")
            return self.read_line(prompt)
        except (EOFError, KeyboardInterrupt):
            return ""
        finally:
            if self._cooked:
                self._cooked(False)
            self.b.prompting = False

    def act(self, action, params=None):
        ok, msg = self.b.do_action(action, params)
        self.b.log("Key: %s%s" % ("" if ok else "REFUSED - ", msg))

    # ---- the commands ----
    def handle_key(self, ch):
        b = self.b
        k = (ch or "").lower()
        if k in ("h", "?"):
            with b.print_lock:
                print(KEY_HELP)
        elif k == "v":
            b.log("Bridge version %s (%s)" % (VERSION, BUILD_DATE))
        elif k == "w":
            b.open_help()
        elif k == "i":
            self.help_dialog()
        elif k == "o":
            self.act("toggle_operate")
        elif k == "a":
            self.act("toggle_atu")
        elif k == "n":
            self.act("toggle_ant")
        elif k == "s":
            self.act("toggle_sot")
        elif k == "c":
            self.act("clear_fault")
        elif k in ("+", "="):
            self.act("fan_up")
        elif k == "-":
            self.act("fan_down")
        elif k == "f":
            self.fan_dialog()
        elif k == "d":
            self.find_dialog()
        elif k == "p":
            self.act("power_on")
        elif k == "y":
            self.act("confirm_off_off" if b.confirm_power_off else "confirm_off_on")
        elif k == "g":
            self.act("log_off" if b.log_enabled else "log_on")
        elif k == "k":
            self.act("thetis_off_off" if b.allow_thetis_off else "thetis_off_on")
        elif k == "b":
            self.act("block_off_tx_off" if b.block_off_tx else "block_off_tx_on")
        elif k == "x":
            if b.confirm_power_off:
                ans = self.ask("Turn the amplifier power supplies OFF? Type YES then Enter: ")
                if ans.strip().upper() != "YES":
                    b.log("Power OFF cancelled")
                    return
            self.act("power_off")
        elif k == "l":
            self.lp_dialog()
        elif k == "m":
            self.act("dummy_ok")
        elif k == "t":
            self.act("radio_tune_toggle")
        elif k == "r":
            self.noant_dialog()
        elif k == "q":
            b.log("Quit requested from the keyboard")
            b.quit = True

    def help_dialog(self):
        secs = help_sections()
        with self.b.print_lock:
            print("\nHelp topics:")
            for n, (sid, title, blocks) in enumerate(secs, 1):
                print("  %2d  %s" % (n, re.sub(r"^\d+\.\s*", "", title)))
        while True:
            ans = self.ask("Topic number to read (Enter = back): ").strip()
            if not ans:
                return
            if ans.isdigit() and 1 <= int(ans) <= len(secs):
                with self.b.print_lock:
                    print(render_help_text([secs[int(ans) - 1]]))
            else:
                self.b.log("Not a topic number: %s" % ans[:20])

    def find_dialog(self):
        b = self.b
        b.log("Searching the network for a KPA1500 (a few seconds) ...")
        ok, msg = b.do_action("amp_find")
        found = b.found_amps
        if not found:
            b.log("Nothing found. You can also type the address into the panel (Layout), "
                  "or start with --amp-ip 192.168.x.x")
            return
        cur = b.amp.addr[0]
        if len(found) == 1:
            ip = found[0]["ip"]
            if ip == cur:
                b.log("That is the address already in use")
                return
            if self.ask("Use %s? [Y/n]: " % describe_amp(found[0])).strip().lower() not in ("", "y", "yes"):
                b.log("Amplifier address unchanged")
                return
        else:
            with b.print_lock:
                for n, f in enumerate(found, 1):
                    print("  %d  %s%s" % (n, describe_amp(f), "   (in use)" if f["ip"] == cur else ""))
            ans = self.ask("Number to use (Enter = keep current): ").strip()
            if not ans.isdigit() or not 1 <= int(ans) <= len(found):
                b.log("Amplifier address unchanged")
                return
            ip = found[int(ans) - 1]["ip"]
        self.act("amp_ip", {"ip": ip})

    def noant_dialog(self):
        b = self.b
        while True:
            st = b.noant_state()
            lim = b.noant_limits
            with b.print_lock:
                print("\n'No antenna?' check: %s, action: %s" % (
                    "ON" if b.noant_enabled else "OFF",
                    "warn only" if b.noant_action == "warn" else "warn + keep amp in STANDBY"))
                print("Now: band %s m, receive level %s, state %s" % (
                    st["band"] or "?", "%.1f dBm" % st["dbm"] if st["dbm"] is not None else "-- (none from Thetis)",
                    st["state"]))
                print("Limits (dBm; below = warning):  " + "  ".join(
                    "%s:%s" % (k, "off" if v is None else v) for k, v in lim.items()))
                print("  1 check on/off   2 warn only / keep STANDBY   3 set a band limit")
                print("  4 learn this band (antenna disconnected!)     5 all limits to defaults")
            ans = self.ask("Choice (Enter = done): ").strip()
            if not ans:
                return
            if ans == "1":
                self.act("noant_off" if b.noant_enabled else "noant_on")
            elif ans == "2":
                self.act("noant_action", {"action": "standby" if b.noant_action == "warn" else "warn"})
            elif ans == "3":
                band = self.ask("Band (160 80 60 40 30 20 17 15 12 10 6) [%s]: " % (st["band"] or "")).strip() or st["band"]
                v = self.ask("Limit in dBm, e.g. -105, or off: ").strip()
                if band and v:
                    self.act("noant_limit", {"band": band, "dbm": v})
            elif ans == "4":
                self.act("noant_learn")
            elif ans == "5":
                self.act("noant_defaults")
            else:
                b.log("Not a choice: %s" % ans[:10])

    def fan_dialog(self):
        b = self.b
        now = "%s now, minimum %s" % (
            b.fan_speed if b.fan_speed is not None else "?",
            b.fan_min if b.fan_min is not None else "?")
        ans = self.ask("Minimum fan speed 0-5 (fan %s). Enter = keep: " % now).strip()
        if not ans:
            b.log("Fan speed unchanged")
            return
        self.act("fan_min", {"speed": ans})

    def lp_dialog(self):
        b = self.b
        cur = b.lp.port if b.lp else ""
        baud = b.lp.baud if b.lp else 115200
        ports, note = list_serial_ports()
        with b.print_lock:
            print("\nLP-100A port now: %s @ %d" % (cur or "(none)", baud))
            print("Ports found: %s" % (", ".join(p["device"] for p in ports)
                                      if ports else (note or "none")))
        port = self.ask("New port, e.g. COM5 (Enter = keep, - = disconnect): ").strip()
        if not port:
            b.log("LP-100A port unchanged")
            return
        if port == "-":
            port = ""
        if re.match(r"(?i)com", port):
            port = "COM" + port[3:]
        baud_s = self.ask("Baud rate [%d]: " % baud).strip() or str(baud)
        self.act("lp_port", {"port": port, "baud": baud_s})


# --------------------------------------------------------------------------
# Web page (served at /)
# --------------------------------------------------------------------------
PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KPA1500 / LP-100A</title>
<style>
:root{--s:1;--cell:9.5;--bg:#eef1f4;--card:#fff;--fg:#111c24;--fg2:#4a5b68;--line:#c9d3db;
--ok:#17803d;--warn:#b26b0e;--bad:#b3261e;--acc:#16708c;--bar:#dfe6eb;--btn:#e4eaef;--peak:#e3b800}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d1216;--card:#151e25;
--fg:#e1e8ed;--fg2:#9fb0bc;--line:#26343d;--ok:#4fc77a;--warn:#e8a33d;--bad:#ff7b72;
--acc:#54b6d2;--bar:#22303a;--btn:#22303a;--peak:#ffe000}}
:root[data-theme="dark"]{--bg:#0d1216;--card:#151e25;--fg:#e1e8ed;--fg2:#9fb0bc;--line:#26343d;
--ok:#4fc77a;--warn:#e8a33d;--bad:#ff7b72;--acc:#54b6d2;--bar:#22303a;--btn:#22303a;--peak:#ffe000}
*{box-sizing:border-box}
html{font-size:calc(15px * var(--s))}
body{margin:0;background:var(--bg);color:var(--fg);font:1rem/1.35 system-ui,Segoe UI,sans-serif;
padding:.6rem;min-height:100vh}
.top{display:flex;align-items:center;gap:.6rem;margin-bottom:.5rem}
.top h1{font-size:1.15rem;margin:0;flex:1}
.nohdr .top h1,.nohdr .top .dry{display:none}
.nohdr .top{justify-content:flex-end;margin:0 0 .25rem}
.nohdr #gear,.nohdr .hbtn{font-size:.7rem;padding:.1rem .45rem}
.small{font-size:.8rem;color:var(--fg2)}
#gear,.hbtn{position:relative;z-index:5;font-size:.8rem;padding:.25rem .6rem;min-height:0;opacity:.75}
.hbtn{border:1px solid var(--line);border-radius:.4rem;background:var(--btn);color:var(--fg);text-decoration:none;line-height:1.35}
.hbtn:hover{opacity:1;border-color:var(--acc)}
#gear:hover,.editing #gear{opacity:1}
#tiles{display:flex;flex-wrap:wrap;gap:.45rem;align-items:stretch}
.tile{flex:1 1 calc(var(--cell) * var(--w,1) * 1rem);max-width:100%;min-width:0;background:var(--card);
border:1px solid var(--line);border-radius:.4rem;padding:.4rem .55rem;position:relative;
display:flex;flex-direction:column;justify-content:center;gap:.25rem}
.t-head{display:flex;justify-content:space-between;align-items:baseline;gap:.5rem}
.t-lbl{color:var(--fg2);font-size:.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.t-val{font-weight:600;font-variant-numeric:tabular-nums;text-align:right;overflow:hidden;
text-overflow:ellipsis;white-space:nowrap}
.bar{height:.6rem;background:var(--bar);border-radius:.3rem;overflow:hidden;position:relative}
.peak{position:absolute;left:0;top:0;height:100%;width:0;background:transparent}
.peak.on{background:var(--peak);box-shadow:inset -2px 0 0 var(--bad)}
.nobars .bar{display:none}
.fill{height:100%;width:0;background:var(--ok);transition:width .15s;position:relative}
.good{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
button{font:inherit;padding:.4rem .6rem;min-height:2.2rem;border-radius:.4rem;border:1px solid var(--line);
background:var(--btn);color:var(--fg);cursor:pointer}
button:hover{border-color:var(--acc)}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.segs{display:flex;gap:.2rem;margin-top:.1rem}
.segs button{flex:1;min-width:0;min-height:1.8rem;padding:.1rem 0}
.tile.k-button,.tile.k-toggle{padding:.25rem}
.tile.k-button .inner,.tile.k-toggle .inner{height:100%}
.tile.k-button .inner button,.tile.k-toggle .inner button{width:100%;height:100%;min-height:2.3rem}
button.act{background:var(--acc);color:#fff;border-color:var(--acc)}
button.alarm{background:var(--bad);color:#fff;border-color:var(--bad)}
button.danger{border-color:var(--bad);color:var(--bad)}
.tile[data-id="ampf"] .t-val{font-size:1.35rem}
.tile.k-check label{display:flex;gap:.45rem;align-items:center;cursor:pointer}
.msg{min-height:1.3rem;font-size:.85rem;margin-top:.5rem}
.msg.good{color:var(--ok)}.msg.badm{color:var(--bad)}
#offline{display:none;color:var(--bad);font-weight:600;margin-bottom:.4rem}
#pwbox{display:none;background:var(--card);border:1px solid var(--warn);border-radius:.4rem;padding:.6rem;margin-bottom:.6rem}
#pwbox.on{display:block}#pwbox label{margin:0 .4rem}
#ampdown{display:none;background:var(--bad);color:#fff;font-weight:700;padding:.4rem .6rem;border-radius:.3rem;margin-bottom:.5rem}
#ampbadge{font-size:.8rem;font-weight:700;padding:.1rem .5rem;border-radius:1rem;border:1px solid var(--line)}
#ampbadge.on{background:var(--ok);color:#fff;border-color:var(--ok)}
#ampbadge.off{background:var(--bad);color:#fff;border-color:var(--bad)}
#ampbadge.nolink{background:var(--warn);color:#000;border-color:var(--warn)}
/* edit mode */
.tools{display:none;position:absolute;top:-.55rem;right:.3rem;gap:.15rem;z-index:3}
.editing .tools{display:flex}
.tools button{min-height:0;padding:.05rem .4rem;font-size:.8rem;line-height:1.2;background:var(--card)}
.editing .tile{outline:1px dashed var(--acc);outline-offset:1px;cursor:grab;margin-top:.15rem}
.editing .tile .inner{pointer-events:none}
.tile.is-hidden{opacity:.4}
.tile.dragover{outline:2px solid var(--acc)}
#drawer{display:none;background:var(--card);border:1px solid var(--acc);border-radius:.4rem;
padding:.6rem;margin-bottom:.8rem}
.editing #drawer{display:block}
.drow{display:flex;flex-wrap:wrap;gap:.6rem .9rem;align-items:center;margin-bottom:.5rem}
.drow label{display:flex;gap:.35rem;align-items:center;font-size:.85rem}
select,textarea,input[type=text]{font:inherit;font-size:.85rem;background:var(--bg);color:var(--fg);
border:1px solid var(--line);border-radius:.3rem;padding:.2rem .3rem}
textarea{width:100%;font-family:ui-monospace,Consolas,monospace;font-size:.75rem}
input[type=range]{width:7rem}
.dh{font-weight:700;font-size:.9rem;margin:.7rem 0 .3rem;padding-top:.4rem;border-top:1px solid var(--line);color:var(--acc)}
.dh:first-child{margin-top:0;padding-top:0;border-top:0}
#d_nalim label{font-size:.8rem;gap:.2rem}#d_nalim input{width:3.4rem}
.ktable{display:grid;grid-template-columns:minmax(9rem,auto) minmax(12rem,1fr) auto;gap:.25rem .5rem;align-items:center;margin:.4rem 0;max-width:52rem}
.ktable .kl{font-size:.82rem}.ktable .kl.hit{color:var(--acc);font-weight:700}
.ktable select{max-width:100%}.ktable .kc{grid-column:2 / span 2}
.ktable button{min-height:0;padding:.1rem .5rem;font-size:.78rem}
.dsub{font-weight:600;font-size:.85rem;margin:.5rem 0 .2rem}
.tblist{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:.3rem;margin:.4rem 0}
.tbi{display:flex;align-items:center;gap:.15rem;border:1px solid var(--line);border-radius:.3rem;padding:.15rem .25rem;background:var(--bg);font-size:.8rem;min-width:0}
.tbi span{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tbi.gap span{color:var(--fg2);font-style:italic}
.tbi button,#d_tbhid button,#d_tmhid button,#d_kwhid button{min-height:0;padding:.05rem .35rem;font-size:.75rem}
#antwarn{display:none;background:var(--warn);color:#000;font-weight:700;padding:.4rem .6rem;border-radius:.3rem;margin-bottom:.5rem;align-items:center;gap:.6rem;flex-wrap:wrap}
#antwarn.on{display:flex}#antwarn.tx{background:var(--bad);color:#fff;animation:blink 1s steps(2) infinite}
#drvwarn{display:none;background:var(--bad);color:#fff;font-weight:700;padding:.4rem .6rem;border-radius:.3rem;margin-bottom:.5rem}
#drvwarn.on{display:block}#drvwarn.tx{animation:blink 1s steps(2) infinite}
@media (prefers-reduced-motion:reduce){#drvwarn.tx{animation:none}}
#antwarn span{flex:1}#antwarn button{min-height:1.8rem;padding:.15rem .6rem;font-weight:700}
@keyframes blink{50%{opacity:.55}}
@media (prefers-reduced-motion:reduce){#antwarn.tx{animation:none}}
.tc .tna{display:none;color:#ff3030;font-weight:700;white-space:pre;text-align:center}
.tc .tna.on{display:block}.tc .tna.low{color:#ffa500}
/* Thetis look: the two Thetis containers, live in the browser */
#thetis{display:none;flex-wrap:wrap;gap:.6rem;align-items:flex-start}
.thv #thetis{display:flex}.thv #tiles{display:none}
.tc{background:#000;border:1px solid #3c3c3c;border-radius:.2rem;padding:.3rem .4rem;width:27rem;max-width:100%;
font-family:Verdana,Tahoma,sans-serif;color:#fff;font-size:.8rem;line-height:1.3}
.tc .tl{white-space:pre;overflow:hidden;text-overflow:ellipsis}
.tc .tw{display:none;color:#ff3030;font-weight:700;white-space:pre;text-align:center}
.stale .tc .tw{display:block}
.tc svg{display:block;width:100%;height:auto;margin:.1rem 0}
.tc svg text{font-family:Verdana,Tahoma,sans-serif}
.tbtns{display:grid;grid-template-columns:repeat(4,1fr);gap:.3rem;margin:.3rem 0 .15rem}
.tbtns button{background:#000;color:#fff;border:1px solid #8c8c8c;border-radius:.3rem;font:.78rem Verdana,Tahoma,sans-serif;
min-height:2.4rem;padding:.1rem;white-space:nowrap;overflow:hidden}
.tbtns button.lit{background:#6e9be0;color:#000;border-color:#6e9be0}
.tbtns button:hover{border-color:#fff}
.editing #thetis{pointer-events:none;opacity:.8}
</style></head><body>
<div class="top"><h1>KPA1500 &amp; LP-100A</h1><span id="ver" class="small dry"></span><span id="ampbadge" title="Is the amplifier answering at its network address?">AMP ?</span><span id="dry" class="small dry"></span>
<a id="helplink" class="hbtn" href="/help" target="_blank" rel="noopener">Help</a>
<button id="gear" aria-label="Settings and layout">Settings</button></div>
<div id="offline">Bridge offline - retrying...</div>
<div id="pwbox"><b>This panel has a password.</b>
 <label>Password <input type="password" id="pw_in" size="14" autocomplete="current-password"></label> <button id="pw_ok" type="button">Open</button>
 <div class="small">Forgot it? Open the panel on the bridge computer itself (<b>http://127.0.0.1:8080</b>) - no password is needed there - then Settings &gt; Panel access &gt; Remove password.</div></div>
<div id="ampdown"></div>
<div id="antwarn" role="alert"><span id="antwarn_t"></span> <button id="antwarn_b" type="button">DUMMY OK</button></div>
<div id="drvwarn" role="alert"></div>
<div id="drawer">
 <div class="dh">Layout</div>
 <div class="drow">
  <label>Layout <select id="d_layout"></select></label>
  <button id="d_saveas">Save as...</button><button id="d_del">Delete</button>
  <label>Preset <select id="d_preset"><option value="">Apply preset...</option>
   <option>Full</option><option>Compact</option><option>Telemetry</option><option>Controls</option><option value="Thetis">Thetis look</option></select></label>
  <label title="Tiles: the normal panel. Thetis look: the same meters and buttons as the KPA1500 windows in Thetis, working in the browser">Style <select id="d_style"><option value="tiles">Tiles</option><option value="thetis">Thetis look</option></select></label>
 </div>
 <div class="drow">
  <label>Size <input type="range" id="d_scale" min="0.6" max="2" step="0.05"></label>
  <label>Tile width <input type="range" id="d_cell" min="5" max="22" step="0.5"></label>
  <label>Labels <select id="d_labels"><option value="short">Short</option><option value="full">Full</option></select></label>
  <label><input type="checkbox" id="d_bars"> Bars</label>
  <label>Theme <select id="d_theme"><option value="auto">Auto</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
  <label><input type="checkbox" id="d_hdr"> Title bar</label>
 </div>
 <div class="drow">
  <button id="d_showall">Show all tiles</button><button id="d_export">Export</button><button id="d_import">Import</button>
 </div>
 <textarea id="d_json" rows="2" aria-label="Layout JSON" placeholder="Layout JSON: press Export, or paste a layout here and press Import"></textarea>
 <div class="small">Tiles style: drag tiles to reorder, or use the arrows on each tile. Width cycles 1x/2x/3x/4x. The x hides a tile, + shows it again. Changes save automatically in this browser under the layout name. Open <b>?layout=Name</b> in another window for a different layout.</div>
 <div class="dh">Amplifier</div>
 <div class="drow">
  <label>Amplifier address <input type="text" id="d_ampip" size="15" placeholder="192.168.0.175" autocomplete="off"></label>
  <button id="d_ampfind">Find amplifier</button><button id="d_ampuse">Use this address</button>
  <select id="d_ampfound" style="display:none" aria-label="Amplifiers found"></select>
  <span id="d_ampstat" class="small"></span>
 </div>
 <div class="dh">Safety</div>
 <div class="drow">
  <label><input type="checkbox" id="d_confirm"> Ask before Power OFF</label>
  <label title="Lets a Thetis container button (KPA_POWER_OFF) switch the amplifier off"><input type="checkbox" id="d_thetisoff"> Allow Thetis to power off the amp</label>
  <label title="Untick only if you want an emergency power off to work even while the radio is transmitting"><input type="checkbox" id="d_blockofftx"> Block power off while transmitting</label>
  <label title="Put the amp in STANDBY for the radio's TUNE and back to OPERATE afterwards"><input type="checkbox" id="d_sot"> Standby-on-Tune</label>
  <label title="A TUNE started with the bridge TUNE button stops by itself after this time">Auto-stop TUNE after <input type="text" id="d_tunemax" size="3" inputmode="numeric"> s (0 = never)</label>
 </div>
 <div class="dh">No antenna? check <span class="small">(receive level from Thetis)</span></div>
 <div class="drow">
  <label><input type="checkbox" id="d_na"> Check is on</label>
  <label>When the level is too low <select id="d_naact"><option value="warn">Warn only</option><option value="standby">Warn and keep the amp in STANDBY</option></select></label>
  <span id="d_nastat" class="small"></span>
 </div>
 <div class="drow" id="d_nalim" aria-label="Limit per band in dBm"></div>
 <div class="drow">
  <button id="d_nalearn" title="Disconnect the antenna (or switch the radio to no antenna), wait 3 seconds, then press">Learn this band</button>
  <button id="d_nadef">Default limits</button>
  <span class="small">Limit per band in dBm: a lower receive level shows the warning. Empty = no check on that band. Learn sets the limit to the level measured with NO antenna + 6 dB.</span>
 </div>
 <div class="dh">Over-drive protection <span class="small">(drive going into the amplifier)</span></div>
 <div class="drow">
  <label>Limit <input type="text" id="d_dglim" size="5" inputmode="decimal" placeholder="off"> W</label>
  <label>If it goes over <select id="d_dgact"><option value="ignore">Ignore</option><option value="warn">Warn</option><option value="limit">Hold at the limit</option></select></label>
  <label title="The radio's RF power setting is a percent of this. Most FlexRadios: 100">Radio full power <input type="text" id="d_dgrw" size="5" inputmode="decimal"> W</label>
  <span id="d_dgstat" class="small"></span>
 </div>
 <div class="small">Empty limit = off. Only judged while the amp is in OPERATE (not in STANDBY, and not while the amp tunes its own ATU). <b>Warn</b> shows a red message. <b>Hold at the limit</b> also sets the radio's RF power back to the limit, and puts the amp in STANDBY if the measured drive stays over it. This helps; it does not replace care. The amplifier's own protection stays the last line of defence.</div>
 <div class="dh">Thetis windows <span class="small">(KPA1500 Telemetry and KPA1500 Controls)</span></div>
 <div class="small">Choose what each Thetis window shows and in which order. The Thetis look here shows it at once. Arrows move an item, x takes it out, + puts it back. In a title, <b>{ver}</b> shows the bridge version.</div>
 <div class="dsub">Telemetry window</div>
 <div class="drow"><label>Title <input type="text" id="d_tmtitle" size="32" maxlength="48" autocomplete="off"></label><span class="small">(shown when the "Title line" item is in the list)</span></div>
 <div id="d_tm" class="tblist" aria-label="Telemetry window order"></div>
 <div class="drow" id="d_tmhid"></div>
 <div class="drow"><button id="d_tmgap">Add blank line</button><button id="d_tmdef">Standard order</button></div>
 <div class="dsub">Controls window</div>
 <div class="drow"><label>Title <input type="text" id="d_tbtitle" size="32" maxlength="48" autocomplete="off"></label></div>
 <div id="d_tb" class="tblist" aria-label="Button order"></div>
 <div class="drow" id="d_tbhid"></div>
 <div class="drow">
  <label>Columns <select id="d_tbcols"><option>3</option><option>4</option><option>5</option><option>6</option></select></label>
  <button id="d_tbgap">Add blank space</button><button id="d_tbdef">Standard order</button>
 </div>
 <div class="dsub">Knob window <span class="small">(what the FlexControl knob and buttons do right now)</span></div>
 <div class="drow"><label><input type="checkbox" id="d_kwon"> Show the KPA1500 Knob window in Thetis</label>
  <label>Title <input type="text" id="d_kwtitle" size="32" maxlength="48" autocomplete="off"></label></div>
 <div id="d_kw" class="tblist" aria-label="Knob window order"></div>
 <div class="drow" id="d_kwhid"></div>
 <div class="drow"><button id="d_kwgap">Add blank line</button><button id="d_kwdef">Standard order</button>
  <span class="small">In the window, '&gt;AF' means the press switches the knob to AF volume; 2x = double tap, hold = long press.</span></div>
 <div class="drow">
  <button id="d_tbbuild" class="act" title="Opens the setup on the bridge computer">Rebuild Thetis windows</button>
  <span class="small">Puts both windows into Thetis as shown here. The setup window opens on the bridge computer, offers to close Thetis (the normal way - it saves its settings), makes a backup, rebuilds both windows in the same place and offers to start Thetis again.</span>
 </div>
 <div class="dh">Panel access</div>
 <div class="drow"><span id="d_pwstat" class="small"></span></div>
 <div class="drow">
  <label>New password <input type="text" id="d_pwnew" size="16" maxlength="32" autocomplete="off" placeholder="4-32 letters/digits"></label>
  <button id="d_pwset">Set password</button><button id="d_pwdel">Remove password</button>
 </div>
 <div class="small">The password is only asked on other computers and phones; this computer never needs it. It can be changed or removed only here on the bridge computer. Whether other devices can reach the panel at all is chosen in the installer (Step 6).</div>
 <div class="dh">FlexControl tuning knob</div>
 <div class="drow"><span id="d_kstat" class="small"></span></div>
 <div class="drow">
  <label>Knob <select id="d_kport"><option value="auto">Find it automatically</option><option value="">Off (not used)</option><option value="manual">On a port I type...</option></select></label>
  <input type="text" id="d_kportman" size="8" placeholder="COM7" autocomplete="off" style="display:none"><button id="d_kportuse" style="display:none">Use this port</button>
  <label title="How far the VFO moves when the knob is spun fast">Fast spin <select id="d_kspeed"><option value="1">x1</option><option value="2">x2</option><option value="4">x4</option><option value="8">x8</option></select></label>
  <label>AF volume per click <select id="d_kaf"><option>1</option><option>2</option><option>5</option></select></label>
  <label title="After this many seconds without touching the knob it goes back to VFO A tuning">Back to VFO A after <input type="text" id="d_kret" size="3" inputmode="numeric"> s (0 = never)</label>
 </div>
 <div id="d_ktable" class="ktable" aria-label="Knob functions"></div>
 <div class="drow"><button id="d_kdef">Default functions</button>
  <span class="small">Turning the knob does what its mode says (VFO A, AF volume, AGC gain ...); the presses below change the mode or run a function. <b>Try</b> runs a function as if you pressed it. Only one program can use the knob: remove it from DDUtil (or close DDUtil) first.</span></div>
 <div class="dh">Log file</div>
 <div class="drow">
  <label><input type="checkbox" id="d_log"> Write log file</label>
  <label>Size limit <select id="d_logmax"><option value="1">1 MB</option><option value="2">2 MB</option><option value="5">5 MB</option><option value="10">10 MB</option></select></label>
  <span id="d_logstat" class="small"></span>
 </div>
 <div class="dh">LP-100A wattmeter</div>
 <div class="drow">
  <label>LP-100A port <input type="text" id="d_lpport" list="d_ports" size="9" placeholder="COM5" autocomplete="off"></label>
  <datalist id="d_ports"></datalist>
  <label>Baud <select id="d_lpbaud"><option>115200</option><option>57600</option><option>38400</option><option>19200</option><option>9600</option></select></label>
  <button id="d_lpconnect">Connect</button><button id="d_lpdisc">Disconnect</button><button id="d_lpscan">Scan ports</button>
  <span id="d_lpstat" class="small"></span>
 </div>
 <div class="drow" style="margin-top:.6rem">
  <button id="d_done" class="act">Done</button>
  <span class="small"><span id="ver2"></span> <a href="/help" target="_blank" rel="noopener">Open the full help</a>. Bridge settings are saved by the bridge (kpa1500_settings.json); layouts are saved in this browser.</span>
 </div>
</div>
<script type="application/json" id="knobcat">__KNOB_CATALOG__</script>
<div id="tiles"></div>
<div id="thetis"></div>
<div id="msg" class="msg"></div>
<script>
(function(){
'use strict';
const P=new URLSearchParams(location.search), T=P.get('t')||'';
const Q=T?('?t='+encodeURIComponent(T)):'';
const $=id=>document.getElementById(id);
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));

/* ---------------- widget registry ---------------- */
function mk(id,kind,s,f,extra){return Object.assign({id:id,kind:kind,s:s,f:f},extra||{});}
const WIDGETS=[
 mk('tci','chip','TCI','TCI link'),mk('amp','chip','AMP','Amp link'),
 mk('lp','chip','LP','LP-100A link',{needs:'lp'}),mk('freq','chip','MHz','Frequency'),
 mk('ampf','chip','AMP','Amp frequency (follows the radio?)',{defw:2}),
 mk('rx','text','RX','Receive level (no antenna? check)'),
 mk('knob','chip','KNOB','FlexControl knob: what turning does now',{needs:'knob',defw:2}),
 mk('mode','chip','MODE','Amp mode'),mk('tx','chip','TX','RX / TX'),
 mk('fwd','meter','FWD','Amp forward power'),mk('refl','meter','REF','Amp reflected power'),
 mk('swr','meter','SWR','Amp SWR'),mk('drive','meter','DRV','Drive in'),
 mk('gain','meter','GAIN','Amp gain'),mk('temp','meter','TMP','PA temperature'),
 mk('volts','text','V/A','PA volts / amps'),mk('fault','text','FLT','Fault'),
 mk('fan','seg','FAN','Fan: now / minimum speed',{act:'fan_min',defw:2}),
 mk('operate','button','OPR','OPERATE',{act:'operate'}),mk('standby','button','STBY','STANDBY',{act:'standby'}),
 mk('clear_fault','button','CLR','Clear fault',{act:'clear_fault'}),
 mk('atu_inline','button','INL','ATU inline',{act:'atu_inline'}),mk('atu_bypass','button','BYP','ATU bypass',{act:'atu_bypass'}),
 mk('atu_tune','button','TUNE','ATU tune',{act:'atu_tune'}),mk('atu_cancel','button','CNCL','Cancel tune',{act:'atu_cancel'}),
 mk('ant1','button','A1','Antenna 1',{act:'ant1'}),mk('ant2','button','A2','Antenna 2',{act:'ant2'}),
 mk('ant_next','button','NXT','Next antenna',{act:'ant_next'}),
 mk('sot','check','SOT','Standby amp during radio TUNE'),
 mk('power_on','button','ON','Power ON',{act:'power_on'}),mk('power_off','button','OFF','Power OFF',{act:'power_off',danger:true}),
 mk('enable_wol','button','WOL','Enable Wake-on-LAN',{act:'enable_wol'}),
 mk('lpw','meter','LP PWR','LP-100A power',{needs:'lp'}),mk('lps','meter','LP SWR','LP-100A SWR',{needs:'lp'}),
 mk('lpr','meter','LP REF','LP-100A reflected',{needs:'lp'}),mk('lprl','text','RL','Return loss',{needs:'lp'}),
 mk('lpz','text','Z','Impedance / phase',{needs:'lp'}),mk('lprx','text','R+jX','Resistance + reactance',{needs:'lp'}),
 mk('lpd','text','dBm','LP-100A dBm',{needs:'lp'}),mk('cmp','text','A/L','Amp vs LP-100A',{needs:'lp'}),
 mk('lp_alarm','button','ALM','LP alarm',{act:'lp_alarm',needs:'lp'}),mk('lp_mode','button','MODE','LP mode',{act:'lp_mode',needs:'lp'}),
 // one-button toggles (like the Thetis container): lit = on, label shows the state
 mk('pwr_t','toggle','AMP','Amp power ON / OFF'),mk('opr_t','toggle','OPR','Operate / Standby'),
 mk('atu_t','toggle','ATU','ATU inline / bypass'),mk('rtune_t','toggle','TUNE','Radio TUNE (amp to STANDBY first)'),
 mk('tune_t','toggle','ATU TUNE','ATU tune / stop'),
 mk('ant_t','toggle','ANT','Antenna 1 / 2'),mk('sot_t','toggle','SoT','Standby-on-Tune'),
 mk('flt_t','toggle','FLT','Fault / clear'),mk('dmy_t','toggle','DUMMY','DUMMY OK (dummy load on purpose)'),
 mk('fan_t','fanpm','FAN','Fan: now / minimum, - / +')
];
const NEWT=['pwr_t','opr_t','atu_t','rtune_t','tune_t','ant_t','sot_t','flt_t','dmy_t','fan_t'];
const OLDB=['operate','standby','clear_fault','atu_inline','atu_bypass','atu_tune','atu_cancel','ant1','ant2',
 'ant_next','sot','power_on','power_off','fan'];
function tstate(id,s){   // [lit, label, action]
 const amp=!!s.amp;
 switch(id){
  case 'pwr_t':return [amp,amp?'AMP ON':'AMP OFF',amp?'power_off':'power_on'];
  case 'opr_t':return [amp&&s.mode==='OPERATE',!amp?'OPR/STBY':(s.mode==='OPERATE'?'OPERATE':'STANDBY'),'toggle_operate'];
  case 'atu_t':return [amp&&s.atu==='I',!amp?'ATU':(s.atu==='I'?'ATU IN':'ATU BYP'),'toggle_atu'];
  case 'tune_t':return [amp&&!!s.atu_tuning,(amp&&s.atu_tuning)?'STOP ATU':'ATU TUNE',(amp&&s.atu_tuning)?'atu_cancel':'atu_tune'];
  case 'rtune_t':return [!!s.tune_active,s.tune_active?('STOP TUNE'+(s.tune_left!=null?' '+s.tune_left+' s':'')):'TUNE',s.tune_active?'radio_tune_stop':'radio_tune'];
  case 'ant_t':return [amp&&s.ant===1,!amp?'ANT':('ANT '+(s.ant||'?')),'toggle_ant'];   // lit on ANT 1, like Thetis
  case 'sot_t':return [!!s.standby_on_tune,s.standby_on_tune?'SoT ON':'SoT OFF','toggle_sot'];
  case 'flt_t':return [amp&&!!s.fault,(amp&&s.fault)?'FAULT - CLR':'NO FAULT','clear_fault'];
  case 'dmy_t':return [!!(s.noant&&s.noant.dummy),'DUMMY OK','dummy_ok'];
 }
 return [false,'',null];
}
const BYID={};WIDGETS.forEach(w=>BYID[w.id]=w);
const IDS=WIDGETS.map(w=>w.id);

/* ---------------- layout model (pure functions) ---------------- */
const DEFSET={scale:1,cell:9.5,labels:'short',bars:true,theme:'auto',hdr:true,style:'tiles'};
function normalize(L){
 L=L||{};const order=[];
 (Array.isArray(L.order)?L.order:[]).forEach(id=>{if(BYID[id]&&order.indexOf(id)<0)order.push(id);});
 // a tile added in a newer version goes next to the tile before it in the list
 IDS.forEach((id,k)=>{if(order.indexOf(id)>=0)return;const p=k?order.indexOf(IDS[k-1]):-1;
  if(p>=0)order.splice(p+1,0,id);else order.push(id);});
 const hidden={};Object.keys(L.hidden||{}).forEach(id=>{if(BYID[id]&&L.hidden[id])hidden[id]=true;});
 const span={};Object.keys(L.span||{}).forEach(id=>{const v=Math.round(+L.span[id]);if(BYID[id]&&v>=1&&v<=4)span[id]=v;});
 const s=Object.assign({},DEFSET,L.settings||{});
 s.scale=clamp(+s.scale||1,0.5,2.5);s.cell=clamp(+s.cell||9.5,4,30);
 s.labels=s.labels==='full'?'full':'short';s.bars=s.bars!==false;
 s.theme=['light','dark'].indexOf(s.theme)>=0?s.theme:'auto';s.hdr=s.hdr!==false;
 s.style=s.style==='thetis'?'thetis':'tiles';
 const out={order:order,hidden:hidden,span:span,settings:s,v:2};
 if(L.v!==2){
  // one-time update of a layout saved before the one-button toggles existed:
  // show the toggles where the old buttons were, and hide the old separate buttons
  const anyOld=OLDB.some(id=>!hidden[id]&&order.indexOf(id)>=0);
  const rest=order.filter(id=>NEWT.indexOf(id)<0);
  let at=rest.findIndex(id=>OLDB.indexOf(id)>=0&&!hidden[id]);if(at<0)at=rest.length;
  out.order=rest.slice(0,at).concat(NEWT,rest.slice(at));
  OLDB.forEach(id=>{hidden[id]=true;});
  NEWT.forEach(id=>{if(anyOld)delete hidden[id];else hidden[id]=true;});
 }
 return out;
}
function showOnly(ids,first){
 const hidden={};IDS.forEach(id=>{if(ids.indexOf(id)<0)hidden[id]=true;});
 const order=ids.slice();IDS.forEach(id=>{if(order.indexOf(id)<0)order.push(id);});
 return {order:order,hidden:hidden};
}
function preset(name){
 const n=String(name||'').toLowerCase();let L;
 if(n==='compact'){
  L=showOnly(['ampf','drive','fwd','gain','swr','tx','fault','opr_t','pwr_t']);
  L.span={drive:2,fwd:2};L.settings={scale:0.9,cell:7.5,labels:'short',bars:true,hdr:false};
 }else if(n==='telemetry'){
  L=showOnly(WIDGETS.filter(w=>['button','check','toggle','fanpm'].indexOf(w.kind)<0).map(w=>w.id));L.settings={};
 }else if(n==='controls'){
  L=showOnly(['tci','amp','mode','tx','ampf','rx'].concat(NEWT,['lp_alarm','lp_mode']));L.settings={};
 }else if(n==='full'){L={order:IDS.slice(),hidden:{},span:{},settings:{},v:2};}
 else if(n==='thetis'){L={order:IDS.slice(),hidden:{},span:{},settings:{style:'thetis'},v:2};}
 else if(n==='default'){L=showOnly(IDS.filter(id=>OLDB.indexOf(id)<0&&id!=='enable_wol'));L.settings={};}
 else return null;
 L.v=2;   // built-in layouts already use the one-button toggles
 return normalize(L);
}
function moveTile(L,id,dir){
 const i=L.order.indexOf(id);if(i<0)return;
 // move relative to neighbours that are currently shown or in edit view (all), simple swap
 const j=clamp(i+dir,0,L.order.length-1);if(j===i)return;
 L.order.splice(i,1);L.order.splice(j,0,id);
}
function moveBefore(L,id,targetId){
 if(id===targetId)return;const i=L.order.indexOf(id);if(i<0||L.order.indexOf(targetId)<0)return;
 L.order.splice(i,1);L.order.splice(L.order.indexOf(targetId),0,id);
}
function cycleSpan(L,id){const d=BYID[id].defw||1;const nx=((L.span[id]||d)%4)+1;if(nx===d)delete L.span[id];else L.span[id]=nx;}
function validateImport(text){
 let o;try{o=JSON.parse(text);}catch(e){return {ok:false,error:'Not valid JSON'};}
 if(!o||typeof o!=='object'||!Array.isArray(o.order))return {ok:false,error:'Not a layout (missing order list)'};
 const known=o.order.filter(id=>BYID[id]).length;
 if(!known)return {ok:false,error:'No recognised tiles in this layout'};
 return {ok:true,layout:normalize(o)};
}
window.__layout={normalize:normalize,preset:preset,moveTile:moveTile,moveBefore:moveBefore,
 cycleSpan:cycleSpan,validateImport:validateImport,WIDGETS:WIDGETS};

/* ---------------- storage ---------------- */
const KEY='kpa_layouts_v1';
function loadAll(){try{const o=JSON.parse(localStorage.getItem(KEY)||'{}');return (o&&typeof o==='object')?o:{};}catch(e){return {};}}
function saveAll(){try{localStorage.setItem(KEY,JSON.stringify(ALL));}catch(e){}}
let ALL=loadAll();
let NAME=(P.get('layout')||'Default').slice(0,24);
function ensure(name){
 if(!ALL[name]){ALL[name]=preset(name)||normalize(ALL.Default||preset('Full'));saveAll();}
 else{const was=ALL[name].v;ALL[name]=normalize(ALL[name]);if(was!==2)saveAll();}
 return ALL[name];
}
let L=ensure(NAME);
function persist(){ALL[NAME]=L;saveAll();}

/* ---------------- DOM construction ---------------- */
const R={};           // widget refs
const grid=$('tiles');
function build(w){
 const t=document.createElement('div');t.className='tile k-'+w.kind;t.dataset.id=w.id;
 const r={tile:t};
 const tools=document.createElement('div');tools.className='tools';
 function tb(txt,label,fn){const b=document.createElement('button');b.type='button';b.textContent=txt;
  b.setAttribute('aria-label',label+' '+w.f);b.title=label;
  b.addEventListener('click',e=>{e.stopPropagation();fn();});tools.appendChild(b);return b;}
 tb('\u25C0','Move earlier',()=>{moveTile(L,w.id,-1);changed();});
 tb('\u25B6','Move later',()=>{moveTile(L,w.id,1);changed();});
 tb('\u2194','Change width',()=>{cycleSpan(L,w.id);changed();});
 r.hideBtn=tb('\u2715','Hide / show',()=>{if(L.hidden[w.id])delete L.hidden[w.id];else L.hidden[w.id]=true;changed();});
 t.appendChild(tools);
 const inner=document.createElement('div');inner.className='inner';t.appendChild(inner);
 if(w.kind==='toggle'){
  const b=document.createElement('button');b.type='button';
  b.addEventListener('click',()=>{if(S){const a=tstate(w.id,S)[2];if(a)act(a);}});inner.appendChild(b);r.btn=b;
 }else if(w.kind==='fanpm'){
  const h=document.createElement('div');h.className='t-head';
  const l=document.createElement('span');l.className='t-lbl';const v=document.createElement('span');v.className='t-val';
  h.appendChild(l);h.appendChild(v);inner.appendChild(h);r.lbl=l;r.val=v;
  const row=document.createElement('div');row.className='segs';
  [['\u2212','fan_down','Lower the minimum fan speed'],['+','fan_up','Raise the minimum fan speed']].forEach(x=>{
   const b=document.createElement('button');b.type='button';b.textContent=x[0];b.setAttribute('aria-label',x[2]);
   b.addEventListener('click',()=>act(x[1]));row.appendChild(b);});
  inner.appendChild(row);
 }else if(w.kind==='button'){
  const b=document.createElement('button');b.type='button';b.addEventListener('click',()=>act(w.act));
  if(w.danger)b.classList.add('danger');inner.appendChild(b);r.btn=b;
 }else if(w.kind==='check'){
  const lab=document.createElement('label');const c=document.createElement('input');c.type='checkbox';
  c.addEventListener('change',()=>act(c.checked?'sot_on':'sot_off'));
  const sp=document.createElement('span');lab.appendChild(c);lab.appendChild(sp);inner.appendChild(lab);r.chk=c;r.lbl=sp;
 }else if(w.kind==='seg'){
  const h=document.createElement('div');h.className='t-head';
  const l=document.createElement('span');l.className='t-lbl';const v=document.createElement('span');v.className='t-val';
  h.appendChild(l);h.appendChild(v);inner.appendChild(h);r.lbl=l;r.val=v;
  const row=document.createElement('div');row.className='segs';r.segs=[];
  for(let n=0;n<=5;n++){const b=document.createElement('button');b.type='button';b.textContent=String(n);
   b.setAttribute('aria-label','Minimum fan speed '+n);b.addEventListener('click',()=>act(w.act,{speed:n}));
   row.appendChild(b);r.segs.push(b);}
  inner.appendChild(row);
 }else{
  const h=document.createElement('div');h.className='t-head';
  const l=document.createElement('span');l.className='t-lbl';const v=document.createElement('span');v.className='t-val';
  h.appendChild(l);h.appendChild(v);inner.appendChild(h);r.lbl=l;r.val=v;
  if(w.kind==='meter'){const b=document.createElement('div');b.className='bar';const f=document.createElement('div');
   f.className='fill';const pk=document.createElement('div');pk.className='peak';b.appendChild(pk);b.appendChild(f);
   inner.appendChild(b);r.fill=f;r.peak=pk;r.hist=[];}
 }
 // drag and drop (edit mode only)
 t.addEventListener('dragstart',e=>{if(!editing){e.preventDefault();return;}e.dataTransfer.setData('text/plain',w.id);e.dataTransfer.effectAllowed='move';});
 t.addEventListener('dragover',e=>{if(editing){e.preventDefault();t.classList.add('dragover');}});
 t.addEventListener('dragleave',()=>t.classList.remove('dragover'));
 t.addEventListener('drop',e=>{if(!editing)return;e.preventDefault();t.classList.remove('dragover');
  const id=e.dataTransfer.getData('text/plain');if(BYID[id]){moveBefore(L,id,w.id);changed();}});
 R[w.id]=r;return r;
}
WIDGETS.forEach(build);

/* ---------------- Thetis look (same meters and buttons as the Thetis containers) ---------------- */
const SVGNS='http://www.w3.org/2000/svg';
function sv(tag,at,parent){const e=document.createElementNS(SVGNS,tag);Object.keys(at).forEach(k=>e.setAttribute(k,at[k]));if(parent)parent.appendChild(e);return e;}
const TBARS=[
 {v:'amp_fwd',t:'KPA1500 Fwd',u:'W',min:0,max:1750,hi:1500,step:175},
 {v:'amp_swr',t:'KPA1500 SWR',u:':1',min:1,max:3,hi:2,step:0.2},
 {v:'amp_drive',t:'Drive',u:'W',min:0,max:100,hi:80,step:10},
 {v:'lp_pwr',t:'LP-100A Pwr',u:'W',min:0,max:1750,hi:1500,step:175,lp:true},
 {v:'lp_swr',t:'LP-100A SWR',u:':1',min:1,max:3,hi:2,step:0.2,lp:true}];
const TX0=4,TX1=396;
function tx(b,v){return TX0+(TX1-TX0)*clamp((v-b.min)/(b.max-b.min),0,1);}
function tbar(b){
 const s=sv('svg',{viewBox:'0 0 400 36',role:'img','aria-label':b.t});
 sv('text',{x:200,y:10,'font-size':10,fill:'#9a9a9a','text-anchor':'middle'},s).textContent=b.t;
 b.cur=sv('text',{x:TX0,y:10,'font-size':11,fill:'#fff'},s);
 b.pk=sv('text',{x:TX1,y:10,'font-size':11,fill:'#ff3030','text-anchor':'end'},s);
 const xh=tx(b,b.hi);
 b.band=sv('rect',{x:TX0,y:13,width:0,height:6,fill:'#ffe000'},s);
 b.fl=sv('rect',{x:TX0,y:13,width:0,height:6,fill:'#1e90ff'},s);
 b.fh=sv('rect',{x:xh,y:13,width:0,height:6,fill:'#ff2020'},s);
 sv('line',{x1:TX0,y1:20,x2:xh,y2:20,stroke:'#fff','stroke-width':1},s);
 sv('line',{x1:xh,y1:20,x2:TX1,y2:20,stroke:'#ff2020','stroke-width':1},s);
 const n=Math.round((b.max-b.min)/b.step);
 for(let i=0;i<=n;i++){const v=b.min+i*b.step,x=tx(b,v),c=(v>b.hi+1e-9)?'#ff2020':'#fff';
  sv('line',{x1:x,y1:20,x2:x,y2:23,stroke:c,'stroke-width':1},s);
  if(i>0&&i<n)sv('text',{x:x,y:33,'font-size':9.5,fill:c,'text-anchor':'middle'},s).textContent=b.step<1?v.toFixed(1):String(Math.round(v));}
 b.hist=[];return s;
}
function fmtv(b,v){return (+v||0).toFixed(1)+b.u;}
function setTbar(b,v){
 v=+v||0;const now=Date.now();b.hist.push([now,v]);while(b.hist.length&&now-b.hist[0][0]>PEAK_MS)b.hist.shift();
 let m=v;b.hist.forEach(h=>{if(h[1]>m)m=h[1];});
 const x=tx(b,v),xh=tx(b,b.hi),xp=tx(b,m);
 b.fl.setAttribute('width',Math.max(0,Math.min(x,xh)-TX0));
 b.fh.setAttribute('width',Math.max(0,x-xh));
 b.band.setAttribute('x',x);b.band.setAttribute('width',Math.max(0,xp-x));
 b.cur.textContent=fmtv(b,v);b.pk.textContent=fmtv(b,m);
}
const TBTN={   // id: [lit label, dark label, lit?, action when lit, action when dark, needs, tooltip, list name]
 title:['Title','Title',null,'','','','Title line (the window name)','Title line'],
 opr:['OPERATE','STANDBY',m=>m.amp_operate==1,'toggle_operate','toggle_operate','','Operate / Standby','OPERATE / STANDBY'],
 atu:['ATU IN','ATU BYP',m=>m.amp_atu_inline==1,'toggle_atu','toggle_atu','','ATU inline / bypass','ATU IN / BYP'],
 ant:['ANT 1','ANT 2',m=>m.amp_ant==1,'toggle_ant','toggle_ant','','Antenna 1 / 2','ANT 1 / 2'],
 amp:['AMP ON','AMP OFF',m=>m.amp_online==1,'power_off','power_on','','Amp power: press to switch off / on','AMP ON / OFF'],
 tune:['STOP TUNE','TUNE',m=>m.amp_tune_active==1,'radio_tune_stop','radio_tune','','Radio TUNE the safe way: amp to STANDBY first, then the radio keys','TUNE (radio)'],
 atutune:['STOP ATU','ATU TUNE',m=>m.amp_atu_tuning==1,'atu_cancel','atu_tune','','Amp ATU tune / stop','ATU TUNE'],
 sot:['SoT ON','SoT OFF',m=>m.amp_sot==1,'toggle_sot','toggle_sot','','Standby-on-Tune','SoT'],
 dummy:['DUMMY OK','DUMMY OK',m=>m.dummy_ok==1,'dummy_ok','dummy_ok','','DUMMY OK: a dummy load is connected on purpose (silences the no-antenna warning on this band)','DUMMY OK'],
 fault:['FAULT - CLR','NO FAULT',m=>m.amp_fault!=0,'clear_fault','clear_fault','','Fault: press to clear','FAULT clear'],
 lpalarm:['LP ALARM','LP ALARM',null,'lp_alarm','lp_alarm','lp','LP-100A alarm','LP ALARM'],
 lpmode:['LP MODE','LP MODE',null,'lp_mode','lp_mode','lp','LP-100A mode','LP MODE'],
 fandn:['FAN -','FAN -',null,'fan_down','fan_down','','Lower the minimum fan speed','FAN -'],
 fanup:['FAN +','FAN +',null,'fan_up','fan_up','','Raise the minimum fan speed','FAN +'],
 gap:['','',null,null,null,'','','(blank space)']};
const TB_STD=['title','opr','atu','ant','amp','tune','atutune','sot','dummy','fault','lpalarm','lpmode','fandn','fanup'];
const TH={};
(function buildThetis(){
 const host=$('thetis');
 function line(par,col,bold){const d=document.createElement('div');d.className='tl';d.style.color=col;if(bold)d.style.fontWeight='700';par.appendChild(d);return d;}
 function warn(par){const d=document.createElement('div');d.className='tw';d.textContent='!!  BRIDGE NOT RUNNING - data frozen  !!';par.appendChild(d);}
 const te=document.createElement('div');te.className='tc';te.setAttribute('aria-label','KPA1500 Telemetry');
 TH.tbody=document.createElement('div');te.appendChild(TH.tbody);TH.tel={};TH.tkey='';TH.line=line;
 function naLine(par){const d=document.createElement('div');d.className='tna';par.appendChild(d);return d;}
 TH.na1=naLine(te);warn(te);
 const co=document.createElement('div');co.className='tc';co.setAttribute('aria-label','KPA1500 Controls');
 TH.title=line(co,'#ffff80',true);TH.title.textContent='KPA1500 Controls';
 TH.c1=line(co,'#00e5ff');TH.f2=line(co,'#00ff00',true);
 const g=document.createElement('div');g.className='tbtns';TH.grid=g;TH.btns=[];TH.key='';
 co.appendChild(g);TH.na2=naLine(co);warn(co);
 const kwin=document.createElement('div');kwin.className='tc';kwin.setAttribute('aria-label','KPA1500 Knob');
 TH.kwbody=document.createElement('div');kwin.appendChild(TH.kwbody);warn(kwin);TH.kwin=kwin;TH.kwkey='';TH.kwel={};
 host.appendChild(te);host.appendChild(co);host.appendChild(kwin);
})();
function buildThetisButtons(tb){
 const g=TH.grid,key=JSON.stringify(tb);if(key===TH.key)return;TH.key=key;
 while(g.firstChild)g.removeChild(g.firstChild);TH.btns=[];
 g.style.gridTemplateColumns='repeat('+tb.columns+',1fr)';
 tb.order.forEach(id=>{const d=TBTN[id];if(!d||id==='title')return;const b=document.createElement('button');b.type='button';
  b.textContent=d[1];b.title=d[6];
  if(id==='gap'){b.disabled=true;b.setAttribute('aria-hidden','true');}
  else b.addEventListener('click',()=>{if(!S||document.body.classList.contains('stale'))return;
   const lit=d[2]?d[2](S.mm||{}):false;act(lit?d[3]:d[4]);});
  g.appendChild(b);TH.btns.push([b,d]);});
}
const TMITEM={   // id: [list name, colour, bold, needs]
 title:['Title line','#ffff80',true,''],status:['Status line (power, mode, ATU, ANT)','#00e5ff',false,''],
 freq:['AMP frequency + RX level line','#00ff00',true,''],fwd:['Forward power bar','',false,''],
 swr:['SWR bar','',false,''],drive:['Drive bar','',false,''],refl:['Refl / gain / drive-from line','#fff',false,''],
 pa:['PA temp / volts / amps / fan line','#fff',false,''],fault:['Fault / Stby-on-Tune line','#ffa500',false,''],
 lpp:['LP-100A power bar','',false,'lp'],lps:['LP-100A SWR bar','',false,'lp'],
 lptext:['LP-100A R / X / |Z| / RL line','#00ff00',false,'lp'],gap:['(blank line)','#fff',false,'']};
const TM_STD=['status','freq','fwd','swr','drive','refl','pa','fault','lpp','lps','lptext'];
const TMBAR={fwd:0,swr:1,drive:2,lpp:3,lps:4};
function buildTele(tm,lp){
 const key=JSON.stringify(tm)+(lp?'L':'');if(key===TH.tkey)return;TH.tkey=key;
 const box=TH.tbody;while(box.firstChild)box.removeChild(box.firstChild);TH.tel={};
 tm.order.forEach((id,i)=>{const d=TMITEM[id];if(!d||(d[3]==='lp'&&!lp))return;
  if(id in TMBAR){box.appendChild(tbar(TBARS[TMBAR[id]]));return;}
  const el=TH.line(box,d[1],d[2]);if(id==='gap')el.innerHTML='&nbsp;';TH.tel[id]=el;});
}
const verTitle=(t,m)=>String(t||'').split('{ver}').join(m.bridge_version||'');
const KWITEM={title:['Title line','#ffff80',true],now:['Knob mode now (what turning does)','#00ff00',true],
 knob:['Knob press functions','#fff',false],b1:['Button 1 functions','#fff',false],b2:['Button 2 functions','#fff',false],
 b3:['Button 3 functions','#fff',false],status:['Connection line','#00e5ff',false],gap:['(blank line)','#fff',false]};
const KW_STD=['title','now','knob','b1','b2','b3','status'];
function buildKw(kw){
 const key=JSON.stringify(kw);if(key===TH.kwkey)return;TH.kwkey=key;
 const box=TH.kwbody;while(box.firstChild)box.removeChild(box.firstChild);TH.kwel={};
 TH.kwin.style.display=kw.enabled?'':'none';
 kw.order.forEach(id=>{const d=KWITEM[id];if(!d)return;const el=TH.line(box,d[1],d[2]);if(id==='gap')el.innerHTML='&nbsp;';TH.kwel[id]=el;});
}
function updateThetis(s){
 buildThetisButtons(s.thetis_buttons||{order:TB_STD,columns:4});
 const m=s.mm||{},lp=!!s.lp_enabled,p1=x=>(+x||0).toFixed(1);
 const tm=s.thetis_meters||{order:TM_STD,title:'KPA1500 {ver} Telemetry'};buildTele(tm,lp);
 const T_=TH.tel,set=(id,txt)=>{if(T_[id])T_[id].textContent=txt;};
 const verInTitle=tm.order.indexOf('title')>=0&&String(tm.title).indexOf('{ver}')>=0;
 set('title',verTitle(tm.title,m));
 set('status','KPA1500  '+m.amp_power+'  '+m.amp_mode+'   ATU '+m.amp_atu+'   ANT '+m.amp_ant);
 set('freq','AMP  '+(m.amp_freq_line||'--- MHz')+'  '+(m.rx_text||'')+(verInTitle?'':'   '+(m.bridge_version||'')));
 TBARS.forEach((b,k)=>{if((!b.lp||lp)&&b.cur&&b.cur.isConnected)setTbar(b,m[b.v]);});
 set('refl','Refl '+m.amp_refl+' W   Gain '+p1(m.amp_gain_db)+' dB   Drive from '+m.amp_drive_src);
 set('pa','PA '+m.amp_temp+' C   '+p1(m.amp_volts)+' V   '+m.amp_amps+' A   Fan '+m.amp_fan+' (min '+m.amp_fan_min+')');
 set('fault','Fault: '+m.amp_fault_text+'   Stby-on-Tune: '+m.amp_sot_text);
 if(lp)set('lptext','LP-100A  R '+p1(m.lp_r)+'  X '+p1(m.lp_x)+'  |Z| '+p1(m.lp_z)+'  RL '+p1(m.lp_rl)+' dB');
 TH.title.textContent=verTitle((s.thetis_buttons||{}).title||'KPA1500 {ver} Controls',m);
 TH.title.style.display=((s.thetis_buttons||{order:TB_STD}).order.indexOf('title')>=0)?'':'none';
 {const kw=s.thetis_knobwin||{enabled:true,order:KW_STD,title:'FlexControl Knob {ver}'};buildKw(kw);
  const E=TH.kwel,st=(id,x)=>{if(E[id])E[id].textContent=x;};
  st('title',verTitle(kw.title,m));st('now','KNOB:  '+(m.knob_now||'--'));st('knob','Knob   '+(m.knob_k||''));
  st('b1','B1     '+(m.knob_b1||''));st('b2','B2     '+(m.knob_b2||''));st('b3','B3     '+(m.knob_b3||''));st('status',m.knob_status||'');}
 TH.f2.textContent='AMP  '+(m.amp_freq_line||'--- MHz')+'  '+(m.rx_text||'');
 [TH.na1,TH.na2].forEach(d=>{d.textContent=m.noant_text||'';d.classList.toggle('on',m.noant==1);});
 TH.c1.textContent=m.amp_power+'  '+m.amp_mode+'   Fan '+m.amp_fan+' (min '+m.amp_fan_min+')   Fault: '+m.amp_fault_text;
 const stale=document.body.classList.contains('stale');
 TH.btns.forEach(x=>{const b=x[0],d=x[1];
  b.style.display=(d[5]==='lp'&&!lp)?'none':'';
  const lit=!stale&&!!(d[2]&&d[2](m));b.classList.toggle('lit',lit);b.textContent=lit?d[0]:d[1];});
}

/* ---------------- rendering ---------------- */
let editing=false,S=null;
function applySettings(){
 const s=L.settings,root=document.documentElement;
 root.style.setProperty('--s',s.scale);root.style.setProperty('--cell',s.cell);
 if(s.theme==='auto')root.removeAttribute('data-theme');else root.setAttribute('data-theme',s.theme);
 document.body.classList.toggle('nobars',!s.bars);
 document.body.classList.toggle('nohdr',!s.hdr&&!editing);
 document.body.classList.toggle('thv',s.style==='thetis');
}
function visible(w){
 if(L.hidden[w.id])return false;
 if(w.needs==='lp'&&S&&!S.lp_enabled)return false;
 if(w.needs==='knob'&&S&&!(S.knob&&S.knob.port))return false;
 return true;
}
function render(){
 applySettings();
 while(grid.firstChild)grid.removeChild(grid.firstChild);
 L.order.forEach(id=>{
  const w=BYID[id],r=R[id],vis=visible(w);
  if(!vis&&!editing)return;
  r.tile.style.setProperty('--w',L.span[id]||w.defw||1);
  r.tile.classList.toggle('is-hidden',!vis);
  r.tile.draggable=editing;
  r.hideBtn.textContent=L.hidden[id]?'\uFF0B':'\u2715';
  grid.appendChild(r.tile);
 });
 document.body.classList.toggle('editing',editing);
 if(S)update(S);syncDrawer();
}
function changed(){persist();render();}

/* ---------------- live data ---------------- */
function lab(w,suffix){return (L.settings.labels==='full'?w.f:w.s)+(suffix||'');}
const PEAK_MS=4000;   // peak band holds the highest reading of the last 4 seconds
function setBar(r,f,warn,bad){if(!r.fill)return;f=clamp(f||0,0,1);r.fill.style.width=(f*100)+'%';
 r.fill.style.background=(f>=bad)?'var(--bad)':(f>=warn)?'var(--warn)':'var(--ok)';
 if(r.peak){const now=Date.now();r.hist.push([now,f]);while(r.hist.length&&now-r.hist[0][0]>PEAK_MS)r.hist.shift();
  let m=0;r.hist.forEach(h=>{if(h[1]>m)m=h[1];});r.peak.style.width=(m*100)+'%';r.peak.classList.toggle('on',m>f+0.004);}}
function val(r,txt,cls){r.val.textContent=txt;r.val.className='t-val'+(cls?' '+cls:'');}
function update(s){
 const lp=s.lp,full=L.settings.labels==='full';
 {const b=$('ampbadge'),dn=$('ampdown');
  b.textContent='AMP '+(s.power||'?')+(s.amp&&s.mode?' - '+s.mode:'');
  b.className=s.amp?'on':(s.power==='OFF'?'off':'nolink');
  if(s.amp){dn.style.display='none';}
  else{dn.style.display='block';
   dn.textContent=s.power==='OFF'?(s.on_network?'AMPLIFIER OFF - it is on the network at '+s.amp_ip+' but not answering (switched off or asleep). Use Power ON to wake it.'
     :'AMPLIFIER OFF - not answering at '+s.amp_ip+':'+s.amp_port+' (switched off, lost power, or the network cable is out)')
     :'AMPLIFIER NOT FOUND at '+s.amp_ip+':'+s.amp_port+' (never seen at this address - check the address, power and cable)';}}
 WIDGETS.forEach(w=>{
  const r=R[w.id];if(!r.tile.parentNode)return;
  if(r.lbl&&w.kind!=='check')r.lbl.textContent=lab(w);
  if(w.kind==='toggle'){const t=tstate(w.id,s);r.btn.textContent=t[1];r.btn.title=w.f;
   r.btn.classList.toggle(w.id==='flt_t'?'alarm':'act',!!t[0]);return;}
  if(!s.amp&&['ampf','fwd','refl','swr','gain','temp','volts','fault','fan','fan_t'].indexOf(w.id)>=0){
   val(r,'-');setBar(r,0,2,2);if(r.segs)r.segs.forEach(b=>b.classList.remove('act'));return;}
  switch(w.id){
   case 'tci':val(r,s.tci?'ok':'--',s.tci?'good':'bad');break;
   case 'amp':val(r,s.amp?'ON':(s.power==='OFF'?'OFF':'--'),s.amp?'good':'bad');break;
   case 'lp':val(r,lp?'ok':'--',lp?'good':'bad');break;
   case 'freq':val(r,s.freq_khz?(s.freq_khz/1000).toFixed(3):'--');break;
   case 'knob':{const k=s.knob||{};val(r,k.connected?String(k.mode_name||'').split(' (')[0]:(k.port?'not connected':'off'),
     k.connected?(k.mode==='vfoa'?'good':'warn'):'bad');r.tile.title=k.connected?('FlexControl on '+k.device):(k.error||'');break;}
   case 'rx':{const na=s.noant||{};
    val(r,(na.dbm!=null&&na.live)?na.dbm.toFixed(0)+' dBm'+(full&&na.band?' ('+na.band+' m)':''):'--',
     na.warn?'bad':(na.state==='dummy'?'warn':(na.state==='ok'?'good':'')));
    r.tile.title={off:'No-antenna check is off',na:'No receive level from Thetis',nolimit:'No limit set for this band',
     ok:'Receive level is normal',low:'Below the limit - no antenna?',tx:'Transmitting with no antenna?',dummy:'DUMMY OK pressed'}[na.state]||'';
    break;}
   case 'ampf':{const f=s.follow||'';
    if(s.amp_khz){const ok=f==='= radio';
     val(r,(s.amp_khz/1000).toFixed(3)+(full?' MHz':'')+(ok?' \u2713':(f.indexOf('radio ')===0?' \u2260 '+(s.freq_khz/1000).toFixed(3):'')),ok?'good':'bad');
     r.tile.title=ok?'The amp is on the radio frequency':'The amp is NOT on the radio frequency';}
    else{val(r,s.freq_khz&&s.amp?(s.freq_khz/1000).toFixed(3)+' sent':'--');r.tile.title='The amp does not report its frequency: showing what was sent';}
    break;}
   case 'mode':val(r,(s.mode||'?')+(s.tune_active?' (tune)':''),s.mode==='OPERATE'?'good':(!s.amp?'bad':''));break;
   case 'tx':val(r,s.transmitting?'TX':'RX',s.transmitting?'bad':'');break;
   case 'fwd':val(r,s.fwd+' W');setBar(r,s.fwd/1500,.8,.95);break;
   case 'refl':val(r,s.refl+' W');setBar(r,s.refl/150,.3,.6);break;
   case 'swr':val(r,s.swr.toFixed(1)+':1');setBar(r,(s.swr-1)/3,.33,.66);break;
   case 'drive':val(r,s.drive.toFixed(0)+' W'+(s.drive_src==='radio'?(full?' (radio)':' R'):''));setBar(r,s.drive/100,.8,.95);break;
   case 'gain':{const g=(s.mode==='OPERATE'&&s.drive>0&&s.fwd>0)?s.fwd/s.drive:null;
    val(r,g?(10*Math.log10(g)).toFixed(1)+' dB':'-');setBar(r,g?g/40:0,2,2);break;}
   case 'temp':val(r,s.temp!=null?s.temp+' C':'-');setBar(r,s.temp!=null?(s.temp-20)/80:0,.6,.85);break;
   case 'volts':val(r,(s.volts!=null?s.volts.toFixed(1):'-')+' V '+(s.amps!=null?s.amps:'-')+' A');break;
   case 'fault':val(r,s.fault?(s.fault.toString(16).toUpperCase().padStart(2,'0')+(full?' '+s.fault_text:'')):'none',s.fault?'bad':'good');break;
   case 'lpw':if(lp){val(r,lp.pwr.toFixed(0)+' W');setBar(r,lp.pwr/1500,.8,.95);}else val(r,'-');break;
   case 'lps':if(lp){val(r,lp.swr.toFixed(2)+':1');setBar(r,(lp.swr-1)/3,.33,.66);}else val(r,'-');break;
   case 'lpr':if(lp){val(r,lp.refl.toFixed(1)+' W');setBar(r,lp.refl/150,.3,.6);}else val(r,'-');break;
   case 'lprl':val(r,lp&&lp.rl!=null?lp.rl.toFixed(1)+' dB':'-');break;
   case 'lpz':val(r,lp?lp.z.toFixed(1)+' / '+lp.phase.toFixed(0)+'\u00B0':'-');break;
   case 'lprx':val(r,lp?lp.r.toFixed(1)+(lp.x<0?' -j':' +j')+Math.abs(lp.x).toFixed(1):'-');break;
   case 'lpd':val(r,lp?lp.dbm.toFixed(1):'-');break;
   case 'cmp':val(r,(s.fwd>5&&lp&&lp.pwr>5)?(s.fwd+' / '+lp.pwr.toFixed(0)+' W'):'-');break;
   case 'sot':r.chk.checked=!!s.standby_on_tune;r.lbl.textContent=lab(w);break;
   case 'fan_t':val(r,s.fan!=null?(s.fan+' / min '+(s.fan_min!=null?s.fan_min:'?')):'-');break;
   case 'fan':val(r,s.fan!=null?(s.fan+' / min '+(s.fan_min!=null?s.fan_min:'?')):'-');
    r.segs.forEach((b,n)=>b.classList.toggle('act',s.fan_min===n));break;
   case 'lp_alarm':r.btn.textContent=lab(w)+(lp?': '+lp.alarm_txt:'');break;
   case 'lp_mode':r.btn.textContent=lab(w)+(lp?': '+lp.mode_txt:'');break;
   default:
    if(r.btn){r.btn.textContent=lab(w);
     const on=({operate:s.mode==='OPERATE',standby:s.mode==='STANDBY',atu_inline:s.atu==='I',
      atu_bypass:s.atu==='B',atu_tune:!!s.atu_tuning,ant1:s.ant===1,ant2:s.ant===2})[w.id];
     r.btn.classList.toggle('act',!!on);}
  }
 });
 {const na=s.noant||{},w=$('antwarn');
  w.classList.toggle('on',!!na.warn);w.classList.toggle('tx',na.state==='tx');
  if(na.warn)$('antwarn_t').textContent=na.state==='tx'
   ?'!! TRANSMITTING - NO ANTENNA? The receive level was '+na.dbm.toFixed(0)+' dBm on '+na.band+' m. Check the antenna / dummy load !!'
   :'NO ANTENNA? Receive level '+na.dbm.toFixed(0)+' dBm on '+na.band+' m is below the limit '+na.limit+' dBm.'
    +(na.hold?' The amp is held in STANDBY.':'')+' Check the antenna - press DUMMY OK if a dummy load is connected.';}
 {const dg=s.drive_guard||{},w=$('drvwarn');
  w.classList.toggle('on',!!dg.warn);w.classList.toggle('tx',dg.state==='tx');w.textContent=dg.text||'';}
 if(editing){syncNa(s);syncDg(s);syncTb(s);syncPw(s);syncKnob(s);}
 if(s.mm)updateThetis(s);
 $('dry').textContent=s.dry_run?'[DRY-RUN: buttons do not send]':'';
 if(editing){lpStatus(s);ampStatus(s);if(document.activeElement!==$('d_confirm'))$('d_confirm').checked=s.confirm_off!==false;
  if(document.activeElement!==$('d_thetisoff'))$('d_thetisoff').checked=s.thetis_off!==false;
  if(document.activeElement!==$('d_blockofftx'))$('d_blockofftx').checked=s.block_off_tx!==false;
  const lg=s.log||{};
  if(document.activeElement!==$('d_log'))$('d_log').checked=!!lg.log_enabled;
  if(document.activeElement!==$('d_logmax'))$('d_logmax').value=String(lg.log_max_mb||2);
  $('d_logstat').textContent=lg.log_enabled?('log '+lg.log_kb+' KB of '+lg.log_max_mb+' MB ('+lg.log_file+')'):(lg.log_file?'log file is OFF':'no log file name set');}
 const pv='__VERSION__';
 $('ver').textContent='v'+s.version;
 $('ver2').textContent='Panel v'+pv+' / bridge v'+s.version+(pv!==s.version?' - OLD PAGE, press Ctrl+F5':'');
 if(pv!==s.version)$('ver').textContent+=' (reload: Ctrl+F5)';
 if(s.msg&&!$('msg').dataset.local)$('msg').textContent=s.msg;
}
async function refresh(){
 try{const r=await fetch('/api/state'+Q);
  if(r.status===403){$('pwbox').classList.add('on');$('offline').style.display='none';return;}
  $('pwbox').classList.remove('on');
  if(!r.ok)throw new Error(r.status);
  const first=!S;const hadLp=S&&S.lp_enabled;S=await r.json();$('offline').style.display='none';document.body.classList.remove('stale');
  if(first||hadLp!==S.lp_enabled)render();else update(S);}
 catch(e){$('offline').style.display='block';if(!document.body.classList.contains('stale')){document.body.classList.add('stale');if(S)updateThetis(S);}}
}
function say(m,ok){const e=$('msg');e.textContent=m;e.className='msg '+(ok?'good':'badm');e.dataset.local='1';
 clearTimeout(say.t);say.t=setTimeout(()=>{delete e.dataset.local;},8000);}
async function send(a,params){
 try{const r=await fetch('/api/cmd'+Q,{method:'POST',headers:{'Content-Type':'application/json','X-KPA':'1'},
  body:JSON.stringify({action:a,params:params||{}})});const j=await r.json();say(j.message||j.error,j.ok);}
 catch(e){say('Request failed: '+e,false);} await refresh();
}
async function act(a,params){
 if(editing)return;
 if(a==='power_off'&&(!S||S.confirm_off!==false)&&!confirm('Turn the amplifier power supplies OFF?'))return;
 send(a,params);
}

/* ---------------- edit drawer ---------------- */
function layoutUrl(name){const q=new URLSearchParams(location.search);q.set('layout',name);return location.pathname+'?'+q.toString();}
function switchTo(name){NAME=name;L=ensure(NAME);try{history.replaceState(null,'',layoutUrl(name));}catch(e){}render();}
function syncDrawer(){
 const sel=$('d_layout');sel.textContent='';
 Object.keys(ALL).sort().forEach(n=>{const o=document.createElement('option');o.value=o.textContent=n;if(n===NAME)o.selected=true;sel.appendChild(o);});
 const s=L.settings;$('d_scale').value=s.scale;$('d_cell').value=s.cell;$('d_labels').value=s.labels;
 $('d_bars').checked=s.bars;$('d_theme').value=s.theme;$('d_hdr').checked=s.hdr;$('d_style').value=s.style;

 $('d_del').disabled=(NAME==='Default');
}
function lpStatus(s){
 let t;
 if(!s.lp_port)t='not configured';
 else if(s.lp_connected)t=(s.lp?'connected on ':'port open on ')+s.lp_port+' @ '+s.lp_baud;
 else t=s.lp_error?('error on '+s.lp_port+': '+s.lp_error):('connecting to '+s.lp_port+'...');
 $('d_lpstat').textContent='LP-100A: '+t;
}
async function scanPorts(){
 try{const r=await fetch('/api/ports'+Q);const j=await r.json();const dl=$('d_ports');dl.textContent='';
  (j.ports||[]).forEach(p=>{const o=document.createElement('option');o.value=p.device;o.label=p.desc;dl.appendChild(o);});
  say((j.ports&&j.ports.length)?(j.ports.length+' serial port(s) found - type or pick one'):(j.note||'No serial ports found'),!!(j.ports&&j.ports.length));
 }catch(e){say('Port scan failed',false);}
}
async function lpSet(port){
 try{const r=await fetch('/api/cmd'+Q,{method:'POST',headers:{'Content-Type':'application/json','X-KPA':'1'},
  body:JSON.stringify({action:'lp_port',params:{port:port,baud:+$('d_lpbaud').value}})});
  const j=await r.json();say(j.message||j.error,j.ok);}
 catch(e){say('Request failed: '+e,false);} refresh();
}
function ampStatus(s){
 $('d_ampstat').textContent=s.finding?'Searching the network...':('Now: '+s.amp_ip+':'+s.amp_port+' - '+(s.amp?'responding':'not responding')+
  (s.amp_ip_source==='flag'?' (set by --amp-ip)':''));
}
function showFound(s){
 const sel=$('d_ampfound');sel.textContent='';const f=s.found||[];
 if(f.length>1){f.forEach(a=>{const o=document.createElement('option');o.value=a.ip;
  o.textContent=a.ip+(a.serial?' - serial '+a.serial:'')+(a.firmware?' - fw '+a.firmware:'');sel.appendChild(o);});
  sel.style.display='';sel.onchange=()=>{$('d_ampip').value=sel.value;};$('d_ampip').value=f[0].ip;}
 else{sel.style.display='none';if(f.length===1)$('d_ampip').value=f[0].ip;}
}
async function ampFind(){
 $('d_ampstat').textContent='Searching the network...';
 await send('amp_find');showFound(S);
}
function setEditing(on){editing=on;
 if(on){scanPorts();if(S)$('d_ampip').value=S.amp_ip||'';if(S){$('d_lpport').value=S.lp_port||'';$('d_lpbaud').value=String(S.lp_baud||115200);}}
 render();}
/* ---- no-antenna check settings ---- */
const NABANDS=['160','80','60','40','30','20','17','15','12','10','6'];
(function(){const box=$('d_nalim');NABANDS.forEach(b=>{const l=document.createElement('label');
 l.textContent=b+' m ';const i=document.createElement('input');i.type='text';i.id='d_na_'+b;i.inputMode='numeric';
 i.setAttribute('aria-label','Limit for '+b+' m in dBm (empty = off)');
 i.addEventListener('change',()=>send('noant_limit',{band:b,dbm:i.value.trim()||'off'}));
 l.appendChild(i);box.appendChild(l);});})();
function syncNa(s){
 const na=s.noant||{},lim=s.noant_limits||{};
 if(document.activeElement!==$('d_na'))$('d_na').checked=!!na.enabled;
 if(document.activeElement!==$('d_naact'))$('d_naact').value=na.action||'warn';
 if(document.activeElement!==$('d_sot'))$('d_sot').checked=!!s.standby_on_tune;
 if(document.activeElement!==$('d_tunemax'))$('d_tunemax').value=String(s.tune_timeout!=null?s.tune_timeout:20);
 NABANDS.forEach(b=>{const i=$('d_na_'+b);if(document.activeElement!==i)i.value=lim[b]==null?'':String(lim[b]);
  i.parentNode.style.fontWeight=(b===na.band)?'700':'';});
 $('d_nastat').textContent='Now: '+(na.band?na.band+' m':'band ?')+', receive level '+
  ((na.dbm!=null&&na.live)?na.dbm.toFixed(1)+' dBm':'-- (none from Thetis)')+' - '+
  ({off:'check off',na:'no level from Thetis (is Thetis running? TCI on?)',nolimit:'no limit for this band',ok:'normal',
    low:'TOO LOW - no antenna?',tx:'transmitting - no antenna?',dummy:'DUMMY OK pressed'}[na.state]||'');
}
function syncDg(s){
 const dg=s.drive_guard||{};
 if(document.activeElement!==$('d_dglim'))$('d_dglim').value=dg.limit>0?String(dg.limit):'';
 if(document.activeElement!==$('d_dgact'))$('d_dgact').value=dg.action||'warn';
 if(document.activeElement!==$('d_dgrw'))$('d_dgrw').value=String(dg.radio_w||100);
 $('d_dgstat').textContent='Now: '+({off:'protection is off',idle:'waiting: the amp is not in OPERATE',ok:'ok',
   slider:'radio drive setting is over the limit',tx:'drive is over the limit',held:'amp held in STANDBY - press OPERATE'}[dg.state]||'')+
  (dg.slider!=null?' - radio RF power setting: '+dg.slider+' (about '+Math.round(dg.slider_w)+' W)':' - radio setting not known');
}
$('d_dglim').addEventListener('change',e=>send('drive_guard',{limit:e.target.value}));
$('d_dgact').addEventListener('change',e=>send('drive_guard',{action:e.target.value}));
$('d_dgrw').addEventListener('change',e=>send('drive_guard',{radio_w:e.target.value}));
$('d_na').addEventListener('change',e=>send(e.target.checked?'noant_on':'noant_off'));
$('d_naact').addEventListener('change',e=>send('noant_action',{action:e.target.value}));
$('d_sot').addEventListener('change',e=>send(e.target.checked?'sot_on':'sot_off'));
$('d_tunemax').addEventListener('change',e=>send('tune_timeout',{s:e.target.value.trim()}));
$('d_nalearn').addEventListener('click',()=>{if(confirm('Learn the limit for the band the radio is on now, from the receive level now?\n\nThe antenna must be DISCONNECTED (or the radio switched to no antenna) for this.'))send('noant_learn');});
$('d_nadef').addEventListener('click',()=>{if(confirm('Put all no-antenna limits back to the defaults?'))send('noant_defaults');});
$('antwarn_b').addEventListener('click',()=>send('dummy_ok'));
/* ---- FlexControl knob ---- */
const KCAT=(function(){try{return JSON.parse($('knobcat').textContent);}catch(e){return {events:[],actions:[],modes:{},defaults:{}};}})();
const KROW={};
(function buildKnobTable(){
 const box=$('d_ktable');
 KCAT.events.forEach(ev=>{const id=ev[0];
  const l=document.createElement('span');l.className='kl';l.textContent=ev[1];box.appendChild(l);
  const sel=document.createElement('select');sel.setAttribute('aria-label','Function for '+ev[1]);
  const groups={};KCAT.actions.forEach(a=>{let par=sel;if(a[2]){if(!groups[a[2]]){groups[a[2]]=document.createElement('optgroup');groups[a[2]].label=a[2];sel.appendChild(groups[a[2]]);}par=groups[a[2]];}
   const o=document.createElement('option');o.value=a[0];o.textContent=a[1];par.appendChild(o);});
  sel.addEventListener('change',()=>{const t={};t[id]=sel.value;send('knob_set',{table:t});});
  box.appendChild(sel);
  const tr=document.createElement('button');tr.type='button';tr.textContent='Try';tr.title='Run this function now, as if you pressed it';
  tr.addEventListener('click',()=>send('knob_try',{event:id}));box.appendChild(tr);
  const c=document.createElement('input');c.type='text';c.className='kc';c.placeholder='Custom: a Thetis CAT command like ZZMA1; or a TCI command like mute:true;';
  c.setAttribute('aria-label','Custom command for '+ev[1]);c.style.display='none';
  c.addEventListener('change',()=>{const t={};t[id]=c.value.trim();send('knob_set',{custom:t});});
  box.appendChild(c);KROW[id]={l:l,sel:sel,c:c};});
})();
function syncKnob(s){
 const k=s.knob||{};if(!k.table)return;
 $('d_kstat').textContent=(k.port===''?'Knob: off':(k.connected?('Knob connected on '+k.device+' - turning now does: '+k.mode_name):('Knob: '+(k.error||'looking for it ...'))))+
  (k.tci_cat===false?'   |   THETIS DOES NOT RUN CAT COMMANDS OVER TCI (run_cat_ex) - update Thetis for the knob functions':'')+
  (k.last?('   |   last: '+k.last+' = '+k.last_text+(k.last_age!=null?' ('+k.last_age+' s ago)':'')):'');
 const ps=$('d_kport');if(document.activeElement!==ps&&document.activeElement!==$('d_kportman')){
  const man=!!k.port&&k.port!=='auto';ps.value=man?'manual':k.port;$('d_kportman').style.display=$('d_kportuse').style.display=man?'':'none';if(man)$('d_kportman').value=k.port;}
 [['d_kspeed','speed'],['d_kaf','af_step'],['d_kret','return_s']].forEach(x=>{if(document.activeElement!==$(x[0]))$(x[0]).value=String(k[x[1]]);});
 KCAT.events.forEach(ev=>{const R=KROW[ev[0]],a=k.table[ev[0]];if(!R)return;
  if(document.activeElement!==R.sel)R.sel.value=a;R.c.style.display=a==='custom'?'':'none';
  if(document.activeElement!==R.c)R.c.value=(k.custom||{})[ev[0]]||'';
  R.l.classList.toggle('hit',k.last_text===ev[1]&&k.last_age!=null&&k.last_age<3);});
}
$('d_kport').addEventListener('change',e=>{const v=e.target.value;if(v==='manual'){$('d_kportman').style.display=$('d_kportuse').style.display='';$('d_kportman').focus();return;}send('knob_set',{port:v});});
$('d_kportuse').addEventListener('click',()=>{const v=$('d_kportman').value.trim().replace(/^com/i,'COM');if(v)send('knob_set',{port:v});});
$('d_kspeed').addEventListener('change',e=>send('knob_set',{speed:+e.target.value}));
$('d_kaf').addEventListener('change',e=>send('knob_set',{af_step:+e.target.value}));
$('d_kret').addEventListener('change',e=>send('knob_set',{return_s:+e.target.value||0}));
$('d_kdef').addEventListener('click',()=>{if(confirm('Put the knob functions back to the defaults?'))send('knob_defaults');});

/* ---- panel password ---- */
function pwGo(){const v=$('pw_in').value.trim();if(!v)return;const q=new URLSearchParams(location.search);q.set('t',v);location.search=q.toString();}
$('pw_ok').addEventListener('click',pwGo);
$('pw_in').addEventListener('keydown',e=>{if(e.key==='Enter')pwGo();});
function syncPw(s){
 const net=s.web_bind&&s.web_bind!=='127.0.0.1'&&s.web_bind!=='localhost';
 $('d_pwstat').textContent=(net?'Other computers and phones can open this panel':'The panel is open only on this computer')+
  ' - password: '+(s.web_password_set?'SET':'none')+(s.client_local?'':' (you are on another device: change it on the bridge computer)');
 $('d_pwset').disabled=$('d_pwdel').disabled=$('d_pwnew').disabled=!s.client_local;
 $('d_pwdel').disabled=!s.client_local||!s.web_password_set;
}
$('d_pwset').addEventListener('click',()=>{const v=$('d_pwnew').value.trim();if(!v){say('Type the new password first',false);return;}send('web_password',{token:v});$('d_pwnew').value='';});
$('d_pwdel').addEventListener('click',()=>{if(confirm('Remove the panel password? Anyone on your network who can reach the panel can then use it.'))send('web_password',{token:''});});
/* ---- Thetis windows: order editors for the Telemetry items and the Controls buttons ---- */
function tbSmall(txt,label,fn){const b=document.createElement('button');b.type='button';b.textContent=txt;
 b.setAttribute('aria-label',label);b.title=label;b.addEventListener('click',fn);return b;}
const EDIT={
 tb:{key:'',state:'thetis_buttons',std:TB_STD,act:'thetis_buttons',name:id=>TBTN[id]&&TBTN[id][7],needs:id=>TBTN[id]&&TBTN[id][5],
  tip:id=>TBTN[id]&&TBTN[id][6],box:'d_tb',hid:'d_tbhid',title:'d_tbtitle',defTitle:'KPA1500 {ver} Controls',cols:true},
 kw:{key:'',state:'thetis_knobwin',std:KW_STD,act:'thetis_knobwin',name:id=>KWITEM[id]&&KWITEM[id][0],needs:id=>'',
  tip:id=>'',box:'d_kw',hid:'d_kwhid',title:'d_kwtitle',defTitle:'FlexControl Knob {ver}',cols:false},
 tm:{key:'',state:'thetis_meters',std:TM_STD.concat(['title']),act:'thetis_meters',name:id=>TMITEM[id]&&TMITEM[id][0],needs:id=>TMITEM[id]&&TMITEM[id][3],
  tip:id=>'',box:'d_tm',hid:'d_tmhid',title:'d_tmtitle',defTitle:'KPA1500 {ver} Telemetry',cols:false}};
function edCur(E){const v=S&&S[E.state];return v?JSON.parse(JSON.stringify(v)):{order:E.std.filter(x=>x!=='title'),title:E.defTitle,columns:4};}
function edSave(E,o){const p={order:o.order,title:o.title};if(E.cols)p.columns=o.columns;send(E.act,p);}
function edSync(E,s){
 const cur=s[E.state]||edCur(E),key=JSON.stringify(cur)+(s.lp_enabled?'L':'');
 if(document.activeElement!==$(E.title))$(E.title).value=cur.title||'';
 if(key===E.key)return;E.key=key;
 const box=$(E.box);box.textContent='';
 cur.order.forEach((id,i)=>{if(!E.name(id))return;const row=document.createElement('div');row.className='tbi'+(id==='gap'?' gap':'');
  const nm=E.name(id);
  row.appendChild(tbSmall('◀','Move '+nm+' earlier',()=>{const o=edCur(E);if(i>0){const x=o.order.splice(i,1)[0];o.order.splice(i-1,0,x);edSave(E,o);}}));
  const sp=document.createElement('span');sp.textContent=(i+1)+'. '+nm+((E.needs(id)==='lp'&&!s.lp_enabled)?' (LP)':'');sp.title=E.tip(id)||nm;row.appendChild(sp);
  row.appendChild(tbSmall('▶','Move '+nm+' later',()=>{const o=edCur(E);if(i<o.order.length-1){const x=o.order.splice(i,1)[0];o.order.splice(i+1,0,x);edSave(E,o);}}));
  row.appendChild(tbSmall('✕','Take '+nm+' out',()=>{const o=edCur(E);o.order.splice(i,1);
   if(!o.order.some(x=>x!=='gap'&&x!=='title')){say('At least one item must stay',false);return;}edSave(E,o);}));
  box.appendChild(row);});
 const hid=$(E.hid);hid.textContent='';
 const missing=E.std.filter(id=>cur.order.indexOf(id)<0);
 if(missing.length){const l=document.createElement('span');l.className='small';l.textContent='Not shown:';hid.appendChild(l);
  missing.forEach(id=>hid.appendChild(tbSmall('+ '+E.name(id),'Put '+E.name(id)+' back'+(id==='title'?' (at the top)':' (at the end)'),()=>{
   const o=edCur(E);if(id==='title')o.order.unshift(id);else o.order.push(id);edSave(E,o);})));}
}
function syncTb(s){
 edSync(EDIT.tb,s);edSync(EDIT.tm,s);edSync(EDIT.kw,s);
 if(document.activeElement!==$('d_kwon'))$('d_kwon').checked=!(s.thetis_knobwin&&s.thetis_knobwin.enabled===false);
 const tb=s.thetis_buttons||{columns:4};
 if(document.activeElement!==$('d_tbcols'))$('d_tbcols').value=String(tb.columns);
 $('d_tbbuild').disabled=!s.is_windows;$('d_tbbuild').title=s.is_windows?'Opens the setup on the bridge computer':'Only when the bridge runs on Windows';
}
$('d_tbcols').addEventListener('change',e=>{const o=edCur(EDIT.tb);o.columns=+e.target.value;edSave(EDIT.tb,o);});
$('d_tbgap').addEventListener('click',()=>{const o=edCur(EDIT.tb);o.order.push('gap');edSave(EDIT.tb,o);});
$('d_tbdef').addEventListener('click',()=>{if(confirm('Put the Controls buttons back in the standard order?'))send('thetis_buttons_default');});
$('d_tmgap').addEventListener('click',()=>{const o=edCur(EDIT.tm);o.order.push('gap');edSave(EDIT.tm,o);});
$('d_tmdef').addEventListener('click',()=>{if(confirm('Put the Telemetry window back in the standard order?'))send('thetis_meters_default');});
$('d_tbtitle').addEventListener('change',e=>{const o=edCur(EDIT.tb);o.title=e.target.value.trim();edSave(EDIT.tb,o);});
$('d_kwtitle').addEventListener('change',e=>{const o=edCur(EDIT.kw);o.title=e.target.value.trim();edSave(EDIT.kw,o);});
$('d_kwgap').addEventListener('click',()=>{const o=edCur(EDIT.kw);o.order.push('gap');edSave(EDIT.kw,o);});
$('d_kwdef').addEventListener('click',()=>{if(confirm('Put the Knob window back in the standard order?'))send('thetis_knobwin_default');});
$('d_kwon').addEventListener('change',e=>send('thetis_knobwin',{enabled:e.target.checked}));
$('d_tmtitle').addEventListener('change',e=>{const o=edCur(EDIT.tm);o.title=e.target.value.trim();edSave(EDIT.tm,o);});
$('d_tbbuild').addEventListener('click',()=>{if(confirm('Open the Thetis setup now? It rebuilds both KPA1500 windows in Thetis with this button order.\n\nThe setup window offers to close Thetis for you and to start it again afterwards. A backup is made first.'))send('thetis_rebuild');});
$('d_ampfind').addEventListener('click',ampFind);
$('d_ampuse').addEventListener('click',()=>send('amp_ip',{ip:$('d_ampip').value.trim()}));
$('d_lpconnect').addEventListener('click',()=>lpSet($('d_lpport').value.trim().replace(/^com/i,'COM')));
$('d_lpdisc').addEventListener('click',()=>{$('d_lpport').value='';lpSet('');});
$('d_lpscan').addEventListener('click',scanPorts);
$('gear').addEventListener('click',()=>setEditing(!editing));
$('d_done').addEventListener('click',()=>setEditing(false));
$('d_layout').addEventListener('change',e=>switchTo(e.target.value));
$('d_saveas').addEventListener('click',()=>{
 const n=(prompt('Name for this layout (letters, numbers, space, - _):',NAME==='Default'?'':NAME)||'').trim();
 if(!n)return;if(!/^[A-Za-z0-9 _-]{1,24}$/.test(n)){say('Layout name not allowed',false);return;}
 ALL[n]=normalize(JSON.parse(JSON.stringify(L)));saveAll();switchTo(n);
});
$('d_del').addEventListener('click',()=>{
 if(NAME==='Default')return;if(!confirm('Delete layout "'+NAME+'"?'))return;
 delete ALL[NAME];saveAll();switchTo('Default');
});
$('d_preset').addEventListener('change',e=>{
 const p=preset(e.target.value);e.target.value='';if(!p)return;
 L=p;persist();render();
});
function setting(key,val){L.settings[key]=val;L=normalize(L);persist();render();}
$('d_scale').addEventListener('input',e=>setting('scale',+e.target.value));
$('d_cell').addEventListener('input',e=>setting('cell',+e.target.value));
$('d_labels').addEventListener('change',e=>setting('labels',e.target.value));
$('d_bars').addEventListener('change',e=>setting('bars',e.target.checked));
$('d_theme').addEventListener('change',e=>setting('theme',e.target.value));
$('d_hdr').addEventListener('change',e=>setting('hdr',e.target.checked));
$('d_style').addEventListener('change',e=>setting('style',e.target.value));
$('d_confirm').addEventListener('change',e=>send(e.target.checked?'confirm_off_on':'confirm_off_off'));
$('d_thetisoff').addEventListener('change',e=>send(e.target.checked?'thetis_off_on':'thetis_off_off'));
$('d_blockofftx').addEventListener('change',e=>{if(!e.target.checked&&!confirm('Allow power OFF even while transmitting? Use only for emergencies such as a radio stuck in transmit.')){e.target.checked=true;return;}send(e.target.checked?'block_off_tx_on':'block_off_tx_off');});
$('d_log').addEventListener('change',e=>send(e.target.checked?'log_on':'log_off'));
$('d_logmax').addEventListener('change',e=>send('log_limit',{mb:+e.target.value}));
$('d_showall').addEventListener('click',()=>{L.hidden={};changed();});
$('d_export').addEventListener('click',()=>{const t=$('d_json');t.value=JSON.stringify(L);t.focus();t.select();});
$('d_import').addEventListener('click',()=>{
 const v=validateImport($('d_json').value);
 if(!v.ok){say('Import failed: '+v.error,false);return;}
 L=v.layout;persist();render();say('Layout imported',true);
});

render();refresh();setInterval(refresh,300);
})();
</script></body></html>
"""


# --------------------------------------------------------------------------
# Built-in self-test: fake amp + fake Thetis + fake LP-100A, no hardware
# --------------------------------------------------------------------------
class FakeAmp(threading.Thread):
    def __init__(self, host="127.0.0.1", port=0):
        super().__init__(daemon=True)
        self.boot, self.junk, self.serial, self.firmware = False, False, "00022", "03.02"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.port = self.sock.getsockname()[1]
        self.sock.settimeout(0.2)
        self.mode, self.freq, self.rx_log, self.running = 1, 0, [], True
        self.atu, self.ant, self.fwd, self.fault = "I", 1, 1204, 0
        self.asleep, self.wl = False, 0
        self.fan_min = 1

    def run(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
            except socket.timeout:
                continue
            c = data.decode().strip().upper()
            self.rx_log.append(c)
            out = None
            if self.junk:                      # something that is not a KPA1500
                self.sock.sendto(b"hello", addr)
                continue
            if self.asleep:                    # sleeping amp: only ^ON1; wakes it
                if c == "^ON1;":
                    self.asleep = False
                continue
            if c == "^I;":
                out = "^kpa1500;" if self.boot else "^KPA1500;"
            elif c == "^SN;":
                out = "^SN%s;" % self.serial
            elif c == "^RV;":
                out = "^RV%s;" % self.firmware
            elif c == "^FC;":
                out = "^FC%d;" % self.fan_min
            elif re.fullmatch(r"\^FC[0-9];", c):
                self.fan_min = int(c[3])
            elif c == "^FS;":
                out = "^FS%d;" % max(self.fan_min, 1)      # never below the minimum
            elif c == "^ON;":
                out = "^ON1;"
            elif c == "^MA;":
                out = "^MA54:10:EC:14:75:22;"
            elif c == "^WL;":
                out = "^WL%d;" % self.wl
            elif c == "^WL1;":
                self.wl = 1
            elif c == "^OS;":
                out = "^OS%d;" % self.mode
            elif c in ("^OS0;", "^OS1;"):
                self.mode = int(c[3])
            elif c == "^FR;":
                out = "^FR%05d;" % self.freq
            elif c.startswith("^FR") and len(c) == 9:
                self.freq = int(c[3:8])
            elif c == "^WS;":
                out = "^WS%04d 014;" % self.fwd
            elif c == "^PWI;":
                out = "^PWI%04d;" % (47 if self.mode == 1 else 0)
            elif c == "^PWR;":
                out = "^PWR0012;"
            elif c == "^TM;":
                out = "^TM031;"
            elif c == "^FL;":
                out = "^FL%02X;" % self.fault
            elif c == "^FLC;":
                self.fault = 0
            elif c == "^VI;":
                out = "^VI513 061;"
            elif c == "^AM;":
                out = "^AM%s;" % self.atu
            elif c in ("^AMI;", "^AMB;"):
                self.atu = c[3]
            elif c == "^AN;":
                out = "^AN%d;" % self.ant
            elif c in ("^AN1;", "^AN2;"):
                self.ant = int(c[3])
            elif c == "^TP;":
                out = "^TP0;"
            elif c == "^CR;":
                out = "^CR2C;"
            elif c == "^LR;":
                out = "^LR0A;"
            elif c == "^SI;":
                out = "^SIA;"
            if out:
                self.sock.sendto(out.encode(), addr)


class FakeSerial:
    """Stands in for pyserial: answers 'P' with one LP-100A frame."""
    def __init__(self, frame):
        self.frame, self.buf, self.written = frame, b"", []

    def write(self, b):
        self.written.append(b)
        if b == b"P":
            self.buf += self.frame.encode()

    @property
    def in_waiting(self):
        return len(self.buf)

    def read(self, n):
        d, self.buf = self.buf[:n], self.buf[n:]
        return d

    def close(self):
        pass


def selftest():
    import urllib.request
    import urllib.error
    print("=== SELF-TEST (fake amp + fake radio + fake LP-100A on localhost) ===")
    amp = FakeAmp()
    amp.start()
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    tci_port = srv.getsockname()[1]

    args = build_parser().parse_args([
        "--amp-ip", "127.0.0.1", "--amp-port", str(amp.port),
        "--tci-port", str(tci_port), "--poll", "0.02", "--logfile", "",
        "--mac-file", "", "--settings-file", "",
        "--web-port", "0"])
    bridge = Bridge(args, quiet=True)
    web_port = bridge.start_web()
    IDLE_FRAME = ";0.0,50.0,0,2,K4ABC,1,0,-99.0,1.0"
    TX_FRAME = ";250.0,60.5,-20,2,K4ABC,1,0,53.98,1.35"
    fake_ser = FakeSerial(IDLE_FRAME)
    bridge.lp = LP100("FAKE", 115200, lambda p, b: fake_ser, bridge.log,
                      interval=0.02)
    bridge.lp.start()
    threading.Thread(target=bridge.tci_loop, daemon=True).start()
    threading.Thread(target=bridge.poll_loop, daemon=True).start()

    conn, _ = srv.accept()
    conn.settimeout(3)
    req = b""
    while b"\r\n\r\n" not in req:
        req += conn.recv(4096)
    key = re.search(rb"Sec-WebSocket-Key: (\S+)", req).group(1)
    acc = base64.b64encode(hashlib.sha1(key + WS_GUID.encode()).digest())
    conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                 b"Connection: Upgrade\r\nSec-WebSocket-Accept: " + acc + b"\r\n\r\n")
    thetis = WebSocket(conn, client=False)

    results = []

    def check(name, cond):
        results.append(bool(cond))
        print("  [%s] %s" % ("PASS" if cond else "FAIL", name))

    def wait_for(fn, t=3.0):
        end = time.time() + t
        while time.time() < end:
            if fn():
                return True
            time.sleep(0.02)
        return False

    base = "http://127.0.0.1:%d" % web_port

    def get_state(token=None):
        url = base + "/api/state" + ("?t=" + token if token else "")
        with urllib.request.urlopen(url, timeout=3) as r:
            return json.loads(r.read())

    def post(action, token=None, header=True):
        url = base + "/api/cmd" + ("?t=" + token if token else "")
        h = {"Content-Type": "application/json"}
        if header:
            h["X-KPA"] = "1"
        rq = urllib.request.Request(url, json.dumps({"action": action}).encode(),
                                    h, method="POST")
        try:
            with urllib.request.urlopen(rq, timeout=3) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, {}

    print("-- radio tracking and Standby on Tune --")
    try:
        first = thetis.recv_message()
    except Exception:
        first = ""
    check("bridge asks the radio for TX sensors (tx_sensors_enable:true;)",
          first == "tx_sensors_enable:true;")
    thetis.send_text("protocol:esdr,2.0;ready;vfo:0,0,14025000;"
                     "vfo:0,1,14025000;split_enable:0,false;tune:0,false;")
    check("20m VFO sent to amp as ^FR14025;", wait_for(lambda: amp.freq == 14025))
    thetis.send_text("vfo:0,0,7150000;")
    check("QSY to 7.150 MHz -> ^FR07150;", wait_for(lambda: amp.freq == 7150))
    check("amp frequency read back (^FR;): 7.150 MHz, following the radio",
          wait_for(lambda: bridge.follow_state() == (7150, "= radio"))
          and bridge.mmio_vars()["amp_freq"] == "7.150 MHz" and bridge.mmio_vars()["amp_following"] == 1
          and bridge.mmio_vars()["amp_freq_line"] == "7.150 MHz" and bridge.mmio_vars()["bridge_version"] == "v" + VERSION)
    amp.freq = 3550                      # amp moved by hand: no longer on the radio frequency
    check("amp on another frequency is flagged (radio 7.150 !)",
          wait_for(lambda: bridge.follow_state() == (3550, "radio 7.150 !"), 6)
          and bridge.mmio_vars()["amp_following"] == 0
          and bridge.mmio_vars()["amp_freq_line"] == "3.550 MHz  radio 7.150 !")
    amp.freq = 7150
    wait_for(lambda: bridge.follow_state()[0] == 7150, 6)
    check("amp telemetry parsed (1204 W, drive 47 W, refl 12 W, 31 C, 51.3 V)",
          wait_for(lambda: (bridge.fwd, bridge.pin, bridge.refl, bridge.temp,
                            bridge.volts, bridge.amps)
                   == (1204, 47, 12, 31, 51.3, 61)))
    check("ATU mode and antenna read back",
          wait_for(lambda: (bridge.atu, bridge.ant) == ("I", 1)))
    thetis.send_text("tune:0,true;")
    check("radio TUNE -> amp STANDBY", wait_for(lambda: amp.mode == 0))
    thetis.send_text("tune:0,false;")
    check("TUNE ends -> amp restored to OPERATE", wait_for(lambda: amp.mode == 1))
    amp.mode = 0
    time.sleep(0.2)
    thetis.send_text("tune:0,true;")
    time.sleep(0.2)
    thetis.send_text("tune:0,false;")
    time.sleep(0.3)
    check("amp that was in STANDBY stays in STANDBY after tune", amp.mode == 0)
    amp.mode = 1
    time.sleep(0.2)

    print("-- drive power when the amp is in STANDBY --")
    amp.mode = 0
    wait_for(lambda: bridge.mode == 0 and bridge.pin == 0)
    check("amp reports 0 W input power in standby (as the real amp does)",
          get_state()["drive"] == 0 and get_state()["drive_src"] == "none")
    thetis.send_text("trx:0,true;tx_sensors:0,-20.0,45.0,45.0,1.1;")
    check("standby: drive shown from the RADIO (45 W)",
          wait_for(lambda: get_state()["drive"] == 45.0
                   and get_state()["drive_src"] == "radio"))
    thetis.send_text("trx:0,false;")
    check("radio unkeyed -> drive returns to 0",
          wait_for(lambda: get_state()["drive"] == 0))
    thetis.send_text("trx:0,true;tx_sensors:0,-20.0,45.0,45.0,1.1;")
    wait_for(lambda: bridge.radio_fwd == 45.0)
    bridge.radio_t -= 5
    check("stale radio reading (>1.5 s old) is ignored",
          get_state()["drive_src"] == "none")
    thetis.send_text("trx:0,false;")
    amp.mode = 1
    check("operate: drive comes from the amp again (47 W)",
          wait_for(lambda: get_state()["drive"] == 47.0
                   and get_state()["drive_src"] == "amp"))

    print("-- 'no antenna?' check (receive level from Thetis) --")
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0)

    def rx_feed(dbm, n=4):
        bridge.rx_quiet_until = 0
        with bridge.noant_lock:
            bridge.rx_samples = []
        thetis.send_text("".join("rx_sensors:0,%.1f;rx_channel_sensors:0,0,%.1f;"
                                 "rx_channel_sensors_ex:0,0,%.1f,%.1f,-60.0;" % (dbm + 3, dbm + 3, dbm + 3, dbm)
                                 for _ in range(n)))
        return wait_for(lambda: bridge.rx_dbm() is not None and abs(bridge.rx_dbm() - dbm) < 0.01)

    check("bridge asks Thetis for the receive level (rx_sensors_enable)",
          wait_for(lambda: bridge.tci_ok) and "rx_sensors_enable:true,250;" in thetis.recv_message())
    check("40 m with a normal receive level (-78 dBm, the AVERAGE value is used): no warning",
          rx_feed(-78.0) and bridge.noant_state()["state"] == "ok" and bridge.noant_state()["band"] == "40"
          and bridge.mmio_vars()["noant"] == 0 and bridge.mmio_vars()["rx_text"] == "RX -78 dBm")
    check("-119 dBm on 40 m (limit -105): 'ANTENNA?' warning everywhere",
          rx_feed(-119.0) and bridge.noant_state()["state"] == "low"
          and bridge.mmio_vars()["noant"] == 1 and bridge.mmio_vars()["noant_text"].startswith("ANTENNA?")
          and get_state()["noant"]["warn"] and "ANTENNA?" in bridge.status_text())
    thetis.send_text("trx:0,true;")
    check("key up while warned: TX warning (noant_tx = 1), level kept from before TX",
          wait_for(lambda: bridge.noant_state()["state"] == "tx") and bridge.mmio_vars()["noant_tx"] == 1
          and bridge.noant_state()["dbm"] == -119.0)
    thetis.send_text("rx_channel_sensors_ex:0,0,-20.0,-20.0,-10.0;")
    time.sleep(0.2)
    check("readings during transmit are ignored", bridge.rx_dbm() == -119.0)
    thetis.send_text("trx:0,false;")
    wait_for(lambda: not bridge.tx)
    code, j = post("dummy_ok")
    check("DUMMY OK pressed: warning silenced on this band",
          code == 200 and j["ok"] and bridge.noant_state()["state"] == "dummy"
          and bridge.mmio_vars()["dummy_ok"] == 1 and bridge.mmio_vars()["noant"] == 0)
    check("normal level returns: DUMMY OK forgotten, state ok",
          rx_feed(-80.0) and bridge.noant_state()["state"] == "ok" and not bridge.dummy_ok)
    ok_, msg_ = bridge.do_action("dummy_ok")
    check("DUMMY OK refused when there is no warning", not ok_ and "not needed" in msg_)
    bridge.do_action("noant_action", {"action": "standby"})
    amp.mode = 1
    wait_for(lambda: bridge.mode == 1)
    rx_feed(-119.0)
    check("option 'keep STANDBY': amp put in STANDBY while 'no antenna?'",
          wait_for(lambda: amp.mode == 0, 5) and wait_for(lambda: bridge.noant_held))
    ok_, msg_ = bridge.do_action("operate")
    check("OPERATE refused while held (message says press DUMMY OK)", not ok_ and "DUMMY OK" in msg_)
    ok_, msg_ = bridge.do_action("dummy_ok")
    check("DUMMY OK releases the hold: amp back to OPERATE",
          ok_ and wait_for(lambda: amp.mode == 1, 5) and not bridge.noant_held)
    bridge.do_action("dummy_ok")          # undo DUMMY OK -> held again
    check("DUMMY OK undone: amp held in STANDBY again", wait_for(lambda: amp.mode == 0, 5))
    rx_feed(-79.0)
    check("antenna back (normal level): hold released, amp OPERATE",
          wait_for(lambda: amp.mode == 1, 5) and not bridge.noant_held)
    bridge.do_action("noant_action", {"action": "warn"})
    rx_feed(-119.0)
    ok_, msg_ = bridge.do_action("noant_learn")
    check("learn on 40 m with no antenna: limit = -119 + 6 = -113",
          ok_ and bridge.noant_limits["40"] == -113 and bridge.settings["noant"]["limits"]["40"] == -113)
    ok_, msg_ = bridge.do_action("noant_limit", {"band": "40", "dbm": "off"})
    check("limit 'off' for a band: no check there", ok_ and bridge.noant_state()["state"] == "nolimit")
    check("bad limits refused", not bridge.do_action("noant_limit", {"band": "40", "dbm": "-10"})[0]
          and not bridge.do_action("noant_limit", {"band": "99", "dbm": "-100"})[0])
    bridge.do_action("noant_defaults")
    bridge.do_action("noant_off")
    check("check switched off: never warns", bridge.noant_state()["state"] == "off")
    bridge.do_action("noant_on")
    rx_feed(-78.0)
    check("saved settings are read back at start (clean_limits)",
          clean_limits({"40": -100, "6": None, "x": 1, "80": 5})["40"] == -100
          and clean_limits({"80": 5})["80"] == -105)

    print("-- over-drive protection --")
    sent_pct = []
    real = (bridge.flex_rfpower, bridge.flex_set_rfpower, bridge.drive_info, bridge.transmitting)
    cur = {"pct": None, "w": 0.0, "tx": False}
    bridge.flex_rfpower = lambda: cur["pct"]
    bridge.flex_set_rfpower = lambda p: (sent_pct.append(p) or cur.__setitem__("pct", p) or True)   # the radio then reports the new value
    bridge.drive_info = lambda: (cur["w"], "amp" if cur["w"] > 0 else "none")
    bridge.transmitting = lambda: cur["tx"]
    wait_for(lambda: bridge.mode == 1 and bridge.amp_ok)
    bridge.atu_tuning = False
    check("over-drive protection starts off (no limit)", bridge.drive_guard_state()["state"] == "off"
          and bridge.dg_action == "warn" and bridge.dg_limit == 0)
    check("bad limit and bad action refused",
          not bridge.do_action("drive_guard", {"limit": "5000"})[0]
          and not bridge.do_action("drive_guard", {"limit": "abc"})[0]
          and not bridge.do_action("drive_guard", {"action": "boom"})[0])
    ok_, msg_ = bridge.do_action("drive_guard", {"limit": "80", "action": "warn"})
    check("limit 80 W + warn saved to the settings", ok_ and bridge.settings["drive_guard"]["limit"] == 80.0
          and bridge.settings["drive_guard"]["action"] == "warn" and bridge.settings["drive_guard"]["radio_w"] == 100.0)
    cur["pct"] = 90
    bridge.drive_guard_tick()
    st = bridge.drive_guard_state()
    check("radio RF power 90 -> warning about the drive setting, nothing changed",
          st["state"] == "slider" and st["warn"] and "DRIVE SETTING 90 W" in st["text"] and not sent_pct
          and bridge.mmio_vars()["drvlim"] == 1 and "DRIVE SETTING" in bridge.status_text())
    bridge.do_action("drive_guard", {"action": "limit"})
    bridge.dg_clamp_t = 0
    bridge.drive_guard_tick()
    check("Hold at the limit: the radio RF power is put back to 80", sent_pct == [80] and bridge.dg_slider == 80)
    bridge.drive_guard_tick()
    check("back at the limit: no warning and no more changes",
          bridge.drive_guard_state()["state"] == "ok" and sent_pct == [80])
    cur["pct"] = 100
    bridge.dg_clamp_t = time.time()
    bridge.drive_guard_tick()
    check("the correction is not repeated more often than every 1.5 s", sent_pct == [80])
    cur["pct"] = 80
    bridge.drive_guard_tick()
    bridge.mode = 0
    cur["pct"] = 100
    bridge.drive_guard_tick()
    check("amp in STANDBY: the limit is ignored (waiting)",
          bridge.drive_guard_state()["state"] == "idle" and not bridge.drive_guard_state()["warn"] and sent_pct == [80])
    bridge.mode = 1
    wait_for(lambda: bridge.mode == 1)
    bridge.do_action("drive_guard", {"limit": "off"})
    bridge.drive_guard_tick()
    check("limit off: protection off", bridge.drive_guard_state()["state"] == "off")
    bridge.do_action("drive_guard", {"limit": "20", "radio_w": "5", "action": "warn"})
    cur["pct"] = 100
    bridge.drive_guard_tick()
    check("5 W radio, RF power 100 under a 20 W limit: ok", bridge.drive_guard_state()["state"] == "ok")
    bridge.do_action("drive_guard", {"limit": "80", "radio_w": "100", "action": "ignore"})
    cur["pct"] = 100
    bridge.drive_guard_tick()
    check("Ignore: no warning", bridge.drive_guard_state()["state"] == "off")
    bridge.do_action("drive_guard", {"action": "warn"})
    cur["pct"] = 80
    cur["tx"], cur["w"] = True, 95.0
    bridge.dg_over_since = None
    bridge.drive_guard_tick()
    check("a short peak (under 0.8 s) is ignored", bridge.drive_guard_state()["state"] == "ok")
    bridge.dg_over_since = time.time() - 1.0
    bridge.drive_guard_tick()
    st = bridge.drive_guard_state()
    check("95 W lasting longer: OVER-DRIVE warning", st["state"] == "tx" and "OVER-DRIVE: 95 W (limit 80 W)" in st["text"]
          and bridge.mmio_vars()["drvlim"] == 1)
    cur["w"] = 85.0
    bridge.dg_hot_t = 0.0
    bridge.dg_over_since = None
    bridge.drive_guard_tick()
    check("85 W is within the tolerance: ok", bridge.drive_guard_state()["state"] == "ok")
    cur["w"] = 100.0
    bridge.dg_hot_t = 0.0
    bridge.do_action("drive_guard", {"action": "limit"})
    bridge.dg_over_since = time.time() - 1.0
    bridge.dg_clamp_t = 0
    sent_pct.clear()
    bridge.drive_guard_tick()
    check("Hold at the limit, drive over: RF power pulled back, amp still in OPERATE",
          sent_pct == [80] and bridge.mode == 1 and not bridge.dg_held)
    bridge.dg_over_since = time.time() - 3.0
    bridge.dg_clamp_t = time.time() - 1.0
    bridge.drive_guard_tick()
    check("still over after a further 1.2 s: amp put in STANDBY and held",
          wait_for(lambda: amp.mode == 0) and bridge.dg_held and bridge.drive_guard_state()["state"] == "held"
          and "AMP HELD STBY" in bridge.drive_guard_state()["text"])
    amp.mode = 1
    wait_for(lambda: bridge.mode == 1)
    cur["tx"], cur["w"] = False, 0.0
    bridge.drive_guard_tick()
    check("OPERATE pressed again: the hold is released", not bridge.dg_held)
    cur["tx"], cur["w"] = True, 100.0
    bridge.do_action("drive_guard", {"action": "warn"})
    bridge.dg_hot_t = 0.0
    bridge.dg_over_since = time.time() - 1.0
    bridge.atu_tuning = True
    bridge.drive_guard_tick()
    check("the amp's own ATU is tuning: idle, nothing changed",
          bridge.drive_guard_state()["state"] == "idle" and not bridge.drive_guard_state()["warn"])
    bridge.atu_tuning = False
    bridge.drive_info = lambda: (100.0, "radio")
    bridge.dg_hot_t = 0.0
    bridge.dg_over_since = None
    bridge.drive_guard_tick()
    check("100 W seen only from the radio (amp not in the path): not judged",
          bridge.drive_guard_state()["state"] == "ok")
    bridge.do_action("drive_guard", {"limit": "off", "action": "warn", "radio_w": "100"})
    bridge.flex_rfpower, bridge.flex_set_rfpower, bridge.drive_info, bridge.transmitting = real

    print("-- no lock-up when a warning is logged while the screen is busy --")
    rx_feed(-78.0)
    busy = threading.Event()
    done = threading.Event()

    def hold_screen():
        with bridge.print_lock:          # like the status line being written
            busy.set()
            done.wait(3)
    th = threading.Thread(target=hold_screen, daemon=True)
    th.start()
    busy.wait(2)
    warn_t = threading.Thread(target=lambda: rx_feed(-119.0) and bridge.noant_state(), daemon=True)
    warn_t.start()                       # the warning message now waits for the screen ...
    time.sleep(0.4)
    res = {}
    mm_t = threading.Thread(target=lambda: res.setdefault("mm", bridge.mmio_vars()), daemon=True)
    mm_t.start()
    mm_t.join(1.5)
    check("... and the Thetis readings (bridge_time) keep flowing meanwhile (no deadlock)",
          "mm" in res and res["mm"]["noant"] == 1)
    done.set()
    th.join(2)
    warn_t.join(3)
    rx_feed(-78.0)
    check("status line is cut to the window width (no pile-up of status text)",
          len(fit_status("x" * 500)) <= 400 and fit_status("abc").startswith("abc"))

    print("-- TUNE from the bridge (amp STANDBY before RF) --")

    def tci_got(text, t_=3.0):
        end = time.time() + t_
        thetis.sock.settimeout(0.3)
        while time.time() < end:
            try:
                m = thetis.recv_message()
            except socket.timeout:
                continue
            except Exception:
                return False
            if text in (m or ""):
                return True
        return False

    amp.mode = 1
    wait_for(lambda: bridge.mode == 1)
    rx_feed(-78.0)
    code, j = post("radio_tune")
    check("TUNE button: amp confirmed in STANDBY BEFORE Thetis is told to tune",
          code == 200 and j["ok"] and "CONFIRMED" in j["message"] and amp.mode == 0
          and tci_got("tune:0,true;"))
    thetis.send_text("tune:0,true;trx:0,true;")
    time.sleep(0.2)
    check("Thetis echo of tune:true does not repeat the standby step", amp.mode == 0 and bridge.bridge_tune)
    check("OPERATE refused while the tune runs", not bridge.do_action("operate")[0])
    code, j = post("radio_tune_stop")
    check("STOP: Thetis told tune:false", j["ok"] and tci_got("tune:0,false;"))
    thetis.send_text("tune:0,false;trx:0,false;")
    check("tune ended: amp back to OPERATE", wait_for(lambda: amp.mode == 1, 4) and not bridge.tune_active)
    bridge.do_action("tune_timeout", {"s": 1})
    wait_for(lambda: bridge.mode == 1)
    ok_, msg_ = bridge.do_action("radio_tune_toggle")
    check("auto-stop: tune stopped by itself after the set time (1 s here)",
          ok_ and tci_got("tune:0,false;", 4))
    check("... and with no answer from Thetis the bridge finishes it: amp OPERATE",
          wait_for(lambda: not bridge.tune_active and amp.mode == 1, 4))
    check("auto-stop setting saved; bad values refused",
          bridge.settings.get("tune_timeout") == 1 and not bridge.do_action("tune_timeout", {"s": "x"})[0]
          and not bridge.do_action("tune_timeout", {"s": 9999})[0])
    bridge.do_action("tune_timeout", {"s": 20})
    rx_feed(-119.0)
    ok_, msg_ = bridge.do_action("radio_tune")
    check("TUNE refused while 'no antenna?' shows (until DUMMY OK)", not ok_ and "DUMMY OK" in msg_
          and amp.mode == 1)
    rx_feed(-78.0)
    bridge.do_action("sot_off")
    ok_, msg_ = bridge.do_action("radio_tune")
    check("Standby-on-Tune OFF: TUNE starts and the amp is left as it is",
          ok_ and amp.mode == 1 and tci_got("tune:0,true;"))
    bridge.do_action("radio_tune_stop")
    wait_for(lambda: not bridge.tune_active, 4)
    bridge.do_action("sot_on")

    print("-- Thetis Controls button order --")
    ok_, msg_ = bridge.do_action("thetis_buttons", {"order": ["tune", "gap", "opr", "bogus", "opr", "fanup"], "columns": 9})
    check("button order saved: unknown and repeated buttons dropped, columns limited to 2-6",
          ok_ and bridge.thetis_buttons == {"order": ["tune", "gap", "opr", "fanup"], "columns": 6, "tv": 1, "title": TITLE_CTRL}
          and bridge.settings["thetis_buttons"]["order"][0] == "tune" and get_state()["thetis_buttons"]["columns"] == 6)
    check("an empty button list is refused", not bridge.do_action("thetis_buttons", {"order": ["gap"]})[0])
    ok_, msg_ = bridge.do_action("thetis_buttons", {"title": "My amp {ver} <b>100%"})
    check("Controls title saved, cleaned of characters Thetis cannot show (% < >), order kept",
          ok_ and bridge.thetis_buttons["title"] == "My amp {ver} b100" and bridge.thetis_buttons["order"][0] == "tune")
    ok_, msg_ = bridge.do_action("thetis_meters", {"order": ["title", "fwd", "gap", "nope", "fwd", "status"], "title": ""})
    check("Telemetry order saved (unknown and repeated items dropped); empty title -> standard title",
          ok_ and bridge.thetis_meters == {"order": ["title", "fwd", "gap", "status"], "title": TITLE_TELE}
          and get_state()["thetis_meters"]["order"][0] == "title")
    check("Telemetry: an empty list is refused", not bridge.do_action("thetis_meters", {"order": ["gap"]})[0])
    bridge.do_action("thetis_meters_default")
    check("Telemetry standard order restored", bridge.thetis_meters["order"] == TM_DEFAULT
          and clean_thetis_meters(None) == {"order": TM_DEFAULT, "title": TITLE_TELE})
    bridge.do_action("thetis_buttons", {"title": TITLE_CTRL})
    bridge.do_action("thetis_buttons_default")
    check("standard order restored", bridge.thetis_buttons == {"order": TB_DEFAULT, "columns": 4, "tv": 1, "title": TITLE_CTRL}
          and clean_thetis_buttons(None)["order"] == TB_DEFAULT)

    c = setup_launch_cmd(r"C:\Radio Scripts\Setup_Thetis_Containers.bat", "kpa1500_settings.json")
    check("Rebuild: setup command is wrapped for cmd /c (outer quotes kept, paths with spaces work)",
          c.startswith('cmd.exe /c ""C:\\Radio Scripts\\Setup_Thetis_Containers.bat" --settings "')
          and c.endswith('kpa1500_settings.json""') and c.count('"') == 6
          and setup_launch_cmd("x.bat") == 'cmd.exe /c ""x.bat""')

    print("-- FlexControl tuning knob --")

    def tci_collect(t_=1.0):
        out, end = [], time.time() + t_
        thetis.sock.settimeout(0.2)
        while time.time() < end:
            try:
                m = thetis.recv_message()
            except socket.timeout:
                continue
            except Exception:
                break
            out.append(m or "")
        return "".join(out)

    check("knob messages decoded (U, D05, S, X2C, X3L, reset)",
          parse_knob_code("U") == ("turn", 1) and parse_knob_code("D05") == ("turn", -5)
          and parse_knob_code("S") == ("event", "knob_tap") and parse_knob_code("X2C") == ("event", "b2_double")
          and parse_knob_code("X3L") == ("event", "b3_long") and parse_knob_code("F0304") == (None, None))
    tci_collect(0.3)
    th_ = threading.Thread(target=bridge.check_tci_cat, daemon=True)
    th_.start()
    ok1 = tci_got("run_cat_ex:ZZVN;")
    thetis.send_text("run_cat_ex:ZZVN;,ZZVN2.10.3.15;")
    th_.join(5)
    check("bridge checks that Thetis runs CAT commands over TCI (asks ZZVN, gets the version)",
          ok1 and bridge.tci_cat_ok is True and bridge.cat_replies["ZZVN"][0] == "2.10.3.15")
    fk = FakeKnobSerial()
    bridge.knob = FlexKnob("FAKE", lambda p_, b_: fk, bridge.knob_code, bridge.log)
    bridge.knob.start()
    check("knob connects; LEDs set for VFO A (I000;)",
          wait_for(lambda: bridge.knob.connected) and wait_for(lambda: b"I000;" in fk.written))
    tci_collect(0.3)
    fk.feed("U;")
    check("one click up -> Thetis VFO A up one step (run_cat_ex:ZZSB;)", tci_got("run_cat_ex:ZZSB;"))
    fk.feed("D03;")
    got = tci_collect(1.0)
    check("fast spin down (D03, x2) -> 6 steps down (ZZSA x6)", got.count("run_cat_ex:ZZSA;") == 6)
    fk.feed("X1S;")
    check("button 1 tap -> knob now AF volume, LED 1 on (I100;)",
          wait_for(lambda: bridge.knob_mode == "af") and wait_for(lambda: b"I100;" in fk.written))
    fk.feed("U;")
    ok1 = tci_got("run_cat_ex:ZZAG;")
    thetis.send_text("run_cat_ex:ZZAG;,ZZAG040;")
    check("AF mode: reads Thetis AF (40) and sets 41 (run_cat_ex:ZZAG041;)", ok1 and tci_got("run_cat_ex:ZZAG041;"))
    fk.feed("U02;")
    check("... next clicks use the known value: 43", tci_got("run_cat_ex:ZZAG043;"))
    fk.feed("S;")
    check("knob press tap -> back to VFO A", wait_for(lambda: bridge.knob_mode == "vfoa"))
    fk.feed("X2S;")
    ok1 = tci_got("run_cat_ex:ZZVE;")
    thetis.send_text("run_cat_ex:ZZVE;,ZZVE0;")
    check("button 2 tap -> VOX: reads OFF, switches ON (ZZVE1)", ok1 and tci_got("run_cat_ex:ZZVE1;"))
    fk.feed("X1C;")
    wait_for(lambda: bridge.knob_mode == "agc")
    fk.feed("D;")
    ok1 = tci_got("agc_gain:0;")
    thetis.send_text("agc_gain:0,60;")
    check("button 1 double tap -> AGC gain mode; one click down 60 -> 59", ok1 and tci_got("agc_gain:0,59;"))
    fk.feed("X1C;")
    wait_for(lambda: bridge.knob_mode == "vfoa")
    ok_, msg_ = bridge.do_action("knob_try", {"event": "b3_double"})
    check("Try button (button 3 double = band up) -> ZZBU", ok_ and tci_got("run_cat_ex:ZZBU;"))
    ok_, msg_ = bridge.do_action("knob_set", {"table": {"b3_long": "custom"}, "custom": {"b3_long": "ZZMA1;"}})
    fk.feed("X3L;")
    check("custom command on button 3 long (ZZMA1;) is sent, and saved",
          ok_ and tci_got("run_cat_ex:ZZMA1;") and bridge.settings["knob"]["custom"]["b3_long"] == "ZZMA1;")
    check("dangerous / wrong custom commands refused",
          not bridge.do_action("knob_set", {"custom": {"b3_long": "rm -rf; x"}})[0]
          and not bridge.do_action("knob_set", {"port": "http://x"})[0])
    bridge.do_action("knob_set", {"return_s": 1})
    fk.feed("X1S;")
    wait_for(lambda: bridge.knob_mode == "af")
    check("'back to VFO A after 1 s' works", wait_for(lambda: bridge.knob_mode == "vfoa", 4))
    bridge.do_action("knob_defaults")
    check("default functions restored (port kept)", bridge.knob_cfg["table"] == KNOB_DEFAULT_TABLE
          and bridge.knob_cfg["port"] == "auto" and clean_knob(None)["table"] == KNOB_DEFAULT_TABLE)
    check("Knob window lines follow the mode: in VFO A, button 1 shows 'tap >AF'",
          bridge.knob_mode == "vfoa" and bridge.mmio_vars()["knob_b1"] == "tap >AF   2x >AGC   hold Mute"
          and bridge.mmio_vars()["knob_now"] == "VFO A tuning" and bridge.mmio_vars()["knob_status"] == "FlexControl on FAKE")
    bridge.knob_set_mode("af")
    check("... and in AF volume it shows 'tap >VFO A'", bridge.mmio_vars()["knob_b1"].startswith("tap >VFO A")
          and bridge.mmio_vars()["knob_k"] == "tap >VFO A   2x Mute   hold >VFO A"
          and bridge.mmio_vars()["knob_b3"] == "tap TUNE   2x Band +   hold Band -")
    bridge.knob_set_mode("vfoa")
    ok_, msg_ = bridge.do_action("thetis_knobwin", {"title": "My knob {ver}", "order": ["now", "b1", "bogus", "now"]})
    check("Knob window settings saved (title, order cleaned)", ok_ and bridge.thetis_knobwin ==
          {"enabled": True, "order": ["now", "b1"], "title": "My knob {ver}"} and bridge.settings["thetis_knobwin"]["title"] == "My knob {ver}")
    bridge.do_action("thetis_knobwin", {"enabled": False})
    check("Knob window can be switched off; standard order restorable",
          bridge.thetis_knobwin["enabled"] is False and bridge.do_action("thetis_knobwin_default")[0]
          and bridge.thetis_knobwin["order"] == KW_DEFAULT)
    bridge.do_action("thetis_knobwin", {"enabled": True, "title": TITLE_KNOB})
    st = get_state()
    check("panel state shows the knob (connected, mode, last press)",
          st["knob"]["connected"] and st["knob"]["mode"] == "vfoa" and st["knob"]["last"] == "X1S")
    bridge.knob.stop.set()
    time.sleep(0.1)
    bridge.knob = None
    bridge.knob_mode = "vfoa"

    print("-- web control panel --")
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0)
    s = get_state()
    check("GET /api/state returns live data (7.150 MHz, OPERATE)",
          s["freq_khz"] == 7150 and s["mode"] == "OPERATE")
    code, j = post("atu_bypass")
    check("button ATU BYPASS -> amp receives ^AMB; and state follows",
          code == 200 and j["ok"] and wait_for(lambda: amp.atu == "B")
          and wait_for(lambda: bridge.atu == "B"))
    code, j = post("atu_inline")
    check("button ATU INLINE -> amp receives ^AMI;", wait_for(lambda: amp.atu == "I"))
    check("ATU capacitor / inductor relays and side are read from the amp",
          wait_for(lambda: bridge.atu_c == 0x2C and bridge.atu_l == 0x0A and bridge.atu_side == "A", 8))
    code, j = post("ant2")
    check("button ANT 2 -> amp antenna 2", wait_for(lambda: amp.ant == 2))
    code, j = post("atu_tune")
    check("button ATU TUNE -> amp receives ^FT;",
          wait_for(lambda: "^FT;" in amp.rx_log))
    code, j = post("atu_cancel")
    check("button Cancel tune -> amp receives ^FE;",
          wait_for(lambda: "^FE;" in amp.rx_log))
    amp.fault = 0x91
    wait_for(lambda: bridge.fault == 0x91)
    check("fault 91 shown with description",
          get_state()["fault_text"] == "SWR very high")
    code, j = post("clear_fault")
    check("button Clear fault -> ^FLC; and fault clears",
          wait_for(lambda: bridge.fault == 0))
    code, j = post("standby")
    check("button STANDBY -> amp standby", wait_for(lambda: amp.mode == 0))
    code, j = post("operate")
    check("button OPERATE -> amp operate", wait_for(lambda: amp.mode == 1))
    code, j = post("sot_off")
    check("Standby-on-Tune switch can be turned off",
          not get_state()["standby_on_tune"])
    post("sot_on")

    print("-- safety interlocks --")
    amp.fwd = 500
    wait_for(lambda: bridge.fwd == 500)
    before = list(amp.rx_log)
    code, j = post("atu_bypass")
    time.sleep(0.15)
    check("ATU BYPASS refused while transmitting (nothing sent)",
          code == 200 and j["ok"] is False and amp.atu == "I"
          and "^AMB;" not in amp.rx_log[len(before):])
    code, j = post("ant1")
    check("antenna change refused while transmitting",
          j["ok"] is False and amp.ant == 2)
    code, j = post("power_off")
    check("power-off refused while transmitting",
          j["ok"] is False and "^ON0;" not in amp.rx_log)
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0)
    code, _ = post("operate", header=False)
    check("POST without X-KPA header rejected (cross-site protection)", code == 403)
    bridge.a.web_token = "secret"
    bridge.local_no_token = False        # act as if from another computer
    c1 = post("operate")[0]
    c2 = post("operate", token="secret")[0]
    try:
        get_state()
        c3 = 200
    except urllib.error.HTTPError as e:
        c3 = e.code
    bridge.local_no_token = True
    try:
        c4 = 200 if get_state() else 0
    except urllib.error.HTTPError as e:
        c4 = e.code
    check("--web-token enforced for other computers (403 without, 200 with)",
          c1 == 403 and c2 == 200 and c3 == 403)
    check("the bridge computer itself opens the panel without the password", c4 == 200
          and get_state()["client_local"] is True and get_state()["web_password_set"] is True)
    rq = urllib.request.Request(base + "/api/cmd", json.dumps({"action": "web_password", "params": {"token": ""}}).encode(),
                                {"Content-Type": "application/json", "X-KPA": "1"}, method="POST")
    with urllib.request.urlopen(rq, timeout=3) as r_:
        j = json.loads(r_.read())
    check("forgotten password: removed from the panel on the bridge computer (and saved)",
          j["ok"] and bridge.a.web_token == "" and bridge.settings.get("web_token") == "")
    check("bad passwords refused", not bridge.do_action("web_password", {"token": "a b"})[0]
          and not bridge.do_action("web_password", {"token": "ab"})[0])
    ok_, _m = bridge.do_action("web_password", {"token": "New_pw-1"})
    check("a new password can be set", ok_ and bridge.a.web_token == "New_pw-1")
    bridge.do_action("web_password", {"token": ""})
    bridge.settings.pop("web_token", None)
    bridge.a.web_token = ""

    print("-- LP-100A --")
    fake_ser.frame = TX_FRAME
    check("LP-100A frame parsed (250 W, SWR 1.35, alarm 2.0, AVG)",
          wait_for(lambda: (bridge.lp.snapshot() or {}).get("pwr") == 250.0))
    lp = bridge.lp.snapshot()
    check("derived values: R=56.9, X=-20.7, refl 5.5 W, RL 16.5 dB",
          abs(lp["r"] - 56.85) < 0.1 and abs(lp["x"] + 20.69) < 0.1
          and abs(lp["refl"] - 5.55) < 0.1 and abs(lp["rl"] - 16.5) < 0.2
          and lp["alarm_txt"] == "2.0" and lp["mode_txt"] == "AVG")
    check("LP-100A shows in /api/state", get_state()["lp"]["swr"] == 1.35)
    code, j = post("atu_bypass")
    check("LP-100A power alone also blocks ATU changes (RF seen by meter)",
          j["ok"] is False)
    post("lp_alarm")
    post("lp_mode")
    check("LP-100A Alarm/Mode buttons send 'A' and 'F' only",
          wait_for(lambda: b"A" in fake_ser.written and b"F" in fake_ser.written)
          and b"M" not in fake_ser.written)
    check("LP-100A parser rejects garbage", parse_lp100(";abc,def") is None)

    print("-- remote power-on (Wake-on-LAN) --")
    pkt = build_magic("54:10:EC:14:75:22")
    check("magic packet = 6 x FF + MAC x 16 (102 bytes)",
          len(pkt) == 102 and pkt[:6] == b"\xff" * 6
          and pkt[6:12] == bytes.fromhex("5410EC147522") and pkt[6:] == pkt[6:12] * 16)
    check("MAC normalizing (Windows arp style, short octets)",
          norm_mac("54-10-ec-14-75-2") == "54:10:EC:14:75:02" and norm_mac("zz") is None)
    check("amp MAC learned automatically from ^MA;",
          wait_for(lambda: bridge.mac == "54:10:EC:14:75:22", 6))
    check("amp Wake-on-LAN setting read (OFF)", wait_for(lambda: bridge.wol is False, 6))
    post("enable_wol")
    check("button Enable Wake-on-LAN -> ^WL1; and state follows",
          wait_for(lambda: amp.wl == 1) and wait_for(lambda: bridge.wol is True))
    wol_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    wol_sock.bind(("127.0.0.1", 0))
    wol_sock.settimeout(3)
    bridge.a.wol_port = wol_sock.getsockname()[1]
    amp.asleep = True
    code, j = post("power_on")
    try:
        got = wol_sock.recvfrom(2048)[0]
    except socket.timeout:
        got = b""
    check("button Power ON -> magic packet actually sent on the network",
          got == pkt)
    check("sleeping amp wakes (^ON1; reaches it) and power-on is confirmed",
          wait_for(lambda: not amp.asleep, 5)
          and wait_for(lambda: bridge.last_msg == "Amplifier powered on", 6))
    wol_sock.close()

    print("-- Thetis Multi Meter I/O feed (telemetry out) --")
    import xml.etree.ElementTree as ET
    fake_ser.frame = IDLE_FRAME
    amp.fwd = 0
    amp.atu, amp.ant = "I", 1
    wait_for(lambda: bridge.atu == "I" and bridge.ant == 1 and bridge.fwd == 0)
    recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv.bind(("127.0.0.1", 0))
    recv.settimeout(0.2)
    bridge.a.mmio_host, bridge.a.mmio_port = "127.0.0.1", recv.getsockname()[1]
    bridge.a.mmio_rate = 50.0
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    free_port = probe.getsockname()[1]
    probe.close()
    bridge.a.mmio_listen = free_port
    bridge.start_mmio()

    def grab(n=1, t=1.5):
        got, end = [], time.time() + t
        while len(got) < n and time.time() < end:
            try:
                got.append(recv.recvfrom(65535)[0])
            except socket.timeout:
                pass
        return got

    def grab_match(pred, t=4.0):
        """Drain queued datagrams until one satisfies pred (old ones are skipped)."""
        end = time.time() + t
        while time.time() < end:
            try:
                d = recv.recvfrom(65535)[0]
            except socket.timeout:
                continue
            if pred(d):
                return d
        return b""

    bridge.a.mmio_format, bridge.a.mmio_term = "json", "none"
    dg = grab_match(lambda d: d.startswith(b"{"))
    j = json.loads(dg.decode() or "{}")
    check("JSON feed: valid JSON with amp and LP variables",
          j["amp_online"] == 1 and j["amp_atu"] == "INLINE" and j["amp_ant"] == 1
          and "lp_swr" in j and "amp_drive" in j and "amp_fault_text" in j)
    bridge.a.mmio_format = "xml"
    dg = grab_match(lambda d: d.startswith(b"<kpa>"))
    root = ET.fromstring(dg.decode() or "<x/>")
    check("XML feed: well-formed, root <kpa>, children named after variables",
          root.tag == "kpa" and root.find("amp_online").text == "1"
          and root.find("amp_mode").text in ("OPERATE", "STANDBY")
          and root.find("lp_online").text == "1")
    bridge.a.mmio_format = "raw"
    grab_match(lambda d: d.startswith(b"amp_online:"))
    dgs = [d.decode() for d in grab(150, 2.0)]
    check("raw feed: one 'name:value' message per variable",
          "amp_online:1" in dgs and any(d.startswith("amp_fwd:") for d in dgs))
    bridge.a.mmio_format, bridge.a.mmio_term = "json", "crlf"
    check("terminator CRLF is appended",
          grab_match(lambda d: d.startswith(b"{") and d.endswith(b"\r\n")) != b"")
    bridge.a.mmio_format, bridge.a.mmio_term = "xml", "none"
    check("mmio_encode: bool/float formatting",
          mmio_encode({"a": True, "b": 1.5, "c": 2.0}, "xml", "none")[0]
          == b"<kpa><a>true</a><b>1.5</b><c>2</c></kpa>")

    print("-- Thetis button commands (in) --")
    cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_cmd(text):
        cmd.sendto(text.encode(), ("127.0.0.1", free_port))

    time.sleep(0.4)
    send_cmd("KPA_ATU_BYPASS")
    check("plain string KPA_ATU_BYPASS -> amp bypass", wait_for(lambda: amp.atu == "B"))
    wait_for(lambda: bridge.atu == "B")
    time.sleep(0.3)
    send_cmd('{"cmd":"KPA_ATU_TOGGLE"}')
    check("JSON-wrapped KPA_ATU_TOGGLE -> flips back to inline", wait_for(lambda: amp.atu == "I"))
    send_cmd("<m>KPA_ANT2</m>")
    check("XML-wrapped KPA_ANT2 -> antenna 2", wait_for(lambda: amp.ant == 2))
    wait_for(lambda: bridge.mode == amp.mode)
    mode0 = amp.mode
    time.sleep(0.3)
    send_cmd("KPA_OPERATE_TOGGLE\r\n")
    check("KPA_OPERATE_TOGGLE with CRLF -> amp mode flips", wait_for(lambda: amp.mode != mode0))
    wait_for(lambda: bridge.mode == amp.mode)
    time.sleep(0.3)
    m1 = amp.mode
    send_cmd("KPA_OPERATE_TOGGLE")
    send_cmd("KPA_OPERATE_TOGGLE")
    time.sleep(0.5)
    check("duplicate button message within 0.25 s is ignored (debounce)", amp.mode != m1)
    n0 = len(amp.rx_log)
    send_cmd("KPA_FORMAT_DISK")
    send_cmd("hello world")
    time.sleep(0.4)
    check("unknown strings are ignored (nothing sent to the amp)",
          not any(x.startswith("^ON") and x != "^ON;" for x in amp.rx_log[n0:]))
    n0 = len(amp.rx_log)
    send_cmd("KPA_POWER_OFF")
    check("KPA_POWER_OFF from Thetis powers the amp off at once (no question asked)",
          wait_for(lambda: "^ON0;" in amp.rx_log[n0:]))
    seen = []
    orig_log = bridge.log
    bridge.log = lambda msg, verbose=False: (seen.append(msg), orig_log(msg, verbose))[1]
    send_cmd("hello from thetis")
    wait_for(lambda: any("no KPA_ command" in x for x in seen))
    bridge.log = orig_log
    check("a message with no KPA_ command is reported (helps fix a wrong string in Thetis)",
          any("no KPA_ command" in x and "hello from thetis" in x for x in seen))
    amp.fwd = 500
    wait_for(lambda: bridge.fwd == 500)
    cur = amp.atu
    time.sleep(0.3)
    send_cmd("KPA_ATU_TOGGLE")
    time.sleep(0.4)
    check("Thetis button refused while transmitting (interlock still applies)", amp.atu == cur)
    n0 = len(amp.rx_log)
    send_cmd("KPA_POWER_OFF")
    time.sleep(0.4)
    check("KPA_POWER_OFF from Thetis is refused while transmitting", "^ON0;" not in amp.rx_log[n0:])
    amp.fwd = 0

    print("-- single-instance guard (used by the .bat file) --")
    import subprocess
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    lport = probe.getsockname()[1]
    probe.close()
    me = os.path.abspath(__file__)
    base_args = [sys.executable, me, "--lock-port", str(lport)]
    child = subprocess.Popen(base_args + ["--dry-run", "--no-web", "--tci-port", "1",
                                          "--amp-ip", "127.0.0.1", "--amp-port", "9",
                                          "--logfile", ""],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    rc_busy = subprocess.run(base_args + ["--check-running"], capture_output=True).returncode
    second = subprocess.run(base_args + ["--dry-run", "--no-web", "--logfile", ""],
                            capture_output=True, text=True, timeout=10)
    check("--check-running reports 3 while a bridge is running", rc_busy == 3)
    check("a second bridge refuses to start (exit 3, clear message)",
          second.returncode == 3 and "already running" in second.stdout)
    child.terminate()
    child.wait(timeout=5)
    time.sleep(0.3)
    rc_free = subprocess.run(base_args + ["--check-running"], capture_output=True).returncode
    check("--check-running reports 0 once the bridge has stopped", rc_free == 0)

    print("-- change the LP-100A port while the bridge runs --")
    import tempfile
    calls = []

    def spy_opener(port, baud):
        calls.append((port, baud))
        return FakeSerial(TX_FRAME)

    def post_params(action, params):
        rq = urllib.request.Request(base + "/api/cmd",
                                    json.dumps({"action": action, "params": params}).encode(),
                                    {"Content-Type": "application/json", "X-KPA": "1"},
                                    method="POST")
        with urllib.request.urlopen(rq, timeout=3) as r:
            return json.loads(r.read())

    tmp = os.path.join(tempfile.gettempdir(), "kpa_settings_test_%d.json" % os.getpid())
    bridge.lp.stop.set()
    time.sleep(0.2)
    bridge.lp = LP100("", 115200, spy_opener, bridge.log, interval=0.02)
    bridge.lp.start()
    bridge.a.settings_file, bridge.settings = tmp, {}
    st = get_state()
    check("panel state carries the Thetis meter values (Thetis look)",
          isinstance(st.get("mm"), dict) and "amp_fwd" in st["mm"] and "amp_sot_text" in st["mm"])
    check("panel page has the Thetis look and its preset",
          'id="thetis"' in PAGE_HTML and "n==='thetis'" in PAGE_HTML and 'id="d_style"' in PAGE_HTML)
    check("no port set: LP-100A reported as not configured",
          st["lp_enabled"] is False and st["lp_port"] == "" and not calls)
    j = post_params("lp_port", {"port": "COM7", "baud": 115200})
    check("choose COM7 @ 115200: accepted and the serial port is opened",
          j["ok"] and wait_for(lambda: ("COM7", 115200) in calls))
    check("LP-100A data flows and state shows port/connected",
          wait_for(lambda: get_state()["lp"] is not None)
          and get_state()["lp_port"] == "COM7" and get_state()["lp_connected"]
          and get_state()["lp_enabled"])
    j = post_params("lp_port", {"port": "COM9", "baud": 38400})
    check("switch to COM9 @ 38400 while running: reconnects on the new port",
          j["ok"] and wait_for(lambda: ("COM9", 38400) in calls)
          and get_state()["lp_port"] == "COM9")
    n_calls = len(calls)
    bad1 = post_params("lp_port", {"port": "../../etc/passwd", "baud": 115200})
    bad2 = post_params("lp_port", {"port": "COM3", "baud": 12345})
    bad3 = post_params("lp_port", {"port": "COM3", "baud": "fast"})
    time.sleep(0.2)
    check("bad port name / baud rate rejected, nothing reconnects",
          not bad1["ok"] and not bad2["ok"] and not bad3["ok"] and len(calls) == n_calls
          and get_state()["lp_port"] == "COM9")
    saved = load_settings(tmp)
    check("choice saved to the settings file for next start",
          saved.get("lp100_port") == "COM9" and saved.get("lp100_baud") == 38400)
    j = post_params("lp_port", {"port": "", "baud": 115200})
    wait_for(lambda: not get_state()["lp_enabled"])
    time.sleep(0.3)
    st = get_state()
    check("Disconnect: LP-100A off, no stale readings, nothing reopened",
          not st["lp_enabled"] and st["lp"] is None and st["lp_port"] == ""
          and len(calls) == n_calls)
    check("settings file remembers the disconnect", load_settings(tmp).get("lp100_port") == "")
    j = post_params("lp_alarm", {})
    check("LP alarm button refused when no port is configured", j["ok"] is False)
    os.remove(tmp)

    print("-- revision number --")
    with urllib.request.urlopen(base + "/", timeout=3) as r:
        page = r.read().decode()
    check("state reports the bridge version", get_state()["version"] == VERSION)
    check("page is served with the version filled in (no placeholder left)",
          "__VERSION__" not in page and "'%s'" % VERSION in page)
    out = subprocess.run([sys.executable, me, "--version"], capture_output=True, text=True)
    check("--version prints the revision and date",
          VERSION in out.stdout and BUILD_DATE in out.stdout)

    print("-- keyboard commands in the bridge window --")
    answers = []
    ck = ConsoleKeys(bridge, read_line=lambda prompt: answers.pop(0))
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0 and not bridge.transmitting())
    n = len(amp.rx_log)
    answers[:] = ["no"]
    ck.handle_key("x")
    time.sleep(0.3)
    check("X (confirmation ON): answering 'no' cancels, nothing sent",
          "^ON0;" not in amp.rx_log[n:])
    answers[:] = ["YES"]
    ck.handle_key("X")
    check("X (confirmation ON): typing YES sends power-off",
          wait_for(lambda: "^ON0;" in amp.rx_log[n:]))
    ck.handle_key("y")
    check("Y turns 'ask before Power OFF' off (also visible to the panel)",
          bridge.confirm_power_off is False and get_state()["confirm_off"] is False)
    n = len(amp.rx_log)
    ck.handle_key("x")
    check("X (confirmation OFF): sends at once, no question asked",
          wait_for(lambda: "^ON0;" in amp.rx_log[n:]) and answers == [])
    amp.fwd = 500
    wait_for(lambda: bridge.fwd == 500)
    n = len(amp.rx_log)
    ck.handle_key("x")
    time.sleep(0.3)
    check("X is refused while transmitting even with confirmation off",
          "^ON0;" not in amp.rx_log[n:])
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0)
    ck.handle_key("y")
    check("Y turns it back on", bridge.confirm_power_off is True)

    print("-- heartbeat for Thetis --")
    hb = bridge.mmio_vars()["bridge_time"]
    check("bridge_time heartbeat is the current time in whole seconds",
          isinstance(hb, int) and abs(hb - time.time()) < 2)

    print("-- SWR with no RF --")
    amp.fwd = 0
    check("amp SWR reads 1.0 when there is no forward power (no stale value)",
          wait_for(lambda: bridge.fwd == 0 and bridge.swr == 1.0 and bridge.mmio_vars()["amp_swr"] == 1.0))
    amp.fwd = 500
    check("amp SWR follows the amp again under RF",
          wait_for(lambda: bridge.fwd == 500 and abs(bridge.swr - 1.4) < 1e-9))
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0)

    print("-- power-off options (Allow Thetis / Block under RF) --")
    check("defaults: Thetis may power off, power off blocked under RF",
          bridge.allow_thetis_off is True and bridge.block_off_tx is True
          and get_state()["thetis_off"] is True and get_state()["block_off_tx"] is True)
    ck.handle_key("k")
    check("K turns 'Allow Thetis to power off' off (saved, visible to the panel)",
          bridge.allow_thetis_off is False and get_state()["thetis_off"] is False)
    n = len(amp.rx_log)
    send_cmd("KPA_POWER_OFF")
    time.sleep(0.5)
    check("with it off, KPA_POWER_OFF from Thetis is refused", "^ON0;" not in amp.rx_log[n:])
    ck.handle_key("K")
    check("K turns it back on", bridge.allow_thetis_off is True)
    amp.fwd = 500
    wait_for(lambda: bridge.fwd == 500)
    ck.handle_key("b")
    check("B turns 'Block power off while transmitting' off",
          bridge.block_off_tx is False and get_state()["block_off_tx"] is False)
    n = len(amp.rx_log)
    time.sleep(0.3)
    send_cmd("KPA_POWER_OFF")
    check("emergency: KPA_POWER_OFF from Thetis works under RF when blocking is off",
          wait_for(lambda: "^ON0;" in amp.rx_log[n:]))
    n = len(amp.rx_log)
    ok_, msg_ = bridge.do_action("atu_bypass")
    check("other interlocks still apply under RF (ATU change refused)",
          ok_ is False and "^AMB;" not in amp.rx_log[n:])
    ck.handle_key("B")
    n = len(amp.rx_log)
    ok_, msg_ = bridge.do_action("power_off")
    check("B turns blocking back on: power off refused under RF again",
          ok_ is False and "^ON0;" not in amp.rx_log[n:] and bridge.block_off_tx is True)
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0)
    wait_for(lambda: bridge.mode == amp.mode)
    m0 = amp.mode
    ck.handle_key("o")
    check("O toggles operate / standby", wait_for(lambda: amp.mode != m0))
    wait_for(lambda: bridge.atu == amp.atu)
    a0 = amp.atu
    ck.handle_key("a")
    check("A toggles ATU inline / bypass", wait_for(lambda: amp.atu != a0))
    n = len(amp.rx_log)
    ck.handle_key("c")
    check("C clears the fault", wait_for(lambda: "^FLC;" in amp.rx_log[n:]))
    answers[:] = ["com6", "38400"]
    ck.handle_key("L")
    check("L: 'com6' is fixed to COM6 and the port opens at 38400 baud",
          wait_for(lambda: ("COM6", 38400) in calls) and bridge.lp.port == "COM6")
    answers[:] = [""]
    ck.handle_key("l")
    check("L then Enter keeps the current port", bridge.lp.port == "COM6")
    answers[:] = ["-", ""]
    ck.handle_key("l")
    check("L then '-' disconnects the LP-100A", wait_for(lambda: bridge.lp.port == ""))
    answers[:] = ["bad name", ""]
    ck.handle_key("l")
    check("L with a bad port name is refused", bridge.lp.port == "")
    ck.handle_key("h")
    ck.handle_key("v")
    ck.handle_key("q")
    check("H and V work; Q sets the quit flag", bridge.quit is True)
    bridge.quit = False
    bridge.lp.stop.set()

    print("-- fan speed control --")
    amp.fan_min = 1
    check("fan speed and minimum are polled from the amp (^FS; ^FC;)",
          wait_for(lambda: bridge.fan_speed == 1 and bridge.fan_min == 1))
    st = get_state()
    check("panel state reports fan speed and minimum", st["fan"] == 1 and st["fan_min"] == 1)
    j = post_params("fan_min", {"speed": 3})
    check("set minimum fan speed 3: amp receives ^FC3; and it is read back",
          j["ok"] and wait_for(lambda: amp.fan_min == 3) and wait_for(lambda: bridge.fan_min == 3))
    check("current speed follows (never below the minimum)", wait_for(lambda: bridge.fan_speed == 3))
    before = amp.fan_min
    bad = [post_params("fan_min", {"speed": v}) for v in (6, -1, "x", None, 2.5 * 4)]
    time.sleep(0.2)
    check("speeds outside 0-5 or not numbers are refused, amp unchanged",
          all(not b_["ok"] for b_ in bad[:4]) and amp.fan_min == before)
    j = post_params("fan_up", {})
    check("fan_up raises the minimum by one", j["ok"] and wait_for(lambda: amp.fan_min == 4))
    post_params("fan_up", {})
    wait_for(lambda: amp.fan_min == 5)
    n = len(amp.rx_log)
    j = post_params("fan_up", {})
    time.sleep(0.2)
    check("fan_up at 5 stops there and says so (nothing sent)",
          j["ok"] and "already 5" in j["message"] and not any(c_.startswith("^FC") and c_ != "^FC;" for c_ in amp.rx_log[n:]))
    for _ in range(5):
        post_params("fan_down", {})
        time.sleep(0.15)
    check("fan_down steps to 0 and stops", wait_for(lambda: amp.fan_min == 0))
    amp.fwd = 500
    wait_for(lambda: bridge.fwd == 500)
    j = post_params("fan_min", {"speed": 2})
    check("fan changes are allowed while transmitting (no interlock)",
          j["ok"] and wait_for(lambda: amp.fan_min == 2))
    amp.fwd = 0
    wait_for(lambda: bridge.fwd == 0)
    mv = bridge.mmio_vars()
    check("Thetis variables amp_fan and amp_fan_min are published",
          mv["amp_fan"] == bridge.fan_speed and mv["amp_fan_min"] == 2)
    send_cmd("KPA_FAN_5")
    check("Thetis string KPA_FAN_5 sets minimum fan speed 5", wait_for(lambda: amp.fan_min == 5))
    time.sleep(0.35)
    send_cmd("KPA_FAN_DOWN")
    check("Thetis string KPA_FAN_DOWN lowers it by one", wait_for(lambda: amp.fan_min == 4))
    time.sleep(0.35)
    send_cmd("KPA_FAN_UP")
    check("Thetis string KPA_FAN_UP raises it by one", wait_for(lambda: amp.fan_min == 5))
    time.sleep(0.35)
    send_cmd("KPA_FAN_0")
    check("Thetis string KPA_FAN_0 sets the fans back to automatic", wait_for(lambda: amp.fan_min == 0))
    wait_for(lambda: bridge.fan_min == 0)
    ck.handle_key("+")
    check("+ key raises the fan minimum", wait_for(lambda: amp.fan_min == 1))
    wait_for(lambda: bridge.fan_min == 1)
    ck.handle_key("-")
    check("- key lowers it", wait_for(lambda: amp.fan_min == 0))
    answers[:] = ["4"]
    ck.handle_key("f")
    check("F key asks for a speed and sets it", wait_for(lambda: amp.fan_min == 4) and not answers)
    answers[:] = [""]
    ck.handle_key("F")
    check("F then Enter keeps the current setting", amp.fan_min == 4)
    answers[:] = ["9"]
    ck.handle_key("f")
    time.sleep(0.2)
    check("F with an out-of-range number is refused", amp.fan_min == 4)
    amp.fan_min = 1

    print("-- finding the amplifier on the network --")
    import ipaddress as ipa
    P = amp.port
    amp2 = FakeAmp("127.0.0.2", P)
    amp2.serial, amp2.firmware = "00099", "02.31"
    amp3 = FakeAmp("127.0.0.3", P)
    amp3.junk = True
    amp4 = FakeAmp("127.0.0.4", P)
    amp4.boot, amp4.serial = True, "00100"
    for a_ in (amp2, amp3, amp4):
        a_.start()
    found = discover_amps([ipa.ip_network("127.0.0.0/29")], P, passes=2, wait=0.4)
    ips_found = [f["ip"] for f in found]
    check("search finds every amplifier that answers ^I; with ^KPA1500;",
          ips_found == ["127.0.0.1", "127.0.0.2", "127.0.0.4"])
    check("serial number, firmware and MAC are read from each",
          found[0]["serial"] == "00022" and found[1]["serial"] == "00099"
          and found[1]["firmware"] == "02.31" and found[0]["mac"] == "54:10:EC:14:75:22")
    check("something answering with junk is not listed", "127.0.0.3" not in ips_found)
    check("an amplifier in boot block (lowercase ^kpa1500;) is found and flagged",
          found[2]["boot"] is True and found[0]["boot"] is False)
    check("a network with no amplifier gives an empty list",
          discover_amps([ipa.ip_network("127.0.0.8/29")], P, passes=1, wait=0.3) == [])
    check("network choice: given ranges are used as typed; otherwise the /24 of the known address",
          [str(n) for n in discovery_networks("192.168.1.0/24, 10.1.0.0/22", "x")] == ["192.168.1.0/24", "10.1.0.0/22"]
          and ipa.ip_network("192.168.0.0/24") in discovery_networks("", "192.168.0.175"))
    try:
        discovery_networks("10.0.0.0/8", "x")
        too_big_refused = False
    except ValueError:
        too_big_refused = True
    check("a huge network (/8) is refused", too_big_refused)
    check("address choice: explicit flag wins, 'auto' and default use the saved address",
          resolve_amp_ip("1.2.3.4", "9.9.9.9") == ("1.2.3.4", "flag")
          and resolve_amp_ip("auto", "9.9.9.9") == ("9.9.9.9", "auto")
          and resolve_amp_ip(None, "9.9.9.9") == ("9.9.9.9", "saved")
          and resolve_amp_ip(None, None) == (DEFAULT_AMP_IP, "default"))

    sfile = os.path.join(tempfile.gettempdir(), "kpa_ip_settings_%d.json" % os.getpid())
    bridge.a.discover_net = "127.0.0.0/29"
    bridge.a.settings_file, bridge.settings = sfile, {}
    ok_, msg_ = bridge.do_action("amp_find")
    check("panel/window search reports what it found (3 listed with details)",
          ok_ and "Found 3 KPA1500" in msg_ and "serial 00099" in msg_ and len(bridge.found_amps) == 3
          and len(get_state()["found"]) == 3)
    bad_ips = ["8.8.8.8", "abc", "224.0.0.1", "0.0.0.0", "", "::1", "1.2.3"]
    res = [bridge.do_action("amp_ip", {"ip": v})[0] for v in bad_ips]
    check("addresses that are not usable local IPv4 addresses are refused",
          not any(res) and bridge.amp.addr[0] == "127.0.0.1")
    ok_, msg_ = bridge.do_action("amp_ip", {"ip": "127.0.0.2"})
    check("switch to the second amplifier while running", ok_ and bridge.amp.addr == ("127.0.0.2", P)
          and get_state()["amp_ip"] == "127.0.0.2")
    check("bridge now polls the new amplifier and re-sends the radio frequency to it",
          wait_for(lambda: bridge.amp_ok and any(c_ == "^WS;" for c_ in amp2.rx_log))
          and wait_for(lambda: amp2.freq == 7150))
    check("the choice is saved for the next start", load_settings(sfile).get("amp_ip") == "127.0.0.2")
    check("answering once records the address as seen (for the next start)",
          wait_for(lambda: load_settings(sfile).get("amp_seen_ip") == "127.0.0.2", 3))
    check("power state ON while the amp answers", wait_for(lambda: bridge.mmio_vars()["amp_mode"] in ("OPERATE", "STANDBY"), 5)
          and get_state()["power"] == "ON" and bridge.mmio_vars()["amp_power"] == "ON")
    amp2.asleep = True                     # amp loses power / goes to sleep
    check("amp goes silent: state shows OFF, mode OFF, readings cleared",
          wait_for(lambda: not bridge.amp_ok, 8) and get_state()["power"] == "OFF"
          and get_state()["mode"] == "OFF" and get_state()["fwd"] == 0
          and bridge.mmio_vars()["amp_mode"] == "OFF" and bridge.mmio_vars()["amp_power"] == "OFF"
          and bridge.mmio_vars()["amp_online"] == 0 and "AMP:OFF" in bridge.status_text())
    mv = bridge.mmio_vars()
    st = get_state()
    check("all amp readings cleared when the amp is off (nothing stale)",
          st["swr"] == 1.0 and st["temp"] is None and st["volts"] is None and st["amps"] is None
          and st["atu"] is None and st["ant"] is None and st["fan"] is None and st["fan_min"] is None
          and mv["amp_temp"] == 0 and mv["amp_volts"] == 0 and mv["amp_ant"] == 0 and mv["amp_fan"] == 0
          and mv["amp_atu"] == "--" and mv["amp_fault_text"] == "--" and mv["amp_atu_inline"] == 0)
    amp2.asleep = False
    check("amp answers again: back to ON", wait_for(lambda: bridge.amp_ok, 8) and get_state()["power"] == "ON")
    amp2.fwd = 500
    wait_for(lambda: bridge.fwd == 500)
    ok_, msg_ = bridge.do_action("amp_ip", {"ip": "127.0.0.1"})
    check("the address cannot be changed while transmitting",
          not ok_ and "transmitting" in msg_ and bridge.amp.addr[0] == "127.0.0.2")
    amp2.fwd = 0
    wait_for(lambda: bridge.fwd == 0)
    answers[:] = ["2"]
    ck.handle_key("d")
    check("D key: lists the amplifiers found and switches to the one you number",
          wait_for(lambda: bridge.amp.addr[0] == "127.0.0.2") and not answers)
    answers[:] = ["1"]
    ck.handle_key("D")
    check("D key: choosing 1 switches to the first", wait_for(lambda: bridge.amp.addr[0] == "127.0.0.1"))
    answers[:] = [""]
    ck.handle_key("d")
    check("D key then Enter keeps the current address", bridge.amp.addr[0] == "127.0.0.1")
    answers[:] = ["7"]
    ck.handle_key("d")
    check("D key with a bad number keeps the current address", bridge.amp.addr[0] == "127.0.0.1")
    os.remove(sfile)
    bridge.a.settings_file = ""

    def make(extra):
        a2 = build_parser().parse_args(["--amp-port", str(P), "--discover-net", "127.0.0.0/29",
                                        "--logfile", "", "--mac-file", ""] + extra)
        return Bridge(a2, quiet=True)

    json.dump({"amp_ip": "127.0.0.6"}, open(sfile, "w"))
    b1 = make(["--amp-ip", "auto", "--settings-file", sfile])
    check("--amp-ip auto starts from the saved address", b1.amp.addr[0] == "127.0.0.6")
    check("auto: saved address is dead, so the network is searched and the amplifier found",
          b1.startup_discovery() and b1.amp.addr[0] == "127.0.0.1" and len(b1.found_amps) == 3
          and load_settings(sfile).get("amp_ip") == "127.0.0.1")
    json.dump({"amp_ip": "127.0.0.2"}, open(sfile, "w"))
    b2 = make(["--amp-ip", "auto", "--settings-file", sfile])
    t0 = time.time()
    check("auto: saved address answers, so no search is done",
          b2.startup_discovery() and b2.amp.addr[0] == "127.0.0.2" and not b2.found_amps
          and time.time() - t0 < 2.5)
    b3 = make(["--amp-ip", "127.0.0.1", "--settings-file", sfile])
    check("an explicit --amp-ip beats the saved address", b3.amp.addr[0] == "127.0.0.1")
    b4 = make(["--settings-file", sfile])
    check("with no flag the saved address is used", b4.amp.addr[0] == "127.0.0.2")
    b5 = make(["--amp-ip", "auto", "--settings-file", ""])
    b5.a.discover_net = "127.0.0.8/29"
    check("auto with nothing on the network: reports it and keeps going (no crash)",
          b5.startup_discovery() is False)
    ok_, msg_ = b3.do_action("amp_ip", {"ip": "127.0.0.2"})
    check("changing the address when --amp-ip is set warns that the flag wins next time",
          ok_ and "--amp-ip" in msg_)
    os.remove(sfile)
    out = subprocess.run([sys.executable, me, "--discover", "127.0.0.0/29", "--amp-port", str(P),
                          "--settings-file", ""], capture_output=True, text=True, timeout=30)
    check("--discover lists amplifiers, tells you the address to use, exit code 0",
          out.returncode == 0 and "Found: 127.0.0.1 (serial 00022" in out.stdout
          and "--amp-ip 127.0.0.1" in out.stdout)
    out = subprocess.run([sys.executable, me, "--discover", "127.0.0.8/29", "--amp-port", str(P),
                          "--settings-file", ""], capture_output=True, text=True, timeout=30)
    check("--discover with nothing found says so, exit code 1",
          out.returncode == 1 and "No KPA1500 answered" in out.stdout)
    out = subprocess.run([sys.executable, me, "--discover", "10.0.0.0/8", "--settings-file", ""],
                         capture_output=True, text=True, timeout=30)
    check("--discover refuses a network that is too large", out.returncode != 0 and "too large" in (out.stderr + out.stdout))
    for a_ in (amp2, amp3, amp4):
        a_.running = False

    print("-- installer support (probe, WoL broadcast) --")
    pamp = FakeAmp("127.0.0.1", 0)
    pamp.start()
    out = subprocess.run([sys.executable, me, "--probe", "127.0.0.1", "--amp-port", str(pamp.port)],
                         capture_output=True, text=True, timeout=30)
    check("--probe finds a KPA1500 at a given address (exit 0)",
          out.returncode == 0 and "answered" in out.stdout)
    pamp.running = False
    time.sleep(0.6)
    out = subprocess.run([sys.executable, me, "--probe", "127.0.0.1", "--amp-port", str(pamp.port)],
                         capture_output=True, text=True, timeout=30)
    check("--probe reports no answer (exit 1)", out.returncode == 1)
    import tempfile
    sf = os.path.join(tempfile.mkdtemp(), "s.json")
    json.dump({"amp_ip": "127.0.0.9", "amp_seen_ip": "127.0.0.9"}, open(sf, "w"))
    b_seen = Bridge(build_parser().parse_args(["--amp-port", "9", "--logfile", "", "--mac-file", "",
                                               "--settings-file", sf]), quiet=True)
    check("never answering now, but seen at this address before: shows OFF (not NO LINK)",
          b_seen.power_text() == "OFF")
    json.dump({"amp_ip": "127.0.0.9"}, open(sf, "w"))
    b_new = Bridge(build_parser().parse_args(["--amp-port", "9", "--logfile", "", "--mac-file", "",
                                              "--settings-file", sf]), quiet=True)
    check("never seen at this address: NO LINK", b_new.power_text() == "NO LINK")
    b_new.mac, b_new.presence_match = "aa:bb:cc:dd:ee:ff", True
    check("silent but visible on the network with the amp's own MAC: OFF", b_new.power_text() == "OFF")
    b_new.set_amp_ip("127.0.0.8", save=False)
    check("changing the address resets the 'seen before' memory", b_new.power_text() == "NO LINK")
    check("--wol-broadcast option is accepted by the parser",
          build_parser().parse_args(["--wol-broadcast", "10.1.2.255"]).wol_broadcast == "10.1.2.255")
    bridge.a.wol_broadcast = ""

    print("-- built-in help --")
    from html.parser import HTMLParser
    secs = help_sections()
    page_html = render_help_html()
    text_all = render_help_text()

    class Balance(HTMLParser):
        VOID = {"meta", "br", "hr", "img", "link", "input"}

        def __init__(self):
            super().__init__()
            self.stack, self.bad = [], 0

        def handle_starttag(self, tag, attrs):
            if tag not in self.VOID:
                self.stack.append(tag)

        def handle_endtag(self, tag):
            if tag in self.VOID:
                return
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            else:
                self.bad += 1

    bal = Balance()
    bal.feed(page_html)
    check("help HTML is well-formed (every tag closed)", bal.bad == 0 and not bal.stack)
    live_vars = set(bridge.mmio_vars().keys())
    check("every Thetis variable the bridge sends is documented, and nothing extra",
          live_vars == set(MMIO_VAR_HELP) and all(v in page_html for v in live_vars))
    check("every Thetis button string is documented with a description",
          set(MMIO_COMMANDS) == set(MMIO_CMD_HELP) and all(c in page_html for c in MMIO_COMMANDS))
    flags = [o for a_ in build_parser()._actions for o in a_.option_strings if o.startswith("--") and o != "--help"]
    check("every command-line flag appears in the help", all(f in page_html for f in flags))
    titles = [t for _, t, _ in secs]
    check("sections are numbered in order and each is in the contents list",
          all(t.startswith("%d. " % (i + 1)) for i, t in enumerate(titles))
          and all('href="#%s"' % sid in page_html for sid, _, _ in secs))
    check("help covers install, requirements, usage, customizing and Thetis buttons",
          all(any(w in t.lower() for t in titles) for w in
              ("installing", "need", "using", "customiz", "button strings", "goes wrong")))
    check("plain-text help is pure ASCII (safe in any Windows console)",
          all(ord(c) < 128 for c in text_all) and "TODO" not in text_all)
    with urllib.request.urlopen(base + "/help", timeout=3) as r:
        served = r.read().decode()
        ctype = r.headers.get("Content-Type", "")
    check("GET /help serves the help page", "KPA1500 Bridge Help" in served and "KPA_ATU_TOGGLE" in served
          and "text/html" in ctype)
    bridge.a.web_token = "pw"
    try:
        with urllib.request.urlopen(base + "/help", timeout=3) as r:
            help_open = r.status == 200
    except urllib.error.HTTPError:
        help_open = False
    bridge.a.web_token = ""
    check("help stays readable even when the panel has a password", help_open)
    hf = os.path.join(tempfile.gettempdir(), "kpa_help_%d.html" % os.getpid())
    out = subprocess.run([sys.executable, me, "--write-help", hf], capture_output=True, text=True)
    check("--write-help creates the help file", out.returncode == 0 and os.path.exists(hf)
          and "KPA1500 Bridge Help" in open(hf, encoding="utf-8").read())
    os.remove(hf)
    out = subprocess.run([sys.executable, me, "--print-help"], capture_output=True, text=True)
    check("--print-help prints the text help", out.returncode == 0 and "What you need" in out.stdout)

    import webbrowser
    opened = []
    real_open = webbrowser.open
    webbrowser.open = lambda url, *a_, **k_: opened.append(url) or True
    answers = []
    ckh = ConsoleKeys(bridge, read_line=lambda prompt: answers.pop(0))
    ckh.handle_key("w")
    check("W key opens the help page from the running bridge",
          opened and opened[-1] == "http://127.0.0.1:%d/help" % web_port)
    saved_no_web, saved_path = bridge.a.no_web, globals()["help_file_path"]
    globals()["help_file_path"] = lambda: os.path.join(tempfile.gettempdir(), "kpa_help_w_%d.html" % os.getpid())
    bridge.a.no_web = True
    saved_srv = bridge.web
    bridge.web = None
    ckh.handle_key("W")
    wfile = globals()["help_file_path"]()
    check("W key with the panel off writes the help file and opens it",
          opened[-1].startswith("file:") and os.path.exists(wfile))
    bridge.web, bridge.a.no_web = saved_srv, saved_no_web
    globals()["help_file_path"] = saved_path
    os.remove(wfile)
    webbrowser.open = real_open
    answers[:] = [str(help_section_number("customize")), "99", ""]
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ckh.handle_key("i")
    shown = buf.getvalue()
    check("I key lists the topics and prints the chosen one (and rejects a bad number)",
          "Help topics:" in shown and "Customizing" in shown and "Change the short labels" in shown
          and not answers)

    print("-- log file size control --")
    tdir = tempfile.mkdtemp(prefix="kpa_log_")

    def mk_bridge(extra, name="t.log"):
        path = os.path.join(tdir, name)
        a2 = build_parser().parse_args(["--logfile", path, "--settings-file", "",
                                        "--mac-file", ""] + extra)
        return Bridge(a2, quiet=True), path

    lb, lpath = mk_bridge(["--log-max-mb", "0.03"])
    for i in range(3000):
        lb.log("event line %d padding padding padding" % i)
    lim = int(0.03 * 1048576)
    data = open(lpath, encoding="utf-8").read()
    check("log is trimmed automatically and stays under its size limit",
          os.path.getsize(lpath) <= lim + 200)
    check("trimmed log keeps the NEWEST lines and says it was trimmed",
          data.startswith("--- log trimmed") and "event line 2999" in data
          and "event line 0 " not in data)
    size0 = os.path.getsize(lpath)
    for i in range(200):
        lb.log("routine message %d" % i, verbose=True)
    check("routine (verbose) messages are NOT written to the log unless --verbose",
          os.path.getsize(lpath) == size0)
    ok, msg = lb.do_action("log_off")
    size1 = os.path.getsize(lpath)
    for i in range(500):
        lb.log("while off %d" % i)
    check("log OFF: nothing more is written to disk", os.path.getsize(lpath) == size1)
    ok, msg = lb.do_action("log_on")
    lb.log("back on marker")
    check("log ON again: writing resumes", "back on marker" in open(lpath, encoding="utf-8").read())
    check("limit accepts 1/2/5/10 MB and rejects anything else",
          lb.do_action("log_limit", {"mb": 5})[0] and lb.log_max_mb == 5.0
          and not lb.do_action("log_limit", {"mb": 3})[0]
          and not lb.do_action("log_limit", {"mb": "lots"})[0] and lb.log_max_mb == 5.0)
    check("state reports the log settings", lb.state()["log"]["log_max_mb"] == 5.0
          and lb.state()["log"]["log_enabled"] is True)
    ck2 = ConsoleKeys(lb, read_line=lambda prompt: "")
    ck2.handle_key("g")
    off = lb.log_enabled is False
    ck2.handle_key("G")
    check("G key in the bridge window turns the log off and on", off and lb.log_enabled is True)

    big = os.path.join(tdir, "big.log")
    with open(big, "w", encoding="utf-8") as f:
        for i in range(4000):
            f.write("old line %d padding padding padding padding\n" % i)
    lb2, _ = mk_bridge(["--log-max-mb", "0.03"], "big.log")
    lb2.log("fresh start line")
    check("an already-oversize log is cut down at the first write, keeping its end",
          os.path.getsize(big) <= lim + 200 and "old line 3999" in open(big, encoding="utf-8").read()
          and "fresh start line" in open(big, encoding="utf-8").read())
    lb3, p3 = mk_bridge(["--no-log"], "nolog.log")
    lb3.log("hello")
    check("--no-log: no log file is created", not os.path.exists(p3) and not lb3.log_enabled)
    lb3.do_action("log_on")
    lb3.log("now on")
    check("--no-log can still be switched on later (panel or G key)", os.path.exists(p3))
    sf = os.path.join(tdir, "settings.json")
    json.dump({"log_enabled": False, "log_max_mb": 1}, open(sf, "w"))
    a4 = build_parser().parse_args(["--logfile", os.path.join(tdir, "s.log"),
                                    "--settings-file", sf, "--mac-file", ""])
    lb4 = Bridge(a4, quiet=True)
    lb4.log("x")
    check("a choice saved from the panel wins over the flags at next start",
          not lb4.log_enabled and lb4.log_max_mb == 1.0
          and not os.path.exists(os.path.join(tdir, "s.log")))
    lb5, _ = mk_bridge([], "no_such_dir/sub/x.log")
    try:
        lb5.log("will fail to open")
        survived = True
    except Exception:
        survived = False
    check("an unwritable log location never crashes the bridge (logging just turns off)",
          survived and lb5.log_enabled is False)
    for fn in os.listdir(tdir):
        try:
            os.remove(os.path.join(tdir, fn))
        except OSError:
            pass

    bridge.stop.set()
    bridge.lp.stop.set()
    amp.running = False
    ok = all(results)
    print("=== %s (%d/%d) ===" % ("ALL TESTS PASSED" if ok else "SOME TESTS FAILED",
                                  sum(results), len(results)))
    return 0 if ok else 1


# --------------------------------------------------------------------------
def acquire_lock(port):
    """Single-instance guard: hold a localhost TCP port while running.
    Returns the socket (keep it alive) or None if another copy holds it."""
    if not port:
        return socket.socket()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


def build_parser():
    p = argparse.ArgumentParser(
        description="Bridge Thetis/Zeus TCI to an Elecraft KPA1500 and LP-100A.")
    p.add_argument("--amp-ip", default=None, metavar="ADDRESS",
                   help="KPA1500 IP address, or 'auto' to find it on the network. Default: the "
                        "address last chosen in the panel, otherwise 192.168.0.175")
    p.add_argument("--discover", nargs="?", const="", default=None, metavar="NETWORK",
                   help="search the network for KPA1500 amplifiers, list them and exit "
                        "(optionally give a network such as 192.168.1.0/24)")
    p.add_argument("--discover-net", default="", metavar="NETWORK",
                   help="network(s) to search instead of this PC's own, e.g. 192.168.1.0/24 "
                        "(comma separated; /20 or smaller)")
    p.add_argument("--amp-port", type=int, default=1500, help="KPA1500 port")
    p.add_argument("--tci-host", default="127.0.0.1", help="TCI host")
    p.add_argument("--tci-port", type=int, default=50001, help="TCI port")
    p.add_argument("--tci-path", default="/", help="TCI WebSocket path (default /)")
    p.add_argument("--rx", type=int, default=0, help="receiver index (0=RX1)")
    p.add_argument("--radio", default="auto", choices=list(RADIO_KINDS),
                   help="which radio program: auto (find out by itself), thetis or nereus. A choice "
                        "made in the panel is remembered and wins over this flag")
    p.add_argument("--nereus-cat-host", default="127.0.0.1",
                   help="where NereusSDR's TCP/IP CAT port is (default this PC)")
    p.add_argument("--nereus-cat-port", type=int, default=13013,
                   help="NereusSDR TCP/IP CAT port for the knob's CAT commands (default 13013 = CAT 1; 0 = off)")
    p.add_argument("--nereus-mmio-port", type=int, default=50110,
                   help="send telemetry to a NereusSDR 'Meter Data Source' (UDP listener) on this port "
                        "(default 50110; 0 = off)")
    p.add_argument("--nereus-mmio-host", default="127.0.0.1", help="IP of that NereusSDR data source")
    p.add_argument("--nereus-mmio-format", default="json", choices=["xml", "json", "raw"],
                   help="format for NereusSDR (default json: variable names stay plain, e.g. amp_fwd)")
    p.add_argument("--nereus-mmio-term", default="none", choices=list(TERMS),
                   help="message terminator for NereusSDR (default none)")
    p.add_argument("--applet", action="store_true",
                   help="also open the Applet window when the bridge starts")
    p.add_argument("--replace", action="store_true",
                   help="if a bridge is already running, close it first and then start this one")
    p.add_argument("--stop-running", action="store_true",
                   help="close a running bridge and exit")
    p.add_argument("--amp-mac", default="",
                   help="amp MAC for remote power-on (learned automatically "
                        "once the amp has been on)")
    p.add_argument("--wol-broadcast", default="",
                   help="extra address(es) to send Wake-on-LAN to, e.g. 10.1.2.255 "
                        "(for an amp on another subnet; the router must forward it)")
    p.add_argument("--probe", metavar="IP", default=None,
                   help="check whether a KPA1500 answers at this address, then exit "
                        "(0 = yes, 1 = no)")
    p.add_argument("--wol-port", type=int, default=9,
                   help="Wake-on-LAN UDP port (default 9)")
    p.add_argument("--mac-file", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "kpa1500_mac.txt"),
        help="where the learned MAC address is remembered ('' to disable)")
    p.add_argument("--no-standby-on-tune", action="store_true",
                   help="start with Standby-on-Tune OFF")
    p.add_argument("--send-band", action="store_true",
                   help="also send ^BNbb; on band change")
    p.add_argument("--dry-run", action="store_true",
                   help="read only; buttons and tracking print instead of sending")
    p.add_argument("--poll", type=float, default=0.1,
                   help="seconds between amp polls (default 0.1)")
    p.add_argument("--no-web", action="store_true", help="disable the web panel")
    p.add_argument("--web-port", type=int, default=8080, help="web panel port")
    p.add_argument("--web-bind", default="127.0.0.1",
                   help="web panel address (0.0.0.0 = whole LAN)")
    p.add_argument("--web-token", default="",
                   help="password required by the web panel (use with 0.0.0.0)")
    p.add_argument("--settings-file", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "kpa1500_settings.json"),
        help="remembers choices made in the panel, e.g. LP-100A port ('' = off)")
    p.add_argument("--lp100-port", default="",
                   help="LP-100A serial port, e.g. COM5 (needs pyserial)")
    p.add_argument("--lp100-baud", type=int, default=115200,
                   help="LP-100A baud (115200; 38400 for firmware < 1.2.0.0)")
    p.add_argument("--lp100-debug", action="store_true",
                   help="log raw LP-100A frames (use for first-time check)")
    p.add_argument("--mmio-port", type=int, default=0,
                   help="send telemetry to a Thetis Multi Meter I/O UDP 'In' entry "
                        "on this port (0 = off)")
    p.add_argument("--mmio-host", default="127.0.0.1",
                   help="IP of the Thetis MMIO UDP 'In' entry (default 127.0.0.1)")
    p.add_argument("--mmio-format", default="xml", choices=["xml", "json", "raw"],
                   help="data format; must match Thetis 'Format (in)' (default xml)")
    p.add_argument("--mmio-term", default="none", choices=list(TERMS),
                   help="message terminator; must match Thetis 'Terminator (in)'")
    p.add_argument("--mmio-root", default="kpa", help="XML root element name")
    p.add_argument("--mmio-rate", type=float, default=10.0,
                   help="telemetry updates per second (default 10)")
    p.add_argument("--mmio-listen", type=int, default=0,
                   help="listen on this UDP port for button strings sent by a "
                        "Thetis MMIO 'Out' entry (0 = off)")
    p.add_argument("--mmio-listen-bind", default="127.0.0.1",
                   help="address for the button listener (default 127.0.0.1)")
    p.add_argument("--mmio-test", action="store_true",
                   help="send test variables to Thetis (no amp/radio needed)")
    p.add_argument("--lock-port", type=int, default=50199,
                   help="localhost port used to stop two copies running (0 = off)")
    p.add_argument("--check-running", action="store_true",
                   help="exit code 3 if a bridge is already running, else 0")
    p.add_argument("--write-help", nargs="?", const="", default=None, metavar="FILE",
                   help="write the help to an HTML file (next to the program if no "
                        "name is given) and exit")
    p.add_argument("--print-help", action="store_true",
                   help="print the full help as plain text and exit")
    p.add_argument("--no-keys", action="store_true",
                   help="turn off the keyboard commands in the bridge window")
    p.add_argument("--version", action="version",
                   version="KPA1500 bridge %s (%s)" % (VERSION, BUILD_DATE))
    p.add_argument("--verbose", action="store_true", help="show every message")
    p.add_argument("--logfile", default="kpa1500_bridge.log",
                   help="log file name ('' for none)")
    p.add_argument("--no-log", action="store_true",
                   help="do not write a log file (can be turned on again in the panel)")
    p.add_argument("--log-max-mb", type=float, default=2.0,
                   help="trim the log file when it passes this size, keeping the "
                        "newest part (default 2; 0 = never trim)")
    p.add_argument("--selftest", action="store_true",
                   help="run built-in tests with simulated hardware")
    if flexemu:
        flexemu.add_arguments(p)
    return p


def main():
    args = build_parser().parse_args()
    if getattr(args, "flex_selftest", False) and flexemu:
        sys.exit(flexemu.selftest())
    if args.selftest:
        rc = selftest()
        if flexemu:
            rc = rc or flexemu.selftest()
        sys.exit(rc)
    if args.discover is not None:
        saved = load_settings(args.settings_file).get("amp_ip") if args.settings_file else None
        hint, _src = resolve_amp_ip(args.amp_ip, saved)
        try:
            nets = discovery_networks(args.discover or args.discover_net, hint)
        except ValueError as e:
            sys.exit("Cannot search: %s" % e)
        n_addr = sum(max(0, n.num_addresses - 2) for n in nets)
        print("Searching %d addresses on %s for a KPA1500 (about 5 seconds)..." % (
            n_addr, ", ".join(str(n) for n in nets)))
        found = discover_amps(nets, args.amp_port)
        if not found:
            print("No KPA1500 answered. Check that it is switched on and on this network, "
                  "or give the network with --discover 192.168.x.0/24.")
            sys.exit(1)
        for f in found:
            print("  Found: %s%s" % (describe_amp(f), ("  MAC " + f["mac"]) if f["mac"] else ""))
        print("Use it with:  --amp-ip %s   (or start the bridge with --amp-ip auto)" % found[0]["ip"])
        sys.exit(0)
    if args.probe:
        r = _probe(args.probe, args.amp_port, "^I;", "^KPA1500;", 1.5)
        if r is None:
            r = _probe(args.probe, args.amp_port, "^I;", "^kpa1500;", 0.3)
        if r is None:
            r = _probe(args.probe, args.amp_port, "^SN;", "^SN", 1.0)
        if r is None:
            print("No KPA1500 answered at %s:%d" % (args.probe, args.amp_port))
            sys.exit(1)
        print("KPA1500 answered at %s:%d" % (args.probe, args.amp_port))
        sys.exit(0)
    if args.write_help is not None:
        path = write_help_file(args.write_help or None)
        print("Help written to: %s" % path)
        sys.exit(0)
    if args.print_help:
        text = render_help_text()
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode("ascii", "replace").decode("ascii"))
        sys.exit(0)
    if args.check_running:
        lock = acquire_lock(args.lock_port)
        if lock is None:
            print("The bridge is already running.")
            sys.exit(3)
        lock.close()
        sys.exit(0)
    if args.mmio_test:
        if not args.mmio_port:
            sys.exit("--mmio-test needs --mmio-port (the port of your Thetis UDP 'In' entry)")
        return mmio_test(args)
    if args.stop_running:
        if stop_running_bridge(args.lock_port, args.web_port):
            print("No bridge is running now.")
            sys.exit(0)
        print("Could not close the running bridge. Close its window yourself.")
        sys.exit(1)
    lock = acquire_lock(args.lock_port)
    if lock is None and args.replace:
        if stop_running_bridge(args.lock_port, args.web_port):
            lock = acquire_lock(args.lock_port)
    if lock is None:
        print("The KPA1500 bridge is already running (lock port %d is in use).\n"
              "Close the other copy first, or start with --replace to close it for you "
              "(or --lock-port 0 to allow two)." % args.lock_port)
        sys.exit(3)
    Bridge(args).run()


# --------------------------------------------------------------------------
# Pictures used in the help (JPEG, base64). Screenshots of the Thetis windows.
# --------------------------------------------------------------------------
HELP_IMAGES = {
    'thetis_overview': (
        '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'
        'I3nFXaQEPHM5elf6kv6xORd3EzVJzAXvRSndu6kFmojxB8ubJCLtYHkF2uovwspFNOKmETNaQx3iE9Y4rHN/SFyMa0sbV1rWkBpa'
        'KWWxA+pOx/pM5IQgiOqqgCb25lLYebRBaNihZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5'
        'BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5'
        'KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/n'
        'dV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tH'
        'kn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9y'
        'P1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53Vfy'
        'UvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O'
        '6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aP'
        'JP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI'
        '/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaN'
        'chZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3'
        'ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/'
        'JS+5BaNchZH9aPJP53VfyUvuR+tHkn87qv5KX3ILRrkLI/rR5J/O6r+Sl9yP1o8k/ndV/JS+5BaNcTYXXDJmvdYMkb3ujIHtWU/W'
        'jyT+d1X8lL7kfrR5J/O6r+Sl9yC0a5CyP60eSfzuq/kpfcj9aPJP53VfyUvuQWjRVdTUx7QwtZlhtmzak34KWw5mNda1wDbgse79'
        'JXI5787p6gu4mhl9y7/WjyT+d1X8lL7kFo1y4mc5kTnNLQWi/S3LKfrR5J/O6r+Sl9yR36T+SThZ1VUkcDRS+5BaNTTTmoa5+XIL'
        '2DT4w86eWQH6T+SWYuFVU5jvPMpdfYuv1n8lNL1lQLm1zRyD8kFnkGCuIwmn16j+K1dPh9NVUkDnSim+LcTbpSSEW3a2I17rWWTw'
        'b91QeY/in5Xr1L1UeR7s0zsJppai1PVObHoOkWk6htuvrJPoVbiUUdDVbFkrn9G5zWBabkWNiR1X+tUzZnMe17HFrmm4I3gpDK5x'
        'JJuSbk8VaZNC3w+SGTEadk+sTpGh4LrAi+uvUrePD8Nmj2basNeZC8PBzHIW3awDishnRnRhM1Bw+iy2GIO2lvlNAbfLm43t1edK'
        '/C6Zr9mK1+0e5rI2kN1cc1ibHcco9Ky2ddxVEkL88Tyx1iLt70pi0WM8jI53xskL2tcQHcVLwjY1E8zZWh5bC5zGnW7tLaXF/SqD'
        'OUZ1eg6mqGDxvgjkZVHNJuBy2d4t7G/UHHfwTseF0ccYMlWx7pAbXIs2zhrodbglZLbv2WyznIHZsvVfiuc6lMto1jcIpi0l9bJG'
        'QWAtLWnxtSdDu71TSzMbK9rHOLQ4gE7yFWZ0ZyqiF7hfN6idzaggRhvjOfls6+g+s6fWp0fg9k1MXRQuFRcuY55tFYWI0Pa9iymc'
        '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'
        'PDsQlkbHFi9DI95s1jMVjJcTuAGbUqLnnNFVxzySOLHsBa55Njc3VBgGGVEGP4XM9rLCrhzNDwXMu4WuOpaKo/8Amf8Azx/rcuuH'
        'iKexyxcKWG0mqK5CELsecEIQgBCEIAQhCAEIQgJWGEjEIiDYjNYjq6JVGzlBWR1crJ6qYsabNs86K8w7+vx+Z3+krHVUUpqpSI3k'
        'F5+SVyxGzrhpPc3EVHjcvOLOextMAZHvqcrbZc9wb6jLromY24pNTc4imdIwtkcwNqelK1njOaL3ICrIuWeMxUVJTMga3mtNJA14'
        'a4OdnFsxPEAABNU3KfEIKOKJ1G2aeCOWKKpeHF7WyeN3HebE8VybZ2qJZzz4jT4fDWyyyNjnjEkbOcfGOZqM2W97aFRvC1bYENry'
        'CbA2fqeCTA+VlRhEdNTHD3Op43tdKAXOLwL3ADrhua9jbep0H6Scdp2TxcyZJHOZAQ/PcB7r6WOhA0BCXIUhvB8UFZizaSonqm9p'
        'pe5pT1ZPNFWzRx1E4Y15DfjXbvSs9R4nJHyg8JTU0gDnatu5xA87rk/WrmombUVEkzfFkcXD610w229TniJJaHXO6n5zN9o73qwo'
        'KgyUk7ZXuLw5gbI6Z4LcxsTYOAKqVcYNSUlVBIKiNvjgGVx0aLbt4IPfYhdWcUTWYJL0GTYzJFK8nRz9AAevpb9dFSYzUT4VNM1t'
        'ZPM2K2udzTr3XV27kvREPdHWvc1oLi1rWnKL21N+rrWTxiIspJ4mAutYDv17lk3WpZUVbS1rwxmNTB5bmykuv5t6Vhr5G5o5Kt7b'
        'huZpcRc7hvWYwyqkpqiLa09mMuMzYrON+J61qqTF46GMxSwySgkOaAG2bcWLgbXBt32XLO6OmSNnDxiMTXPfz5rWktcSHaEC560w'
        '+umjdlfVVDXWvYlwNvSrE8o4GxkR0shcIti0SAFuWxsSOs66qFiWKxV1EyJsDo5Q8OccjQ3RoFhYXA0OinMkXlobZWzSGzaue9r+'
        'O4fmm6TGIp87Z8RngexxGW7nacd6YpQdqbgjonqVXS4hiGF1dU6kBG2DmPvEHXaT3hXM6JlVmua9zKmaJlbJURGnebucbHo8CVVq'
        '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'
        'CG3tiDtRY/8Ahkv+9J8F8HP/AMwd/lkv+9aam/2nnisKLTWIvg/oUuEuoTV0b9kQGTRtcS2+pcLX9C2fKj9njH/rx/8Akcq2n5NY'
        'YyWIsxSRjWSskIbhsgJym/W5T+UUm3osTqGse1k1Y17czbaF5IWsODipWTi8aOI4KNadlRRYP+6YPMfxTsu9NYP+6YPMfxTsu9eu'
        'OyPmS3ZH60IQqQEIQgBCEIAUGqxWOknMTonOIANwQpyz2M/vB30R+CxNtLQ3BJvUm+HofIyekI8PQ+Rk9IVGhceZI7cuJeeHofIy'
        'ekI8PQ+Rk9IVGhOZIcuJeeHofIyekI8PQ+Rk9IVGhOZIcuJeeHofIv8ASEvh2HyL/SExydmggxAvqpYWQZSJBK2+YcBodevqvxVl'
        'hlXhNNhkcchp3zMmLyH3+MNxlB0PRte/BcMTipwdKN7FWFEh+HYfIv8ASEeHofISekKbiVXhL8Iq44ZoXzPeHeLc5ujcA2F2+NY6'
        'eZZY71vC4ieIraoPCijQM5TmNuVhqGtG4NksF18Kn9uq+1PvWdQuueQ5cTRfCl/bqvtT70fCl/bqvtT71nUJnkTlxNF8KX9uq+1P'
        'vR8KX9uq+1PvWdQrnY5cTRfCl/bqvtT70fCl/bqvtT71nUK5mOXE0Xwpf26r7U+9L8KZO3Vfan3rOrSipw0VuGSzy00pijc2bK2z'
        'STfIT0RuNr6ad65YmNKGyvcqw4nHwok7dV9qfej4Uyduq+1PvVi6uwDI0MkiuJL5i295NdSLeINNe7cszi8lPLikz6YtMZIsWiwJ'
        'sLkDhe6xg8TLEdOLXvDwootfhS/t1X2p96T4Uv7dV9qfes8henMycuJovhS/t1X2p96PhS/t1X2p96zqFbY5cTRfCl/bqvtT71y/'
        'lJtRleah44Okus+hLZMkS88Ow+Rf6Qjw7D5F/pCo0qtscuJd+HYfIyekI8Ow+Rf6QqRWuATU8NXI6qkhbCYyHiRty4WO7Q692nnW'
        'cSbjFySsLDiPeHIfIv8ASEeHIfJP9IU/CqrBIMOhiqzGXxyOLtLlzr9G+ni23+ZM4rUUJoKrYVNPOZpGlrA0B0drXINgTc6DuXnX'
        'Eyc8uR+/8+JrlRojeHIfIv8ASEeHIfIv9IVIUL2GeXEu/DkPkZPSEeHIPJSekKkQg5cS8bj0THBzY5WkbiDYhO/Ch/lKr7U+9Z5K'
        'gyI0Hwof26r7U+9Hwof26n7U+9Z9CoyRND8KH+UqvtT70fCh/lKn7U+9Z5CDIjQ/Cd/lKn7U+9Hwnf5Sp+1PvSsqMOvhT6mWCQwk'
        '7YMbvbplvoN3DVTKqr5PyUr2OkGrw6UxNu5zrjRug6Nr63BXifEyTSyP8ZrlRIXwnf5Sq+1PvR8KH+UqvtT71X4/NRz4zUS0Bbzd'
        '+UsDWZAOiLi3nVcvVhtyipVVmXhxND8KH+UqvtT70fCd/lKr7U+9Z5C3QyI0Pwof5Sq+1PvR8KH+UqvtT71nkIMiND8KH+UqvtT7'
        '0fCh/lKn7U+9Z5CUMkTQfCh/bqftT70fCh/bqftT71nkqDJEv3cpnPBa51S5p3gyEg+1N+HIfJP9IUfk/NDBibX1MkTIQPjBKL5m'
        '9YGh1VphNTglPRbOrcx1psztOk8XGUbt2++ui8uLjyw20ot7bFWHFkPw5D5F/pCTw5D5F/pCn4lWYPJhlVHDJHzhxBcWjxnaWDdN'
        'W+Nrossd+i3g4rxU24te8PDii68OQ+Rf6Qjw5D5F/pCpELsTlxLvw5D5GT0hHh2HyMnpCpEJqOXEu/DsPkZPSEeHYfIv9IVIhS2O'
        'XEu/DsPkZPSEeHYfIyekKkSKWxy4mi+FD+3Vfan3o+FD+3Vfan3rPDvWkbU4btsKkqJaeQwhwmytsCD4t9Bu6xru61xxcWUKpX/o'
        'qw4nHwof26n7U+9Hwpf26r7U+9WZr8As20sIIlzPJZmzP0/u+LvF/YVmcbkp5sVnkpiwxuIsWCwvYXt9d+F1yweJliSpxaK8KKLL'
        '4Uv7dV9qfej4Uv7dV9qfes8henMycuJofhS/t1X2p96PhS/t1X2p96zyEzMcuJofhS/t1X2p96PhTJ26r7U+9Z5ImZjlxNF8KX9u'
        'q+1PvR8KX9uq+1PvWdQpmY5cTRfCl/bqvtT70fCmTt1X2p96zqtuT81PBiGepkhZDltIJBfM3rA0OvovxXOeLKMXLcqw4k34Uydu'
        'q+1PvR8KX9uq+1PvRR1OGw4KIDPHHUCW5ky3cbubY2tawbm8y7rcTw6rw2sPxLZHvcGMEdnE5m5HDTdlDr95XDzqeasul19y8qI3'
        '8KX9uq+1PvTb+UbZTeRkzyNxc+/4qhO9C9OeRnlxNF8Kn9uq+1PvR8Kn9uq+1KzqFM8hy4mi+FT+3VfalHwqf26r7UrOoTmSHLia'
        'L4VP7dV9qUfCp/bqvtSs6hOZIcuJovhU/t1X2pR8KX9uq+1PvWdSgpzJDlxND8KZO3Vfan3pfhTJ26n7Y+9EdRhuzwg1UsEhglvM'
        'GN3x9GwOg1GumvWbp6oxCkMkkMFXTtM8kTS90YcyKwu9w6NyLgBebzud1l/Lrt/JrlRLHDK+eqhkl201jTyOAMhNjbzp2mnc6Kpm'
        'qKiqc2FgIbHMQSS4N678U3TSRyyVD4nBzDTPAcLdKzbX0AGtktJHJLR1zYo3yP2bCGsFzpI3cvapNwzHCvSocnrW0pAqIcViLhcZ'
        '6kC/sTbcVpnuDWeEnOcbACqBJPoVxTVcb3gVGF1bC3pOmdThzpDwsBbXdfTiuKfEjHUPml5P1Ljc5A2EABt7tG7q4rlnkdskSqOK'
        '07SQRiQINiOdD3K55K0tNymxkYdznEaf4p8mfnAd4ttLW71mpcPr5JXv5hUjM4utsj1laz9GFHU03K8ST08sTOayjM9haL6dZTNI'
        'ZIms/VlT7/DeJefMF56S5mxjviNTNK6SzYZ7aNcW7iCvbYaGlp6+orWSO2tSGh4dMS0W4NJsO+y8UO2jlpp2U1RNGOcNcIYw4G8p'
        '0IIsQtKToy4qxnnJ+bYvoQP6x1kE9ngD6EVFTzTLzmnxWLP4uepAv7FI8IVoonU7MHqm3je1pyk2JPQO75LSR9aiYo+vxIWGFzxW'
        'lc8ZYSLggb7DU6b1nPI1kiN+Fqb/APqX80PctjyR5MU3KnC5K7wjiNNkmMWTah17AG9/rWA8GYh8xqPsne5es/oup3RclKqCqjdE'
        'X1T7tfdhILGj/spmkMkSDyg5GR4FgstfDitdK+JzQGSO0NzbqWPxKR8mAVG0e59pYbZnE21XpfKykp8P5CTUdO97mRujAMkpkcen'
        'fUnUrzKv/cFT/wA2H8SuibcHZzaSmqKrCTbBoiOph/Epjk3i76yrpsMmijkmqZmxMlkGgubap/Cv3LF9B35rPYdBicFRDW0VNM58'
        'Tw9j2xlwuNySdUWCts9IrcGnwyiNZX09JTwsbI6QlpcWBjwwaDfmJBHck8D1OSWRtJSOjhkexzm66NiEodu3EEAd51WSfjnK+WLY'
        '1EdRUxlrmuZPT5w4Oy6G418RtuFkrce5YNkmkDKkGcSCQc30Ie1rCLW3ZWtAHVbRcrdHWl2JVXi9LWcmJ5KejbBMLESAajVRMM5R'
        'UzzBT1NNGHuIa6UsuPPYKvbHiNPg88E2HzxwkftXRkAG6hRYbiQLJY6KoNiC0iMkJZKR6KaIGufSRx0j3R1wonOyEASFrnX83RKY'
        'xOGTCsJ8Jz0VO6Ashc0tHjbQOIHnGXUd4WcixflVDU1NQ2nlMlTNt3uNMDaSxGZunRNnEacU1U13Kiswx+Gzw1L6Vzo3GPYbixuV'
        'pGmmm/ilui0uxd1dbS1lDTPp6RkB3uLRYnRZLF5Htr3hriBlCuaPnzKVkVXRS04b4jnsLQ70qnxYMOIPzPt0R1dy6P1DmvXIG2l7'
        'RRtpO2VfYV4KihDKgQVLZKiNgL2ZXtG9xvfduH1lQsdioY8Sc2klYW5G59m3o57dK2p0uvJHFueSjtWhXmaSw6ZSbaTtlKWx6fGf'
        'dSZY/KfdXYgomk7ZSbaTtlAbH5T7qMsflPuoA20nbKdlmkDYrO+R+ZTWWPyn3U7M2PLF8YfE7PeUA1tpO2Uu2k7ZSZY/KfdS5Y/K'
        'fdVAm2k7ZRtpO2UZY/KfdRlj8p91UCmaTtlG2k7ZQWx6fGfdRlj8p91WiAJpO2UbaTtlAbH5T7qMsflPuqgNtJ2yl20nbKTLH5T7'
        'qXLH5T7qoE20nbKdhleRJd1+gfyTWWPyn3U7C2O0vxn9mfk+ZUDe2k7ZSbaTtlLlj8p91GWPyn3UAGaTtlJtpO0UpbH5T7qMsflP'
        'uq0AE0nbKVs0mYdI70gbH5Q+qlayPMPjOvsrVENU1rco6DN3ZCXK3sM9ULtrWZR8Z1dlLlZ5T7qgG8rew31QgNb2GeqE5lZ5T7qM'
        'rPKfdVA3lb2GeqEZW9hnqhd5WeU+6lys8p91AJI1oDLMZ4g+SFxZvYZ6oT8jWWZ0/kD5K4ys7fsVA2Gt7DPVCMrewz1QnA1nb+6j'
        'LH5T7qUDjK3sM9UIyN7DPVC7ys8p91LlZp8Z91WgN5W9hvqhAa3sM9ULvKzyn3UuVnlPuq0BvK3sM9UIyt7DfVC7ys8p91LlZ5T7'
        'qAbyt7DPVCMrew31QnC1mnxn3UZWeU+6rQKTE3FtbZtgNiToB3qr20nbKtsVazn37T+xPyfOqnJH5T7q0kBNtJ2ylM0nbKMkflPu'
        'oLI/KH1VaIJtpO2Uu2kv45Rkj8p91AbH5T7qUBNtJ2yjbSdspckflPuoyR+U+6lATbSdso20nbKXJH5Q+qkyx+U+6pQFE0l/HKTb'
        'SdopQ2O/7T7qTLH5T7qUA20nbKcklkEcXSOrfzKbyx+U+6nZWx7OL4w+L2e8qUUa20nbKBNJ2yjLH5T7qUNj8p91KIJtpO2UrZJn'
        'GzS4+YJMsflPuq45L4W3GMZhw4VBi5w4Mzhvi6+dYnJQi5PoVFV/SeD/AFUf0ng/1Vun8hmw4m/DZ66UVMNI+qlYyMusB4rQb6kh'
        'OUn6PpKvFKujbXkMghje2TKbue8XbGRfQ8V4/PcPc1lZgRzng/1Uf0ng/wBVaKHAxJgNfiRqHtloZWROgIOuYkb79ys6fkazEJKX'
        'wdiBqYZntjkqB4sTi3MWkXvca+ey1LioLcZTFf0ng/1UHnHB/qrbDkYzm/PfCEnMjTidr8pz6yZLWvbf37lEZyVldypqcDfVBvNd'
        'o6SbW2RgzEgcbdSyuKg79gysyf8ASeD/AFU5Dzjp3a/xDborSUfJ3wo0y4dVfEBzIi+pJZ8Y82azQnfxTzuReJx0ZqJHxMIjfKYj'
        'Kc4ax2V3oKr4iCdMUZH+k8H+qj+k8H+qtpX8i5KWpr2R4lTvhoRHtJZXOZq8XAtrqncP5CVUuJQ09bMGRGTZTmF5c+F5YXgEHuWf'
        'OsOrsZWYb+k8H+qUf0ng/wBUrSYjycrMMw+CuncNlUAGPK5xuDe2u6+mouqrKOLvWK2sVS1Qogf0ng/1Sk/pPB/qlWGUcXesUZRx'
        'd6xWsxKK/wDpPB/qlKec8H+qp+Xvd6xRlHF3rFMwK/8ApPB/qoHOeD/VVhlHF3rFGUcXesVMxSv/AKTwf6qP6Twf6qsMve71ijKO'
        'LvWKlghy84yx2a/xNej3lN/0ng/1SrDL3u9Yoy97vWKWCv8A6Twf6pSf0ng/1SrHL3u9Yoy97vWKArv6Twf6pS/0ng/1SrDL3u9Y'
        'oy97vWKgK1zp2jpZh5wuRNJ2yp9WBzUXcQNp3nqKghsflPuoBNtJ2yjbSdsoyx+U+6jLH5T7qAXbSW8cpNtJ2ylyx2/afdSZY/Kf'
        'dQDsEshebu+S78E1tpO2U7Ttj2h+MPiu+T3JrLH5T7qA1eCTsjo2OmDnNkhcw5SAddL6qaH0LTdvPGnuc0fkqvDrDD4bG4y/mpK9'
        'S2PJLcm7ek7dd9o1G3pO3XfaNUJCtEsm7ek7dd9o1JtqPt132jVDQlCyZtqPtVvrtQJaJos11aB3PaFDQlCybt6Tt132jUbek7dd'
        '9o1QkJQsm7ek7dd9o1G2o7+PW/aNUJKN6ULLKGSjcbXrD53tKcxaWAYLLFC2W75IyS8jqPd51Bg8ZPYn+7XfSZ+IUktGWL1RBwr9'
        'yxfQd+apMExOrp6mCljmIilmaHDzkAq7wr9yxfQd+apcOwF+IU+2jrYI7Gxa8kEH0LlLZHaG7PTq/DMPpqeeWir5K2Rkk7o4GS6v'
        'DWZmR/SGpPXoodVRsjwqeqG3ZVMpWzQ0hnGaR5jDntHX8WTc9ZBt1LEjkpUgi2J0oIN9HO9yDyVqibnE6a/HM73LkdSTJi9ZXck6'
        'hk8mYG34hSOS1VO/Ba+eqimfTUcZyTMebh9jkYGga3OpO4AFQpuTdbQYNPUOxCnkpyADG0m9yd+5VbcLqQ3oVDA08HELMpxjuzvg'
        '8Pi418uN0buWZp2zqaGSaWLDYKplMyZxdK6Qtzd9mgnQcVPfh1Ls64x4i/a0pqnCN0g6TY42kAHi17rHiPMvNRhVU11xUMBA3hxu'
        'jwTU+Xj9YrPNh3Oy8n8V/gzTSYjU1+G0pqHZiBcehZbGP3i76IVph8NTA0xzSh7LXaAb2Vbi0j24g8B1hlC7pp4aaPDPDnhYzjNU'
        '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'
        'aTtlJlj8p91KGx+UPqqgTbSdspdtJ2ykyx+U+6lyx+U+6qAM0nbKNtJ2ygtj8p91GSPyn3VqgAnl7ZRtpO2UoZH5T7qMsflfurSR'
        'BNtJ2yl20nbKMsflPuoyx+V+6tANtJ2ynYZpLS9M/sz+SayR+V+6nYWx2k+M+Qfk+ZKA1tpO2UbaTtlLlj8p91GWPyn3VpIBtpO2'
        'UbaTtlGSPyn3UZY/KfdWqIAmk7ZStmkzDpnegNj8r91DWx5h8Z19laoGtbK/KOkdyXav7RSNazKPjOrspcrPKfdWKAbR/aKBI/tF'
        'GVnlPupQ1nb+6rQE2j+0Uolk7RSZWdv7qUNZ2/uq0DuSR9mdI+IFxtX9oruRrLM6fyB8lcZWdv7qUAEj+0UbR/bKUNZ2/uoys7f3'
        'VaAm0f2yl2j9OkUZWdv7qUtZYdP7qtEsTav7RQJZO0UZWdv7qUNZ2/upQsTaSdoo2j+0UuVnb+6jKzt/dVolibR/aKNo/tFdZWdv'
        '7qTKzt/dSkLKbFZZOfeMf2J/NVO1k7ZVvijY+fftP7E/J86qckflPurrFKiCbWTtlG1k7ZXWRnlPuoLI/KfdWqQs52snbKUSydsp'
        'ckflPuoDI7/tPuqUgc7WTtFG1k7RS5Y/KfdS5Y/KfdSkDkyyWHTKNrJ2yuskenxn3UmSPyn3UpAQTS9so20vbKUMjv8AtPuoyR+U'
        '+6lFOdtJ2ynZZpNnD0z4v5lN5I/KH1U7KyPZxfGfJ7PepQGdrJ2ygTSX8cpckflD6qMkflD6qlA520naKu+SFWyDlLQTVMoZEyoj'
        'LnuNg0Zt6pckflD6qt+TFNT1OO0sEwEsb5mBzHN0IvexXLF9RlR6yaKpLiRHcX3hzSD7UcxqfJH1h715K/lryiD3BuJOaATZrY2A'
        'DzaLn4bcpP4pJ6jPcs/qE+yOHmse565zGq8kfWHvRzGp8j94e9eR/DXlJ/FJPUb7kfDXlJ/FJPUZ7lf1CfZDzWPc9c5jU+SPrD3o'
        '5jU+SPrD3ryP4bcpP4pJ6jPclHLXlHf96Seo33J+oT7Ieax7nr7p4ZGHDGTROrImMe+ESNzAXd3+xN8xqfJH1h71hqrEamn5E03K'
        'GExsxSplEElSIm5i0F/da+guVnPhtyj/AIrJ6jPcsQ46cb09pqXDxfU9c5jU+SPrD3o5jU+S+8PevI/hryk/iknqN9yX4a8pP4pJ'
        '6jPct/qE+yM+ax7nrfMaryR9Ye9HMaryR9Ye9eR/DXlJ/FJPUZ7kfDXlJ/FJPUb7k/UJ9kPNY9z1+Cnlp6mOaYNjjjcHPe57QGgH'
        'Uk3XAc3FIYKuheyeF8TQHseN40I36FeXYVytxutxajpauuM8E07I5I5I2FrmkgEHTgVN5T4ziHJzFzheD1HM6SGKPLHGxu8tuSSR'
        'cm5WHx086lRrzeOWrPROY1Pkj6w96OY1Pkj6w968j+GvKT+KSeoz3I+GvKT+KSeo33Lf6hPsjPmse565zGp8kfWHvRzGp8ifWHvX'
        'kfw15SfxST1Ge5Hw15SfxST1G+5P1CfZDzWPc9c5jU+SPrD3pyKeHDMrK2aKB1TKI4g+RozOs7v82vevH/hryk/iknqN9y0fJXEa'
        'jH4MRlxYx1j8PiFRTuliaSx4DuA1Gg0PBc8TjZzjlo1Hh4xd2bgUNTb9l95vvS8xqfJH1h715J8NeUnVikn1MZ7knw25SfxST1Ge'
        '5dP1CfZGfNY9z1zmFT5H7w96OY1Xkj6w968j+G3KT+KSeoz3I+GvKT+KSeoz3J+oT7Ieax7nrnManyJ9Ye9HManyX3h715H8NeUn'
        '8Uk9RvuSjltyj68Uk9RnuT9Qn2Q81j3Lj9JFQw4yxkMrXOhghjkykHK4BxIuOvVY0TSdsrQcpcs0VFVPyslqqWKWUsYAHvIcCbDr'
        'NgqANj8r91eFvM22elKlQm2k7ZSbaXtlLlj8p91GWPyn3Vlmg20lvHKTby9spckflPupMsflPuqAdp5pNoemfEd+Ca20nbKdp2x7'
        'Q/GfJd8nuTeWPyv3UBoKOVzMOp331/8A2rmnxqNtRFSSENfI27XHcqOCwwuCxuNNfSoWNkiohINvi/zXZtpaHnSTlqb3bN+cQ+lG'
        '2b84h9KxPJbFY8M5SUVXVykU0cnxt25+j16LX0XKrk9Hh1G3nslPPHTOiDdiXMjlIdeQ6b7kWIvv3aLHMkdOXElwfHyiNlRDc96j'
        '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'
        'i7Nh3PPqp2FsdpPjD4h+T5lMhpzBh9QH2zyR3PFoFioMDSWSkA2DDc8NQpCanddDc8NwSvqcZI/KH1UuSPyn3U6aKZtOJrAgi+Xr'
        'A4pmNhfI1g3uNl0jKLVpmXFrRoXJH5Q+qjJH5Q+quqmndT1D4ib5Da4603ZbjqrRlpp0zsMj8ofVQ1keYfGHf2VyFLoqQVEcx1zN'
        'y5OBN93oCSkoK2WMXN0jStazKOn1dlKWs7Z9VcAaDzJ2OB8ti21twJNlhtRVtkjFydI5ys7f3Uoay/j/AHUuxfs3PtYNNinJIBHE'
        'Ha367qcyCaVmuXKmxrKzt/dS5Gdv7qWSExvDd5tfRcgE7gStqSkrTMSTTpjkjWWZ0/kD5K4ys7f3U/NTua25PiMb9aZfE6MNLhbM'
        'LhYjiQlsyyw5x3QBrO391GVvb+6kARZdaOYuVnbPqpcrLDp/dXQgdYng0OXOR1gcpsRosqcXszThJboMrO391KGs7Z9VLDHtJWsv'
        'vK5IsSOCtrNl6kyvLm6C5Gdv7qMje391IhaM2dZWWHT+6kys7f3UltEK0CoxRrOfayf2J+T51VZY/KH1Va4mCa7QXtCfzUCejkgZ'
        'E89JsjA4EDd3LopRVJvcKLabXQZyx+UPqpSyPyh9VIASbAXJ0Fkrmlri1wsRoQepdK1MiZI/KH1UoZHf9ofVSWI6k6KZ3NOckjLn'
        'yW77XUbS3Kk3sNZI/KH1UZI/KH1UiLK0Q6LI9PjD6qTIzyh9VLJC+ItEjcpLQRfgVzZRU1aK7WjFDI/KH1UmSPyn3UAaoLCACRod'
        'x4pRBckflPuruVkezi+MPi9nvTZa5oFwRcXF+tdyC8cX0fzUoo3s4/KfdRkZ5Q+qksgBKFhkj8ofVVlgFI2sxempxUSR7SZgzs0c'
        '3pXuDx0VZayuuSP/AJkov+ez8Vxx/wDts1Hcsn/pIcHuHgSldqdXvJce8nrKT9ZLv4FResVin/tHecrQ0nJGSpxOtoudAGk2d3tj'
        'Lgc5ABOugF9SvjnctP1ku/gVF6xR+sl38CovWKpMK5MzYtT1MsVXCw087Ii1x0cDe7geAAupFXyQdSVT6M10b6ktkkiYIzlkYwm5'
        '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'
        'aWHHv8tPEJwJh5NV7GB7qgNaXHUh2jRe7j3aKrrIJqKrfTvlzFluk0mxBFwfQVNdygxP5UzL33bMeL2fo9ygVM8tXUPnmcHPedSB'
        'YLngcHxqn/1kq9hXk6De0k7bvSl2snbd6UhaAbXPoQAd9l7PNsT/ABOeh0JJO270pdpJ23elcAgpbgb9FVw8t6JQ7zify0nrFLzi'
        'fy0nrFNZtbWKW/UtLhpv9pKHecT+Wk9YpecT+Wk9Ypm+/uShzMl82vCy15tNftJQ7zify0nrFS8PgqMQmdCyrLHhpc0OLjmsL203'
        'KuDwTaxUqhr5aKUyQhodbRz2B1u8cCueJw2NKD5a16BJXqiyosHxGupIqiOocBK4hoLjoBvPcuKjD6mnhqJOelxpnND29IGx3b/w'
        'TNPjlXBDs4ZWsbqbbMa3Ny3zHrCKnF6utp9jK2NzS7MMrACLab/MLLzx4Tj3iXSy34X7u31NPJWxFFRP5aT1il5xN5aT1imc/wDd'
        'KQTDWzTove+HktHE55fYP84n8s/1ilE8/lpPWKYbLmtZp1SmQMNnNIKqwJVeUmX2D+3m8s/1ijnE/ln+sVH2wvbKV0JRbcquHk9o'
        'ky+we283lpPWKNvN5Z/rFMiUG9huS7QHcL/Wr5tL/EmX2D23m8s/1ijbz+Wk9Ypgy2GrT6V0x5kfkZG5zuAU5DXQZS1GGVUr6IR1'
        'O055cNNyMpG+907PgFdDA6USF4z5WNAN3bhfuGqhOxmrhdEwtZGYDmZZjd/We8rs8pa9zS3a7PqaWNALRp0WnqGg0XgfDcfmWWq9'
        'vvfs7UdFGFbDeIUs+HVslJJLmfGQC5p0OgP5qPnf23eldVWIzV9Q+oqCZJTbMdNbCyaMhDQ4sNju1XuwuHxVBcxelWtd+pzcddEd'
        '539t3pSbR/bd6U2Z7fIKBO0/JN+C3yJf4jK+w7nf23elGd/bd6Uyaho+QUrZg91gw386zyndUMj7Dmd/bd6UZ39t3pTRnb2SPOjb'
        'A7mlXkP/ABGV9hzO/tu9KM7+270prbi5GU6JWyZ3Wa0k9yysFy2Rcr7E3D6WTEKptM2o2b3eLmubnhopVFgtbX0rZopfGk2bWkk9'
        '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'
        'SpmQsrcUx3lJjNLzbEHSTxCTaNaYQMrtbkWGm9Qaw11ZHA19JIDECNGnXd7lofhN/gO9KByl/wAF3pS4jN7TORCviaxopXODDcB0'
        'ZPf+aYko6t73O5rILm9g0rV/CYeRPpUrBcZmxDG46LK1scxOrm3LbNJ/JV4lqjLeXVGH5hV/NpfVKOYVfzaX1StpLyieKWCaSBoM'
        'gJswWTPwmHkXelZzIqnasyPMKv5tL6pRzCr+bSeqVrfhMPIu9KPhN/gO9Ktoub2mS5hV/NpPVKOYVfzaX1StZ8Jv8A+lHwnPkHel'
        'LQv2mT5hV/NpfVKOY1Y308nqre4bjZna47Eg95VZytne+OOUHK4ZbEfWqqYbaoyvMKv5tL6pRzCr+bS+qVuoa+ojwnC/2s1ZiUZM'
        'DY2gsBD8gDieJ38NFP8ABnKcGS4oMsRs4tnDtbEkAW3gA6Joa1PNuYVfzaX1Sg0FWN9NIP8A2r1CXB+UsdRPsn0L4IS9wkfLkLmM'
        '8Zwba9tCqfFK59e6CR4AsywtuOqsUpOjMm0rMPzGq+byeqjmNV83k9VapC68pHPmsyvMar5vJ6qOY1XzeT1VqkJykOazK8xqvm8n'
        'qo5jVfN5PVWqQnKQ5rMrzGq+byeqjmNV83k9VapCcpDmsyvMar5vJ6qOY1XzeT1VqkJykOazK8xqvm8nqo5jVfN5PVWqQnKQ5rMr'
        'zGq+byeqjmNV83k9VapCcpDmsyvMar5vJ6qOY1XzeT1VqkJykOazK8xqvm8nqo5jVfN5PVWqQnKQ5rMrzGq+byeqjmNV83k9VapC'
        'cpDmsyvMar5vJ6qOY1XzeT1VqkJykOazK8xqvm8nqo5jVfN5PVWqQnKQ5rMqKGqv/V5PVUlpxJheRE+795ybtLacNFoUKqFbMjxL'
        '3Rn9pilwXMkeWtytLmXI9K4Yyvj8SF7ekHaM67WutGhXK+7JnXYzw8IiAw7BxYRbWME286jGhqvm8nqrVIUcL3ZViVsjK8xq/m8n'
        'qpyOCviN2wy6Ajd1HetMhFhpdRzL6Gdi8IwhoZC+zRYAsuN9/wAV0x2JRtysieBe99nqtAhaytdWTMuxQ7XE+qE9VrRDTS2iakbi'
        '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'),
    'thetis_controls': (
        '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAQDAwMDAgQDAwMEBAQFBgoGBgUFBgwICQcKDgwPDg4MDQ0PERYTDxAVEQ0NExoTFRcY'
        'GRkZDxIbHRsYHRYYGRj/2wBDAQQEBAYFBgsGBgsYEA0QGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgY'
        'GBgYGBgYGBj/wAARCAC7AWoDASIAAhEBAxEB/8QAHAAAAgIDAQEAAAAAAAAAAAAAAAgGBwIEBQMB/8QAWxAAAAUCAQUJCwcIBwYE'
        'BwAAAAIDBAUGEgcBExQiMggVQlJTVZKT0hYYIzNXYnKRorLiERc0OEOC0yQxNXN0dZTCJTZEVmOGsyE3QUVkhSYnUXFGR2GBg6Gj'
        '/8QAGwEBAAIDAQEAAAAAAAAAAAAAAAIDAQQFBgf/xAA5EQACAQIDBQMICgMBAAAAAAAAAgMBBAUREhMUIjJSBjFCFRYhM2FygaEj'
        'NEFTYnGRwdHwUbHhgv/aAAwDAQACEQMRAD8AUlNjPOGpVY8zsqKbcpjGQT1S6t2sDe+qjIN187JZlbVRNb4z0Q2m5dawshhBVRaj'
        'MYseomnnlC7RS5sFdIzLHdDYex8eVPuHLmd6TNPFqcbOecOFPjTLcyQaeXP/AEWLHw6hT3EPWLNAy7zfRBMpdYxi7I8WbGpZJIxm'
        'LmSclLtGTLdaHOxGq6nKRryvEKqnGz1rIRZWzOFTKZUxVDcLWLaXjbQ9sHW8HhbhRCqzi8W2eVU4KZZN3ddmTcEurtWiny3IsW02'
        'fF6NI2YkZTTSiuaSk3xlDG2Sj2Wa1G3kix67mSK6NsoGLaYwtyap2Tw13Vi0LHltRM+ziZs2VUpkzGu84SjH40gx3ZDN9ERhXrpF'
        'Fqsi2ttTUMUtw6HlLU6qviXUR0lBrQtZtW6i6++6SaZbjGMnsjFGLq90y0xsrJLt+UKUM4o6SxioisKjqVCSpV9Epp6qbxQrdTW8'
        'WZMwmimfj68wpiqcStp1w3RK4KmiUyalxdbOao0nxuReHTxf8zJbMSlmzqWQOYrFzJOTF2s2W4ebos4zcGQcvnyaxdpNTVMUN88a'
        'xULhLiE5okqRXRagzJjNPGFT4JS+aK73UDdimrRLkqSZZRxCpmeWltMY3Bu84bFtjDTSrHp/tKZhoyiWLWpZJUxWLmQcmLrGKgW6'
        '0YukZ9i4zD589QWKXWKoW0MdBlLD7hl9NUckUs4o6KnIOW3jk0/eKNfCulVcQJxxK4ltjPnUfG59i0X1TOylutu4wl5VyV5G5aNl'
        '7SOyFx0iTs/S7npAK6ly7Mu7LcXW1uCGmh8PaLqaJw/qiQpxpEyElILNHUamUyabkpdk1ptYdipsPaAdGxMiGtJx7EsCzTds10Ls'
        '4U3CKbzRU2OIradLf2uRLZiluG9RtWqa7l5IIJqeLUNqlMNXPSvBlXOztXBuMWnyDzBvDNDeWPXReJooKKZkvg/RGniFTOG7fH2P'
        'wyQoyNi2rgyKikoUxirFKYpdXWNaMx41q5l/z8g0YqZVJUxyl33c3G2bR2p6ma2plu1czR5Jsm8Tzje4vjChmJrDuiXzXEJmanG0'
        'EWmVk97X6dxTLekY20JNiAxox1UeGpa6bKrwqcWtcZNEyhUzWltMYu1aKmx7iXQv+f8AWZnZCT56Tut33c9IGelbP0u56QvDHKhW'
        '1N01DyceWm3Ma+UuRexbczY1vFzZhR461pcrcR7RCrTpDPSvO7npAz0rzu56QADZAZ6Vv/S7npAz0rzu56QAAAz0rzu56QM9K87u'
        'ekAAAM9Jm/5u56QM9K87uekAAAM9K87uekDPSvO7npAAADPSvO7npAz0rzu56QAAAz0rzu56QM9J86uekAAANIlSlMUsu7tN5wM9'
        'J86uekAAAM9K87uekDPSvO7npAAADPSpf+buekDPSvO7npAAADPSvO7npAz0rzu56QAAAz0rzu56QM9K87uekAAAM9J3luk1zela'
        'I3N/1nkf9mX6Ur7+USThF9IcGbeL908jrF+lK8Hz8oAnkfXFX07BrQ0HJmbMXjdPSE+N4Mo2E8UsREY2Nj99zaPHmzjVM1tyPomt'
        'HUi2cZF0MpUa7ROQWtTRRKsW4uzwijdaMoidjYqa3qbNliv9FcIoplTTU+6NlsMjlbU2nU3pOJPjaxs1NPCtcs/aQKeqaqKmnjTk'
        '45K7fKW3L3FLs7I3pyvK2qA7E0vJ5/e8pdF/w7RZstTMAvPupKNYIEbJt1kVE+CmoUtxTCmrbeD6Qhc4esGSt8DYw3FkxCjVjpp7'
        'iROMTK/dVMnULqQSVkEUyplXVKU1toymMTsQZ6baysnKlUfNTFMiuYpSm1RvUyzjmNGvqjfM0XKyK2ZboKluKXV4RR0WLSNn4RhK'
        'mjWjZZOSTbrJoplTTUL6JRCPDEbS2ldWXyKZ8aWNm4eFa5Z+04E1iZiDPQy0VIyZdFcGKZRIpSp3elaXWGUbitiNEwjeKj5kqTNM'
        'pioluuMX0TCaz0TGJ79tn8PGskkrdCMimUqhjfd1h51czKzkV2zFrTyDfNltKoVPObItrg8ao1TUi7SUlZVVeb2/l/JAoGvq4pkj'
        'osVIGTK6NnFim1s4bjWmHPnqmqWppc0nOOSuVjFtzhjbJfNLwRbMfBtzRcKY0Ew3uUYZx06zJbrvSEfoWFjVZmSknUfpsaipmUSW'
        '3bRhKmFqrr+IyvaSOqO9V5f5y/UiFO1xWNLpLJwr4rYqxfCIbRTfdNqjY+cSuu6hOoSyZivky5sqhTbJful2RLo+PTh8Ve5x3FNH'
        'LVZwYxc83KY1vB2hnS+VlOVzINXMRFFI3RWzeTRkyl1eMMVwuNm4ubuJPj2hWkVNS0pn3/YRR5iViDITzGXcyv5Ux1m5i6pUzeiB'
        'TEzEJZxLKqy9yksmVN4bligqa78nKoWGKYtxfyAqZTcHatEdNaNOSzhjbTpO1az7ePWSBHEavU6ZbwJpO6PRN4EqhSmMX0dUaM5W'
        'FY1FUe/k08z8gmVMuf4WrsjvYbsWb6sDJO0Gy6ZW6ihSuS6uzwrhtnjEpeZytXaDQySZc4XepFM2t5xii+PD1qutTQnxhYZ2iZeW'
        'mZyJjE7EGehjR8nL59vcUxv8S23aNwh6GxYxGWO1UVmCr6G3M2RKpaa1M3B2RIVMOmKdQN013S6DdZiZ7dwtXaKI9UMBGtqdazMQ'
        '5XURUWMioVfauKIthKxrxKotsctrhlWNm4v7+xzagrKsaqO336eaSm31W5TeDTT+6I/c8s8UXpCe04yaMqGkajXYIvHKapUSJrJ3'
        'FLcNKtWLNrJsXzNAqKb5qm5zZdUpTcIWpabOLNSceJrJctb6fj7aEPufcml0hlc+5NLpCbGTSj8NGZUilK4lnRs8bhZsvBHdNQdP'
        '5ZXeo0g60rI1M7vt1S2lutFi2jNylEmOQx+sXxV+XorX9Sqrn3JpdIGdeckl0hZLSkoxSShHbBdUzV8pm7Vky/eGWSjoBNsm7fvF'
        '01nD9ZqmVFO0uqbVDcpDDY/bLXT6f0/P+CtLn1/ikukC59f4hPpDuTkPvTVC0VcVQqZi61vGFhFjYhtVLCkTQrZVFwjaouZMucuM'
        'XVMUwjFbMzMrFt1i8cNFdV1aqZ/ClMyo7n2t4JLpAufcml0hYLRNOWw/lGTgxci0WpnE1Cl2iiDaorkj06TZtLzedVNOTUNXOvOS'
        'S6QLn3JpdIdaJTSWm2aRi3FM4KUxTcIWHVjZFnMu2SDWBKhdmypoopmcW+9cJRQbRWYou8UW3lpFp7ypjGfF+yS6QDGfF20k+kLK'
        'laAatoEsgzyu0UyuCt1CuClKa03CKUabijEEJefZ59S2LblWTMYu1cUpv5hKtpIpWmPWrrqVv76KfvQgNz7kC9IZXPrvFF9oXsaI'
        'gHS5ssq0yGIWCMoUxUy6puMXzhVJWsCpHPjFcuSuCm/J0zF1jCyayaGvMV2GNx3mrgrw/uR3OvOSS6QM685JLpCRUvEpz1UNY1dX'
        'MJrXXG4RbSiSr0PGvG+U0E7XUMk/KzVz/FNwvZMKY7Z5F1KbVxi0FvLspCuLnxvsk/umBnHl5vBJ6u1rCfuqUiFmsgWIdrruo/Wc'
        'JqbJi3WmMUdJ1Q0Jvk6h2sk5Uet2pXBbtnZuFm5SGu2PWi82r9Py/mhV1z7k0ukMrn3JpdIWa0w6Syw7Yz5dZN0s30gpimKVMt2z'
        'cIA4R0d0oga24prdUwqkt3j5jbssRgvGZYmz0mjc+5NLpAufcml0hsaoNUUm+a9z7k0ukC59yaXSGxqg1QBrpmeZ0txUrbhHJ/8A'
        'rXJ/7P7Wr7+USstpjl9IcObRbd00j+Wf2pXg+flAFh0tLTjp8WkYqB3/ANKRTMZkYvml4XBFhqYc4y3x6cfhuu0ZsVM4mgXWuN5x'
        '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'),
    'thetis_telemetry': (
        '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAQDAwMDAgQDAwMEBAQFBgoGBgUFBgwICQcKDgwPDg4MDQ0PERYTDxAVEQ0NExoTFRcY'
        'GRkZDxIbHRsYHRYYGRj/2wBDAQQEBAYFBgsGBgsYEA0QGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgY'
        'GBgYGBgYGBj/wAARCAEPAWoDASIAAhEBAxEB/8QAHAAAAQUBAQEAAAAAAAAAAAAABwADBAUGAggB/8QAURAAAQMDAgMEBQcGCgkE'
        'AgMAAgMEBQAGEhMiBxQyFUJSkgEII2JyFhczU4KishgkNENUVRElJkRWc5TC0uIJITU2N1djdPAnRUaxMWRRg5P/xAAaAQEAAwEB'
        'AQAAAAAAAAAAAAAAAgMEBQEG/8QAPREAAgEDAQQFCQcDBAMAAAAAAAIDAQQSEQUTIjIUITFS0QZBQlFhcZGh8CNigaKxweEVM3IW'
        'JDSSQ4Lx/9oADAMBAAIRAxEAPwDyrcCcv2s4VQcu00U8RLT6R21BTj7lWJMUl5ItQck8e9RYt8YcoGYKcUU5XURyx+EaYhxkB4qq'
        'doECbEWinK8sPsxTx7tdJbBWVWy5j5F/KKSNpY1j5PzdVOwFjxrcLExF45kECLp1NuVNuEZxqQi5fPUiIct1Exo7jpuTaW6Kzh0i'
        '3dE9dO3QjkmmPdpy8xQuSyCl0HiDt1HrbiTy+jp0JcWZWLk29IsscUsemXv8/Z8faC8hmk2orm+fCip0kXSVSE4u6lmouUlZQkSH'
        'LIR21sLiUkHHCW31XIqKEmSmREOI47asIpT5RxEfDroyTBRq0U03Ca3syHq3VUtouWJc+2ZKRb3GnNWjfhqD1uxuN5qcsvJKafVj'
        '3abatbhfEQs3cguQ9Qp92iWwB23tS3ko1VQh7RIXWiXd96nZbVG2pwoXLW7SLLlurHKrehLjkZn2/JRtFWnbp89OsFaxS7dwSS8g'
        '9SUTLEhIumm9aTIse1Xfh6q1nELS+VaP1hNUdb+sxqLYYtivyP5zTxEi6vFuxrM0P2u7O0t9lZ9Kx82pVrRt0NWvMrqySaPVqF00'
        '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'
        'odIIY8ui6Ux94cq28sqcrFl8n3rfTTaiSjYUcSLHqKh0NwORYE2JikRKLaxKKDkWXxeGp5Xm99DNZFpEsmRqp6ZrNk8SIfDUprWZ'
        't2y8y/wSubOeTdsq8S/x1ldls3bq3FjtW1wNXVvvkkhTHcLnHp+1Q75xXLLliq0RuiQawZRTZDSRIsiIeoq039vJNFu4+b9DVtO3'
        'kuId3Dwt3vUW12LD8o1mIthQRZjopjj3a1lgW6SDhrIOo/0O1HWQpp45CO2hzKXE+mHCK7xt7ZNPTyEfpPCRVzG3E+iXibxmkpkn'
        '0iXTWaazmktN0jaMZbixuJLHcI2jafXiaaOfOYufcR+SDQdbElyTyId3TTN6JpI3appICkJJiW3vbR3VVNLrcNlFDUhGTolC1MnS'
        'eW6vql5SS0m4fLskFzWT0/aJ5CmPu0S2mjl3tKej8T2K0mjuN7Sno/HsN2wjE2tpRSLF03bu5ESLJQdynu0PnzddnJLNnOOsmW7G'
        'pEfesiwZJN/RGtlibkRN1Fk8iTy8NVLiUcunBLrpKKqEWRFUrK3mikbecv1+x7s6zuLeV2k5W8fA01k4/LqPy+sHu1Kt8pUroeNm'
        'iopp6hEsoSYkKY5VQ2tNJxt1s3blBQU0yyKpbK9HUWMg0Simq7d4sRHrJll90qjdQSNI+K68NP1qRvIZpJpN2uvDT9amp7YbSnFK'
        'NSQFPRZlpiQiI6nirEyAkUy4Ed3tCHHH3qnRdzIfKmPeKRCDJNuW7l8t3mKqOQkNaRcKigRCooRVK1hrC+Kr6NP1qe7OtawS41XF'
        'cafrUMNq21ycK6RKL9Dtw4ZksSxJ5Y5VX2HbRNXSLxzHk5UdaiaaZD9GI+Kh1F3ZKw66yjYTyWT0yy8NNxtySETIi+bJFqDl1dNY'
        'ZNm3bUlXec316znybGva0npSTn/n2+4mTDVVvcbhBUdLFbcPh3UQ5CH9KaSEFDumaK5oj7EhHJQsfEVDL5SPCQeJkxTUJ59IqoOR'
        'D8NWafECXSSTII5uTlJPTTeEnksP2qvuba5kxx9E1XVldyrHp6JUEJCRCe0st1buw27ha35smYo80PpTFIlBHxe9Q4J8qRERNiyK'
        'p7S5XzKJeR6Db2LrHUy6tvhLu1tvreSeHBebqN+07WS6t93HzdX6hOUbtfnOi2KzVMlxTLmMU9pFjQydY86sIDtEi6fiqzbcQJhB'
        'dmuozRcKs/oVFhLL7RCVV0hcXaAEPYbZsRFlqICWX3irNYWk1u3F6vEx7Ms7i1k+0XzUp86+Jq4xfsaw0ZJsKROnDzTUUJPLaNQL'
        '1aoNrnT9DYRT5pumsQiWO4qp427H0eyUZlHoO25FqCm5TyES8VQ5KefSz9R48TU1CHHbtERHu17DazLcbyvtJ29lMt00rcvX89NP'
        'gEm2omLhrvgm6zRRd6vieQ9I1Mbmk3tFqsTto3JR4sKhKJiWWJVg2XEGVZE3Ls1qss1/R3KiftBptG+HYxybJxCsnSSahKDrI5bi'
        'LLxVzpdm3MjZP7P3/g5E+yLuaTJ+vs/Ht8aEu9mqTO93mgkKTdYRWRxHqTLpKs/XUtcD6YkiePEiIsREREcRERHaNQecV/ZirvWk'
        'bRxKsnMfT2UckcCRycy0JlKofOF+ylS5wv2Uq0msmUqh84X7KVLnC/ZSoCZ4aIjD/ZLX+pD/AOvRQx5wv2ZWiQwU/ilrt/Uh/wDX'
        'orbZ+kQcyMwnozJJCQkIpjuH4ag1PetllXuQej0+kdMeovdqLyjjwejzVG//AOTJ/lU9i/trkNUqd5Rx4PR5qXKOPB6PNWQkNUqd'
        '5Rx4PR5qXKOPB6PNQDVKneUceD0ealyjjwejzUA1Sp3lHHg9Hmpco48Ho81ANUqd5Rx4PR5qXKOPB6PNQDVKneUceD0ealyjjwej'
        'zUA1Sp3lHHg9Hmpco48Ho81ANUqd5Rx4PR5qXKOPB6PNQDVKneUceD0ealyjjwejzUA1Sp3lHHg9Hmpco48Ho81ANF9kq5/8Gn+U'
        'ceD0ealyjjwejzUAwWVLGn+UceD0ealyjjwejzUA1Sp3lHHg9Hmpco48Ho81ANUqd5Rx4PR5qXKOPB6PNQDVKneUceD0ealyjjwe'
        'jzUA1Sp3lHHg9Hmpco48Ho81ANUqd5Rx4PR5qXKOPB6PNQDVKneUceD0ealyjjwejzUA1Sp3lHHg9Hmpco48Ho81ANUqd5Rx4PR5'
        'qXKOPB6PNQDVKneUceD0ealyjjwejzUAwW0aLsVDtjgWJ88zHJun6f4NT/8AG30UKeVcd1P0eaiEwQPspr/q9H0Qf/XordZK1aNi'
        'xW9Kt2V0P//Z'),
}


if __name__ == "__main__":
    main()
