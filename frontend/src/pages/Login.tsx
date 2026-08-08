import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Github } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const t = params.get('token')
    if (t) {
      useAuthStore.getState().setToken(t)
      navigate(params.get('new') === '1' ? '/onboarding' : '/dashboard', { replace: true })
    }
  }, [navigate])

  useEffect(() => {
    if (token) navigate('/dashboard', { replace: true })
  }, [token, navigate])

  const handleGithubLogin = () => {
    // In prod VITE_API_URL is the backend origin; in dev the vite proxy maps /api → :8000.
    const base = import.meta.env.VITE_API_URL ?? '/api'
    window.location.href = `${base}/auth/github`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">AlgoSweeped</h1>
          <p className="text-gray-400">Your developer progress dashboard</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          <button
            onClick={handleGithubLogin}
            className="w-full flex items-center justify-center gap-3 bg-white text-gray-900 font-medium py-3 px-4 rounded-xl hover:bg-gray-100 transition-colors"
          >
            <Github size={20} />
            Continue with GitHub
          </button>
          <p className="text-center text-xs text-gray-600 mt-4">
            Track your LeetCode, Codeforces &amp; GitHub progress
          </p>
        </div>
      </div>
    </div>
  )
}
