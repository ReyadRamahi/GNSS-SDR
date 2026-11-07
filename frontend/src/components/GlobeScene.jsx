import { Component, Suspense, useMemo, useRef, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Line, OrbitControls, Stars, useTexture } from "@react-three/drei";
import * as THREE from "three";
import { geographic, satellitePosition } from "../lib/geometry.js";
import { signalColor } from "../lib/telemetry.js";

class SceneBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="scene-error">
        3D view unavailable. Enable WebGL and reload. Your telemetry is still
        available in the panels.
      </div>
    ) : (
      this.props.children
    );
  }
}
function Earth() {
  const map = useTexture("/earth.jpg");
  map.colorSpace = THREE.SRGBColorSpace;
  return (
    <group>
      <mesh>
        <sphereGeometry args={[2, 96, 64]} />
        <meshStandardMaterial
          map={map}
          color="#a6c3c6"
          roughness={0.92}
          metalness={0.08}
        />
      </mesh>
      <mesh scale={1.025}>
        <sphereGeometry args={[2, 64, 48]} />
        <shaderMaterial
          transparent
          depthWrite={false}
          side={THREE.BackSide}
          vertexShader={`varying vec3 vNormal; varying vec3 vView; void main(){ vec4 p=modelViewMatrix*vec4(position,1.0); vNormal=normalize(normalMatrix*normal); vView=normalize(-p.xyz); gl_Position=projectionMatrix*p; }`}
          fragmentShader={`varying vec3 vNormal; varying vec3 vView; void main(){ float rim=pow(1.0-abs(dot(normalize(vNormal),normalize(vView))),3.0); gl_FragColor=vec4(0.25,0.68,0.78,rim*0.38); }`}
        />
      </mesh>
    </group>
  );
}
// A native Three.js sprite keeps labels inside the scene, including Earth occlusion.
function SatelliteLabel({ prn, selected }) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 52;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0b151be6";
    ctx.fillRect(1, 1, 126, 50);
    ctx.strokeStyle = selected ? "#83dec5" : "#51666f";
    ctx.strokeRect(1, 1, 126, 50);
    ctx.font = "24px monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = selected ? "#b7ffe8" : "#d4e0e4";
    ctx.fillText("G" + String(prn).padStart(2, "0"), 64, 27);
    return new THREE.CanvasTexture(canvas);
  }, [prn, selected]);
  useEffect(() => {
    texture.needsUpdate = true;
    return () => texture.dispose();
  }, [texture]);
  return (
    <sprite position={[0, 0.15, 0]} scale={[0.045, 0.0183, 1]}>
      <spriteMaterial
        map={texture}
        transparent
        depthWrite={false}
        sizeAttenuation={false}
      />
    </sprite>
  );
}
function Satellite({ sat, receiver, selected, onSelect, beams }) {
  const position = satellitePosition(receiver, sat);
  const origin = geographic(receiver.latitude, receiver.longitude, 2.025);
  const pulse = useRef();
  const reducedMotion = useMemo(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    [],
  );
  const color = signalColor(sat);
  const isSelected = selected === sat.prn;
  const points = useMemo(
    () => (position ? [origin, position] : []),
    [...origin, ...(position || [])],
  );
  useFrame(({ clock }) => {
    if (pulse.current && points.length && !reducedMotion) {
      const t = (clock.elapsedTime * 0.32 + sat.prn * 0.07) % 1;
      pulse.current.position.set(
        ...origin.map((v, i) => position[i] + (v - position[i]) * t),
      );
    }
  });
  if (!position) return null;
  return (
    <group>
      {beams && (
        <>
          <Line
            points={points}
            color={color}
            lineWidth={isSelected ? 1.8 : 0.7}
            transparent
            opacity={isSelected ? 0.85 : 0.28}
          />
          <mesh ref={pulse} visible={!reducedMotion}>
            <sphereGeometry args={[0.012, 8, 8]} />
            <meshBasicMaterial color={color} />
          </mesh>
        </>
      )}
      <group
        position={position}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(sat.prn);
        }}
        onPointerOver={() => {
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "auto";
        }}
      >
        <mesh>
          <boxGeometry args={[0.065, 0.065, 0.08]} />
          <meshStandardMaterial
            color={isSelected ? "#ffffff" : "#d8ddd9"}
            metalness={0.7}
            roughness={0.3}
          />
        </mesh>
        {[-1, 1].map((side) => (
          <mesh key={side} position={[side * 0.105, 0, 0]}>
            <boxGeometry args={[0.13, 0.008, 0.075]} />
            <meshStandardMaterial
              color="#375a75"
              metalness={0.65}
              roughness={0.4}
            />
          </mesh>
        ))}
        <SatelliteLabel prn={sat.prn} selected={isSelected} />
      </group>
    </group>
  );
}
function CameraControls({ reset, receiver }) {
  const ref = useRef();
  useEffect(() => {
    if (!ref.current) return;
    const direction = receiver
      ? geographic(receiver.latitude, receiver.longitude, 1)
      : [0.8, 0.45, 0.4];
    ref.current.object.position.set(
      direction[0] * 7.4,
      direction[1] * 7.4,
      direction[2] * 7.4 + 2.5,
    );
    ref.current.target.set(0, 0, 0);
    ref.current.update();
  }, [reset, Boolean(receiver)]);
  return (
    <OrbitControls
      ref={ref}
      makeDefault
      enablePan={false}
      enableDamping
      dampingFactor={0.06}
      minDistance={3.4}
      maxDistance={13}
    />
  );
}
export default function GlobeScene({
  positions,
  receiver,
  satellites,
  selected,
  onSelect,
  beams,
  reset,
}) {
  const track = useMemo(
    () => positions.map((p) => geographic(p.latitude, p.longitude, 2.008)),
    [positions],
  );
  return (
    <SceneBoundary>
      <Canvas
        camera={{ position: [6, 3.8, 3], fov: 43, near: 0.1, far: 150 }}
        dpr={[1, 1.75]}
        gl={{ antialias: true }}
      >
        <color attach="background" args={["#080e12"]} />
        <ambientLight intensity={0.85} />
        <directionalLight
          position={[6, 4, 5]}
          intensity={2.5}
          color="#e5f4ff"
        />
        <Stars
          radius={65}
          depth={25}
          count={900}
          factor={2}
          saturation={0}
          fade
          speed={0}
        />
        <Suspense fallback={null}>
          <Earth />
        </Suspense>
        {track.length > 1 && (
          <Line
            points={track}
            color="#83dec5"
            lineWidth={1.5}
            transparent
            opacity={0.65}
          />
        )}
        {receiver && (
          <>
            <mesh
              position={geographic(
                receiver.latitude,
                receiver.longitude,
                2.025,
              )}
            >
              <sphereGeometry args={[0.025, 16, 16]} />
              <meshBasicMaterial color="#b2ffe2" />
            </mesh>
            {Object.values(satellites).map((sat) => (
              <Satellite
                key={sat.prn}
                {...{ sat, receiver, selected, onSelect, beams }}
              />
            ))}
          </>
        )}
        <CameraControls reset={reset} receiver={receiver} />
      </Canvas>
    </SceneBoundary>
  );
}
