import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { updateProfile } from '../api/auth'

export default function Onboarding() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ lc_username: '', cf_handle: '', gh_username: '' })
  const mutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: () => navigate('/dashboard'),
  })

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-white mb-2">Connect your accounts</h1>
        <p className="text-gray-400 text-sm mb-6">Add your handles to start tracking progress.</p>
        <div className="space-y-3">
          {[
            { key: 'lc_username', label: 'LeetCode username', placeholder: 'e.g. johndoe' },
            { key: 'cf_handle', label: 'Codeforces handle', placeholder: 'e.g. tourist' },
            { key: 'gh_username', label: 'GitHub username', placeholder: 'e.g. johndoe' },
          ].map(({ key, label, placeholder }) => (
            <div key={key}>
              <label className="text-xs text-gray-400 mb-1 block">{label}</label>
              <input
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                placeholder={placeholder}
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              />
            </div>
          ))}
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {mutation.isPending ? 'Saving...' : 'Continue to Dashboard'}
          </button>
          <button onClick={() => navigate('/dashboard')} className="w-full text-center text-xs text-gray-600 hover:text-gray-400 transition-colors">
            Skip for now
          </button>
        </div>
      </div>
    </div>
  )
}
