import client from './client'
import type { Question, QuestionProgress } from '../types'

export interface QuestionsFilter {
  topic?: string
  platform?: string
  difficulty?: string
  company?: string
  q?: string
  page?: number
  limit?: number
}

export const getQuestions = (params: QuestionsFilter) =>
  client.get<Question[]>('/questions', { params }).then((r) => r.data)

export const getQuestionsByTopic = () =>
  client.get<Record<string, Question[]>>('/questions/by-topic').then((r) => r.data)

export const getQuestion = (id: string) =>
  client.get<Question>(`/questions/${id}`).then((r) => r.data)

export const updateQuestionProgress = (id: string, status: QuestionProgress['status']) =>
  client.patch<QuestionProgress>(`/questions/${id}/progress`, { status }).then((r) => r.data)

export const getMyQuestionProgress = () =>
  client
    .get<Record<string, QuestionProgress['status']>>('/questions/progress/me')
    .then((r) => r.data)
