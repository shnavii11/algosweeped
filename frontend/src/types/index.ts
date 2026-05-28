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
  number?: string
  title: string
  slug?: string
  url: string
  difficulty: 'easy' | 'medium' | 'hard'
  difficulty_rating?: number
  statement_html?: string
  topics?: string[]
  companies?: string[]
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
  status?: 'todo' | 'attempted' | 'done'
  // /sheet/curated returns the question fields flattened onto the row
  title?: string
  url?: string
  difficulty?: Question['difficulty']
  platform?: Question['platform']
  slug?: string
  is_premium?: boolean
}

export interface SheetSource {
  id: string
  name: string
  url?: string
  problem_count: number
  weight: number
}

export interface PlatformSnapshot {
  data: Record<string, unknown>
  fetched_at: string
}

export interface StatsMe {
  user: { username: string; last_synced: string | null }
  snapshots: {
    leetcode?: PlatformSnapshot
    codeforces?: PlatformSnapshot
    github?: PlatformSnapshot
  }
  topic_scores: TopicScore[]
  sheet: { done: number; total: number }
}

export interface ReadinessScore {
  total: number
  breakdown: {
    dsa_consistency: number
    github_activity: number
    topic_coverage: number
    sheet_progress: number
  }
}
