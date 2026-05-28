import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMe, updateProfile } from '../api/auth'
import Card from '../components/ui/Card'

export default function Profile() {
  const qc = useQueryClient()
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: getMe })
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ lc_username: '', cf_handle: '', gh_username: '' })

  const mutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['me'] }); setEditing(false) },
  })

  if (!user) return null

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold text-white">Profile</h1>
      <Card>
        <div className="flex items-center gap-4 mb-4">
          {user.avatar_url && (
            <img src={user.avatar_url} alt={user.name} className="w-16 h-16 rounded-full" />
          )}
          <div>
            <p className="font-semibold text-white">{user.name}</p>
            <p className="text-gray-400 text-sm">@{user.username}</p>
            {user.college && <p className="text-gray-500 text-xs">{user.college}</p>}
          </div>
        </div>

        {editing ? (
          <div className="space-y-3">
            {['lc_username', 'cf_handle', 'gh_username'].map((field) => (
              <div key={field}>
                <label className="text-xs text-gray-400 mb-1 block capitalize">{field.replace(/_/g, ' ')}</label>
                <input
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                  value={form[field as keyof typeof form] || (user[field as keyof typeof user] as string) || ''}
                  onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
                  placeholder={field.replace(/_/g, ' ')}
                />
              </div>
            ))}
            <div className="flex gap-2">
              <button
                onClick={() => mutation.mutate(form)}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-2 bg-gray-800 text-gray-300 text-sm rounded-lg hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {[
              { label: 'LeetCode', value: user.lc_username },
              { label: 'Codeforces', value: user.cf_handle },
              { label: 'GitHub', value: user.gh_username },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between text-sm">
                <span className="text-gray-500">{label}</span>
                <span className="text-gray-300">{value || <span className="text-gray-600">not set</span>}</span>
              </div>
            ))}
            <button
              onClick={() => { setForm({ lc_username: user.lc_username || '', cf_handle: user.cf_handle || '', gh_username: user.gh_username || '' }); setEditing(true) }}
              className="mt-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              Edit platforms
            </button>
          </div>
        )}
      </Card>
    </div>
  )
}
