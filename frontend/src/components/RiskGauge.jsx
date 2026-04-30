import React from "react";

/** Semi-circle gauge SVG — Swiss style, 1px stroke base, bold stroke value. */
export default function RiskGauge({ value = 0, max = 100, label = "RISK SCORE", size = 200, testId }) {
  const pct = Math.max(0, Math.min(1, value / max));
  const cx = size / 2;
  const cy = size * 0.65;
  const r = size * 0.45;
  const start = Math.PI;
  const end = 0;
  const angle = start - pct * Math.PI;

  const polar = (a) => ({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
  const p0 = polar(start);
  const pEnd = polar(angle);
  const largeArc = pct > 0.5 ? 1 : 0;

  const color = value >= 80 ? "#16A34A" : value >= 60 ? "#EAB308" : value >= 40 ? "#F97316" : "#DC2626";

  return (
    <div className="flex flex-col items-center" data-testid={testId}>
      <svg width={size} height={size * 0.78} viewBox={`0 0 ${size} ${size * 0.78}`}>
        {/* base arc */}
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} stroke="#0A0A0A" strokeWidth="1" fill="none" />
        {/* value arc */}
        {pct > 0 && (
          <path
            d={`M ${p0.x} ${p0.y} A ${r} ${r} 0 ${largeArc} 1 ${pEnd.x} ${pEnd.y}`}
            stroke={color}
            strokeWidth="8"
            fill="none"
            strokeLinecap="butt"
          />
        )}
        {/* ticks */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const a = start - t * Math.PI;
          const p1 = polar(a);
          const p2 = { x: cx + (r - 10) * Math.cos(a), y: cy + (r - 10) * Math.sin(a) };
          return <line key={t} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#0A0A0A" strokeWidth="1" />;
        })}
      </svg>
      <div className="-mt-16 text-center">
        <div className="serif text-6xl leading-none" data-testid={testId ? `${testId}-value` : undefined}>{value.toFixed(1)}</div>
        <div className="label-xs mt-2">{label}</div>
      </div>
    </div>
  );
}
