#!/usr/bin/env python3
"""
compute_doppler.py - real-time per-PRN Doppler from GNSS-SDR ephemeris XML.

Reads ~/gnss/assist/gps_ephemeris.xml (boost::serialization format produced by
rinex2assist / the F9T refresh pipeline), propagates each satellite's Kepler
orbit per ICD-GPS-200 to the current epoch, and reports:

    * elevation / azimuth from the receiver
    * line-of-sight Doppler shift at L1
    * which PRNs are above the elevation mask (= valid acquisition targets)

Optionally emits a GNSS-SDR config snippet that:
    * limits Channels_1C to the currently-visible PRNs
    * tightens Acquisition_1C.doppler_max to max|expected Doppler| + margin
    * sets a small Acquisition_1C.doppler_step

Optionally patches an existing base config in-place (writing a new file).

Default receiver location is UIUC (Urbana, IL). Override with --lat/--lon/--alt
if needed; receiver position accuracy of ~100 km is fine for Doppler.

USAGE

    # Just print the visible-satellite table
    python3 compute_doppler.py

    # Print table + config snippet
    python3 compute_doppler.py --snippet

    # Patch lime_diagnostic_clean.conf into lime_doppler_aided.conf
    python3 compute_doppler.py \
        --patch ~/gnss/configs/lime_diagnostic_clean.conf \
        --out   ~/gnss/configs/lime_doppler_aided.conf

NOTES

    * Tested against gnss-sdr v0.0.16 ephemeris XML.
    * GPS-UTC leap-second offset assumed = 18 (no new leap seconds since
      2017-01-01). If a future leap second is added, bump GPS_UTC_LEAP.
    * Margin default = 500 Hz. With the 10 MHz external reference locked,
      TCXO drift contribution to Doppler uncertainty is small; without it,
      raise --margin to ~1500.
"""

import argparse
import math
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# ---------- physical / geodetic constants ----------
MU         = 3.986005e14            # WGS-84 gravitational parameter, m^3/s^2
OMEGA_E    = 7.2921151467e-5        # WGS-84 Earth rotation rate, rad/s
C_LIGHT    = 2.99792458e8           # m/s
F_L1       = 1575.42e6              # Hz

WGS84_A    = 6378137.0
WGS84_F    = 1.0 / 298.257223563
WGS84_E2   = 2 * WGS84_F - WGS84_F * WGS84_F

GPS_EPOCH_UNIX = 315964800          # 1980-01-06 00:00:00 UTC
GPS_UTC_LEAP   = 18                 # GPS-UTC offset since 2017-01-01


# ---------- data ----------
@dataclass
class Eph:
    prn: int
    toe: float
    sqrt_A: float
    e: float
    M0: float
    OMEGA0: float
    omega: float
    i0: float
    delta_n: float
    OMEGA_DOT: float
    IDOT: float
    Cuc: float
    Cus: float
    Crc: float
    Crs: float
    Cic: float
    Cis: float
    gps_week: int
    sv_health: int = 0


# ---------- XML parsing ----------
def _find_text(node, *tag_candidates):
    """Find the first child element whose tag matches any candidate; return its text or None."""
    for t in tag_candidates:
        el = node.find(t)
        if el is not None and el.text is not None:
            return el.text.strip()
    return None


def _f(node, *tags, default=0.0):
    txt = _find_text(node, *tags)
    if txt is None:
        return default
    try:
        return float(txt)
    except ValueError:
        return default


def _i(node, *tags, default=0):
    txt = _find_text(node, *tags)
    if txt is None:
        return default
    try:
        return int(txt)
    except ValueError:
        return default


def parse_xml(p: Path):
    """Parse a GNSS-SDR boost::serialization ephemeris XML into a list of Eph.

    Handles both the older format (d_Toe, d_sqrt_A, ..., i_GPS_week) and the
    newer format used in boost_serialization v18 (toe, sqrtA, ..., WN). In the
    new format <first> holds a map index and the PRN lives in <second><PRN>.
    """
    tree = ET.parse(p)
    root = tree.getroot()
    ephs = []
    for item in root.findall('.//item'):
        second = item.find('second')
        if second is None:
            continue

        # PRN: newer format puts it in <second><PRN>; older format used <first>.
        prn = _i(second, 'PRN', 'i_satellite_PRN', default=-1)
        if prn <= 0:
            first = item.find('first')
            if first is not None and first.text is not None:
                try:
                    prn = int(first.text.strip())
                except ValueError:
                    continue
        if prn <= 0:
            continue

        # Filter out non-ephemeris items.
        if _find_text(second, 'sqrtA', 'd_sqrt_A') is None:
            continue

        ephs.append(Eph(
            prn=prn,
            toe=_f(second,       'toe',     'd_Toe'),
            sqrt_A=_f(second,    'sqrtA',   'd_sqrt_A'),
            e=_f(second,         'ecc',     'd_e_eccentricity'),
            M0=_f(second,        'M_0',     'd_M_0'),
            OMEGA0=_f(second,    'OMEGA_0', 'd_OMEGA0'),
            omega=_f(second,     'omega',   'd_OMEGA'),
            i0=_f(second,        'i_0',     'd_i_0'),
            delta_n=_f(second,   'delta_n', 'd_Delta_n'),
            OMEGA_DOT=_f(second, 'OMEGAdot','d_OMEGA_DOT'),
            IDOT=_f(second,      'idot',    'd_IDOT'),
            Cuc=_f(second,       'Cuc',     'd_Cuc'),
            Cus=_f(second,       'Cus',     'd_Cus'),
            Crc=_f(second,       'Crc',     'd_Crc'),
            Crs=_f(second,       'Crs',     'd_Crs'),
            Cic=_f(second,       'Cic',     'd_Cic'),
            Cis=_f(second,       'Cis',     'd_Cis'),
            gps_week=_i(second,  'WN',      'i_GPS_week', 'd_GPS_week'),
            sv_health=_i(second, 'SV_health','i_SV_health','d_SV_health'),
        ))

    # Dedup by PRN: when F9T writes multiple ephemeris records for the same
    # satellite, keep the one with the latest toe.
    best = {}
    for e in ephs:
        prev = best.get(e.prn)
        if prev is None or e.toe > prev.toe:
            best[e.prn] = e
    return list(best.values())


# ---------- orbit propagation ----------
def sat_ecef(e: Eph, sow: float):
    """Satellite ECEF position at GPS seconds-of-week `sow`. Returns (X, Y, Z) in meters."""
    A = e.sqrt_A * e.sqrt_A
    if A < 1.0:
        return float('nan'), float('nan'), float('nan')

    n0 = math.sqrt(MU / (A * A * A))
    tk = sow - e.toe
    if tk > 302400.0:
        tk -= 604800.0
    elif tk < -302400.0:
        tk += 604800.0

    n = n0 + e.delta_n
    M = e.M0 + n * tk

    # Solve Kepler's equation for eccentric anomaly E.
    E = M
    for _ in range(15):
        E_new = M + e.e * math.sin(E)
        if abs(E_new - E) < 1e-12:
            E = E_new
            break
        E = E_new

    sinE = math.sin(E)
    cosE = math.cos(E)
    sinv = math.sqrt(1.0 - e.e * e.e) * sinE / (1.0 - e.e * cosE)
    cosv = (cosE - e.e) / (1.0 - e.e * cosE)
    nu = math.atan2(sinv, cosv)

    phi = nu + e.omega
    s2 = math.sin(2.0 * phi)
    c2 = math.cos(2.0 * phi)

    du = e.Cus * s2 + e.Cuc * c2
    dr = e.Crs * s2 + e.Crc * c2
    di = e.Cis * s2 + e.Cic * c2

    u = phi + du
    r = A * (1.0 - e.e * cosE) + dr
    i = e.i0 + di + e.IDOT * tk

    xp = r * math.cos(u)
    yp = r * math.sin(u)

    Om = e.OMEGA0 + (e.OMEGA_DOT - OMEGA_E) * tk - OMEGA_E * e.toe
    cO = math.cos(Om); sO = math.sin(Om)
    ci = math.cos(i);  si = math.sin(i)

    X = xp * cO - yp * ci * sO
    Y = xp * sO + yp * ci * cO
    Z = yp * si
    return X, Y, Z


# ---------- coordinate transforms ----------
def lla_to_ecef(lat_deg, lon_deg, alt_m):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sl = math.sin(lat); cl = math.cos(lat)
    N = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sl * sl)
    X = (N + alt_m) * cl * math.cos(lon)
    Y = (N + alt_m) * cl * math.sin(lon)
    Z = (N * (1.0 - WGS84_E2) + alt_m) * sl
    return X, Y, Z


def ecef_to_enu(dx, dy, dz, lat_deg, lon_deg):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sl = math.sin(lat); cl = math.cos(lat)
    so = math.sin(lon); co = math.cos(lon)
    E =          -so * dx + co * dy
    N = -sl * co * dx - sl * so * dy + cl * dz
    U =  cl * co * dx + cl * so * dy + sl * dz
    return E, N, U


def unix_to_gps(t_unix):
    gps_t = t_unix - GPS_EPOCH_UNIX + GPS_UTC_LEAP
    week = int(gps_t // 604800)
    sow = gps_t - week * 604800
    return week, sow


# ---------- visibility / Doppler computation ----------
def compute(ephs, lat, lon, alt, t_unix, mask_deg):
    week, sow = unix_to_gps(t_unix)
    rx = lla_to_ecef(lat, lon, alt)
    dt = 0.5  # seconds for numerical velocity

    rows = []
    for e in ephs:
        if e.sqrt_A < 1.0:
            continue
        if e.sv_health != 0:
            continue
        p1 = sat_ecef(e, sow)
        p2 = sat_ecef(e, sow + dt)
        if any(math.isnan(v) for v in p1):
            continue

        dx = p1[0] - rx[0]
        dy = p1[1] - rx[1]
        dz = p1[2] - rx[2]
        rng = math.sqrt(dx * dx + dy * dy + dz * dz)

        E, N, U = ecef_to_enu(dx, dy, dz, lat, lon)
        elev = math.degrees(math.asin(U / rng))
        azim = math.degrees(math.atan2(E, N)) % 360.0
        if elev < mask_deg:
            continue

        # ECEF velocity by finite difference (Earth-rotation effects already in Omega term).
        vx = (p2[0] - p1[0]) / dt
        vy = (p2[1] - p1[1]) / dt
        vz = (p2[2] - p1[2]) / dt
        ux = dx / rng; uy = dy / rng; uz = dz / rng
        range_rate = vx * ux + vy * uy + vz * uz  # m/s; positive = receding
        doppler_hz = -range_rate * F_L1 / C_LIGHT

        toe_age = sow - e.toe
        if toe_age > 302400.0:
            toe_age -= 604800.0
        elif toe_age < -302400.0:
            toe_age += 604800.0

        rows.append({
            'prn': e.prn,
            'elev': elev,
            'azim': azim,
            'doppler': doppler_hz,
            'rng_km': rng / 1000.0,
            'toe_age': toe_age,
        })

    rows.sort(key=lambda r: -r['elev'])
    return rows, week, sow


# ---------- config snippet / patching ----------
def emit_snippet(rows, max_channels, margin_hz):
    if not rows:
        return ""
    chosen = rows[:max_channels]
    md = max(abs(r['doppler']) for r in chosen)
    dmax = int(math.ceil((md + margin_hz) / 100.0) * 100)

    lines = []
    lines.append("; ---- doppler-aided channel plan (compute_doppler.py) ----")
    lines.append(f"Channels_1C.count={len(chosen)}")
    lines.append(f"Channels.count={len(chosen)}")
    lines.append("Channels.in_acquisition=1")
    lines.append("Channel.signal=1C")
    for idx, r in enumerate(chosen):
        lines.append(
            f"; PRN {r['prn']:2d}  elev {r['elev']:5.1f} deg  az {r['azim']:5.1f} deg  "
            f"expected Doppler {r['doppler']:+7.0f} Hz"
        )
        lines.append(f"Channel{idx}.satellite={r['prn']}")
    lines.append("")
    lines.append(f"Acquisition_1C.doppler_max={dmax}")
    lines.append("Acquisition_1C.doppler_step=125")
    return "\n".join(lines) + "\n"


PATCH_PATTERNS = [
    r'^[ \t]*Channels_1C\.count[ \t]*=.*\n?',
    r'^[ \t]*Channels\.count[ \t]*=.*\n?',
    r'^[ \t]*Channels\.in_acquisition[ \t]*=.*\n?',
    r'^[ \t]*Channel\.signal[ \t]*=.*\n?',
    r'^[ \t]*Channel\d+\.satellite[ \t]*=.*\n?',
    r'^[ \t]*Acquisition_1C\.doppler_max[ \t]*=.*\n?',
    r'^[ \t]*Acquisition_1C\.doppler_step[ \t]*=.*\n?',
]


def patch_config(base_path, out_path, snippet):
    with open(base_path) as f:
        text = f.read()
    for pat in PATCH_PATTERNS:
        text = re.sub(pat, '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text).rstrip() + "\n\n"
    text += snippet
    with open(out_path, 'w') as f:
        f.write(text)


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xml', default=str(Path.home() / 'gnss/assist/gps_ephemeris.xml'))
    ap.add_argument('--lat', type=float, default=40.1106, help='receiver latitude (deg), default UIUC')
    ap.add_argument('--lon', type=float, default=-88.2073, help='receiver longitude (deg), default UIUC')
    ap.add_argument('--alt', type=float, default=225.0, help='receiver altitude (m), default UIUC')
    ap.add_argument('--mask', type=float, default=5.0, help='elevation mask in degrees')
    ap.add_argument('--time', type=float, default=None, help='Unix time; default = now')
    ap.add_argument('--snippet', action='store_true', help='also print GNSS-SDR config snippet')
    ap.add_argument('--max-channels', type=int, default=12)
    ap.add_argument('--margin', type=int, default=500, help='extra margin (Hz) on doppler_max')
    ap.add_argument('--patch', metavar='BASE', help='base config to patch')
    ap.add_argument('--out', metavar='OUT', help='output config path; required with --patch')
    args = ap.parse_args()

    t_unix = args.time if args.time is not None else time.time()
    xml_path = Path(args.xml)
    if not xml_path.exists():
        print(f"ERR: ephemeris XML not found: {xml_path}", file=sys.stderr)
        sys.exit(1)

    ephs = parse_xml(xml_path)
    if not ephs:
        print(f"ERR: parsed zero ephemeris records from {xml_path}", file=sys.stderr)
        sys.exit(2)

    rows, week, sow = compute(ephs, args.lat, args.lon, args.alt, t_unix, args.mask)

    print(f"# rx: lat {args.lat:.4f} lon {args.lon:.4f} alt {args.alt:.0f} m")
    print(f"# GPS week {week}, sow {sow:.0f}, unix {t_unix:.0f}")
    print(f"# eph: {len(ephs)} records parsed, {len(rows)} above {args.mask:.0f} deg")
    if rows:
        oldest = max(r['toe_age'] for r in rows)
        print(f"# oldest visible ephemeris toe age: {oldest / 60.0:.1f} min")
        if oldest > 4 * 3600:
            print("# WARN: ephemeris > 4 h old -- Doppler accuracy will degrade")
    print()
    print(f"{'PRN':>4} {'Elev':>6} {'Az':>7} {'Doppler Hz':>12} {'Rng km':>8}")
    for r in rows:
        print(f"{r['prn']:>4} {r['elev']:>6.1f} {r['azim']:>7.1f} {r['doppler']:>+12.1f} {r['rng_km']:>8.0f}")

    snippet = ""
    if args.snippet or args.patch:
        snippet = emit_snippet(rows, args.max_channels, args.margin)

    if args.snippet:
        print()
        print(snippet, end='')

    if args.patch:
        if not args.out:
            print("ERR: --patch requires --out", file=sys.stderr)
            sys.exit(3)
        patch_config(args.patch, args.out, snippet)
        print(f"\n# patched config -> {args.out}", file=sys.stderr)


if __name__ == '__main__':
    main()
