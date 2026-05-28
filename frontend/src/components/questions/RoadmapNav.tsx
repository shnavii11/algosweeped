import clsx from 'clsx'

interface Props {
  topics: string[]
  displayNames: Record<string, string>
  active?: string
  onSelect: (topic: string) => void
}

export default function RoadmapNav({ topics, displayNames, active, onSelect }: Props) {
  return (
    <div className="w-48 shrink-0 space-y-1 py-4 px-2 bg-gray-900 border-r border-gray-800 overflow-y-auto">
      {topics.map((t, i) => (
        <button
          key={t}
          onClick={() => onSelect(t)}
          className={clsx(
            'w-full text-left px-3 py-1.5 rounded text-xs transition-colors',
            active === t
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-800',
          )}
        >
          <span className="text-gray-600 mr-2">{i + 1}.</span>
          {displayNames[t] || t}
        </button>
      ))}
    </div>
  )
}
