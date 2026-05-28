import client from './client'
import type { Recommendations, ReadinessSummary, TopicExplanation } from '../types'

export const getReadinessSummary = () =>
  client.get<ReadinessSummary>('/insights/readiness-summary').then((r) => r.data)

export const getRecommendations = () =>
  client.get<Recommendations>('/insights/recommendations').then((r) => r.data)

export const getTopicExplanation = (topic: string) =>
  client.get<TopicExplanation>(`/insights/topics/${topic}/explain`).then((r) => r.data)
