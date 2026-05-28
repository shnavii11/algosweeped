import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight } from 'lucide-react'
import Card from '../ui/Card'
import { getTopicExplanation } from '../../api/insights'
import type { TopicScore } from '../../types'

interface Props {
  topics: TopicScore[]
}

function TopicRow({ topic }: { topic: TopicScore }) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)

  const { data: explain, isLoading } = useQuery({
    queryKey: ['topic-explain', topic.topic],
    queryFn: () => getTopicExplanation(topic.topic),
    enabled: expanded,
    staleTime: Infinity,
  })

  return (
    <div>
      <div className="flex items-center gap-3 -mx-2 px-2 py-1.5 rounded hover:bg-gray-800 transition-colors">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="shrink-0 text-gray-600 hover:text-gray-300"
          title="Explain this gap"
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <span
          className="text-sm text-gray-300 w-32 truncate capitalize cursor-pointer"
          onClick={() => navigate(`/questions?topic=${topic.topic}`)}
        >
          {topic.topic.replace(/-/g, ' ')}
        </span>
        <div
          className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden cursor-pointer"
          onClick={() => navigate(`/questions?topic=${topic.topic}`)}
        >
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(100, topic.weakness_score * 100)}%`,
              background: topic.weakness_score > 0.7 ? '#ef4444' : topic.weakness_score > 0.4 ? '#f59e0b' : '#22c55e',
            }}
          />
        </div>
        <span className="text-xs text-gray-500 w-16 text-right">
          {topic.solved}/{topic.attempted}
        </span>
      </div>

      {expanded && (
        <div className="ml-7 mr-2 mt-1 mb-2 text-xs text-gray-400 leading-relaxed">
          {isLoading ? (
            <span className="text-gray-600">Analyzing…</span>
          ) : explain?.explanation ? (
            explain.explanation
          ) : (
            <span className="text-gray-600">Explanation unavailable right now.</span>
          )}
        </div>
      )}
    </div>
  )
}

export default function TopicTable({ topics }: Props) {
  const sorted = [...topics].sort((a, b) => b.weakness_score - a.weakness_score)

  return (
    <Card>
      <h2 className="text-sm font-medium text-gray-400 mb-3">Topic Weakness Analysis</h2>
      <div className="space-y-1">
        {sorted.slice(0, 10).map((t) => (
          <TopicRow key={t.topic} topic={t} />
        ))}
      </div>
    </Card>
  )
}
