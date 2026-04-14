import { DayBucketBarChart, type DayBucketBarChartProps } from '@/components/ui/day-bucket-bar-chart'

export type AgentDashboardBarChartCardProps = {
  title: string
  subtitle: string
} & DayBucketBarChartProps

export function AgentDashboardBarChartCard({
  title,
  subtitle,
  ...chartProps
}: AgentDashboardBarChartCardProps) {
  return (
    <div className="flex min-w-0 flex-col border border-border bg-card">
      <div className="border-b border-border/60 px-2 py-1.5">
        <p className="text-[12px] font-medium">{title}</p>
        <p className="text-[10px] text-muted-foreground">{subtitle}</p>
      </div>
      <div className="p-2">
        <DayBucketBarChart {...chartProps} />
      </div>
    </div>
  )
}
