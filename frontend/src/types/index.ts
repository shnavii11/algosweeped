export interface User {
  id: string
  email: string
  name: string
  username: string
  college: string
  avatar_url?: string
  lc_username?: string
  cf_handle?: string
  gh_username?: string
  created_at: string
  last_synced?: string
}

export interface Question {
  id: string
  platform: 'leetcode' | 'codeforces'
  number: string
  title: string
  slug?: string
  url: string
  difficulty: 'easy' | 'medium' | 'hard'
  difficulty_rating?: number
  statement_html?: string
  topics: string[]
  companies: { name: string; frequency: number }[]
  is_premium: boolean
  acceptance_rate?: number
  solved_count?: number
}

export interface QuestionProgress {
  question_id: string
  status: 'todo' | 'attempted' | 'done'
  notes?: string
}

export interface RoadmapTopic {
  topic: string
  ordinal: number
  display_name: string
  prerequisite_topics: string[]
  summary: string
  core_patterns: string[]
  starter_problems: string[]
  milestone_problems: string[]
}

export interface TopicScore {
  topic: string
  attempted: number
  solved: number
  accuracy: number
  weakness_score: number
}

export interface SheetProblem {
  question_id: string
  topic: string
  ordinal: number
  cross_sheet_count: number
  source_sheets: string[]
  score: number
  question: Question
  status?: 'todo' | 'attempted' | 'done'
}

export interface SheetSource {
  id: string
  name: string
  url?: string
  problem_count: number
  weight: number
}

export interface StatsMe {
  user: User
  readiness_score: number
  topic_scores: TopicScore[]
  platform_data: {
    leetcode?: Record<string, unknown>
    codeforces?: Record<string, unknown>
    github?: Record<string, unknown>
  }
}
