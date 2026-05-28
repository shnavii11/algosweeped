import { useQuery } from '@tanstack/react-query'
import { getMe } from '../api/auth'
import { useAuthStore } from '../store/authStore'

export function useMe() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['me'],
    queryFn: getMe,
    enabled: !!token,
  })
}
