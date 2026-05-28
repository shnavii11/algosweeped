import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyStats, triggerSync, getReadiness } from '../api/stats'
import ReadinessScore from '../components/dashboard/ReadinessScore'
import TopicTable from '../components/dashboard/TopicTable'
import PlatformCard from '../components/dashboard/PlatformCard'

// Snapshot raw_data is platform-shaped (LeetCode is deeply nested); flatten to
// a few headline numbers the generic PlatformCard can render.
function summarize(platform: string, raw?: Record<string, unknown>): Record<string, unknown> | undefined {
  if (!raw) return undefined
  const r = raw as any
  if (platform === 'leetcode') {
    const ac: { difficulty: string; count: number }[] = r.submitStatsGlobal?.acSubmissionNum ?? []
    const byDiff = Object.fromEntries(ac.map((d) => [d.difficulty, d.count]))
    return { solved: byDiff.All ?? 0, easy: byDiff.Easy ?? 0, medium: byDiff.Medium ?? 0, hard: byDiff.Hard ?? 0 }
  }
  if (platform === 'codeforces') {
    return { rating: r.rating, max_rating: r.maxRating, rank: r.rank, solved: r.problemsSolved }
  }
  return raw
}

export default function Dashboard() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['stats'], queryFn: getMyStats })
  const username = data?.user?.username
  const { data: readiness } = useQuery({
    queryKey: ['readiness', username],
    queryFn: () => getReadiness(username!),
    enabled: !!username,
  })
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
            {data?.user?.username}
            {data?.user?.last_synced && ` · synced ${new Date(data.user.last_synced).toLocaleDateString()}`}
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
        <ReadinessScore score={readiness?.total ?? 0} />
        <PlatformCard platform="leetcode" data={summarize('leetcode', data?.snapshots?.leetcode?.data)} />
        <PlatformCard platform="codeforces" data={summarize('codeforces', data?.snapshots?.codeforces?.data)} />
      </div>

      {data?.topic_scores && <TopicTable topics={data.topic_scores} />}
    </div>
  )
}
