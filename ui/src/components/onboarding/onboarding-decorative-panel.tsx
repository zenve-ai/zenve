import { Bot, GitPullRequest, ShieldCheck, Zap, FileText, Rocket } from 'lucide-react'

const AGENTS = [
  { icon: Bot, label: 'Dev Agent', desc: 'Code generation & review' },
  { icon: GitPullRequest, label: 'PR Reviewer', desc: 'Automated pull request analysis' },
  { icon: ShieldCheck, label: 'Sec Audit', desc: 'Vulnerability scanning' },
  { icon: FileText, label: 'Doc Writer', desc: 'Documentation generation' },
  { icon: Zap, label: 'Test Gen', desc: 'Test suite generation' },
  { icon: Rocket, label: 'Deploy Agent', desc: 'CI/CD pipeline automation' },
]

const PlusCorner = ({ x, y }: { x: number; y: number }) => (
  <g transform={`translate(${x - 6}, ${y - 6})`}>
    <line x1="6" y1="2" x2="6" y2="10" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5" />
    <line x1="2" y1="6" x2="10" y2="6" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5" />
  </g>
)

export function OnboardingDecorativePanel() {
  // --- render helpers ---
  const renderBackground = () => (
    <>
      {/* grid lines */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
        }}
      />

      {/* top-left decorative box */}
      <svg className="absolute top-8 left-8 pointer-events-none" width="140" height="80" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="140" height="80" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <PlusCorner x={0} y={0} />
        <PlusCorner x={140} y={0} />
        <PlusCorner x={0} y={80} />
        <PlusCorner x={140} y={80} />
      </svg>

      {/* bottom-right decorative box */}
      <svg className="absolute bottom-8 right-8 pointer-events-none" width="160" height="80" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="160" height="80" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <PlusCorner x={0} y={0} />
        <PlusCorner x={160} y={0} />
        <PlusCorner x={0} y={80} />
        <PlusCorner x={160} y={80} />
      </svg>

      {/* radial vignette */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.55) 100%)',
        }}
      />
    </>
  )

  const renderContent = () => (
    <div className="relative z-10 flex h-full flex-col items-center justify-center px-10 py-12">
      {/* badge */}
      <div className="mb-8 flex items-center gap-2 border border-white/15 bg-white/5 px-3 py-1.5">
        <span className="size-1.5 rounded-full bg-emerald-400" />
        <span className="font-mono text-[10px] tracking-widest uppercase text-white/50">
          Agent Runtime Active
        </span>
      </div>

      {/* headline */}
      <h2 className="mb-4 text-center text-3xl font-bold leading-tight tracking-tight text-white">
        Automate your codebase<br />
        <span className="bg-gradient-to-r from-white via-white/70 to-white/30 bg-clip-text text-transparent">
          with AI agents
        </span>
      </h2>

      {/* description */}
      <p className="mb-10 max-w-xs text-center font-mono text-[12px] leading-relaxed text-white/35">
        Connect your repo and deploy specialized agents that respond to code events in real time.
      </p>

      {/* agent cards */}
      <div className="grid w-full max-w-sm grid-cols-2 gap-2">
        {AGENTS.map(({ icon: Icon, label, desc }) => (
          <div
            key={label}
            className="flex items-start gap-2.5 border border-white/10 bg-white/5 p-3 backdrop-blur-sm"
          >
            <div className="mt-0.5 shrink-0 rounded-none bg-white/10 p-1.5">
              <Icon className="size-3.5 text-white/60" />
            </div>
            <div>
              <p className="font-mono text-[11px] font-medium leading-tight text-white/80">{label}</p>
              <p className="mt-0.5 font-mono text-[9px] leading-tight text-white/30">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* bottom label */}
      <p className="mt-8 font-mono text-[10px] tracking-widest uppercase text-white/20">
        ZENVE / ONBOARDING
      </p>
    </div>
  )

  // --- return ---
  return (
    <div className="relative h-full w-full overflow-hidden bg-black">
      {renderBackground()}
      {renderContent()}
    </div>
  )
}
