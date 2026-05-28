import { useQuery } from '@tanstack/react-query'
import { getRoadmap } from '../api/roadmap'
import { ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Card from '../components/ui/Card'

export default function Roadmap() {
  const { data: topics, isLoading } = useQuery({ queryKey: ['roadmap'], queryFn: getRoadmap })
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">DSA Roadmap</h1>
      <p className="text-gray-400 text-sm mb-6">Topics in pedagogical order. Click any topic to see its problems.</p>

      <div className="space-y-3">
        {topics?.map((t, i) => (
          <Card key={t.topic} className="cursor-pointer hover:border-gray-700 transition-colors" >
            <div
              className="flex items-start gap-4"
              onClick={() => navigate(`/questions?topic=${t.topic}`)}
            >
              <div className="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-600/40 flex items-center justify-center shrink-0 text-sm font-bold text-blue-400">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-200">{t.display_name}</h3>
                  {t.prerequisite_topics?.length > 0 && (
                    <span className="text-xs text-gray-600">
                      after: {t.prerequisite_topics.join(', ')}
                    </span>
                  )}
                </div>
                {t.summary && <p className="text-sm text-gray-500 mt-1">{t.summary}</p>}
                {t.core_patterns?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {t.core_patterns.map((p) => (
                      <span key={p} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{p}</span>
                    ))}
                  </div>
                )}
              </div>
              <ChevronRight size={16} className="text-gray-600 shrink-0 mt-1" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
