// Explicitly simulated data for exploring the interface without a receiver.
export function createDemo() {
  const specs = [
    [3, 62, 24, 46],
    [7, 28, 77, 38],
    [11, 47, 128, 43],
    [16, 18, 177, 29],
    [19, 73, 230, 49],
    [22, 36, 277, 41],
    [26, 14, 315, 33],
    [31, 51, 348, 44],
  ];
  const positions = Array.from({ length: 181 }, (_, i) => ({
    timestamp: `120${Math.floor(i / 60)}${String(i % 60).padStart(2, "0")}.00`,
    latitude: 41.275 + Math.sin(i / 24) * 0.00003,
    longitude: 1.987 + Math.cos(i / 25) * 0.00004,
    altitude: 24.3,
    fix_quality: 1,
    num_satellites: 8,
  }));
  const satellites = Object.fromEntries(
    specs.map(([prn, elevation, azimuth, cn0]) => [
      prn,
      { prn, elevation, azimuth, cn0 },
    ]),
  );
  const history = Object.fromEntries(
    specs.map(([prn, , , cn0]) => [
      prn,
      positions.map((p, i) => ({
        t: p.timestamp,
        cn0: cn0 + Math.sin(i / 17 + prn) * 2.2,
      })),
    ]),
  );
  return {
    positions,
    satellites,
    history,
    raw: ["SIMULATED DATA — connect a receiver for actual NMEA sentences."],
  };
}
