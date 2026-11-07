// Pure data functions: no React or browser dependencies.
export const EMPTY = { positions: [], satellites: {}, history: {}, raw: [] };
export function signalColor(sat) {
  if (sat.predicted_los === false) return "#f17c6c";
  if (sat.has_reflection) return "#e9b86c";
  if (sat.cn0 == null) return "#748793";
  return sat.cn0 >= 40 ? "#83dec5" : sat.cn0 >= 30 ? "#e9b86c" : "#f17c6c";
}
export function seconds(timestamp) {
  const s = String(timestamp || "").padStart(6, "0");
  return (
    Number(s.slice(0, 2)) * 3600 +
    Number(s.slice(2, 4)) * 60 +
    Number(s.slice(4))
  );
}
export function clockLabel(timestamp) {
  if (!timestamp) return "—";
  const s = String(timestamp).padStart(6, "0");
  return `${s.slice(0, 2)}:${s.slice(2, 4)}:${s.slice(4, 6)}`;
}
export function timeline(data) {
  const stamps = [
    ...new Set([
      ...data.positions.map((p) => p.timestamp),
      ...Object.values(data.history)
        .flat()
        .map((p) => p.t),
    ]),
  ]
    .filter(Boolean)
    .sort();
  // Unwrap midnight so a recording that crosses 00:00 still plays forward.
  if (stamps.length > 1) {
    let largest = 0,
      split = 0;
    for (let i = 1; i < stamps.length; i++) {
      const gap = seconds(stamps[i]) - seconds(stamps[i - 1]);
      if (gap > largest) {
        largest = gap;
        split = i;
      }
    }
    if (largest > 43200)
      return [...stamps.slice(split), ...stamps.slice(0, split)];
  }
  return stamps;
}
export function elapsedSeconds(stamps) {
  let day = 0,
    previous = 0;
  return stamps.map((t, i) => {
    const now = seconds(t);
    if (i && now < previous) day += 86400;
    previous = now;
    return now + day - seconds(stamps[0]);
  });
}
export function frameAt(data, stamps, index) {
  if (!stamps.length)
    return { receiver: data.positions.at(-1), satellites: data.satellites };
  const order = new Map(stamps.map((t, i) => [t, i]));
  let receiver;
  for (const p of data.positions)
    if ((order.get(p.timestamp) ?? Infinity) <= index) receiver = p;
  const satellites = Object.fromEntries(
    Object.entries(data.satellites).map(([key, sat]) => {
      const series = data.history[key];
      if (!series?.length) return [key, sat];
      let sample;
      for (const point of series)
        if ((order.get(point.t) ?? Infinity) <= index) sample = point;
      return [key, { ...sat, cn0: sample?.cn0 ?? null }];
    }),
  );
  return { receiver, satellites };
}
export function parseSentence(line) {
  if (!line.startsWith("$")) return null;
  const [body, checksum] = line.slice(1).split("*");
  if (checksum != null) {
    const xor = [...body].reduce((sum, c) => sum ^ c.charCodeAt(0), 0);
    if (!/^[0-9a-f]{2}$/i.test(checksum) || xor !== parseInt(checksum, 16))
      return null;
  }
  const f = body.split(",");
  if (f[0].endsWith("GGA")) {
    const coord = (v, h, n) =>
      (Number(v.slice(0, n)) + Number(v.slice(n)) / 60) *
      (["S", "W"].includes(h) ? -1 : 1);
    if (
      f.length < 10 ||
      !f[1] ||
      !f[2] ||
      !f[4] ||
      !["N", "S"].includes(f[3]) ||
      !["E", "W"].includes(f[5]) ||
      !f[9]
    )
      return null;
    const fix = {
      timestamp: f[1],
      latitude: coord(f[2], f[3], 2),
      longitude: coord(f[4], f[5], 3),
      altitude: Number(f[9]),
      fix_quality: Number(f[6]),
      num_satellites: Number(f[7]),
    };
    if (
      ![fix.latitude, fix.longitude, fix.altitude].every(Number.isFinite) ||
      Math.abs(fix.latitude) > 90 ||
      Math.abs(fix.longitude) > 180
    )
      return null;
    return { fix };
  }
  if (f[0].endsWith("GSV")) {
    const sats = [];
    for (let i = 4; i + 3 < f.length; i += 4) {
      if (!f[i] || !Number.isFinite(Number(f[i]))) continue;
      const value = (s) =>
        s !== "" && Number.isFinite(Number(s)) ? Number(s) : null;
      sats.push({
        prn: Number(f[i]),
        elevation: value(f[i + 1]),
        azimuth: value(f[i + 2]),
        cn0: value(f[i + 3]),
      });
    }
    return { sats };
  }
  return null;
}
export function applySentence(data, line) {
  const parsed = parseSentence(line);
  const next = { ...data, raw: [...data.raw, line].slice(-50) };
  if (parsed?.fix)
    next.positions = [...data.positions, parsed.fix].slice(-10000);
  if (parsed?.sats) {
    next.satellites = { ...data.satellites };
    next.history = { ...data.history };
    for (const sat of parsed.sats) {
      next.satellites[sat.prn] = sat;
      const t = next.positions.at(-1)?.timestamp;
      if (t)
        next.history[sat.prn] = [
          ...(next.history[sat.prn] || []),
          { t, cn0: sat.cn0 },
        ].slice(-300);
    }
  }
  return { data: next, valid: !!parsed };
}
