import client from './client'
import type { SheetProblem, SheetSource } from '../types'

export const getCuratedSheet = () =>
  client.get<Record<string, SheetProblem[]>>('/sheet/curated').then((r) => r.data)

export const getSheetSources = () =>
  client.get<SheetSource[]>('/sheet/sources').then((r) => r.data)

export const getMySheetProgress = () =>
  client.get('/sheet/progress/me').then((r) => r.data)

export const updateSheetProgress = (problemId: string, status: string) =>
  client.patch(`/sheet/progress/${problemId}`, null, { params: { status } }).then((r) => r.data)
