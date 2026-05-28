import { Search, X } from 'lucide-react'

interface Filters {
  q: string
  difficulty: string
  platform: string
  topic: string
}

interface Props {
  filters: Filters
  onChange: (f: Partial<Filters>) => void
}

export default function QuestionFilterBar({ filters, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-3 p-4 bg-gray-900 border-b border-gray-800">
      <div className="relative flex-1 min-w-48">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          placeholder="Search problems..."
          value={filters.q}
          onChange={(e) => onChange({ q: e.target.value })}
        />
        {filters.q && (
          <button onClick={() => onChange({ q: '' })} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
            <X size={12} />
          </button>
        )}
      </div>

      <select
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
        value={filters.difficulty}
        onChange={(e) => onChange({ difficulty: e.target.value })}
      >
        <option value="">All difficulties</option>
        <option value="easy">Easy</option>
        <option value="medium">Medium</option>
        <option value="hard">Hard</option>
      </select>

      <select
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
        value={filters.platform}
        onChange={(e) => onChange({ platform: e.target.value })}
      >
        <option value="">All platforms</option>
        <option value="leetcode">LeetCode</option>
        <option value="codeforces">Codeforces</option>
      </select>
    </div>
  )
}
