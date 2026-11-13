"""
gnss.py -- Minimal GNSS toolkit for AAE4203 Lab 1 (own-data SPP).

Implements, from scratch and with numpy only:
  * RINEX 3.0x observation / navigation readers (GPS, Galileo, BeiDou, GLONASS)
  * broadcast-ephemeris satellite position and clock (ICD-200 style)
  * Klobuchar ionosphere and Saastamoinen troposphere models
  * weighted least-squares single point positioning (SPP) with one
    receiver clock per constellation, elevation / C/N0 weighting,
    elevation and C/N0 masks and residual-based outlier rejection
  * UBX NAV-HPPOSECEF reader (receiver's own solution)
  * ECEF <-> geodetic / ENU helpers

Author: Group 18, AAE4203 2026/27.
"""

import struct
import numpy as np
from datetime import datetime, timedelta

C_LIGHT = 299792458.0
OMEGA_E = 7.2921151467e-5
MU = 3.986005e14
F_REL = -4.442807633e-10

GPS_EPOCH = datetime(1980, 1, 6)


# --------------------------------------------------------------------------
# time helpers
# --------------------------------------------------------------------------
def cal2tow(y, mo, d, h, mi, s):
    """Calendar (GPST) -> GPS time of week [s] and week number."""
    dt = datetime(int(y), int(mo), int(d), int(h), int(mi)) + timedelta(seconds=float(s))
    sec = (dt - GPS_EPOCH).total_seconds()
    week = int(sec // 604800)
    return week, sec - week * 604800.0


# --------------------------------------------------------------------------
# RINEX 3 observation
# --------------------------------------------------------------------------
class RinexObs:
    def __init__(self, path):
        self.path = path
        self.obs_types = {}
        self.approx_pos = None
        self.epochs = []
        self._read()

    def _read(self):
        with open(self.path, 'r', errors='ignore') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            ln = lines[i]
            label = ln[60:].strip() if len(ln) > 60 else ''
            if 'SYS / # / OBS TYPES' in label:
                sys_char = ln[0]
                n = int(ln[3:6])
                types = [ln[7 + 4 * k: 10 + 4 * k] for k in range(min(n, 13))]
                i += 1
                while i < len(lines) and lines[i][0] == ' ' and 'SYS / # / OBS TYPES' in lines[i][60:]:
                    types += [lines[i][7 + 4 * k: 10 + 4 * k] for k in range(13)]
                    i += 1
                self.obs_types[sys_char] = [t for t in types if t]
                continue
            if 'APPROX POSITION XYZ' in label:
                self.approx_pos = np.array([float(ln[0:14]), float(ln[14:28]), float(ln[28:42])])
            if 'END OF HEADER' in label:
                i += 1
                break
            i += 1

        # ---- epochs -------------------------------------------------------
        cur = None
        while i < len(lines):
            ln = lines[i]
            if ln.startswith('>'):
                tok = ln[1:].split()
                if len(tok) < 8:
                    i += 1
                    continue
                y, mo, d, h, mi = [int(v) for v in tok[:5]]
                s = float(tok[5]); flag = int(tok[6]); n = int(tok[7])
                week, tow = cal2tow(y, mo, d, h, mi, s)
                cur = {'week': week, 'tow': tow, 'flag': flag, 'sat': {}}
                self.epochs.append(cur)
                i += 1
                if flag > 1:      # special event: no satellite lines
                    continue
                for _ in range(n):
                    if i >= len(lines):
                        break
                    sl = lines[i]
                    if sl.startswith('>'):
                        break
                    prn = sl[0:3]
                    if len(prn.strip()) < 2:
                        i += 1
                        continue
                    sysc = prn[0]
                    try:
                        prn = '%s%02d' % (sysc, int(prn[1:3]))
                    except ValueError:
                        i += 1
                        continue
                    types = self.obs_types.get(sysc, [])
                    vals = {}
                    for k, t in enumerate(types):
                        # 14-character value followed by LLI and SSI
                        fld = sl[3 + 16 * k: 17 + 16 * k]
                        if fld.strip():
                            try:
                                vals[t] = float(fld)
                            except ValueError:
                                pass
                    cur['sat'][prn] = vals
                    i += 1
                continue
            i += 1

        self.epochs = [e for e in self.epochs if e['flag'] <= 1]


# --------------------------------------------------------------------------
# RINEX 3 navigation
# --------------------------------------------------------------------------
class Eph:
    __slots__ = ('sys', 'prn', 'toc', 'af0', 'af1', 'af2', 'iode', 'crs', 'deln',
                 'm0', 'cuc', 'e', 'cus', 'sqrta', 'toe', 'cic', 'omg0', 'cis',
                 'i0', 'crc', 'omg', 'omgd', 'idot', 'week', 'tgd', 'health',
                 'toes', 'iodc')


def read_rinex_nav(path):
    """Return {(sys, prn): [Eph, ...]} sorted by toe.

    RINEX 3 navigation records are written both with separating spaces and with
    the values glued together (``4.344531250000D+02-2.097230167308D-09``), and
    sparse records leave some fields empty.  Each number is therefore located
    with a regular expression and assigned to its 19-column slot, so that a
    missing value shifts nothing.
    """
    import re
    ephs = {}
    with open(path, 'r', errors='ignore') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines) and 'END OF HEADER' not in lines[i]:
        i += 1
    i += 1

    NUMRE = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[DEde][-+]?\d+)?')

    def is_start(s):
        return (len(s) > 22 and s[0] in 'GRECJSI' and s[1:3].strip().isdigit())

    def slots(s, base, n):
        out = [0.0] * n
        for m in NUMRE.finditer(s):
            k = int(round((m.start() - base) / 19.0))
            if 0 <= k < n:
                try:
                    out[k] = float(m.group(0).replace('D', 'E').replace('d', 'e'))
                except ValueError:
                    pass
        return out

    while i < len(lines):
        if not is_start(lines[i]):
            i += 1
            continue
        l0 = lines[i]
        sysc = l0[0]
        prn = '%s%02d' % (sysc, int(l0[1:3]))
        rec = [l0]
        j = i + 1
        while j < len(lines) and not is_start(lines[j]) and len(rec) < 8:
            rec.append(lines[j])
            j += 1
        i = j
        if sysc == 'R':
            continue                       # GLONASS: different record layout

        tok = slots(l0[23:], 0, 3)         # af0, af1, af2
        for ln in rec[1:8]:
            tok += slots(ln, 4, 4)
        try:
            e = Eph()
            e.sys, e.prn = sysc, prn
            y, mo, d = int(l0[4:8]), int(l0[9:11]), int(l0[12:14])
            h, mi, sec = int(l0[15:17]), int(l0[18:20]), int(l0[21:23])
            e.toc = cal2tow(y, mo, d, h, mi, sec)
            e.af0, e.af1, e.af2 = tok[0:3]
            (e.iode, e.crs, e.deln, e.m0) = tok[3:7]
            (e.cuc, e.e, e.cus, e.sqrta) = tok[7:11]
            (e.toe, e.cic, e.omg0, e.cis) = tok[11:15]
            (e.i0, e.crc, e.omg, e.omgd) = tok[15:19]
            e.idot = tok[19]
            e.week = tok[21]               # GPS/GAL week; BDT week for BeiDou
            e.health = tok[24]
            e.tgd = tok[25]
            e.iodc = tok[26]
        except (IndexError, ValueError):
            continue

        if sysc == 'C':
            # BeiDou broadcasts in BDT (week 0 = 2006-01-01 = GPS week 1356),
            # and BDT = GPST - 14 s
            e.toes = (e.week + 1356.0) * 604800.0 + e.toe + 14.0
            e.toc = (e.toc[0], e.toc[1] + 14.0)
        else:
            e.toes = e.week * 604800.0 + e.toe
        ephs.setdefault((sysc, prn), []).append(e)

    for k in ephs:
        ephs[k].sort(key=lambda x: x.toes)
    return ephs


def read_iono_header(path):
    """Klobuchar coefficients from the RINEX navigation header (GPSA/GPSB)."""
    out = {}
    with open(path, 'r', errors='ignore') as f:
        for ln in f:
            if 'END OF HEADER' in ln:
                break
            tag = ln[60:].strip()
            if tag == 'IONOSPHERIC CORR':
                name = ln[0:4].strip()
                vals = []
                for k in range(4):
                    fld = ln[5 + 12 * k: 17 + 12 * k]
                    try:
                        vals.append(float(fld.replace('D', 'E').replace('d', 'e')))
                    except ValueError:
                        vals.append(0.0)
                out[name] = vals
    return out


def pick_eph(ephs, sysc, prn, t_abs):
    """Closest-in-time ephemeris valid within +-2 h."""
    lst = ephs.get((sysc, prn))
    if not lst:
        return None
    best, bd = None, 1e18
    for e in lst:
        dt = abs(t_abs - e.toes)
        if dt < bd:
            best, bd = e, dt
    if bd > 7200:
        return None
    if best.health not in (0.0,):
        return None
    return best


# --------------------------------------------------------------------------
# broadcast ephemeris -> satellite position / clock
# --------------------------------------------------------------------------
def sat_pos_clock(e, t_abs):
    """t_abs: absolute GPS time [s] (week*604800+tow). Returns (pos, dts, el_ok)."""
    tk = t_abs - e.toes
    if tk > 302400:
        tk -= 604800
    elif tk < -302400:
        tk += 604800

    A = e.sqrta ** 2
    n0 = np.sqrt(MU / A ** 3)
    n = n0 + e.deln
    M = e.m0 + n * tk

    E = M
    for _ in range(12):
        E = M + e.e * np.sin(E)
    sinE, cosE = np.sin(E), np.cos(E)
    v = np.arctan2(np.sqrt(1 - e.e ** 2) * sinE, cosE - e.e)
    phi = v + e.omg

    s2, c2 = np.sin(2 * phi), np.cos(2 * phi)
    du = e.cus * s2 + e.cuc * c2
    dr = e.crs * s2 + e.crc * c2
    di = e.cis * s2 + e.cic * c2

    u = phi + du
    r = A * (1 - e.e * cosE) + dr
    inc = e.i0 + di + e.idot * tk

    xp, yp = r * np.cos(u), r * np.sin(u)
    Om = e.omg0 + (e.omgd - OMEGA_E) * tk - OMEGA_E * e.toe

    X = xp * np.cos(Om) - yp * np.cos(inc) * np.sin(Om)
    Y = xp * np.sin(Om) + yp * np.cos(inc) * np.cos(Om)
    Z = yp * np.sin(inc)

    dtc = t_abs - (e.toc[0] * 604800.0 + e.toc[1])
    dts = (e.af0 + e.af1 * dtc + e.af2 * dtc ** 2
           + F_REL * e.e * e.sqrta * sinE)
    if e.sys == 'G':
        dts -= e.tgd
    elif e.sys == 'C':
        dts -= e.tgd
    dts -= 0.0
    return np.array([X, Y, Z]), dts


# --------------------------------------------------------------------------
# atmosphere
# --------------------------------------------------------------------------
def klobuchar(alpha, beta, lat, lon, az, el, t_gps):
    """Klobuchar broadcast ionosphere model, single frequency L1 [m]."""
    El = max(el, 0.0)
    psi = 0.0137 / (El / np.pi + 0.11) - 0.022
    phi_i = np.clip(lat / np.pi + psi * np.cos(az), -0.416, 0.416)
    lam_i = lon / np.pi + psi * np.sin(az) / np.cos(phi_i * np.pi)
    phi_m = phi_i + 0.064 * np.cos((lam_i - 1.617) * np.pi)
    t = (t_gps % 86400.0) + lam_i * 43200.0
    t = t % 86400.0 if t >= 0 else t + 86400.0
    F = 1.0 + 16.0 * (0.53 - El / np.pi) ** 3
    amp = sum(alpha[k] * phi_m ** k for k in range(4))
    per = sum(beta[k] * phi_m ** k for k in range(4))
    amp = max(amp, 0.0)
    per = max(per, 72000.0)
    x = 2.0 * np.pi * (t - 50400.0) / per
    if abs(x) < 1.57:
        dI = F * (5e-9 + amp * (1 - x ** 2 / 2 + x ** 4 / 24))
    else:
        dI = F * 5e-9
    return dI * C_LIGHT


def tropo_saastamoinen(el, h):
    """Saastamoinen zenith delay with standard atmosphere, mapped by 1/sin(el)."""
    El = max(el, 5e-3)
    h = float(np.clip(h, -500.0, 10000.0))
    P = 1013.25 * (1 - 2.2557e-5 * h) ** 5.2568
    T = 15.0 - 6.5e-3 * h + 273.15
    e_w = 0.5 * np.exp(17.67 * (T - 273.15) / (T - 29.65)) * 6.11
    z = np.pi / 2 - El
    tr = 0.002277 / np.sin(El) * (P + (1255.0 / T + 0.05) * e_w)
    return tr


# --------------------------------------------------------------------------
# coordinate helpers
# --------------------------------------------------------------------------
def ecef2geo(x):
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    p = np.hypot(x[0], x[1])
    lon = np.arctan2(x[1], x[0])
    lat = np.arctan2(x[2], p * (1 - e2))
    for _ in range(8):
        N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
        h = p / np.cos(lat) - N
        lat = np.arctan2(x[2], p * (1 - e2 * N / (N + h)))
    N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    h = p / np.cos(lat) - N
    return lat, lon, h


def geo2ecef(lat, lon, h):
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    return np.array([(N + h) * np.cos(lat) * np.cos(lon),
                     (N + h) * np.cos(lat) * np.sin(lon),
                     (N * (1 - e2) + h) * np.sin(lat)])


def rot_ecef2enu(lat, lon):
    sl, cl = np.sin(lat), np.cos(lat)
    so, co = np.sin(lon), np.cos(lon)
    return np.array([[-so, co, 0.0],
                     [-sl * co, -sl * so, cl],
                     [cl * co, cl * so, sl]])


def azel(d, lat, lon):
    """Azimuth (from north, clockwise) and elevation of vector d in local ENU."""
    e = rot_ecef2enu(lat, lon) @ np.asarray(d, dtype=float)
    rng = np.linalg.norm(d)
    el = np.arcsin(np.clip(e[2] / rng, -1.0, 1.0))
    az = np.arctan2(e[0], e[1]) % (2 * np.pi)
    return az, el


def enu_offset(pos, ref):
    lat, lon, _ = ecef2geo(ref)
    return rot_ecef2enu(lat, lon) @ (np.asarray(pos) - np.asarray(ref))


# --------------------------------------------------------------------------
# UBX NAV-HPPOSECEF
# --------------------------------------------------------------------------
def read_hpposecef(path):
    """Return (week, tow, ecef, hacc) arrays from a u-center UBX log."""
    d = open(path, 'rb').read()
    out = []
    i = 0
    while True:
        j = d.find(b'\xb5\x62\x01\x13', i)
        if j < 0 or j + 44 > len(d):
            break
        ln = struct.unpack('<H', d[j + 4:j + 6])[0]
        p = d[j + 6:j + 6 + ln]
        if ln >= 28:
            itow = struct.unpack('<I', p[4:8])[0]
            x = struct.unpack('<i', p[8:12])[0] / 100.0 + struct.unpack('<b', p[20:21])[0] / 1e4
            y = struct.unpack('<i', p[12:16])[0] / 100.0 + struct.unpack('<b', p[21:22])[0] / 1e4
            z = struct.unpack('<i', p[16:20])[0] / 100.0 + struct.unpack('<b', p[22:23])[0] / 1e4
            hacc = struct.unpack('<I', p[24:28])[0] / 1e4
            out.append((itow, x, y, z, hacc))
        i = j + 6 + ln
    return out
