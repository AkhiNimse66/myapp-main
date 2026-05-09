/**
 * AthanniLogo — shared logo component.
 *
 * Renders "athanni" (dotless-i) in Instrument Serif, with a copper coin
 * circle sitting exactly where the dot of the final "i" would be.
 *
 * Uses CSS positioning (not SVG text metrics) so it works reliably
 * regardless of font-load state or browser rendering differences.
 *
 * Usage:
 *   <AthanniLogo size="md" dark={false} />
 *
 * size: "sm" (nav, 20px) | "md" (default, 28px) | "lg" (hero, 44px)
 * dark: false = ink on transparent | true = cream on transparent
 */
import React from "react";

const SIZES = {
  sm: { fontSize: 20, coinSize: 8,  coinTop: -7  },
  md: { fontSize: 28, coinSize: 11, coinTop: -10 },
  lg: { fontSize: 44, coinSize: 17, coinTop: -15 },
};

export function AthanniLogo({ size = "md", dark = false }) {
  const cfg = SIZES[size] || SIZES.md;
  const textColor = dark ? "#EDE8DC" : "#0A0A0A";

  return (
    <span
      aria-label="Athanni"
      style={{
        display: "inline-flex",
        alignItems: "baseline",
        fontFamily: "'Instrument Serif', Georgia, 'Times New Roman', serif",
        fontSize: cfg.fontSize,
        color: textColor,
        letterSpacing: "-0.02em",
        lineHeight: 1,
        userSelect: "none",
      }}
    >
      {/* "athann" — browser handles natural font spacing */}
      athann
      {/* dotless-i: coin circle sits where the dot would be */}
      <span style={{ position: "relative", display: "inline-block" }}>
        {/* U+0131 LATIN SMALL LETTER DOTLESS I */}
        ı
        {/* Coin — radial gradient mimics the metallic 25 paise coin:
              bright gold highlight (upper-left) → warm amber → dark bronze edge */}
        <span
          aria-hidden="true"
          style={{
            position: "absolute",
            top: cfg.coinTop,
            left: "50%",
            transform: "translateX(-50%)",
            width: cfg.coinSize,
            height: cfg.coinSize,
            borderRadius: "50%",
            background: "radial-gradient(circle at 36% 30%, #E8C060 0%, #C4872A 38%, #A86020 68%, #7A3E12 100%)",
            display: "block",
            pointerEvents: "none",
          }}
        />
      </span>
    </span>
  );
}

/**
 * AthanniMarkOnly — just the coin mark (no wordmark).
 * Used as a standalone icon / favicon-like mark.
 */
export function AthanniMarkOnly({ size = 36, dark = false }) {
  const color  = dark ? "#EDE8DC" : "#0A0A0A";
  const r      = size / 2;
  const cx     = r;
  const cy     = r;
  const outerR = r - 1;
  const innerR = outerR * 0.72;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Athanni"
    >
      <circle
        cx={cx} cy={cy} r={outerR}
        stroke={color} strokeWidth="1.2"
        strokeDasharray="2 1.8"
      />
      <circle cx={cx} cy={cy} r={innerR} stroke={color} strokeWidth="0.7" />
      <text
        x={cx} y={cy - innerR * 0.42}
        fontFamily="Georgia, serif"
        fontSize={size * 0.115}
        fill={color}
        textAnchor="middle"
        dominantBaseline="middle"
        letterSpacing={size * 0.045}
      >
        PAISE
      </text>
      <text
        x={cx} y={cy + innerR * 0.1}
        fontFamily="Georgia, serif"
        fontSize={size * 0.38}
        fill={color}
        textAnchor="middle"
        dominantBaseline="middle"
      >
        25
      </text>
      <path
        d={`M${cx - innerR * 0.55} ${cy + innerR * 0.75} Q${cx - innerR * 0.42} ${cy + innerR * 0.45} ${cx - innerR * 0.28} ${cy + innerR * 0.28}`}
        stroke={color} strokeWidth="0.6" strokeLinecap="round"
      />
      <path
        d={`M${cx + innerR * 0.55} ${cy + innerR * 0.75} Q${cx + innerR * 0.42} ${cy + innerR * 0.45} ${cx + innerR * 0.28} ${cy + innerR * 0.28}`}
        stroke={color} strokeWidth="0.6" strokeLinecap="round"
      />
      <circle cx={cx} cy={cy + innerR * 0.82} r={size * 0.022} fill={color} />
    </svg>
  );
}
