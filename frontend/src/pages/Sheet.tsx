import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getCuratedSheet, getSheetSources, getMySheetProgress, updateSheetProgress } from '../api/sheet'
import TopicAccordion from '../components/questions/TopicAccordion'
import type { Question, QuestionProgress } from '../types'

const TOPIC_ORDER = [
  'arrays','strings','hashing','two-pointers','sliding-window','prefix-sum',
  'binary-search','linked-list','stacks-queues','recursion','backtracking',
  'trees','bst','heap','greedy','dynamic-programming','graphs','tries',
  'segment-trees','bit-manipulation','math','string-algorithms',
]

const DISPLAY_NAMES: Record<string, string> = {
  'arrays': 'Arrays', 'strings': 'Strings', 'hashing': 'Hashing',
  'two-pointers': 'Two Pointers', 'sliding-window': 'Sliding Window',
  'prefix-sum': 'Prefix Sum', 'binary-search': 'Binary Search',
  'linked-list': 'Linked List', 'stacks-queues': 'Stacks & Queues',
  'recursion': 'Recursion', 'backtracking': 'Backtracking',
  'trees': 'Trees', 'bst': 'BST', 'heap': 'Heap / Priority Queue',
  'greedy': 'Greedy', 'dynamic-programming': 'Dynamic Programming',
  'graphs': 'Graphs', 'tries': 'Tries', 'segment-trees': 'Segment Trees',
  'bit-manipulation': 'Bit Manipulation', 'math': 'Math',
  'string-algorithms': 'String Algorithms',
}

export default function Sheet() {
  const queryClient = useQueryClient()
  const { data: sheet, isLoading } = useQuery({ queryKey: ['sheet'], queryFn: getCuratedSheet })
  const { data: sources } = useQuery({ queryKey: ['sheet-sources'], queryFn: getSheetSources })
  const { data: sheetProgress } = useQuery({ queryKey: ['sheet-progress'], queryFn: getMySheetProgress })

  // Optimistic local overrides layered on top of the server-hydrated map.
  const [overrides, setOverrides] = useState<Record<string, QuestionProgress['status']>>({})
  const progress = { ...(sheetProgress?.progress_map ?? {}), ...overrides }

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: QuestionProgress['status'] }) =>
      updateSheetProgress(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sheet-progress'] })
      // Step-7 Fix 2 busts the stats:/readiness: Redis keys on a sheet write; refetch them
      // so the sidebar OverallProgress bar reflects the new sheet completion.
      queryClient.invalidateQueries({ queryKey: ['readiness'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const handleStatusChange = (id: string, status: QuestionProgress['status']) => {
    setOverrides((prev) => ({ ...prev, [id]: status }))
    mutation.mutate({ id, status })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  const totalProblems = Object.values(sheet || {}).reduce((s, arr) => s + arr.length, 0)
  const doneCount = Object.values(progress).filter((s) => s === 'done').length

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Curated Sheet</h1>
          <p className="text-gray-400 text-sm mt-1">
            Optimal mix of {totalProblems} problems · {doneCount} solved
          </p>
        </div>
      </div>

      {sources && sources.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          <span className="text-xs text-gray-500">Sources:</span>
          {sources.filter((s) => s.problem_count > 0).map((s) => (
            <span key={s.id} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded border border-gray-700">
              {s.name}
            </span>
          ))}
        </div>
      )}

      <div className="space-y-2">
        {TOPIC_ORDER.map((topic) => {
          const problems = sheet?.[topic] || []
          if (!problems.length) return null
          const questions: Question[] = problems.map((p) => ({
            id: p.question_id,
            platform: p.platform ?? 'leetcode',
            title: p.title ?? p.question_id,
            url: p.url ?? '#',
            difficulty: p.difficulty ?? 'medium',
            slug: p.slug,
            is_premium: p.is_premium ?? false,
          }))
          return (
            <TopicAccordion
              key={topic}
              topic={topic}
              displayName={DISPLAY_NAMES[topic] || topic}
              questions={questions}
              progress={progress}
              onStatusChange={handleStatusChange}
            />
          )
        })}
      </div>
    </div>
  )
}
