export function OnboardingDecorativePanel() {
  // --- render helpers ---
  const renderDotGrid = () => {
    const cols = 24
    const rows = 32
    const dots = Array.from({ length: cols * rows }, (_, i) => i)
    return (
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${cols * 20} ${rows * 20}`}
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 opacity-20"
      >
        {dots.map((i) => {
          const cx = (i % cols) * 20 + 10
          const cy = Math.floor(i / cols) * 20 + 10
          return <circle key={i} cx={cx} cy={cy} r={1} fill="currentColor" className="text-border" />
        })}
      </svg>
    )
  }

  const renderWireframe = () => (
    <svg
      viewBox="0 0 400 500"
      className="absolute inset-0 m-auto h-[70%] w-[70%] opacity-10"
      fill="none"
      stroke="currentColor"
      strokeWidth="0.5"
    >
      {/* outer box */}
      <rect x="40" y="40" width="320" height="420" className="text-foreground" />
      {/* inner dividers */}
      <line x1="40" y1="100" x2="360" y2="100" className="text-foreground" />
      <line x1="40" y1="160" x2="360" y2="160" className="text-foreground" />
      <line x1="200" y1="160" x2="200" y2="460" className="text-foreground" />
      {/* top bar sections */}
      <rect x="60" y="60" width="80" height="20" className="text-foreground" />
      <rect x="160" y="60" width="40" height="20" className="text-foreground" />
      <rect x="220" y="60" width="40" height="20" className="text-foreground" />
      <rect x="280" y="60" width="60" height="20" className="text-foreground" />
      {/* grid cells */}
      {[0, 1, 2, 3, 4, 5].map((row) => (
        <g key={row}>
          <rect x="60" y={180 + row * 40} width="120" height="25" className="text-foreground" />
          <rect x="220" y={180 + row * 40} width="120" height="25" className="text-foreground" />
        </g>
      ))}
      {/* corner brackets */}
      <path d="M40,40 L60,40 L60,60" className="text-foreground" strokeWidth="1.5" />
      <path d="M360,40 L340,40 L340,60" className="text-foreground" strokeWidth="1.5" />
      <path d="M40,460 L60,460 L60,440" className="text-foreground" strokeWidth="1.5" />
      <path d="M360,460 L340,460 L340,440" className="text-foreground" strokeWidth="1.5" />
    </svg>
  )

  const renderLabel = () => (
    <div className="absolute bottom-6 left-0 right-0 flex justify-center">
      <span className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/30">
        ZENVE / ONBOARDING
      </span>
    </div>
  )

  // --- return ---
  return (
    <div className="relative h-full w-full overflow-hidden bg-muted/10">
      {renderDotGrid()}
      {renderWireframe()}
      {renderLabel()}
    </div>
  )
}
