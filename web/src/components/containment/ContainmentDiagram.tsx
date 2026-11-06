const LANES = [
  { y: 52, label: "network: none", sub: "no DNS, no sockets out" },
  { y: 150, label: "environment: empty", sub: "no keys ever enter" },
  { y: 248, label: "30 s · 512 MB caps", sub: "then the container is destroyed" },
];

/** One input, the sealed processor, three containment lanes, with pulses running along the lines. */
export function ContainmentDiagram() {
  return (
    <svg viewBox="0 0 640 300" className="h-auto w-full" role="img" aria-labelledby="diagram-title">
      <title id="diagram-title">
        A CSV and the agent&apos;s code enter a gVisor sandbox. Three controls apply: no network, an empty environment,
        and time, memory and process caps.
      </title>
      <defs>
        <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" stroke="var(--p-line)" strokeWidth="2" />
        </pattern>
      </defs>

      <g fontFamily="var(--font-plex-mono)" fontSize="12">
        <rect x="8" y="118" width="120" height="64" rx="4" fill="var(--p-paper)" stroke="var(--p-ink)" />
        <text x="68" y="146" textAnchor="middle" fill="var(--p-ink)">input.csv</text>
        <text x="68" y="164" textAnchor="middle" fill="var(--p-muted)" fontSize="10">+ agent code</text>
      </g>

      <line x1="128" y1="150" x2="220" y2="150" stroke="var(--p-line)" strokeWidth="2" />
      <line x1="128" y1="150" x2="220" y2="150" stroke="var(--p-accent)" strokeWidth="2" strokeDasharray="14 106" style={{ animation: "pulse-line 2.8s linear infinite" }} />

      <rect x="220" y="70" width="170" height="160" rx="6" fill="url(#hatch)" stroke="var(--p-ink)" strokeWidth="1.5" />
      <rect x="236" y="86" width="138" height="128" rx="4" fill="var(--p-paper)" stroke="var(--p-ink)" />
      <g fontFamily="var(--font-plex-mono)" textAnchor="middle">
        <text x="305" y="130" fontSize="13" fill="var(--p-ink)">gVisor</text>
        <text x="305" y="148" fontSize="10" fill="var(--p-muted)">user-space kernel</text>
        <text x="305" y="178" fontSize="10" fill="var(--p-muted)">uid 1000, no caps</text>
        <text x="305" y="194" fontSize="10" fill="var(--p-muted)">read-only root</text>
      </g>

      {LANES.map((lane, i) => (
        <g key={lane.label}>
          <path d={`M390 150 C 430 150, 430 ${lane.y}, 470 ${lane.y}`} fill="none" stroke="var(--p-line)" strokeWidth="2" />
          <path
            d={`M390 150 C 430 150, 430 ${lane.y}, 470 ${lane.y}`}
            fill="none"
            stroke="var(--p-accent)"
            strokeWidth="2"
            strokeDasharray="14 106"
            style={{ animation: `pulse-line 2.8s ${0.4 + i * 0.3}s linear infinite` }}
          />
          <rect x="470" y={lane.y - 26} width="164" height="52" rx="4" fill="var(--p-paper)" stroke="var(--p-line)" />
          <circle cx="486" cy={lane.y - 6} r="4" fill="var(--p-accent)" />
          <text x="498" y={lane.y - 2} fontFamily="var(--font-plex-mono)" fontSize="11.5" fill="var(--p-ink)">{lane.label}</text>
          <text x="486" y={lane.y + 15} fontFamily="var(--font-plex-sans)" fontSize="10.5" fill="var(--p-muted)">{lane.sub}</text>
        </g>
      ))}
    </svg>
  );
}
