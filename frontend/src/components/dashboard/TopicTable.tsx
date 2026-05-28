import { useNavigate } from 'react-router-dom'
import Card from '../ui/Card'
import type { TopicScore } from '../../types'

interface Props {
  topics: TopicScore[]
}

export default function TopicTable({ topics }: Props) {
  const navigate = useNavigate()
  const sorted = [...topics].sort((a, b) => b.weakness_score - a.weakness_score)

  return (
    <Card>
      <h2 className="text-sm font-medium text-gray-400 mb-3">Topic Weakness Analysis</h2>
      <div className="space-y-2">
        {sorted.slice(0, 10).map((t) => (
          <div
            key={t.topic}
            className="flex items-center gap-3 cursor-pointer hover:bg-gray-800 -mx-2 px-2 py-1.5 rounded transition-colors"
            onClick={() => navigate(`/questions?topic=${t.topic}`)}
          >
            <span className="text-sm text-gray-300 w-32 truncate capitalize">{t.topic.replace(/-/g, ' ')}</span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(100, t.weakness_score * 100)}%`,
                  background: t.weakness_score > 0.7 ? '#ef4444' : t.weakness_score > 0.4 ? '#f59e0b' : '#22c55e',
                }}
              />
            </div>
            <span className="text-xs text-gray-500 w-16 text-right">
              {t.solved}/{t.attempted}
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}
