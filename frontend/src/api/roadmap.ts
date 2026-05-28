import client from './client'
import type { RoadmapTopic } from '../types'

export const getRoadmap = () =>
  client.get<RoadmapTopic[]>('/roadmap').then((r) => r.data)
