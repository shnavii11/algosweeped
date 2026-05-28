import { useState } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import QuestionRow from './QuestionRow'
import type { Question, QuestionProgress } from '../../types'

interface Props {
  topic: string
  displayName: string
  questions: Question[]
  progress?: Record<string, QuestionProgress['status']>
  defaultOpen?: boolean
  onStatusChange?: (id: string, status: QuestionProgress['status']) => void
}

export default function TopicAccordion({ topic, displayName, questions, progress = {}, defaultOpen = false, onStatusChange }: Props) {
  const [open, setOpen] = useState(defaultOpen)
  const done = questions.filter((q) => progress[q.id] === 'done').length

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden mb-2">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-900 hover:bg-gray-800 transition-colors text-left"
      >
        {open ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
        <span className="font-medium text-gray-200 flex-1">{displayName}</span>
        <span className="text-xs text-gray-500">
          {done}/{questions.length}
        </span>
        <div
          className="w-16 h-1.5 rounded-full bg-gray-800 overflow-hidden ml-2"
          title={`${done}/${questions.length} solved`}
        >
          <div
            className="h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${questions.length ? (done / questions.length) * 100 : 0}%` }}
          />
        </div>
      </button>

      {open && (
        <div className="bg-gray-900/50">
          {questions.map((q) => (
            <QuestionRow key={q.id} question={q} status={progress[q.id]} onStatusChange={onStatusChange} />
          ))}
        </div>
      )}
    </div>
  )
}
