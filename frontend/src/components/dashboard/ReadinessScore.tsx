import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts'
import Card from '../ui/Card'

interface Props {
  score: number
}

export default function ReadinessScore({ score }: Props) {
  const data = [{ value: score, fill: '#3b82f6' }]
  const label =
    score >= 80 ? 'Interview Ready' : score >= 60 ? 'Getting There' : score >= 40 ? 'Keep Grinding' : 'Just Started'

  return (
    <Card className="flex flex-col items-center justify-center">
      <h2 className="text-sm font-medium text-gray-400 mb-2">Readiness Score</h2>
      <div className="relative w-36 h-36">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="70%"
            outerRadius="100%"
            data={data}
            startAngle={90}
            endAngle={90 - 360 * (score / 100)}
          >
            <RadialBar dataKey="value" background={{ fill: '#1f2937' }} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-white">{Math.round(score)}</span>
        </div>
      </div>
      <p className="text-sm text-blue-400 mt-2">{label}</p>
    </Card>
  )
}
