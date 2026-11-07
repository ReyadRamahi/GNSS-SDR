import { useEffect, useMemo, useState } from "react";
import { timeline, elapsedSeconds } from "../lib/telemetry.js";

export default function usePlayback(data, live, source) {
  const stamps = useMemo(() => timeline(data), [data]);
  const elapsed = useMemo(() => elapsedSeconds(stamps), [stamps]);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  useEffect(() => {
    setCursor(0);
    setPlaying(true);
  }, [source]);
  const duration = elapsed.at(-1) || 0;
  useEffect(() => {
    if (live || !playing || !duration) return;
    let previous = performance.now();
    const timer = setInterval(() => {
      const now = performance.now(),
        delta = (now - previous) / 1000;
      previous = now;
      setCursor((t) => (t + delta * speed > duration ? 0 : t + delta * speed));
    }, 100);
    return () => clearInterval(timer);
  }, [live, playing, speed, duration]);
  let index = live ? stamps.length - 1 : 0;
  if (!live)
    for (let i = 0; i < elapsed.length; i++) {
      if (elapsed[i] <= cursor) index = i;
      else break;
    }
  return {
    stamps,
    index,
    cursor,
    duration,
    playing,
    setPlaying,
    speed,
    setSpeed,
    seek: setCursor,
  };
}
