import { useEffect, useState } from 'react'

const FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

export function RunLoadingIndicator({ elapsedSeconds }: { elapsedSeconds: number }) {
  const [frame, setFrame] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setFrame((f) => (f + 1) % FRAMES.length), 150)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="px-3 py-2 font-mono text-[11px] text-slate-400">
      {FRAMES[frame]} running ({elapsedSeconds}s)
    </div>
  )
}
