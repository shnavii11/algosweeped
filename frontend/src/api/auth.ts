import client from './client'
import type { User } from '../types'

export const getMe = () => client.get<User>('/users/me').then((r) => r.data)
export const updateProfile = (data: Partial<User>) =>
  client.patch<User>('/users/me', data).then((r) => r.data)
export const getPublicProfile = (username: string) =>
  client.get<User>(`/users/${username}/public`).then((r) => r.data)
