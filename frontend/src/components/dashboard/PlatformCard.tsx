import Card from '../ui/Card'
import { RefreshCw } from 'lucide-react'

interface Props {
  platform: string
  data?: Record<string, unknown>
  onSync?: () => void
  syncing?: boolean
}

export default function PlatformCard({ platform, data, onSync, syncing }: Props) {
  const label = platform === 'leetcode' ? 'LeetCode' : platform === 'codeforces' ? 'Codeforces' : 'GitHub'

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-400">{label}</h3>
        {onSync && (
          <button
            onClick={onSync}
            disabled={syncing}
            className="text-gray-600 hover:text-gray-400 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
          </button>
        )}
      </div>
      {data ? (
        <div className="space-y-1">
          {Object.entries(data)
            .filter(([, v]) => typeof v === 'number' || typeof v === 'string')
            .slice(0, 5)
            .map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm">
                <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}</span>
                <span className="text-gray-300 font-medium">{String(v)}</span>
              </div>
            ))}
        </div>
      ) : (
        <p className="text-sm text-gray-600">Not connected</p>
      )}
    </Card>
  )
}
