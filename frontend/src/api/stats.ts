import client from './client'
import type { StatsMe, ReadinessScore } from '../types'

export const getMyStats = () => client.get<StatsMe>('/stats/me').then((r) => r.data)
export const triggerSync = () => client.post('/stats/sync').then((r) => r.data)
export const getReadiness = (username: string) =>
  client.get<ReadinessScore>(`/stats/${username}/readiness`).then((r) => r.data)
