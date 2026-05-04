export interface User {
  id: string
  nickname: string
  avatar_url: string
  bio: string
  credits: number
}

export interface Artwork {
  id: string
  user_id: string
  title: string
  prompt: string
  negative_prompt: string
  image_url: string
  category: string
  visibility: 'public' | 'private'
  style: string
  width: number
  height: number
  liked: boolean
  favorited: boolean
  likes: number
  collects: number
  followed?: boolean
  blocked?: boolean
  params?: Record<string, unknown>
  similar?: Artwork[]
}

export interface FollowState {
  user_id: string
  followed: boolean
}

export interface BlockState {
  user_id: string
  blocked: boolean
}

export interface PromptItem {
  id: string
  title: string
  content: string
  category: string
  visibility: 'public' | 'private'
  uses: number
}

export interface PromptOptimization {
  original_prompt: string
  positive_prompt: string
  negative_prompt: string
  source: 'rag_gallery' | 'rag_prompt' | 'mock_ai'
  score: number
  fusion_mode?: 'gallery_skill_user_prompt' | 'ai_user_prompt_only'
  gallery_skill?: string
  preserved_user_prompt?: boolean
  user_prompt_coverage?: number
  references: Array<{
    id: string
    title: string
    content: string
    category: string
    style?: string
    source: 'gallery' | 'prompt'
    score: number
  }>
}

export interface ConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  image_url: string
  reference_image_url?: string
  task_id: string
  created_at: number
}

export interface Conversation {
  id: string
  title: string
  cover_image_url: string
  messages?: ConversationMessage[]
}

export interface GenerationTask {
  id: string
  conversation_id: string
  prompt: string
  negative_prompt?: string
  status: 'pending' | 'generating' | 'completed' | 'failed'
  image_url: string
  error: string
}

export interface CreditTransaction {
  id: string
  type: string
  amount: number
  balance_after: number
  title: string
  created_at: number
}

export interface PaymentOrder {
  id: string
  package_id: string
  credits: number
  price: number
  currency: string
  status: 'pending' | 'paid' | 'failed' | 'cancelled' | 'expired' | 'refunded'
  provider: string
  provider_order_id: string
  payment_url: string
  created_at: number
  paid_at: number
}

export interface PaymentCheckout {
  payment_url: string
  provider: string
  payment_params?: Record<string, unknown>
  integration_note?: string
}
