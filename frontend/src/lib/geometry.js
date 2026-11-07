// Earth-centred display coordinates, Y up. Radius 2 represents Earth.
export function geographic(latitude, longitude, radius = 2) {
  const lat = (latitude * Math.PI) / 180,
    lon = (longitude * Math.PI) / 180;
  return [
    radius * Math.cos(lat) * Math.cos(lon),
    radius * Math.sin(lat),
    -radius * Math.cos(lat) * Math.sin(lon),
  ];
}
export function satellitePosition(receiver, sat) {
  if (sat.azimuth == null || sat.elevation == null) return null;
  const lat = (receiver.latitude * Math.PI) / 180,
    lon = (receiver.longitude * Math.PI) / 180;
  const az = (sat.azimuth * Math.PI) / 180,
    el = (sat.elevation * Math.PI) / 180;
  const e = Math.sin(az) * Math.cos(el),
    n = Math.cos(az) * Math.cos(el),
    u = Math.sin(el);
  const origin = geographic(receiver.latitude, receiver.longitude, 2.015);
  const east = [-Math.sin(lon), 0, -Math.cos(lon)];
  const north = [
    -Math.sin(lat) * Math.cos(lon),
    Math.cos(lat),
    Math.sin(lat) * Math.sin(lon),
  ];
  const up = [
    Math.cos(lat) * Math.cos(lon),
    Math.sin(lat),
    -Math.cos(lat) * Math.sin(lon),
  ];
  // Same compressed display distance as the previous dashboard: 3,500 km.
  return origin.map(
    (v, i) => v + (3500 / 6371) * 2 * (e * east[i] + n * north[i] + u * up[i]),
  );
}
