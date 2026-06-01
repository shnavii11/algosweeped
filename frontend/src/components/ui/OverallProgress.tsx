import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { getReadiness, getMyStats } from '../../api/stats'
import { getMySheetProgress } from '../../api/sheet'

// Overall sidebar progress = 50/50 blend of platform problem-solving and curated-sheet completion.
//   overall = round( (readiness.breakdown.dsa_consistency + sheetProgress.pct) / 2 )
// Platforms half = dsa_consistency (LC+CF, already 0-100). Sheet half = sheetProgress.pct (done/406).
// GitHub and topic-coverage are intentionally excluded. Clamp to [0,100].
export function computeOverall(dsaConsistency: number, sheetPct: number): number {
  const avg = (dsaConsistency + sheetPct) / 2
  return Math.max(0, Math.min(100, Math.round(avg)))
}

// Mirror Dashboard.tsx:summarize field paths for the subtext counts.
function lcSolved(raw?: Record<string, unknown>): number | undefined {
  if (!raw) return undefined
  const ac: { difficulty: string; count: number }[] = (raw as any).submitStatsGlobal?.acSubmissionNum ?? []
  const all = ac.find((d) => d.difficulty === 'All')
  return all?.count ?? 0
}

function cfSolved(raw?: Record<string, unknown>): number | undefined {
  if (!raw) return undefined
  return (raw as any).problemsSolved ?? 0
}

export default function OverallProgress() {
  // Reuse the same query keys as Dashboard / Sheet so React Query serves these from cache.
  const username = useAuthStore((s) => s.user)?.username

  const { data: readiness } = useQuery({
    queryKey: ['readiness', username],
    queryFn: () => getReadiness(username!),
    enabled: !!username,
  })
  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: getMyStats })
  const { data: sheetProgress } = useQuery({ queryKey: ['sheet-progress'], queryFn: getMySheetProgress })

  const dsa = readiness?.breakdown?.dsa_consistency ?? 0
  const pct = sheetProgress?.pct ?? 0
  const overall = computeOverall(dsa, pct)

  // While the underlying queries are still loading, show dashes rather than misleading 0s.
  const ready = readiness !== undefined && sheetProgress !== undefined

  const lc = lcSolved(stats?.snapshots?.leetcode?.data)
  const cf = cfSolved(stats?.snapshots?.codeforces?.data)
  const done = sheetProgress?.done
  const total = sheetProgress?.total

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium text-gray-400">Overall Progress</span>
        <span className="text-sm font-semibold text-white">{ready ? `${overall}%` : '—'}</span>
      </div>
      {/* Bar styling mirrors components/questions/TopicAccordion.tsx */}
      <div className="mt-2 h-1.5 rounded-full bg-gray-800 overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${ready ? overall : 0}%` }}
        />
      </div>
      <p className="mt-2 text-[11px] text-gray-500 truncate">
        LC {lc ?? '–'} · CF {cf ?? '–'} · Sheet {done ?? '–'}/{total ?? '–'}
      </p>
    </div>
  )
}
