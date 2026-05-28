import { useState } from 'react'
import { ExternalLink, CheckCircle2, Circle, Minus } from 'lucide-react'
import Badge from '../ui/Badge'
import type { Question, QuestionProgress } from '../../types'
import { updateQuestionProgress } from '../../api/questions'

interface Props {
  question: Question
  status?: QuestionProgress['status']
  onStatusChange?: (id: string, status: QuestionProgress['status']) => void
}

const STATUS_CYCLE: QuestionProgress['status'][] = ['todo', 'attempted', 'done']

export default function QuestionRow({ question, status = 'todo', onStatusChange }: Props) {
  const [localStatus, setLocalStatus] = useState(status)

  const cycleStatus = async () => {
    const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(localStatus) + 1) % STATUS_CYCLE.length]
    setLocalStatus(next)
    onStatusChange?.(question.id, next)
    try {
      await updateQuestionProgress(question.id, next)
    } catch {
      setLocalStatus(localStatus)
    }
  }

  const StatusIcon = localStatus === 'done' ? CheckCircle2 : localStatus === 'attempted' ? Minus : Circle

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-800/50 border-b border-gray-800/50 last:border-0">
      <button onClick={cycleStatus} className="shrink-0">
        <StatusIcon
          size={16}
          className={
            localStatus === 'done'
              ? 'text-green-400'
              : localStatus === 'attempted'
                ? 'text-yellow-400'
                : 'text-gray-600'
          }
        />
      </button>

      <span className="text-gray-500 text-xs w-12 shrink-0">
        {question.platform === 'leetcode' ? '#' : ''}{question.number}
      </span>

      <span className="flex-1 text-sm text-gray-200 truncate">{question.title}</span>

      <div className="flex items-center gap-2 shrink-0">
        <Badge variant={question.difficulty as 'easy' | 'medium' | 'hard'}>{question.difficulty}</Badge>
        <Badge variant={question.platform === 'leetcode' ? 'blue' : 'gray'}>
          {question.platform === 'leetcode' ? 'LC' : 'CF'}
        </Badge>
        {(question.companies ?? []).slice(0, 2).map((c) => (
          <Badge key={c} variant="gray" className="hidden md:inline-flex">{c}</Badge>
        ))}
        <a
          href={question.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-600 hover:text-gray-400 transition-colors"
        >
          <ExternalLink size={14} />
        </a>
      </div>
    </div>
  )
}
