import { useEffect, useState } from "react";
import * as THREE from "three";

// EUMETSAT composite processed by Live Cloud Maps. No API key is needed.
export const CLOUD_SOURCE =
  "https://clouds.matteason.co.uk/images/2048x1024/clouds-alpha.png";
export default function useClouds(enabled) {
  const [layer, setLayer] = useState({
    texture: null,
    status: "loading",
    retrievedAt: null,
  });
  useEffect(() => {
    if (!enabled) {
      setLayer({ texture: null, status: "off", retrievedAt: null });
      return;
    }
    let stopped = false,
      busy = false,
      ownedTexture = null,
      controller;
    setLayer({ texture: null, status: "loading", retrievedAt: null });
    async function refresh() {
      if (busy) return;
      busy = true;
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15000);
      let objectUrl;
      try {
        const response = await fetch(CLOUD_SOURCE, {
          signal: controller.signal,
          cache: "no-cache",
        });
        if (
          !response.ok ||
          !response.headers.get("content-type")?.startsWith("image/")
        )
          throw Error("Cloud imagery unavailable");
        objectUrl = URL.createObjectURL(await response.blob());
        const image = new Image();
        image.src = objectUrl;
        await image.decode();
        if (stopped) return;
        const texture = new THREE.Texture(image);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.needsUpdate = true;
        const previous = ownedTexture;
        ownedTexture = texture;
        setLayer({ texture, status: "ready", retrievedAt: new Date() });
        previous?.dispose();
      } catch {
        if (!stopped)
          setLayer((previous) => ({
            ...previous,
            status: ownedTexture ? "cached" : "unavailable",
          }));
      } finally {
        clearTimeout(timeout);
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        busy = false;
      }
    }
    refresh();
    const timer = setInterval(refresh, 30 * 60 * 1000);
    return () => {
      stopped = true;
      controller?.abort();
      clearInterval(timer);
      ownedTexture?.dispose();
    };
  }, [enabled]);
  return layer;
}
