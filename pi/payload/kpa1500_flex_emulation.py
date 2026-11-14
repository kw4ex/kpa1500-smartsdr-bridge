#!/usr/bin/env python3
"""
kpa1500_flex_emulation.py  -  makes the KPA1500 look like a FlexRadio-style
Power Genius XL (PGXL) amplifier and Tuner Genius XL (TGXL) tuner.

This file is an add-on for kpa1500_sdr_bridge.py (version 2.50 or newer). It uses
only what comes with Python. The bridge starts it when you give it the flags
described in KPA1500_Flex_Emulation_Guide.html. It does nothing otherwise.

WHAT IT DOES (three independent parts)
  1. PGXL device   a network server on TCP port 9008 that answers like a real
                   Power Genius XL (status, power, SWR, current, temperature,
                   operate/standby).
  2. TGXL device   a network server on TCP port 9010 that answers like a real
                   Tuner Genius XL. The KPA1500's built-in ATU plays the tuner.
  3. Radio login   (only when you give --flex-radio-ip, or auto) the program logs in to
                   your FlexRadio the way a real PGXL/TGXL does, registers the
                   amplifier and tuner, and streams the meter readings, so
                   SmartSDR shows them. THIS PART IS EXPERIMENTAL: FlexRadio
                   does not publish every detail of it. It is switched off
                   unless you ask for it.

WHAT IT NEVER DOES
  - It never keys the amplifier or the radio.
  - It only asks the bridge for actions the bridge already has (OPERATE,
    STANDBY, ATU inline/bypass, ATU tune), and the bridge keeps all its own
    safety rules (for example no ATU change while transmitting).
  - The FlexRadio "interlock" (the radio waiting for the amp to say ready
    before it transmits) is OFF unless you ask for it with --flex-interlock,
    so this add-on cannot hold back your transmissions by default.

Sources used (all public): FlexRadio's SmartSDR API pages (amplifier, meter,
interlock, PowerGenius Ethernet API) and the message formats seen in the
open-source AetherSDR program. Nothing here was copied from any commercial
product.
"""
import argparse
import ipaddress
import math
import os
import re
import socket
import struct
import threading
import time

FLEX_EMU_VERSION = "1.0"

PGXL_MODEL = "PowerGeniusXL"
TGXL_MODEL = "TunerGeniusXL"
PGXL_FIRMWARE = "3.8.9"
TGXL_FIRMWARE = "1.2.17"
INTERLOCK_NAME = "PG-XL"

# meters a real PGXL registers (names, ranges and units as seen on a real one)
#          name    min   max    units(first choice, other spellings to try)
METERS = (("FWD", 30.0, 63.0, ("DBM",)),
          ("RL", 0.4, 60.0, ("DB",)),
          ("DRV", 10.0, 50.0, ("DBM",)),
          ("ID", 0.0, 70.0, ("AMPS",)),
          ("TEMP", 0.0, 100.0, ("TEMP_C", "DEGC", "TEMPC")))

# the tuner's own meters, created on the tuner's radio connection (ranges as the working bridge used)
METERS_T = (("RL", 0.35, 60.0, ("DB",)),
            ("FWD", 30.0, 63.01, ("DBM",)))

BANDS = ((1800, 2000, "160"), (3500, 4000, "80"), (5300, 5500, "60"),
         (7000, 7300, "40"), (10100, 10150, "30"), (14000, 14350, "20"),
         (18068, 18168, "17"), (21000, 21450, "15"), (24890, 24990, "12"),
         (28000, 29700, "10"), (50000, 54000, "6"))


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def band_name(khz):
    if not khz:
        return "0"
    for lo, hi, name in BANDS:
        if lo <= khz <= hi:
            return name
    return "0"


def watts_to_dbm(w, lo=30.0, hi=63.0):
    """watts -> dBm, kept inside the range the meter was registered with"""
    try:
        v = 10.0 * math.log10(max(float(w), 0.0001) * 1000.0)
    except (ValueError, TypeError):
        v = lo
    return max(lo, min(hi, v))


def swr_to_return_loss(swr):
    """SWR -> return loss in dB (positive). A perfect match is capped at 60."""
    try:
        swr = float(swr)
    except (TypeError, ValueError):
        return 60.0
    if swr <= 1.0:
        return 60.0
    rho = (swr - 1.0) / (swr + 1.0)
    return max(0.4, min(60.0, -20.0 * math.log10(rho)))


def parse_radio_info(text):
    """The radio's 'info' answer -> a small dict (model, name, serial, version, callsign).
    The radio separates the fields with commas (or spaces) and may quote values containing spaces."""
    out = {}
    for m in re.finditer(r'([A-Za-z_]+)=("([^"]*)"|[^,\s]*)', text or ""):
        out[m.group(1).lower()] = (m.group(3) if m.group(3) is not None else m.group(2)).strip()
    want = (("model", ("model",)), ("name", ("nickname", "name", "radio_name")),
            ("serial", ("chassis_serial", "serial", "serial_num")),
            ("version", ("software_ver", "version", "fpga_ver")), ("callsign", ("callsign",)))
    res = {}
    for key, names in want:
        for n in names:
            if out.get(n):
                res[key] = out[n]
                break
    return res


def parse_kv(text):
    """'a=1 b=two c=' -> {'a': '1', 'b': 'two', 'c': ''}"""
    out = {}
    for part in text.split():
        if "=" in part:
            k, _, v = part.partition("=")
            if k:
                out[k] = v
    return out


def local_ip_towards(target):
    """The address of this PC on the network that reaches `target`."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target, 9))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return ""


def int16(v):
    return int(v) & 0xFFFF


# --------------------------------------------------------------------------
# FlexRadio meter packet (VITA-49 "meter extension" packet)
# Layout follows FlexRadio's public meter description: extension-data packet
# with stream id and class id, no timestamps; the payload is a list of 32-bit
# words, upper 16 bits = meter number, lower 16 bits = the value.
# NOT yet checked against a real radio - see the guide.
# --------------------------------------------------------------------------
FLEX_OUI = 0x00001C2D
METER_INFO_CLASS = 0x534C
METER_PACKET_CLASS = 0x8002
METER_STREAM_ID = 0x00000700     # stream id used by meter packets; the radio's reply gives only the meter number
AMP_METER_STREAM_ID = 0x88000000  # stream id FlexRadio's public meter documentation shows for external (amplifier) meters


# Ways to build the packet, tried in turn until the radio shows our meters (variant 0 copies a
# real packet captured from the radio: header 0x3853xxxx = type 3, class id, UTC time, sample count)
METER_VARIANTS = (
    # style 0 copies what a working amplifier bridge was seen sending to a real radio (network capture
    # 2026-11-05): short packet, NO timestamps, stream 0x88000000, every meter in ONE packet, sent
    # from a separate UDP socket
    dict(tsi=0, short=True, stream="amp", sock="own"),
    dict(tsi=1, now=True, stream="meter"),
    dict(tsi=1, now=True, stream="handle"),
    dict(tsi=3, now=False, stream="meter"),
    dict(tsi=0, short=True, stream="meter"),
    dict(tsi=1, now=True, stream="zero"),
    dict(tsi=1, now=True, stream="meter", port=4992),
    dict(tsi=1, now=True, stream="meter", split=True),
)


def build_meter_packet(stream_id, pairs, count, tsi=1, now=True, short=False, **_ignored):
    """Meter packet like the radio's own: 28-byte header (header word, stream id, class id x2,
    integer timestamp, 64-bit fractional timestamp), then (meter number, value) pairs."""
    cls = (METER_INFO_CLASS << 16) | METER_PACKET_CLASS
    if short:
        words = [0, stream_id & 0xFFFFFFFF, FLEX_OUI, cls]
        tsf = 0
    else:
        words = [0, stream_id & 0xFFFFFFFF, FLEX_OUI, cls,
                 int(time.time()) & 0xFFFFFFFF if now else 0, 0, 0]
        tsf = 1
    for meter_id, raw in pairs:
        words.append(((meter_id & 0xFFFF) << 16) | int16(raw))
    words[0] = ((0x3 << 28) | (1 << 27) | ((tsi & 3) << 22) | (tsf << 20)
                | ((count & 0xF) << 16) | (len(words) & 0xFFFF))
    return struct.pack(">%dI" % len(words), *words)


def parse_meter_packet(data):
    """Inverse of build_meter_packet; also reads the radio's own meter packets."""
    n = len(data) // 4
    words = struct.unpack(">%dI" % n, data[:n * 4])
    hdr = words[0]
    pairs = []
    # header words: 0 header, 1 stream id, 2-3 class id, then an integer timestamp if TSI != 0
    # and a 64-bit fractional timestamp if TSF != 0
    skip = 4 + (1 if (hdr >> 22) & 3 else 0) + (2 if (hdr >> 20) & 3 else 0)
    for w in words[skip:]:
        raw = w & 0xFFFF
        if raw >= 0x8000:
            raw -= 0x10000
        pairs.append((w >> 16, raw))
    return {"ptype": hdr >> 28, "class_present": bool(hdr & (1 << 27)),
            "count": (hdr >> 16) & 0xF, "size": hdr & 0xFFFF,
            "stream": words[1], "oui": words[2] & 0xFFFFFF,
            "info_class": words[3] >> 16, "packet_class": words[3] & 0xFFFF,
            "pairs": pairs}


def meter_raw(name, snap):
    """The 16-bit number sent for each meter (scaling as FlexRadio describes:
    dB/dBm x128, amps x256, degrees C x64)."""
    if name == "FWD":
        return int(round(watts_to_dbm(snap["fwd"], 30.0, 63.0) * 128))
    if name == "RL":
        return int(round(swr_to_return_loss(snap["swr"] if snap["fwd"] > 0 else 1.0) * 128))
    if name == "DRV":
        return int(round(watts_to_dbm(snap["drive"], 10.0, 50.0) * 128))
    if name == "ID":
        a = snap["amps"] if snap["amps"] is not None else 0
        return int(round(max(0.0, min(70.0, float(a))) * 256))
    if name == "TEMP":
        t = snap["temp"] if snap["temp"] is not None else 0
        return int(round(max(0.0, min(100.0, float(t))) * 64))
    return 0


# --------------------------------------------------------------------------
# command line flags (called by the bridge's build_parser)
# --------------------------------------------------------------------------
def add_arguments(p):
    g = p.add_argument_group("FlexRadio PGXL/TGXL emulation")
    g.add_argument("--flex-emulate", action="store_true",
                   help="make the KPA1500 appear as a Power Genius XL (TCP 9008) and "
                        "Tuner Genius XL (TCP 9010) on the network")
    g.add_argument("--flex-radio-ip", default="", metavar="IP",
                   help="EXPERIMENTAL: log in to this FlexRadio so SmartSDR shows the amp "
                        "and tuner ('auto' = look for the radio). Implies --flex-emulate")
    g.add_argument("--flex-radio-fallback-ip", default="", metavar="IP",
                   help="used when --flex-radio-ip auto finds no radio within a few seconds")
    g.add_argument("--flex-no-follow-freq", action="store_true",
                   help="do not take the frequency from the FlexRadio's transmit slice (by default the "
                        "amp follows it when no Thetis/TCI connection supplies the frequency)")
    g.add_argument("--flex-radio-port", type=int, default=4992, help=argparse.SUPPRESS)
    g.add_argument("--flex-meter-port", type=int, default=4991, help=argparse.SUPPRESS)
    g.add_argument("--flex-ip", default="", metavar="IP",
                   help="address of this PC to tell the radio (normally found by itself)")
    g.add_argument("--flex-serial", default="KPA1500-0001",
                   help="serial number shown for the amplifier (no spaces)")
    g.add_argument("--flex-nickname", default="KPA1500", help="name shown for the amplifier")
    g.add_argument("--flex-allow", default="", metavar="IP,IP",
                   help="extra computers allowed to CONTROL the amp (operate/standby, ATU). "
                        "This PC and the FlexRadio are always allowed")
    g.add_argument("--flex-interlock", action="store_true",
                   help="EXPERIMENTAL: also register the FlexRadio transmit interlock "
                        "(the radio then waits for the amp before it transmits)")
    g.add_argument("--flex-no-tuner", action="store_true", help="do not present a Tuner Genius XL")
    g.add_argument("--flex-no-meters", action="store_true", help="do not send meter readings to the radio")
    g.add_argument("--flex-no-discovery", action="store_true", help="do not broadcast on the network")
    g.add_argument("--flex-pgxl-port", type=int, default=9008, help=argparse.SUPPRESS)
    g.add_argument("--flex-tgxl-port", type=int, default=9010, help=argparse.SUPPRESS)
    g.add_argument("--flex-verbose", action="store_true",
                   help="log every message to and from the radio and the devices")
    g.add_argument("--flex-selftest", action="store_true",
                   help="run the built-in tests of this add-on and exit")
    return g


def wanted(a):
    return bool(getattr(a, "flex_emulate", False) or getattr(a, "flex_radio_ip", ""))


# --------------------------------------------------------------------------
# a small TCP server that speaks the PGXL/TGXL text protocol
# --------------------------------------------------------------------------
class DeviceServer(threading.Thread):
    MAX_CLIENTS = 10          # the real devices also allow about ten

    def __init__(self, emu, label, port, greeting, on_command):
        super().__init__(daemon=True, name="flex-" + label)
        self.emu, self.label, self.port = emu, label, port
        self.greeting, self.on_command = greeting, on_command
        self.sock = None
        self.clients = []
        self.lock = threading.Lock()
        self.error = ""
        self.last_peer = ""

    def open(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name != "nt":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.emu.bind_ip, self.port))
        s.listen(8)
        s.settimeout(0.5)
        self.port = s.getsockname()[1]
        self.sock = s

    def run(self):
        while not self.emu.stop.is_set():
            try:
                c, addr = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self.lock:
                full = len(self.clients) >= self.MAX_CLIENTS
            if full:
                c.close()
                continue
            threading.Thread(target=self._client, args=(c, addr[0]), daemon=True).start()
        try:
            self.sock.close()
        except OSError:
            pass

    def count(self):
        with self.lock:
            return len(self.clients)

    def _send(self, c, text):
        try:
            with self.lock:
                c.sendall(text.encode("utf-8"))
            return True
        except OSError:
            return False

    def broadcast(self, text):
        with self.lock:
            cs = list(self.clients)
        for c in cs:
            self._send(c, text)

    def _client(self, c, ip):
        if not self.emu.read_allowed(ip):
            self.emu.log("FLEX %s: refused a connection from %s (not a local-network address)"
                         % (self.label, ip))
            c.close()
            return
        c.settimeout(1.0)
        with self.lock:
            self.clients.append(c)
        self.last_peer = ip
        self.emu.log("FLEX %s: connection from %s" % (self.label, ip), verbose=True)
        try:
            if not self._send(c, self.greeting + "\n"):
                return
            buf = b""
            while not self.emu.stop.is_set():
                try:
                    d = c.recv(4096)
                except socket.timeout:
                    continue
                if not d:
                    break
                buf += d
                if len(buf) > 16384:
                    break
                while True:
                    m = re.search(rb"[\r\n]", buf)
                    if not m:
                        break
                    line = buf[:m.start()].decode("utf-8", "replace").strip()
                    buf = buf[m.end():]
                    if line:
                        self._line(c, ip, line)
        except OSError:
            pass
        finally:
            with self.lock:
                if c in self.clients:
                    self.clients.remove(c)
            try:
                c.close()
            except OSError:
                pass

    def _line(self, c, ip, line):
        self.emu.log("FLEX %s <- %s: %s" % (self.label, ip, line), verbose=True)
        m = re.match(r"C(\d+)\|(.*)$", line, re.S)
        if not m:
            self.emu.note_unknown("%s %s sent: %r" % (self.label, ip, line))
            return
        for out in self.on_command(int(m.group(1)), m.group(2), ip):
            self.emu.log("FLEX %s -> %s: %s" % (self.label, ip, out), verbose=True)
            self._send(c, out + "\n")


# --------------------------------------------------------------------------
# the login to the FlexRadio (experimental)
# --------------------------------------------------------------------------
class FlexRadioLink(threading.Thread):
    """One login to the radio. A real PGXL and a real TGXL are two separate boxes, each with
    its own connection, and the radio keeps only ONE amplifier object per connection - so
    the amplifier and the tuner each get a login of their own (role "PGXL" or "TGXL")."""

    def __init__(self, emu, role="PGXL"):
        super().__init__(daemon=True, name="flex-radio-" + role.lower())
        self.role = role
        self.emu = emu
        self.sock = None
        self.buf = b""
        self.seq = 0
        self.state = "off"           # off, searching, connecting, registering, registered, error
        self.error = ""
        self.radio_ip = ""
        self.radio_handle = ""
        self.version = ""
        self.handles = {}            # "PowerGeniusXL" -> "0x...."
        self.reg = {}                # what each registration step got
        self.meters = []             # (name, meter id, stream id)
        self.il_id = None
        self.il_mode = None
        self.slices = {}             # slice number -> {"mhz":, "tx":, "active":} from the radio
        self.follow_hz = 0           # last frequency handed to the bridge
        self.radio_info = {}         # what the radio says about itself (model, name, serial ...)
        self.radio_status = {}       # last 'amplifier ...' line the radio sent for each of our devices
        self.udp = None
        self.pkt_count = 0
        self.todo = []
        self.meter_sent = 0
        self.rfpower = None          # the radio's RF power setting 0-100 (from its 'transmit' status)
        self.tunepower = None

    # ---- low level ----------------------------------------------------
    def _readline(self, wait):
        """Return one text line, or None if nothing arrives within `wait` seconds."""
        end = time.time() + wait
        while True:
            m = re.search(rb"[\r\n]+", self.buf)
            if m:
                line = self.buf[:m.start()].decode("utf-8", "replace")
                self.buf = self.buf[m.end():]
                if line:
                    return line
                continue
            left = end - time.time()
            if left <= 0:
                return None
            self.sock.settimeout(min(left, 0.2))
            try:
                d = self.sock.recv(8192)
            except socket.timeout:
                continue
            if not d:
                raise ConnectionError("the radio closed the connection")
            self.buf += d
            if len(self.buf) > 262144:
                self.buf = self.buf[-65536:]

    def _send_cmd(self, text):
        self.seq += 1
        self.emu.log("FLEX radio -> C%d|%s" % (self.seq, text), verbose=True)
        self.sock.sendall(("C%d|%s\n" % (self.seq, text)).encode("utf-8"))
        return self.seq

    def cmd(self, text, wait=3.0):
        """Send a command and wait for its answer. Returns (code, message)."""
        seq = self._send_cmd(text)
        end = time.time() + wait
        while time.time() < end:
            line = self._readline(max(0.05, end - time.time()))
            if line is None:
                continue
            m = re.match(r"R(\d+)\|([0-9A-Fa-f]*)\|?(.*)$", line)
            if m and int(m.group(1)) == seq:
                try:
                    code = int(m.group(2) or "0", 16)
                except ValueError:
                    code = -1
                self.emu.log("FLEX radio <- R%d|%s|%s" % (seq, m.group(2), m.group(3)), verbose=True)
                return code, m.group(3).strip()
            self._on_line(line)
        return None, "no answer from the radio"

    def _on_line(self, line):
        self.emu.log("FLEX radio <- %s" % line, verbose=True)
        if line.startswith("S") and "|" in line:
            body = line.split("|", 1)[1]
            if body.startswith("amplifier "):
                m = re.match(r"amplifier\s+(\S+)\s*(.*)$", body)
                if m:
                    kv = parse_kv(m.group(2))
                    model = kv.get("model", "")
                    if kv.get("serial_num") in (self.emu.serial, self.emu.serial_t) or model in (
                            PGXL_MODEL, TGXL_MODEL) and kv.get("ip") == self.emu.adv_ip:
                        self.handles[model or "?"] = m.group(1)
                        self.radio_status[model or "?"] = body[:200]
            elif body.startswith("transmit ") and self.role == "PGXL":
                kv = parse_kv(body[len("transmit "):])
                try:
                    if "rfpower" in kv:
                        self.rfpower = max(0, min(100, int(float(kv["rfpower"]))))
                    if "tunepower" in kv:
                        self.tunepower = max(0, min(100, int(float(kv["tunepower"]))))
                except ValueError:
                    pass
            elif body.startswith("slice ") and self.role == "PGXL":
                self._slice_status(body)
            elif body.startswith("meter ") and self.meters:
                self._meter_status(body)
            elif body.startswith("interlock") and self.il_id is not None:
                if ("state=PTT_REQUESTED" in body
                        and ("AMP:" + INTERLOCK_NAME) in body):
                    self.todo.append("ready")
        elif line.startswith("M") and "|" in line:
            self.emu.log("FLEX radio message: %s" % line.split("|", 1)[1], verbose=True)

    # ---- the session --------------------------------------------------
    def run(self):
        while not self.emu.stop.is_set():
            try:
                self._session()
            except (OSError, ConnectionError) as e:
                self.error = str(e)
                if self.state != "error":
                    self.emu.log("FLEX radio: %s (will keep trying)" % e)
                self.state = "error"
            finally:
                self._drop()
            self.emu.stop.wait(5.0)

    def _drop(self):
        s, self.sock = self.sock, None
        self.handles, self.meters, self.il_id, self.il_mode = {}, [], None, None
        self.slices, self.follow_hz = {}, 0
        self.rfpower = self.tunepower = None
        self.buf, self.todo = b"", []
        if s:
            try:
                s.close()
            except OSError:
                pass

    def _session(self):
        ip = self.emu.radio_ip
        if ip.lower() == "auto" and self.role == "TGXL":
            ip = self.emu.radio_ip_found
            if not ip:
                self.state = "searching"
                raise ConnectionError("waiting for the amplifier login to find the radio")
        elif ip.lower() == "auto":
            self.state = "searching"
            ip = discover_radio(6.0, self.emu.stop)
            if ip:
                self.emu.log("FLEX radio: found a FlexRadio at %s" % ip)
            elif self.emu.radio_fallback:
                ip = self.emu.radio_fallback
                self.emu.log("FLEX radio: none found by searching - using the address you gave: %s" % ip)
            else:
                raise ConnectionError("no FlexRadio found yet - set a fallback address "
                                      "(--flex-radio-fallback-ip) or use --flex-radio-ip with the address")
        self.radio_ip = ip
        self.emu.radio_ip_found = ip
        self.state = "connecting"
        self.sock = socket.create_connection((ip, self.emu.radio_port), timeout=5.0)
        self.sock.settimeout(1.0)
        # prologue: V<version> then H<handle>
        t_end = time.time() + 5.0
        while time.time() < t_end and not (self.version and self.radio_handle):
            line = self._readline(0.5)
            if line and line[0] == "V":
                self.version = line[1:].strip()
            elif line and line[0] == "H":
                self.radio_handle = line[1:].strip()
        if not self.radio_handle:
            raise ConnectionError("connected, but the radio did not send its greeting")
        self.emu.log("FLEX radio: connected to %s (version %s, our handle %s)"
                     % (ip, self.version, self.radio_handle))
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(("", 0))
        self.udp_port = self.udp.getsockname()[1]
        self.rx_vals, self.rx_count = {}, 0
        self.rx_total, self.rx_sample, self.tx_sample = 0, "", ""
        self.variant, self.var_t, self.var_n, self.var_locked = 0, time.time(), 0, False
        if self.role == "PGXL":
            threading.Thread(target=self._udp_listen, args=(self.udp,), daemon=True,
                             name="flex-meter-rx").start()
        self.state = "registering"
        self.register()
        self.state = "registered"
        self.error = ""
        next_ping = time.time() + 3.0
        next_meter = 0.0
        while not self.emu.stop.is_set():
            line = self._readline(0.05)
            if line:
                self._on_line(line)
            now = time.time()
            snap = self.emu.snapshot()
            self._interlock_tick(snap)
            if self.todo:
                todo, self.todo = self.todo, []
                if "ready" in todo:
                    self._answer_ptt(snap)
                for item in todo:
                    if isinstance(item, tuple) and item[0] == "rfpower":
                        self._set_rfpower(item[1])
            if now >= next_ping:
                code, msg = self.cmd("ping", 2.0)
                if code is None:
                    raise ConnectionError("the radio stopped answering")
                next_ping = now + 3.0
            if self.meters and now >= next_meter:
                self._send_meters(snap)
                next_meter = now + 0.1
        self._goodbye()

    # ---- registering --------------------------------------------------
    def register(self):
        e = self.emu
        code, msg = self.cmd("keepalive enable")
        self.reg["keepalive"] = "ok" if code == 0 else "code %s" % code
        if self.role == "TGXL":
            tgxl = ["ip=%s port=%d model=%s serial_num=%s ant=ANT1,ANT2"
                    % (e.adv_ip, e.tgxl.port, TGXL_MODEL, e.serial_t),
                    "ip=%s port=%d model=%s serial_num=%s ant=ANT1:PORTA,ANT2:PORTB"
                    % (e.adv_ip, e.tgxl.port, TGXL_MODEL, e.serial_t)]
            self._create_device("TGXL", tgxl)
            if e.meters_on:
                self._create_meters(METERS_T)
            return
        pgxl = ["ip=%s port=%d model=%s serial_num=%s ant=ANT1:PORTA,ANT2:PORTB"
                % (e.adv_ip, e.pgxl.port, PGXL_MODEL, e.serial)]
        self._create_device("PGXL", pgxl)
        subs = ["sub amplifier all", "sub meter all", "sub tx all", "client udpport %d" % self.udp_port]
        if not getattr(e.a, "flex_no_follow_freq", False):
            subs.append("sub slice all")             # the transmit slice's frequency steers the amp
        for sub in subs:
            code, msg = self.cmd(sub)
            self.reg[sub] = "ok" if code == 0 else "code %s" % code
        code, msg = self.cmd("info")                      # which radio is this? (display only)
        if code == 0:
            self.radio_info = parse_radio_info(msg)
            self.emu.log("FLEX radio: %s" % (", ".join("%s=%s" % kv for kv in self.radio_info.items())
                                             or "info answer not understood: " + msg[:120]))
        if e.meters_on:
            self._create_meters()
        if e.interlock:
            code, msg = self.cmd("interlock create type=AMP valid_antennas=ANT1,ANT2 name=%s serial=%s"
                                 % (INTERLOCK_NAME, e.serial))
            m = re.search(r"(\d+)", msg or "")
            if code == 0 and m:
                self.il_id = m.group(1)
                self.il_mode = "enabled"
                self.reg["interlock"] = "ok (id %s)" % self.il_id
            else:
                self.reg["interlock"] = "failed: code %s %s" % (code, msg)
                self.emu.log("FLEX radio: interlock was not accepted (%s %s) - carrying on without it"
                             % (code, msg))

    def _create_device(self, label, variants):
        for i, params in enumerate(variants):
            code, msg = self.cmd("amplifier create " + params)
            if code == 0:
                self.reg[label] = "ok" if i == 0 else "ok (alternate form %d)" % (i + 1)
                self.emu.log("FLEX radio: %s registered%s" % (
                    label, "" if i == 0 else " using the alternate form"))
                return True
            self.reg[label] = "refused: code %s %s" % (code, msg)
            self.emu.log("FLEX radio: %s registration refused (code %s %s)" % (label, code, msg))
        return False

    def _create_meters(self, table=None):
        table = table or METERS
        for name, lo, hi, units in table:
            done = False
            for u in units:
                f = lambda x: ("%.1f" if round(x, 1) == x else "%.2f") % x     # 0.35 stays 0.35
                code, msg = self.cmd("meter create name=%s type=AMP min=%s max=%s units=%s"
                                     % (name, f(lo), f(hi), u))
                # the radio answers with just the meter number (for example "10");
                # some versions may add a stream id after a comma
                m = re.match(r"\s*(\d+)\s*(?:,\s*(?:0x)?([0-9A-Fa-f]+))?", msg or "")
                if code == 0 and m:
                    stream = int(m.group(2), 16) if m.group(2) else METER_STREAM_ID
                    self.meters.append([name, int(m.group(1)), stream])
                    done = True
                    break
                if code not in (0x500000A6, 0x500000A5, 0x50000016):
                    break
            if not done:
                self.emu.log("FLEX radio: meter %s was not accepted - skipped" % name)
        self.reg["meters"] = "%d of %d" % (len(self.meters), len(table))

    def _udp_listen(self, sock):
        """The radio streams meter values to the UDP port we registered. If it has accepted our
        meter packets, our own meters come back here - the proof that the radio sees them."""
        sock.settimeout(0.5)
        while not self.emu.stop.is_set() and self.udp is sock:
            try:
                d, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            self.rx_total += 1
            if len(d) < 32 or (struct.unpack(">I", d[12:16])[0] & 0xFFFF) != METER_PACKET_CLASS:
                continue
            if not self.rx_sample:
                self.rx_sample = d[:44].hex(" ")
            ours = {m[1]: m[0] for m in self.meters}
            if not ours:
                continue
            for i in range(28, len(d) - 3, 4):
                mid, raw = struct.unpack(">Hh", d[i:i + 4])
                if mid in ours:
                    self.rx_vals[ours[mid]] = raw
                    self.rx_count += 1

    def _slice_status(self, body):
        """'slice 0 RF_frequency=14.200000 tx=1 active=1 ...' (later lines carry only what changed)"""
        m = re.match(r"slice\s+(\d+)\s*(.*)$", body)
        if not m:
            return
        n, kv = int(m.group(1)), parse_kv(m.group(2))
        sl = self.slices.setdefault(n, {"mhz": 0.0, "tx": False, "active": False})
        try:
            if "RF_frequency" in kv:
                sl["mhz"] = float(kv["RF_frequency"])
            if "tx" in kv:
                sl["tx"] = kv["tx"] == "1"
            if "active" in kv:
                sl["active"] = kv["active"] == "1"
            if kv.get("in_use") == "0":
                self.slices.pop(n, None)
        except ValueError:
            return
        self._follow_frequency()

    def _follow_frequency(self):
        b = self.emu.b
        if getattr(b, "tci_ok", False) or getattr(self.emu.a, "flex_no_follow_freq", False):
            return                                     # Thetis / TCI already supplies the frequency
        live = [(n, v) for n, v in sorted(self.slices.items()) if v["mhz"] > 0]
        if not live:
            return
        pick = ([x for x in live if x[1]["tx"]] or [x for x in live if x[1]["active"]] or live)[0][1]
        hz = int(round(pick["mhz"] * 1e6))
        if hz != self.follow_hz:
            self.follow_hz = hz
            self.emu.log("FLEX radio: transmit slice is on %.6f MHz - passing it to the amp" % pick["mhz"])
            b.freq_hz[0] = hz
            b.update_freq()

    def _meter_status(self, body):
        """'meter 49.src=AMP#49.num=0x..#49.nam=FWD#...' -> if these are our meters, use the
        numbers the radio lists (they can differ from the numbers in its replies)."""
        items = {}
        for part in body[len("meter "):].split("#"):
            m = re.match(r"(\d+)\.(\w+)=(.*)$", part.strip())
            if m:
                items.setdefault(int(m.group(1)), {})[m.group(2)] = m.group(3)
        mine = set(n for n, _, _ in self.meters)
        ok_nums = set(x.lower() for x in (self.handles.get(PGXL_MODEL, ""), "0x" + self.radio_handle) if x)
        for mid, kv in items.items():
            if kv.get("src") != "AMP" or kv.get("nam") not in mine:
                continue
            if ok_nums and kv.get("num", "").lower() not in ok_nums:
                continue
            for m in self.meters:
                if m[0] == kv["nam"] and m[1] != mid:
                    self.emu.log("FLEX radio: meter %s is number %d on the radio (not %d) - using %d"
                                 % (m[0], mid, m[1], mid))
                    m[1] = mid

    # ---- running ------------------------------------------------------
    def _pick_variant(self):
        """If the radio never echoes our meters, try the next way of building the packet; once it
        does, keep the one that worked."""
        if self.var_locked:
            return
        if self.rx_count > self.var_n:
            self.var_locked = True
            self.emu.log("FLEX meters: the radio accepted packet style %d - keeping it" % self.variant)
            return
        if time.time() - self.var_t > 12:
            self.variant = (self.variant + 1) % len(METER_VARIANTS)
            self.var_t, self.var_n, self.tx_sample = time.time(), self.rx_count, ""
            self.emu.log("FLEX meters: no echo from the radio - trying packet style %d: %s"
                         % (self.variant, METER_VARIANTS[self.variant]))

    def _send_meters(self, snap):
        if self.role != "PGXL":
            return              # one packet from the amp's link carries the tuner's meters too
        self._pick_variant()
        if self.emu.verbose and time.time() - getattr(self, "_mlog", 0) > 10:
            self._mlog = time.time()
            self.emu.log("FLEX meters being sent: " + "  ".join(
                "%s(#%d)=%d" % (n, i, meter_raw(n, snap)) for n, i, _ in self.meters)
                + "   [amp temp=%s]" % snap["temp"])
            self.emu.log("FLEX UDP: radio sent %d packets of any kind to our port %s; we sent %d to %s:%d"
                         % (self.rx_total, getattr(self, "udp_port", "?"), self.meter_sent,
                            self.radio_ip, self.emu.meter_port))
            if self.tx_sample:
                self.emu.log("FLEX UDP sample, ours : " + self.tx_sample)
            if self.rx_sample:
                self.emu.log("FLEX UDP sample, radio: " + self.rx_sample)
            self.emu.log("FLEX radio meter stream back to us: %s" % (
                ("%d values, latest %s" % (self.rx_count, self.rx_vals)) if self.rx_count else
                "NOTHING yet (the radio is not showing our meter values)"))
        by_stream = {}
        one_packet = METER_VARIANTS[self.variant].get("stream") == "amp"
        mine = list(self.meters)
        if one_packet and self.role == "PGXL" and self.emu.link_t:
            mine += list(self.emu.link_t.meters)      # the tuner's meters ride in the same packet
        for name, mid, stream in mine:
            by_stream.setdefault(0 if one_packet else stream, []).append((mid, meter_raw(name, snap)))
        jobs = []
        for stream, pairs in by_stream.items():
            if METER_VARIANTS[self.variant].get("split"):
                jobs += [(stream, [pr]) for pr in pairs]
            else:
                jobs.append((stream, pairs))
        for stream, pairs in jobs:
            self.pkt_count = (self.pkt_count + 1) & 0xF
            try:
                v = METER_VARIANTS[self.variant]
                st = {"meter": stream, "handle": int(self.radio_handle, 16) if self.radio_handle else stream,
                      "zero": 0, "amp": AMP_METER_STREAM_ID}[v["stream"]]
                pkt = build_meter_packet(st, pairs, self.pkt_count, **v)
                if not self.tx_sample:
                    self.tx_sample = pkt[:44].hex(" ")
                self._tx_socket(v).sendto(pkt, (self.radio_ip, v.get("port", self.emu.meter_port)))
                self.meter_sent += 1
            except OSError:
                pass

    def _tx_socket(self, variant):
        """The socket meter packets are sent from: the one we registered with the radio, or (like the
        working bridge seen on the wire) a separate socket with its own random port."""
        if variant.get("sock") != "own":
            return self.udp
        if getattr(self, "udp_tx", None) is None:
            self.udp_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_tx.bind(("", 0))
            self.emu.log("FLEX meters: sending from separate UDP port %d" % self.udp_tx.getsockname()[1])
        return self.udp_tx

    def _interlock_tick(self, snap):
        if self.il_id is None:
            return
        want = "enabled" if (snap["ok"] and snap["operate"] and not snap["fault"]) else "disabled"
        if want != self.il_mode:
            self.cmd("interlock %s %s" % ("enable" if want == "enabled" else "disable", self.il_id), 1.0)
            self.il_mode = want

    def _set_rfpower(self, pct):
        """over-drive protection: put the radio's RF power setting back (0-100)"""
        code, msg = self.cmd("transmit set rfpower=%d" % pct, 2.0)
        if code == 0:
            self.rfpower = pct
        else:
            self.emu.log("FLEX radio: RF power could not be set (code %s %s)" % (code, msg))

    def _answer_ptt(self, snap):
        if self.il_id is not None and self.il_mode == "enabled":
            self.cmd("interlock ready %s" % self.il_id, 1.0)

    def _goodbye(self):
        try:
            if self.il_id is not None:
                self.cmd("interlock remove %s" % self.il_id, 1.0)
        except (OSError, ConnectionError):
            pass


def discover_radio(timeout, stop):
    """Listen for a FlexRadio's broadcast and return its address (or '')."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT") and os.name != "nt":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        s.bind(("", 4992))
        s.settimeout(0.5)
        end = time.time() + timeout
        while time.time() < end and not stop.is_set():
            try:
                d, _ = s.recvfrom(4096)
            except socket.timeout:
                continue
            text = d.decode("ascii", "ignore")
            m = re.search(r"\bip=(\d+\.\d+\.\d+\.\d+)", text)
            if m:
                return m.group(1)
    except OSError:
        return ""
    finally:
        s.close()
    return ""


# --------------------------------------------------------------------------
# the emulation itself
# --------------------------------------------------------------------------
class FlexEmulation:
    def __init__(self, bridge, a, log=None, bind_ip="0.0.0.0"):
        self.b = bridge
        self.a = a
        self._log = log or (lambda *x, **k: None)
        self.stop = bridge.stop
        self.bind_ip = bind_ip
        self.verbose = bool(getattr(a, "flex_verbose", False))
        self.serial = re.sub(r"\s+", "", getattr(a, "flex_serial", "") or "KPA1500-0001")[:60]
        self.serial_t = self.serial + "-T"
        self.nickname = re.sub(r"\s+", "_", getattr(a, "flex_nickname", "") or "KPA1500")[:24]
        self.radio_ip = (getattr(a, "flex_radio_ip", "") or "").strip()
        self.radio_ip_found = ""
        self.radio_fallback = (getattr(a, "flex_radio_fallback_ip", "") or "").strip()
        self.radio_port = int(getattr(a, "flex_radio_port", 4992))
        self.meter_port = int(getattr(a, "flex_meter_port", 4991))
        self.tuner = not getattr(a, "flex_no_tuner", False)
        self.meters_on = not getattr(a, "flex_no_meters", False)
        self.interlock = bool(getattr(a, "flex_interlock", False))
        self.discovery_on = not getattr(a, "flex_no_discovery", False)
        self.allow = set(x.strip() for x in (getattr(a, "flex_allow", "") or "").split(",") if x.strip())
        self.adv_ip = (getattr(a, "flex_ip", "") or "").strip()
        self.unknown = []
        self.last_control = ""
        self._ctl_t = {}
        # the tuner applet has two separate switches: OPERATE/STANDBY and BYPASS (green = operate,
        # amber = bypass, grey = standby). The KPA1500 only has ATU in / ATU bypassed, so:
        #   standby -> ATU bypassed, tuning refused;  operate -> ATU as the BYPASS switch says
        self.tuner_operate = True
        self.tuner_bypass = False
        self._tuner_cmd_t = 0.0
        self._tune_t = 0.0
        self._ctl_lock = threading.Lock()
        self.pgxl = DeviceServer(self, "PGXL", int(getattr(a, "flex_pgxl_port", 9008)),
                                 "V" + PGXL_FIRMWARE, self.pgxl_command)
        self.tgxl = DeviceServer(self, "TGXL", int(getattr(a, "flex_tgxl_port", 9010)),
                                 "V" + TGXL_FIRMWARE, self.tgxl_command)
        self.link = FlexRadioLink(self, "PGXL") if self.radio_ip else None
        self.link_t = FlexRadioLink(self, "TGXL") if (self.radio_ip and self.tuner) else None
        self.started = False
        self.errors = []

    # ---- plumbing -----------------------------------------------------
    def log(self, msg, verbose=False):
        if verbose and not self.verbose:
            return
        try:
            self._log(msg)
        except TypeError:
            self._log(msg)

    def note_unknown(self, text):
        self.unknown = (self.unknown + [time.strftime("%H:%M:%S ") + text])[-20:]
        self.log("FLEX UNKNOWN MESSAGE - please keep this line: " + text)

    def start(self):
        if not self.adv_ip:
            target = self.radio_ip if re.match(r"\d+\.\d+\.\d+\.\d+$", self.radio_ip) else self.b.amp.addr[0]
            self.adv_ip = local_ip_towards(target) or "127.0.0.1"
        for srv in ([self.pgxl] + ([self.tgxl] if self.tuner else [])):
            try:
                srv.open()
                srv.start()
            except OSError as e:
                srv.error = str(e)
                self.errors.append("%s port %d: %s" % (srv.label, srv.port, e))
                self.log("FLEX %s: cannot listen on port %d (%s). Is another program using it?"
                         % (srv.label, srv.port, e))
        threading.Thread(target=self._push_loop, daemon=True, name="flex-push").start()
        if self.discovery_on:
            threading.Thread(target=self._discovery_loop, daemon=True, name="flex-disc").start()
        if self.link:
            self.link.start()
        if self.link_t:
            self.link_t.start()
        self.started = True

    # ---- the live readings -------------------------------------------
    def snapshot(self):
        b = self.b
        try:
            drive = float(b.drive_info()[0])
        except Exception:
            drive = 0.0
        khz = getattr(b, "amp_khz", None) or getattr(b, "want_khz", None)
        return {"ok": bool(b.amp_ok), "operate": b.mode == 1, "tx": bool(b.transmitting()),
                "fwd": float(b.fwd or 0), "refl": float(b.refl or 0),
                "swr": float(b.swr or 1.0), "drive": drive, "temp": b.temp,
                "volts": b.volts, "amps": b.amps, "atu": b.atu,
                "tuning": bool(b.atu_tuning),
                "relays": self._relays(b), "fault": b.fault or 0, "ant": b.ant,
                "khz": khz}

    @staticmethod
    def pgxl_state(s):
        if not s["ok"]:
            return "STANDBY"
        if s["operate"]:
            return "TRANSMIT_A" if s["tx"] else "IDLE"
        return "STANDBY"

    def pgxl_status_body(self, s):
        rl = swr_to_return_loss(s["swr"] if s["fwd"] > 0 else 1.0)
        parts = ["state=%s" % self.pgxl_state(s), "fanmode=STANDARD", "meffa=OFF",
                 "bandA=%s" % band_name(s["khz"]), "bandB=0",
                 "biasA=RADIO_AB", "biasB=RADIO_AB", "flexA=KPA1500", "flexB=",
                 "fwd=%.2f" % watts_to_dbm(s["fwd"]), "peakfwd=%.2f" % watts_to_dbm(s["fwd"]),
                 "swr=%.1f" % -rl]
        if s["amps"] is not None:
            parts.append("id=%.1f" % float(s["amps"]))
        if s["volts"] is not None:
            parts.append("vdd=%.1f" % float(s["volts"]))
        if s["temp"] is not None:
            parts.append("temp=%.1f" % float(s["temp"]))
            parts.append("hltemp=%.1f" % float(s["temp"]))     # real units also report a second heatsink
        return " ".join(parts)

    @staticmethod
    def _relays(b):
        """ATU relay bitmasks as the tuner applet's three bars: the amp has one capacitor bank and one
        inductor bank; the capacitor shows as C1 on the transmitter side and as C2 on the antenna side."""
        c, l = getattr(b, "atu_c", None) or 0, getattr(b, "atu_l", None) or 0
        side = getattr(b, "atu_side", None)
        return (c, l, 0) if side != "A" else (0, l, c)

    def tgxl_status_body(self, s):
        bypass = 1 if s["atu"] == "B" else 0
        ptt = 1 if (s["tx"] and s["ok"]) else 0
        rl = swr_to_return_loss(s["swr"] if s["fwd"] > 0 else 1.0)
        return ("fwd=%.2f peak=%.2f max=62.43 swr=%.4f pttA=%d bandA=%s modeA=1 flexA=KPA1500 "
                "freqA=%.3f bypassA=%d bypassRxA=0 antA=0 pttB=0 bandB=0 modeB=0 flexB= freqB=0.000 "
                "bypassB=0 bypassRxB=0 antB=0 state=%d active=1 tuning=%d bypass=%d ag=0 "
                "relayC1=%d relayL=%d relayC2=%d"
                % (watts_to_dbm(s["fwd"]), watts_to_dbm(s["fwd"]), -rl, ptt,
                   band_name(s["khz"]), (s["khz"] or 0) / 1000.0, bypass,
                   1 if (s["ok"] and self.tuner_operate) else 0,
                   1 if s["tuning"] else 0, bypass, s["relays"][0], s["relays"][1], s["relays"][2]))

    # ---- who may do what ---------------------------------------------
    def read_allowed(self, ip):
        try:
            a = ipaddress.ip_address(ip.split("%")[0])
        except ValueError:
            return False
        return a.is_private or a.is_loopback or a.is_link_local

    def control_allowed(self, ip):
        radio = self.radio_ip_found or (self.radio_ip if self.radio_ip.lower() != "auto" else "")
        return ip in ("127.0.0.1", "::1", self.adv_ip) or (radio and ip == radio) or ip in self.allow

    def _do(self, action, ip):
        """Run one bridge action for a network client. Returns (ok, text)."""
        if not self.control_allowed(ip):
            self.note_unknown("control from %s refused (not the radio, this PC or --flex-allow)" % ip)
            return False, "not allowed"
        with self._ctl_lock:
            now = time.time()
            if now - self._ctl_t.get(action, 0.0) < 0.5:
                return True, "repeat ignored"
            self._ctl_t[action] = now
        ok, msg = self.b.do_action(action)
        self.last_control = "%s %s from %s: %s" % (time.strftime("%H:%M:%S"), action, ip, msg)
        self.log("FLEX control: %s from %s -> %s" % (action, ip, msg))
        return ok, msg

    # ---- PGXL commands ------------------------------------------------
    @staticmethod
    def parse_operate(lc):
        m = re.search(r"\boperate\s*=\s*(1|0|true|false|on|off)\b", lc)
        if m:
            return m.group(1) in ("1", "true", "on")
        m = re.search(r"\b(?:mode|state)\s*=\s*(operate|standby)\b", lc)
        if m:
            return m.group(1) == "operate"
        if lc in ("operate", "standby"):
            return lc == "operate"
        return None

    def pgxl_command(self, seq, cmd, ip):
        lc = cmd.strip().lower()
        word = lc.split(None, 1)[0] if lc else ""
        R = lambda code, body="": "R%d|%s|%s" % (seq, code, body)
        s = self.snapshot()
        if word == "info":
            return [R("0", "serial=%s  version=%s protocol=1.0 mains=240" % (self.serial, PGXL_FIRMWARE))]
        if word == "status":
            return [R("0", self.pgxl_status_body(s))]
        if lc in ("setup read", "setup"):
            return [R("0", "nickname=%s ledintens=141 txdelay=16 inactivity-timeout=0 authcode=" % self.nickname)]
        if word in ("ping", "keepalive", "sub", "unsub", "auth"):
            return [R("0")]
        if re.match(r"(ifconf|catradio|flexradio)\s+read", lc):
            return [R("0", "")]
        op = self.parse_operate(lc)
        if op is not None:
            if op and not s["ok"]:
                return [R("50000013")]
            ok, _ = self._do("operate" if op else "standby", ip)
            return [R("0" if ok else "50000013")]
        if word in ("setup", "save", "ifconf", "catradio", "flexradio"):
            self.note_unknown("PGXL %s asked to change settings: %r (refused)" % (ip, cmd))
            return [R("50000013")]
        self.note_unknown("PGXL %s sent: %r" % (ip, cmd))
        return [R("50000015")]

    # ---- TGXL commands ------------------------------------------------
    @staticmethod
    def parse_tuner(lc):
        """-> 'atu_inline', 'atu_bypass', 'atu_tune' or None"""
        if re.match(r"(tgxl\s+)?autotune\b", lc):
            return "atu_tune"
        m = re.search(r"\bbypass\s*=\s*(1|0|true|false|on|off)\b", lc)
        if m:
            return "atu_bypass" if m.group(1) in ("1", "true", "on") else "atu_inline"
        m = re.search(r"\b(?:mode|operate)\s*=\s*(1|0|true|false|on|off)\b", lc)
        if m:
            return "atu_inline" if m.group(1) in ("1", "true", "on") else "atu_bypass"
        if lc in ("operate",):
            return "atu_inline"
        if lc in ("standby", "bypass"):
            return "atu_bypass"
        return None

    @staticmethod
    def parse_tuner_set(lc):
        """SmartSDR's own forms 'operate set=1' and 'bypass set=0' -> ('operate'|'bypass', True|False)"""
        m = re.match(r"(operate|bypass)\s+set\s*=\s*(1|0|true|false|on|off)\b", lc)
        if m:
            return m.group(1), m.group(2) in ("1", "true", "on")
        return None

    def _tuner_set(self, kind, on, ip, s):
        """Apply the OPERATE or BYPASS switch of the tuner applet. Returns True when it worked."""
        old = (self.tuner_operate, self.tuner_bypass)
        self._tuner_cmd_t = time.time()
        if kind == "operate":
            self.tuner_operate = on
            want_bypass = True if not on else self.tuner_bypass
        else:
            self.tuner_bypass = on
            if not self.tuner_operate:
                return True              # standby: remember the choice, the ATU stays out
            want_bypass = on
        if want_bypass == (s["atu"] == "B"):
            return True                  # the ATU is already where it should be
        ok, _ = self._do("atu_bypass" if want_bypass else "atu_inline", ip)
        if not ok:
            self.tuner_operate, self.tuner_bypass = old      # for example refused under RF
        return ok

    def tgxl_command(self, seq, cmd, ip):
        lc = cmd.strip().lower()
        word = lc.split(None, 1)[0] if lc else ""
        R = lambda code, body="": "R%d|%s|%s" % (seq, code, body)
        s = self.snapshot()
        if word == "info":
            return [R("0", "serial=%s version=%s protocol=1.0 model=%s" % (self.serial_t, TGXL_FIRMWARE, TGXL_MODEL))]
        if word == "status":
            return ["S%d|status %s" % (seq, self.tgxl_status_body(s))]
        if word in ("ping", "keepalive", "sub", "unsub", "auth"):
            return [R("0")]
        if lc.startswith("tune"):
            self.note_unknown("TGXL %s asked for manual relay change %r (the KPA1500 ATU has none; refused)" % (ip, cmd))
            return [R("50000013")]
        ts = self.parse_tuner_set(lc)
        if ts:
            if not s["ok"]:
                return [R("50000013")]
            return [R("0" if self._tuner_set(ts[0], ts[1], ip, s) else "50000013")]
        act = self.parse_tuner(lc)
        if act:
            if not s["ok"]:
                return [R("50000013")]
            if act == "atu_tune":
                if not self.tuner_operate:
                    return [R("50000013")]             # tuner in STANDBY: no tuning
                # SmartSDR repeats 'autotune' several times a second after one click; start the
                # amp's tune only once, and not again while it is already tuning
                now = time.time()
                gap = now - self._tune_t          # time since the previous 'autotune' arrived
                self._tune_t = now
                if gap < 1.5:
                    return [R("0")]               # still the same click repeating: ignore
                if s["tuning"]:
                    act = "atu_cancel"            # a new press while tuning stops it, like the front-panel key
            ok, _ = self._do(act, ip)
            return [R("0" if ok else "50000013")]
        self.note_unknown("TGXL %s sent: %r" % (ip, cmd))
        return [R("50000015")]

    # ---- background loops --------------------------------------------
    def _push_loop(self):
        last_p = last_t = None
        while not self.stop.is_set():
            s = self.snapshot()
            sig_p = self.pgxl_state(s)
            if (self.tuner_operate and s["ok"] and s["atu"] in ("I", "B")
                    and time.time() - self._tuner_cmd_t > 3.0):
                self.tuner_bypass = (s["atu"] == "B")       # follow the front panel / bridge panel
            sig_t = (s["atu"], s["tuning"], s["ok"], self.tuner_operate, s["relays"])
            if sig_p != last_p:
                last_p = sig_p
                self.pgxl.broadcast("S0|state=%s fanmode=STANDARD meffa=OFF\n" % sig_p)
            if sig_t != last_t:
                last_t = sig_t
                self.tgxl.broadcast("S0|state state=%d tuning=%d bypass=%d relayC1=%d relayL=%d relayC2=%d\n"
                                    % ((1 if (s["ok"] and self.tuner_operate) else 0,
                                        1 if s["tuning"] else 0, 1 if s["atu"] == "B" else 0)
                                       + tuple(s["relays"])))
            self.stop.wait(0.25)

    def _discovery_loop(self):
        try:
            net = ipaddress.ip_network(self.adv_ip + "/24", strict=False)
            bcast = str(net.broadcast_address)
        except ValueError:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while not self.stop.is_set():
            try:
                s.sendto(("%s ip=%s v=%s serial=%s nickname=%s" % (
                    PGXL_MODEL, self.adv_ip, PGXL_FIRMWARE, self.serial, self.nickname)).encode(),
                    (bcast, self.pgxl.port if self.pgxl.port else 9008))
                if self.tuner:
                    s.sendto(("%s ip=%s v=%s serial=%s nickname=%s" % (
                        TGXL_MODEL, self.adv_ip, TGXL_FIRMWARE, self.serial_t, self.nickname)).encode(),
                        (bcast, self.tgxl.port if self.tgxl.port else 9010))
            except OSError:
                pass
            self.stop.wait(3.0)
        s.close()

    # ---- what the panel shows ----------------------------------------
    def status(self):
        L = self.link
        return {
            "version": FLEX_EMU_VERSION, "ip": self.adv_ip,
            "pgxl_port": self.pgxl.port, "pgxl_clients": self.pgxl.count(),
            "tgxl_port": self.tgxl.port if self.tuner else None,
            "tgxl_clients": self.tgxl.count() if self.tuner else 0,
            "errors": list(self.errors), "unknown": list(self.unknown),
            "last_control": self.last_control, "interlock": self.interlock,
            "tuner_login": ({"state": self.link_t.state, "error": self.link_t.error,
                             "registered": dict(self.link_t.reg)} if self.link_t else None),
            "radio": ({"ip": L.radio_ip or self.radio_ip, "state": L.state, "error": L.error,
                       "version": L.version, "info": dict(L.radio_info), "registered": dict(L.reg),
                       "handles": dict(L.handles), "meters": len(L.meters),
                       "meter_packets": L.meter_sent, "radio_sees": dict(L.radio_status)}
                      if L else None),
        }

    def summary(self):
        """one short line for the bridge window"""
        parts = ["PGXL:%d" % self.pgxl.port]
        if self.tuner:
            parts.append("TGXL:%d" % self.tgxl.port)
        if self.link:
            parts.append("radio:%s" % self.link.state)
        return "FLEX " + " ".join(parts)


STATUS_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>FlexRadio emulation</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:Segoe UI,Arial,sans-serif;margin:16px;max-width:760px;background:#fff;color:#111}
h1{font-size:20px}td{padding:3px 10px 3px 0;vertical-align:top}.k{color:#555}pre{background:#f3f3f3;padding:8px;white-space:pre-wrap}
@media(prefers-color-scheme:dark){body{background:#181818;color:#eee}pre{background:#262626}.k{color:#aaa}}</style></head>
<body><h1>FlexRadio PGXL / TGXL emulation</h1><div id="o">loading...</div>
<script>
function row(k,v){return '<tr><td class="k">'+k+'</td><td>'+v+'</td></tr>'}
function esc(s){return String(s).replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]})}
function go(){fetch('/api/state'+location.search).then(function(r){return r.json()}).then(function(s){
var f=s.flex,h='';
if(!f){document.getElementById('o').innerHTML='<p>Not switched on. Start the bridge with --flex-emulate (see the guide).</p>';return}
h+='<table>'+row('Address told to others',esc(f.ip))+row('PGXL (amplifier) port',f.pgxl_port+' &nbsp; clients: '+f.pgxl_clients)
 +row('TGXL (tuner) port',(f.tgxl_port||'off')+' &nbsp; clients: '+f.tgxl_clients);
if(f.radio){var r=f.radio;h+=row('FlexRadio',esc(r.ip)+' &nbsp; <b>'+esc(r.state)+'</b>'+(r.error?' ('+esc(r.error)+')':''))
 +(r.info&&Object.keys(r.info).length?row('Radio',esc([r.info.model,r.info.name,r.info.callsign,r.info.serial&&('serial '+r.info.serial),r.info.version&&('v'+r.info.version)].filter(Boolean).join(' - '))):'')
 +row('Amp login (PGXL)',esc(JSON.stringify(r.registered)))+(f.tuner_login?row('Tuner login (TGXL)','<b>'+esc(f.tuner_login.state)+'</b> '+esc(JSON.stringify(f.tuner_login.registered))):'')+row('Meters / packets sent',r.meters+' / '+r.meter_packets)
 +row('Radio shows',esc(JSON.stringify(r.radio_sees)))}
else h+=row('FlexRadio','login off (no --flex-radio-ip)');
h+=row('Interlock',f.interlock?'ON':'off')+row('Last control',esc(f.last_control||'-'))+'</table>';
if(f.errors.length)h+='<h3>Problems</h3><pre>'+esc(f.errors.join('\\n'))+'</pre>';
if(f.unknown.length)h+='<h3>Messages not understood (send these if something does not work)</h3><pre>'+esc(f.unknown.join('\\n'))+'</pre>';
document.getElementById('o').innerHTML=h}).catch(function(){document.getElementById('o').innerHTML='bridge not reachable'})}
go();setInterval(go,2000);
</script></body></html>"""


# --------------------------------------------------------------------------
# self-test (no radio, no amplifier needed)
# --------------------------------------------------------------------------
class _FakeBridge:
    def __init__(self):
        self.stop = threading.Event()
        self.amp_ok, self.mode = True, 1
        self.fwd = self.refl = self.pin = 0
        self.swr, self.temp, self.volts, self.amps = 1.0, 38, 51.9, 5
        self.atu, self.atu_tuning, self.fault, self.ant = "I", False, 0, 1
        self.amp_khz = self.want_khz = 14200
        self.actions = []
        self.amp = type("A", (), {"addr": ("127.0.0.1", 1500)})()
        self.freq_hz, self.tci_ok = {0: None, 1: None}, False
        self.atu_c, self.atu_l, self.atu_side = 0x2C, 0x0A, "A"

    def update_freq(self):
        self.want_khz = int(round(self.freq_hz[0] / 1000.0))

    def transmitting(self):
        return self.fwd > 5

    def drive_info(self):
        return float(self.pin), "amp"

    def do_action(self, name, params=None):
        self.actions.append(name)
        return True, "ok " + name


class _TClient:
    def __init__(self, port):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=3)
        self.buf = b""
        self.greeting = self.line()

    def line(self, t=3.0):
        end = time.time() + t
        while b"\n" not in self.buf:
            if time.time() > end:
                return None
            try:
                d = self.s.recv(4096)
            except socket.timeout:
                continue
            if not d:
                return None
            self.buf += d
        l, _, self.buf = self.buf.partition(b"\n")
        return l.decode()

    def ask(self, seq, cmd, skip_push=True):
        self.s.sendall(("C%d|%s\n" % (seq, cmd)).encode())
        while True:
            l = self.line()
            if l is None or not (skip_push and l.startswith("S0|")):
                return l

    def close(self):
        self.s.close()


class _FakeRadio(threading.Thread):
    """Just enough of a FlexRadio's TCP interface to test the login (one thread per connection)."""

    def __init__(self, reject_tuner_first=True, reject_tempc=True):
        super().__init__(daemon=True)
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(4)
        self.srv.settimeout(0.5)
        self.port = self.srv.getsockname()[1]
        self.cmds = []
        self.conns = []
        self.nconn = 0
        self.amp_creates = {}        # connection number -> models created on it
        self.stop = False
        self.reject_tuner_first, self.reject_tempc = reject_tuner_first, reject_tempc
        self.tuner_tries = 0
        self.meter_no = 26

    def push(self, text):
        for c in list(self.conns):
            try:
                c.sendall((text + "\n").encode())
            except OSError:
                pass

    def run(self):
        while not self.stop:
            try:
                c, _ = self.srv.accept()
            except socket.timeout:
                continue
            self.nconn += 1
            threading.Thread(target=self.handle, args=(c, self.nconn), daemon=True).start()

    def handle(self, c, num):
        self.conns.append(c)
        c.settimeout(0.3)
        c.sendall(("V1.4.0.0\nH%08X\n" % (0x1A2B3C00 + num)).encode())
        buf = b""
        while not self.stop:
            try:
                d = c.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not d:
                break
            buf += d
            while b"\n" in buf:
                l, _, buf = buf.partition(b"\n")
                m = re.match(r"C(\d+)\|(.*)", l.decode())
                if not m:
                    continue
                n, cmd = m.group(1), m.group(2)
                self.cmds.append(cmd)
                if cmd.startswith("amplifier create"):
                    self.amp_creates.setdefault(num, []).append(parse_kv(cmd).get("model"))
                try:
                    c.sendall(self.reply(n, cmd).encode())
                except OSError:
                    return

    def reply(self, n, cmd):
        if cmd.startswith("amplifier create"):
            if "TunerGeniusXL" in cmd:
                self.tuner_tries += 1
                if self.reject_tuner_first and self.tuner_tries == 1:
                    return "R%s|50000016|\n" % n
            kv = parse_kv(cmd)
            return "R%s|0|\nS1A2B3C4D|amplifier 0x7BFE73CC ip=%s model=%s serial_num=%s state=IDLE\n" % (
                n, kv.get("ip"), kv.get("model"), kv.get("serial_num"))
        if cmd.startswith("meter create"):
            if self.reject_tempc and ("units=TEMPC" in cmd or "units=DEGC" in cmd):
                return "R%s|500000A6|\n" % n
            self.meter_no += 1
            return "R%s|0|%d\n" % (n, self.meter_no)
        if cmd.startswith("interlock create"):
            return "R%s|0|1\n" % n
        if cmd == "sub slice all":
            return ("R%s|0|\nS1A2B3C4D|slice 0 in_use=1 RF_frequency=7.150000 tx=0 active=0\n"
                    "S1A2B3C4D|slice 1 in_use=1 RF_frequency=14.205000 tx=1 active=1\n") % n
        if cmd == "info":
            return 'R%s|0|model=FLEX-6600,chassis_serial=1234-5678,name="Shack Flex",callsign=KW4EX,software_ver=3.9.1.2\n' % n
        return "R%s|0|\n" % n


def selftest(verbose=False):
    results = []

    def check(name, cond):
        results.append(bool(cond))
        print("  %-4s %s" % ("ok" if cond else "FAIL", name))

    def wait(f, t=5.0):
        end = time.time() + t
        while time.time() < end:
            if f():
                return True
            time.sleep(0.05)
        return False

    print("FlexRadio emulation self-test")
    # --- helpers
    check("dBm: 0 W floors at 30.0, 1500 W is about 61.8",
          watts_to_dbm(0) == 30.0 and abs(watts_to_dbm(1500) - 61.76) < 0.05)
    check("return loss: SWR 1.0 -> 60 dB, SWR 3.0 -> 6.0 dB",
          swr_to_return_loss(1.0) == 60.0 and abs(swr_to_return_loss(3.0) - 6.02) < 0.05)
    pk = build_meter_packet(0x88000000, [(27, 7000), (28, -5)], 3)
    d = parse_meter_packet(pk)
    check("meter packet round trip, laid out like a packet captured from the radio (0x3853xxxx, UTC time)",
          d["ptype"] == 3 and d["class_present"] and d["count"] == 3 and d["size"] == 9
          and d["stream"] == 0x88000000 and d["oui"] == 0x1C2D and d["info_class"] == 0x534C
          and d["packet_class"] == 0x8002 and d["pairs"] == [(27, 7000), (28, -5)]
          and len(pk) == 36 and pk[0] == 0x38 and pk[1] >> 4 == 0x5
          and struct.unpack(">I", pk[16:20])[0] > 1700000000)
    snap = {"fwd": 1000.0, "swr": 1.5, "drive": 50.0, "amps": 19.2, "temp": 44.1}
    check("meter scaling: FWD x128, ID x256, TEMP x64",
          meter_raw("FWD", snap) == int(round(60.0 * 128)) and meter_raw("ID", snap) == int(round(19.2 * 256))
          and meter_raw("TEMP", snap) == int(round(44.1 * 64)) and abs(meter_raw("DRV", snap) - 47.0 * 128) <= 2)

    # --- devices
    p = argparse.ArgumentParser()
    add_arguments(p)
    b = _FakeBridge()
    a = p.parse_args(["--flex-emulate", "--flex-pgxl-port", "0", "--flex-tgxl-port", "0",
                      "--flex-no-discovery", "--flex-ip", "192.168.0.50", "--flex-allow", "192.168.0.99"])
    emu = FlexEmulation(b, a, log=(print if verbose else None))
    emu.start()
    c = _TClient(emu.pgxl.port)
    check("PGXL greets with its version", c.greeting == "V" + PGXL_FIRMWARE)
    r = c.ask(1, "info")
    check("PGXL 'info' reply", r and r.startswith("R1|0|serial=KPA1500-0001"))
    r = c.ask(2, "status")
    kv = parse_kv(r.split("|", 2)[2]) if r else {}
    check("PGXL idle in OPERATE: state=IDLE, fwd floor 30.00 dBm, swr -60.0",
          kv.get("state") == "IDLE" and kv.get("fwd") == "30.00" and kv.get("swr") == "-60.0"
          and kv.get("id") == "5.0" and kv.get("vdd") == "51.9" and kv.get("temp") == "38.0")
    b.fwd, b.swr = 1200, 1.4
    kv = parse_kv(c.ask(3, "status").split("|", 2)[2])
    check("PGXL transmitting: TRANSMIT_A, fwd about 60.8 dBm, swr negative",
          kv.get("state") == "TRANSMIT_A" and abs(float(kv["fwd"]) - 60.79) < 0.05 and float(kv["swr"]) < 0)
    b.fwd = 0
    b.mode = 0
    kv = parse_kv(c.ask(4, "status").split("|", 2)[2])
    check("PGXL in STANDBY reports state=STANDBY", kv.get("state") == "STANDBY")
    check("PGXL 'setup read' reply", "nickname=KPA1500" in (c.ask(5, "setup read") or ""))
    r = c.ask(6, "operate=1")
    check("operate=1 from this PC is passed to the bridge", r == "R6|0|" and b.actions[-1:] == ["operate"])
    time.sleep(0.6)
    c.ask(7, "standby")
    check("'standby' is passed to the bridge", b.actions[-1:] == ["standby"])
    check("an unknown command is answered 50000015 and remembered",
          c.ask(8, "frobnicate") == "R8|50000015|" and any("frobnicate" in u for u in emu.unknown))
    check("settings changes are refused", c.ask(9, "setup nickname=x") == "R9|50000013|")
    n0 = len(b.actions)
    out = emu.pgxl_command(10, "operate=0", "10.9.9.9")
    check("control from an unknown computer is refused and nothing is sent to the bridge",
          out == ["R10|50000013|"] and len(b.actions) == n0)
    check("control from --flex-allow computer works", emu.control_allowed("192.168.0.99")
          and not emu.control_allowed("192.168.0.77"))
    check("a public internet address may not even connect", not emu.read_allowed("8.8.8.8")
          and emu.read_allowed("192.168.1.5"))
    b.mode = 1
    b.amp_ok = False
    check("operate while the amp is off is refused", emu.pgxl_command(11, "operate=1", "127.0.0.1") == ["R11|50000013|"])
    b.amp_ok = True
    c.close()

    t = _TClient(emu.tgxl.port)
    check("TGXL greets with its version", t.greeting == "V" + TGXL_FIRMWARE)
    st = t.ask(1, "status")
    check("TGXL status: S-line with status fields, bypass=0, tuning=0",
          st and st.startswith("S1|status ") and "bypass=0" in st and "tuning=0" in st and "state=1" in st)
    b.atu = "B"
    check("ATU bypass shows as bypass=1", "bypass=1" in t.ask(2, "status"))
    n0 = len(b.actions)
    time.sleep(0.6)
    t.ask(3, "bypass=0")
    time.sleep(0.6)
    t.ask(4, "autotune")
    time.sleep(0.6)
    t.ask(5, "tgxl set handle=0x1 mode=0")
    check("tuner commands map to ATU inline / tune / bypass",
          b.actions[n0:] == ["atu_inline", "atu_tune", "atu_bypass"])
    check("tuner status carries the ATU relays (capacitor on the antenna side -> C2)",
          "relayC1=0 relayL=10 relayC2=44" in t.ask(30, "status"))
    check("manual relay change is refused", t.ask(6, "tune relay=1 move=1") == "R6|50000013|")
    # --- SmartSDR's own forms: 'bypass set=N' and 'operate set=N', repeated 'autotune'
    b.atu = "I"
    time.sleep(3.2)
    tun = t.ask(7, "bypass set=1")
    time.sleep(0.6)
    n0 = len(b.actions)
    check("'bypass set=1' is accepted and sends ATU bypass", tun == "R7|0|" and b.actions[-1:] == ["atu_bypass"])
    b.atu = "B"
    time.sleep(0.6)
    n0 = len(b.actions)
    check("'operate set=0' (standby) is accepted", t.ask(8, "operate set=0") == "R8|0|")
    check("standby status shows state=0", "state=0" in t.ask(9, "status"))
    check("autotune is refused in standby", t.ask(10, "autotune") == "R10|50000013|")
    time.sleep(0.6)
    check("'operate set=1' puts the tuner back to operate", t.ask(11, "operate set=1") == "R11|0|")
    check("operate status shows state=1", "state=1" in t.ask(12, "status"))
    time.sleep(0.6)
    n0 = len(b.actions)
    t.ask(13, "bypass set=0")
    time.sleep(0.6)
    n1 = len(b.actions)
    for i in range(14, 19):
        t.ask(i, "autotune")
    check("a burst of autotune starts the tune only once",
          b.actions[n1:].count("atu_tune") == 1)
    b.atu_tuning = True
    time.sleep(1.7)
    n2 = len(b.actions)
    t.ask(20, "autotune")
    check("a new press while tuning cancels the tune", b.actions[n2:] == ["atu_cancel"])
    t.close()

    # --- radio login
    fr = _FakeRadio()
    fr.start()
    um = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    um.bind(("127.0.0.1", 0))
    um.settimeout(0.5)
    b2 = _FakeBridge()
    b2.fwd, b2.swr, b2.pin, b2.amps, b2.temp = 800, 1.2, 40, 18.0, 44.0
    a2 = p.parse_args(["--flex-radio-ip", "127.0.0.1", "--flex-radio-port", str(fr.port),
                       "--flex-meter-port", str(um.getsockname()[1]), "--flex-pgxl-port", "0",
                       "--flex-tgxl-port", "0", "--flex-no-discovery", "--flex-ip", "127.0.0.1",
                       "--flex-interlock"])
    emu2 = FlexEmulation(b2, a2, log=(print if verbose else None))
    emu2.start()
    check("login: registered with the radio", wait(lambda: emu2.link.state == "registered"))
    creates = [x for x in fr.cmds if x.startswith("amplifier create")]
    wait(lambda: emu2.link_t.state == "registered")
    check("login: keepalive first; amp and tuner each log in on their OWN connection (the radio keeps one amplifier per connection)",
          fr.cmds and fr.cmds[0] == "keepalive enable" and fr.nconn == 2
          and sorted(map(tuple, fr.amp_creates.values())) == [("PowerGeniusXL",), ("TunerGeniusXL", "TunerGeniusXL")])
    check("login: tuner retried in the alternate form after a refusal",
          len(creates) == 3 and any("ant=ANT1:PORTA,ANT2:PORTB" in x and "TunerGeniusXL" in x for x in creates)
          and emu2.link_t.reg.get("TGXL", "").startswith("ok (alternate"))
    mc = [x for x in fr.cmds if x.startswith("meter create")]
    check("login: subscribed to amplifier and meter status, five meters created from the radio's plain-number reply",
          "sub amplifier all" in fr.cmds and "sub meter all" in fr.cmds
          and len(emu2.link.meters) == 5 and all(m[2] == METER_STREAM_ID for m in emu2.link.meters)
          and any("units=TEMP_C" in x for x in mc)
          and any("name=FWD type=AMP min=30.0 max=63.0 units=DBM" in x for x in mc))
    check("login: interlock created", any(x.startswith("interlock create type=AMP") for x in fr.cmds)
          and emu2.link.il_id == "1")
    got = None
    end = time.time() + 5
    while time.time() < end and got is None:
        try:
            d, _ = um.recvfrom(2048)
            got = parse_meter_packet(d)
        except socket.timeout:
            pass
    ok = got is not None
    if ok:
        vals = dict(got["pairs"])
        ids = {n: m for n, m, s in emu2.link.meters}
        ids = ids
        ok = (got["stream"] == AMP_METER_STREAM_ID and got["size"] == 4 + len(got["pairs"])
              and abs(vals[ids["FWD"]] / 128.0 - watts_to_dbm(800)) < 0.01
              and abs(vals[ids["ID"]] / 256.0 - 18.0) < 0.01 and abs(vals[ids["TEMP"]] / 64.0 - 44.0) < 0.02
              and abs(vals[ids["DRV"]] / 128.0 - watts_to_dbm(40, 10, 50)) < 0.01)
    check("login: meter packets arrive with the right stream, ids and scaled values", ok)
    # the tuner's RL and FWD meters are created on the tuner's own connection and ride in the same packet
    tm = emu2.link_t
    wait(lambda: tm is not None and len(tm.meters) == 2, 5)
    got7 = None
    end = time.time() + 5
    while time.time() < end and got7 is None:
        try:
            d, _ = um.recvfrom(2048)
            g = parse_meter_packet(d)
            if g and len(g["pairs"]) == 7:
                got7 = g
        except socket.timeout:
            pass
    check("login: tuner creates RL and FWD meters, sent together with the amp's five in one packet",
          tm is not None and [m[0] for m in tm.meters] == ["RL", "FWD"] and got7 is not None
          and all(m[1] in dict(got7["pairs"]) for m in tm.meters)
          and any("name=RL type=AMP min=0.35 max=60.0 units=DB" in x for x in fr.cmds))
    # the radio streams our meters back to the UDP port we registered -> the link notices
    wait(lambda: "client udpport %d" % emu2.link.udp_port in fr.cmds, 3)
    um2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pk2 = build_meter_packet(0x700, [(emu2.link.meters[4][1], 1728)], 1)
    um2.sendto(pk2, ("127.0.0.1", emu2.link.udp_port))
    check("login: registers its UDP port and recognises its own meters coming back from the radio",
          wait(lambda: emu2.link.rx_vals.get("TEMP") == 1728))
    fr.push("S0|meter 90.src=AMP#90.num=0x7BFE73CC#90.nam=FWD#90.low=30.0#90.hi=63.0#90.unit=dBm#90.fps=0#"
            "91.src=AMP#91.num=0xDEADBEEF#91.nam=RL#91.low=0.4#91.hi=60.0#91.unit=dB#91.fps=0#")
    check("login: meter numbers listed by the radio replace the ones from its replies (only for our amp)",
          wait(lambda: {m[0]: m[1] for m in emu2.link.meters}.get("FWD") == 90)
          and {m[0]: m[1] for m in emu2.link.meters}.get("RL") != 91)
    check("login: the radio's own name, model and serial are read for the display",
          emu2.link.radio_info == {"model": "FLEX-6600", "name": "Shack Flex", "serial": "1234-5678",
                                  "version": "3.9.1.2", "callsign": "KW4EX"}
          and emu2.status()["radio"]["info"]["model"] == "FLEX-6600")
    check("login: the transmit slice's frequency is handed to the bridge (14.205 MHz)",
          wait(lambda: emu2.b.want_khz == 14205, 4) and "sub slice all" in fr.cmds)
    fr.push("S0|slice 1 RF_frequency=14.074000")
    check("login: a tuning change (partial slice line) updates the frequency",
          wait(lambda: emu2.b.want_khz == 14074, 4))
    check("login: subscribes to the radio's transmit settings", "sub tx all" in fr.cmds)
    fr.push("S0|transmit rfpower=90 tunepower=10 max_power_level=100")
    check("login: the radio's RF power setting is read from its transmit status",
          wait(lambda: emu2.link.rfpower == 90 and emu2.link.tunepower == 10, 3))
    fr.push("S0|transmit tunepower=25")
    check("login: a partial transmit line changes only what it carries",
          wait(lambda: emu2.link.tunepower == 25, 3) and emu2.link.rfpower == 90)
    emu2.link.todo.append(("rfpower", 80))
    check("login: asking for a lower RF power sends 'transmit set rfpower=80'",
          wait(lambda: "transmit set rfpower=80" in fr.cmds, 3) and wait(lambda: emu2.link.rfpower == 80, 3))
    emu2.b.tci_ok = True
    fr.push("S0|slice 1 RF_frequency=21.200000")
    time.sleep(0.5)
    check("login: with Thetis/TCI connected the radio's frequency is not used", emu2.b.want_khz == 14074)
    emu2.b.tci_ok = False
    check("login: pings are sent", wait(lambda: "ping" in fr.cmds, 6))
    check("login: radio's status line for our PGXL is recorded",
          wait(lambda: "PowerGeniusXL" in emu2.link.radio_status))
    n0 = len(fr.cmds)
    fr.push("S00000000|interlock state=PTT_REQUESTED reason=AMP:PG-XL source=TUNE")
    check("interlock: PTT request answered 'ready' while amp is in OPERATE",
          wait(lambda: "interlock ready 1" in fr.cmds[n0:], 3))
    b2.mode = 0
    check("interlock: amp in STANDBY -> interlock disabled so the radio never waits for it",
          wait(lambda: "interlock disable 1" in fr.cmds, 3))
    n1 = len(fr.cmds)
    fr.push("S00000000|interlock state=PTT_REQUESTED reason=AMP:PG-XL source=TUNE")
    time.sleep(0.6)
    check("interlock: no 'ready' while disabled", "interlock ready 1" not in fr.cmds[n1:])
    b2.mode = 1
    check("interlock: back in OPERATE -> enabled again", wait(lambda: "interlock enable 1" in fr.cmds, 3))
    s = emu2.status()
    check("status block for the panel", s["radio"]["state"] == "registered" and s["radio"]["meters"] == 5
          and s["radio"]["meter_packets"] > 0)
    b2.stop.set()
    check("clean shutdown removes the interlock", wait(lambda: any(x.startswith("interlock remove") for x in fr.cmds), 4))

    # --- login without interlock (the default) must never touch interlocks
    fr2 = _FakeRadio(False, False)
    fr2.start()
    b3 = _FakeBridge()
    a3 = p.parse_args(["--flex-radio-ip", "127.0.0.1", "--flex-radio-port", str(fr2.port),
                       "--flex-meter-port", "9", "--flex-pgxl-port", "0", "--flex-tgxl-port", "0",
                       "--flex-no-discovery", "--flex-ip", "127.0.0.1", "--flex-no-tuner"])
    emu3 = FlexEmulation(b3, a3, log=None)
    emu3.start()
    check("default login: registered, and NO interlock command is ever sent",
          wait(lambda: emu3.link.state == "registered") and not any("interlock" in x for x in fr2.cmds)
          and not any("TunerGeniusXL" in x for x in fr2.cmds))
    b3.stop.set()
    # auto + fallback: search finds nothing, so the direct address is used
    global discover_radio
    _orig = discover_radio
    discover_radio = lambda timeout, stop: ""
    fr3 = _FakeRadio(False, False)
    fr3.start()
    b4 = _FakeBridge()
    a4 = p.parse_args(["--flex-radio-ip", "auto", "--flex-radio-fallback-ip", "127.0.0.1",
                       "--flex-radio-port", str(fr3.port), "--flex-meter-port", "9",
                       "--flex-pgxl-port", "0", "--flex-tgxl-port", "0", "--flex-no-discovery",
                       "--flex-ip", "127.0.0.1", "--flex-no-tuner"])
    emu4 = FlexEmulation(b4, a4, log=None)
    emu4.start()
    check("auto finds nothing -> the fallback address is used and registers",
          wait(lambda: emu4.link.state == "registered") and emu4.link.radio_ip == "127.0.0.1")
    discover_radio = _orig
    b4.stop.set()
    fr3.stop = True
    fr.stop = fr2.stop = True
    b.stop.set()
    time.sleep(0.3)
    bad = results.count(False)
    print("\n%d checks, %d failed" % (len(results), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest(verbose="--verbose" in sys.argv))
