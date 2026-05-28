import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyStats, triggerSync } from '../api/stats'
import ReadinessScore from '../components/dashboard/ReadinessScore'
import TopicTable from '../components/dashboard/TopicTable'
import PlatformCard from '../components/dashboard/PlatformCard'

export default function Dashboard() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['stats'], queryFn: getMyStats })
  const [syncing, setSyncing] = useState(false)

  const syncMutation = useMutation({
    mutationFn: triggerSync,
    onSuccess: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['stats'] })
        setSyncing(false)
      }, 3000)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            {data?.user?.name || data?.user?.username}
            {data?.user?.college && ` · ${data.user.college}`}
          </p>
        </div>
        <button
          onClick={() => { setSyncing(true); syncMutation.mutate() }}
          disabled={syncing}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
        >
          {syncing ? 'Syncing...' : 'Sync Platforms'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ReadinessScore score={data?.readiness_score ?? 0} />
        <PlatformCard platform="leetcode" data={data?.platform_data?.leetcode as Record<string, unknown>} />
        <PlatformCard platform="codeforces" data={data?.platform_data?.codeforces as Record<string, unknown>} />
      </div>

      {data?.topic_scores && <TopicTable topics={data.topic_scores} />}
    </div>
  )
}
