import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getQuestionsByTopic } from '../api/questions'
import TopicAccordion from '../components/questions/TopicAccordion'
import QuestionFilterBar from '../components/questions/QuestionFilterBar'
import RoadmapNav from '../components/questions/RoadmapNav'
import type { Question } from '../types'

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

interface Filters { q: string; difficulty: string; platform: string; topic: string }

export default function Questions() {
  const [searchParams] = useSearchParams()
  const { data: byTopic, isLoading } = useQuery({
    queryKey: ['questions-by-topic'],
    queryFn: getQuestionsByTopic,
    staleTime: 12 * 60 * 60 * 1000,
  })

  const [filters, setFilters] = useState<Filters>({
    q: '', difficulty: '', platform: '', topic: searchParams.get('topic') || '',
  })
  const [activeTopic, setActiveTopic] = useState(searchParams.get('topic') || '')
  const topicRefs = useRef<Record<string, HTMLDivElement | null>>({})

  useEffect(() => {
    if (activeTopic && topicRefs.current[activeTopic]) {
      topicRefs.current[activeTopic]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [activeTopic])

  const filterQuestions = (questions: Question[]) => {
    return questions.filter((q) => {
      if (filters.q && !q.title.toLowerCase().includes(filters.q.toLowerCase())) return false
      if (filters.difficulty && q.difficulty !== filters.difficulty) return false
      if (filters.platform && q.platform !== filters.platform) return false
      return true
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <RoadmapNav
        topics={TOPIC_ORDER}
        displayNames={DISPLAY_NAMES}
        active={activeTopic}
        onSelect={(t) => { setActiveTopic(t); setFilters((f) => ({ ...f, topic: t })) }}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        <QuestionFilterBar filters={filters} onChange={(f) => setFilters((prev) => ({ ...prev, ...f }))} />
        <div className="flex-1 overflow-y-auto p-4">
          {TOPIC_ORDER.map((topic) => {
            const questions = filterQuestions(byTopic?.[topic] || [])
            if (!questions.length) return null
            return (
              <div key={topic} ref={(el) => { topicRefs.current[topic] = el }}>
                <TopicAccordion
                  topic={topic}
                  displayName={DISPLAY_NAMES[topic] || topic}
                  questions={questions}
                  defaultOpen={activeTopic === topic}
                />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
