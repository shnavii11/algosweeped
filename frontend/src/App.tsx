import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Questions from './pages/Questions'
import Roadmap from './pages/Roadmap'
import Sheet from './pages/Sheet'
import Profile from './pages/Profile'
import Onboarding from './pages/Onboarding'
import Layout from './components/ui/Layout'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding" element={<RequireAuth><Onboarding /></RequireAuth>} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/questions" element={<Questions />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="/sheet" element={<Sheet />} />
          <Route path="/profile/:username?" element={<Profile />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
