import test from "node:test";
import assert from "node:assert/strict";
import {
  parseSentence,
  applySentence,
  EMPTY,
  timeline,
  elapsedSeconds,
  frameAt,
} from "./telemetry.js";
import { geographic, satellitePosition } from "./geometry.js";
import { createDemo } from "./demo.js";
const withChecksum = (body) =>
  "$" +
  body +
  "*" +
  [...body]
    .reduce((v, c) => v ^ c.charCodeAt(0), 0)
    .toString(16)
    .padStart(2, "0");
test("GGA hemispheres, checksums, malformed input", () => {
  const sentence = withChecksum(
    "GPGGA,120000.00,4124.8963,S,00204.7961,W,1,08,1.01,100.0,M,0.0,M,,",
  );
  const { fix } = parseSentence(sentence);
  assert.ok(fix.latitude < -41 && fix.longitude < -2);
  assert.equal(fix.altitude, 100);
  assert.equal(parseSentence(sentence.slice(0, -2) + "FF"), null);
  assert.equal(parseSentence("$GPGGA,120000,,,,,,,,,"), null);
});
test("GSV signal-ID is not a satellite; missing geometry remains null", () => {
  const parsed = parseSentence("$GPGSV,1,1,2,03,45,120,44,07,,,27,1");
  assert.equal(parsed.sats.length, 2);
  assert.equal(parsed.sats[1].azimuth, null);
  assert.equal(parsed.sats[1].cn0, 27);
});
test("live history uses GGA time and bounds the raw feed", () => {
  let data = applySentence(
    EMPTY,
    "$GPGGA,120000,4124.8963,N,00204.7961,E,1,08,1,100,M,0,M,,",
  ).data;
  data = applySentence(data, "$GPGSV,1,1,1,03,45,120,44").data;
  assert.deepEqual(data.history[3], [{ t: "120000", cn0: 44 }]);
  for (let i = 0; i < 60; i++)
    data = applySentence(data, "other sentence").data;
  assert.equal(data.raw.length, 50);
});
test("midnight replay uses preceding samples, never future observations", () => {
  const data = {
    positions: [
      { timestamp: "235959", latitude: 1 },
      { timestamp: "000002", latitude: 2 },
    ],
    satellites: { 3: { prn: 3, cn0: 50 } },
    history: {
      3: [
        { t: "000001", cn0: 30 },
        { t: "000002", cn0: 42 },
      ],
    },
  };
  const stamps = timeline(data);
  assert.deepEqual(stamps, ["235959", "000001", "000002"]);
  assert.deepEqual(elapsedSeconds(stamps), [0, 2, 3]);
  assert.equal(frameAt(data, stamps, 0).satellites[3].cn0, null);
  assert.equal(frameAt(data, stamps, 1).receiver.latitude, 1);
  assert.equal(frameAt(data, stamps, 1).satellites[3].cn0, 30);
});
test("geographic projection has correct up and east directions", () => {
  assert.deepEqual(geographic(0, 0), [2, 0, -0]);
  const receiver = { latitude: 0, longitude: 0 };
  const overhead = satellitePosition(receiver, { azimuth: 0, elevation: 90 });
  assert.ok(overhead[0] > 3 && Math.abs(overhead[1]) < 1e-10);
  const east = satellitePosition(receiver, { azimuth: 90, elevation: 0 });
  assert.ok(east[2] < -1 && Math.abs(east[1]) < 1e-10);
  assert.equal(
    satellitePosition(receiver, { azimuth: null, elevation: 30 }),
    null,
  );
});
test("demo has a coherent three minute timeline", () => {
  const stamps = timeline(createDemo());
  assert.equal(stamps.length, 181);
  assert.equal(elapsedSeconds(stamps).at(-1), 180);
});
