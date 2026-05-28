import { ExternalLink, Sparkles } from 'lucide-react'
import Card from '../ui/Card'
import Badge from '../ui/Badge'
import type { RecommendedProblem } from '../../types'

interface Props {
  items?: RecommendedProblem[]
  weakTopics?: string[]
  isLoading: boolean
}

export default function RecommendedProblems({ items, weakTopics, isLoading }: Props) {
  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={14} className="text-blue-400" />
        <h2 className="text-sm font-medium text-gray-400">Recommended Next Problems</h2>
        {weakTopics && weakTopics.length > 0 && (
          <span className="text-xs text-gray-600 truncate">
            · targeting {weakTopics.slice(0, 3).map((t) => t.replace(/-/g, ' ')).join(', ')}
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-9 bg-gray-800/50 rounded animate-pulse" />
          ))}
        </div>
      ) : !items || items.length === 0 ? (
        <p className="text-sm text-gray-600">No recommendations available right now.</p>
      ) : (
        <div className="space-y-1">
          {items.map((p) => (
            <div
              key={p.slug}
              className="flex items-center gap-3 px-2 py-2 rounded hover:bg-gray-800/50 transition-colors"
            >
              <span className="flex-1 text-sm text-gray-200 truncate">{p.title}</span>
              {p.difficulty && (
                <Badge variant={p.difficulty as 'easy' | 'medium' | 'hard'}>{p.difficulty}</Badge>
              )}
              <Badge variant={p.platform === 'codeforces' ? 'gray' : 'blue'}>
                {p.platform === 'codeforces' ? 'CF' : 'LC'}
              </Badge>
              {p.url && (
                <a
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-600 hover:text-gray-400 transition-colors"
                >
                  <ExternalLink size={14} />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
