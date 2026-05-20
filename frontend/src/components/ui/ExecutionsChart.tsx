import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DailyStats } from '../../types'

interface ExecutionsChartProps {
  data: DailyStats[]
}

function formatDate(dateStr: string): string {
  const [, month, day] = dateStr.split('-')
  return `${month}/${day}`
}

export function ExecutionsChart({ data }: ExecutionsChartProps) {
  const chartData = data.map((d) => ({
    date: formatDate(d.date),
    Success: d.success,
    Failure: d.failure,
  }))

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <p className="mb-4 text-sm font-medium text-gray-500">Executions — Last 7 Days</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} barSize={16}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Success" fill="#22c55e" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Failure" fill="#ef4444" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
