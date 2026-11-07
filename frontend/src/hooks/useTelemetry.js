import { useEffect, useState } from "react";
import { EMPTY, applySentence } from "../lib/telemetry.js";
import { createDemo } from "../lib/demo.js";

// React effects own network connections and clean them up on unmount.
export default function useTelemetry(demo) {
  const [data, setData] = useState(EMPTY);
  const [status, setStatus] = useState("connecting");
  const [error, setError] = useState("");
  useEffect(() => {
    if (demo) {
      setData(createDemo());
      setStatus("demo");
      setError("");
      return;
    }
    setData(EMPTY);
    setStatus("connecting");
    setError("");
    let stopped = false,
      socket,
      reconnect,
      lastLive = 0,
      polling = false;
    const controller = new AbortController();
    async function poll() {
      if (polling || Date.now() - lastLive < 6000) return;
      polling = true;
      try {
        const paths = ["positions", "satellites", "satellite-history", "raw"];
        const results = await Promise.all(
          paths.map(async (path) => {
            const r = await fetch(`/api/${path}`, {
              signal: controller.signal,
            });
            if (!r.ok) return null;
            return r.json();
          }),
        );
        if (stopped || Date.now() - lastLive < 6000) return;
        const [positions, satellites, history, raw] = results;
        if (
          !Array.isArray(positions) ||
          !satellites ||
          typeof satellites !== "object" ||
          Array.isArray(satellites)
        )
          throw Error(
            "No recording loaded. Start the receiver or load the CTTC dataset.",
          );
        setData({
          positions,
          satellites,
          history: history || {},
          raw: raw?.sentences || [],
        });
        setStatus("replay");
        setError("");
      } catch (e) {
        if (!stopped && e.name !== "AbortError") {
          setStatus("offline");
          setError(
            "No recording available. Start the backend and load a recording, or explore the demo.",
          );
        }
      } finally {
        polling = false;
      }
    }
    function connect() {
      if (stopped) return;
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
      );
      socket.onmessage = ({ data: line }) => {
        if (typeof line !== "string" || stopped) return;
        const valid = applySentence(EMPTY, line).valid;
        if (valid) {
          if (Date.now() - lastLive >= 6000) setData(EMPTY);
          lastLive = Date.now();
          setStatus("live");
          setError("");
        }
        setData((previous) => applySentence(previous, line).data);
      };
      socket.onclose = () => {
        if (!stopped) reconnect = setTimeout(connect, 3000);
      };
      socket.onerror = () => socket.close();
    }
    poll();
    connect();
    const timer = setInterval(poll, 3000);
    return () => {
      stopped = true;
      controller.abort();
      clearInterval(timer);
      clearTimeout(reconnect);
      socket?.close();
    };
  }, [demo]);
  return { data, status, error };
}
