import type { SVGProps } from 'react'
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { cn } from '@/lib/utils'

const DAY_BUCKET_BAR_CHART_DEFAULT_HEIGHT_PX = 136

/** Matches prior CSS bars: `min-h-[2px]` so zero days still read as “present”. */
const BAR_MIN_HEIGHT_PX = 2

/** Clearance between adjacent bars (bar face to bar face). */
const INTER_BAR_GAP_PX = 4

/**
 * Recharts treats numeric `barCategoryGap` as horizontal inset on each side of the category band.
 * With no `maxBarSize`, the bar fills the inner width, so gap between neighbours = 2 × this value.
 */
const BAR_CATEGORY_GAP_PX = INTER_BAR_GAP_PX / 2

/** Mirrors `combineAllBarPositions` for a single `<Bar>` per category, no `maxBarSize` (see recharts). */
function barSlotInBand(bandWidth: number): { barW: number; barInset: number } {
  const pad = BAR_CATEGORY_GAP_PX
  let originalSize = bandWidth - 2 * pad
  if (originalSize > 1) originalSize = Math.floor(originalSize)
  const barW = Math.max(0, originalSize)
  return { barW, barInset: pad }
}

function MatchedBarTooltipCursor(props: SVGProps<SVGRectElement>) {
  const bandW = typeof props.width === 'number' ? props.width : 0
  const baseX = typeof props.x === 'number' ? props.x : 0
  const { barW, barInset } = barSlotInBand(bandW)
  return (
    <rect
      x={baseX + barInset}
      y={props.y}
      width={barW}
      height={props.height}
      className={cn('fill-muted/25', props.className)}
      pointerEvents="none"
    />
  )
}

function PinnedFloorBar(props: {
  x?: number
  y?: number
  width?: number
  height?: number
  fill?: string
}) {
  const x = props.x ?? 0
  const y = props.y ?? 0
  const width = props.width ?? 0
  const height = props.height ?? 0
  const bottom = y + height
  const h = Math.max(height, BAR_MIN_HEIGHT_PX)
  const yy = bottom - h
  return <rect x={x} y={yy} width={width} height={h} fill={props.fill} />
}

export interface DayBucket {
  label: string
  dateKey: string
  value: number
}

/** One calendar day bucket with grouped items (oldest → newest in the returned array). */
export interface DayGroup<T = unknown> {
  label: string
  dateKey: string
  items: T[]
}

/** `YYYY-MM-DD` for the given instant in the **local** calendar (not UTC slice of ISO string). */
export function formatLocalCalendarDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Local calendar `YYYY-MM-DD` for an ISO / date string (e.g. run `createdAt`). */
export function timestampToLocalCalendarDateKey(iso: string): string {
  return formatLocalCalendarDateKey(new Date(iso))
}

/**
 * Last `days` **local calendar** days ending on `referenceDate`’s date (default: today),
 * not anchored to the newest item and not rolling raw 24h steps from `Date.now()`.
 * Match items with `getItemDateKey` returning the same `YYYY-MM-DD` keys (e.g. `timestampToLocalCalendarDateKey`).
 */
export function buildDayGroupsForLastNDays<T>(
  items: T[],
  getItemDateKey: (item: T) => string,
  options?: { days?: number; referenceDate?: Date },
): DayGroup<T>[] {
  const days = options?.days ?? 7
  const ref = options?.referenceDate ?? new Date()
  const groups: DayGroup<T>[] = []

  const end = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate())

  for (let back = days - 1; back >= 0; back -= 1) {
    const d = new Date(end)
    d.setDate(d.getDate() - back)
    const dateKey = formatLocalCalendarDateKey(d)
    const dayNum = String(d.getDate()).padStart(2, '0')
    const month = d.toLocaleDateString('en-US', { month: 'short' })
    const label = `${dayNum}/${month}`
    groups.push({ label, dateKey, items: [] })
  }

  for (const item of items) {
    const key = getItemDateKey(item)
    const group = groups.find((g) => g.dateKey === key)
    if (group) group.items.push(item)
  }
  return groups
}

export type DayBucketBarChartProps = {
  buckets: DayBucket[]
  config: ChartConfig
  emptyLabel: string
  formatTooltipValue?: (v: number) => string
  /** Fixed chart height in px (empty state uses the same height). Default matches compact dashboard tiles. */
  heightPx?: number
  className?: string
  /** Merged into `ChartContainer` when data is present. */
  chartClassName?: string
  /** Merged into the empty-state wrapper. */
  emptyClassName?: string
}

export function DayBucketBarChart({
  buckets,
  config,
  emptyLabel,
  formatTooltipValue,
  heightPx = DAY_BUCKET_BAR_CHART_DEFAULT_HEIGHT_PX,
  className,
  chartClassName,
  emptyClassName,
}: DayBucketBarChartProps) {
  const hasData = buckets.some((b) => b.value > 0)
  const sizeStyle = {
    height: heightPx,
    minHeight: heightPx,
    maxHeight: heightPx,
  } as const

  if (!hasData) {
    return (
      <div
        className={cn(
          'flex w-full shrink-0 flex-col items-center justify-center gap-1',
          className,
          emptyClassName,
        )}
        style={sizeStyle}
      >
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground/50">{emptyLabel}</span>
      </div>
    )
  }
  const data = buckets.map((b) => ({ label: b.label, dateKey: b.dateKey, value: b.value }))
  return (
    <ChartContainer
      config={config}
      className={cn('aspect-auto w-full shrink-0', className, chartClassName)}
      style={sizeStyle}
    >
      <BarChart
        data={data}
        margin={{ top: 6, right: 2, left: 0, bottom: 4 }}
        barCategoryGap={BAR_CATEGORY_GAP_PX}
      >
        <CartesianGrid horizontal vertical={false} className="stroke-border/50" />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={6}
          interval={0}
          tick={{ fontSize: 9, fontFamily: 'ui-monospace, monospace' }}
          className="fill-muted-foreground/70"
        />
        <YAxis hide type="number" domain={[0, 'auto']} tickCount={5} />
        <ChartTooltip
          cursor={<MatchedBarTooltipCursor />}
          content={
            <ChartTooltipContent
              hideIndicator
              formatter={
                formatTooltipValue
                  ? (raw) => (
                      <span className="font-mono tabular-nums text-foreground">{formatTooltipValue(Number(raw))}</span>
                    )
                  : undefined
              }
            />
          }
        />
        <Bar dataKey="value" fill="var(--color-value)" radius={0} shape={PinnedFloorBar} />
      </BarChart>
    </ChartContainer>
  )
}
