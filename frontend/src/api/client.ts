import axios from 'axios'
import { useAuthStore } from '../store/authStore'

// In prod set VITE_API_URL to the backend origin (e.g. https://algosweeped.onrender.com).
// In dev it falls back to '/api', which Vite proxies to http://localhost:8000.
const client = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '/api' })

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => {
    const body = res.data
    // Backend wraps most responses in {success, data, meta}. Unwrap to the
    // payload so callers receive the inner shape. Raw responses (e.g.
    // /users/me) have no `success` key and pass through untouched.
    if (body && typeof body === 'object' && 'success' in body && 'data' in body) {
      res.data = body.data
    }
    return res
  },
  (err) => {
    if (err.response?.status === 401) useAuthStore.getState().logout()
    return Promise.reject(err)
  },
)

export default client
