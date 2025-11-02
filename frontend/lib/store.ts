import { create } from 'zustand'

type ThemeState = {
  theme: 'dark' | 'light'
  setTheme: (t: 'dark' | 'light') => void
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: 'dark',
  setTheme: (t) => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', t === 'dark')
    }
    set({ theme: t })
  },
}))

type FocusArea = 'Reduce stress' | 'Build gratitude' | 'Improve self-confidence' | 'Better sleep' | 'Focus & clarity' | 'Emotional balance'

export type MicroGoal = { id: string; text: string; area?: FocusArea; done?: boolean }

type Reminder = 'off' | 'daily' | 'weekly'

type PlanState = {
  chosen: Record<string, boolean>
  toggle: (id: string) => void
  focus: FocusArea[]
  setFocus: (area: FocusArea) => void
  goals: MicroGoal[]
  addGoal: (g: Omit<MicroGoal, 'id'>) => void
  removeGoal: (id: string) => void
  toggleGoal: (id: string) => void
  clearGoals: () => void
  reminder: Reminder
  setReminder: (r: Reminder) => void
}

const PLAN_KEY = 'clarity_plan_v1'

function loadPlan(): Pick<PlanState, 'chosen' | 'focus' | 'goals' | 'reminder'> {
  return safeLoad(PLAN_KEY, { chosen: {}, focus: [], goals: [], reminder: 'off' as Reminder })
}

function savePlan(partial: Partial<PlanState>, get: () => PlanState) {
  const curr = get()
  const next = { chosen: curr.chosen, focus: curr.focus, goals: curr.goals, reminder: curr.reminder, ...partial }
  safeSave(PLAN_KEY, next as any)
}

export const usePlanStore = create<PlanState>((set, get) => ({
  ...loadPlan(),
  toggle: (id) => {
    set((s) => ({ chosen: { ...s.chosen, [id]: !s.chosen[id] } }))
    savePlan({}, get)
  },
  focus: [],
  setFocus: (area) => {
    set((s) => {
      const exists = s.focus.includes(area)
      let focus: FocusArea[]
      if (exists) {
        focus = s.focus.filter((a) => a !== area)
      } else {
        focus = s.focus.length >= 2 ? [s.focus[1], area].filter(Boolean) as FocusArea[] : [...s.focus, area]
      }
      return { focus }
    })
    savePlan({}, get)
  },
  goals: [],
  addGoal: (g) => {
    set((s) => {
      if (s.goals.length >= 3) return {} as any
      const goal: MicroGoal = { id: crypto.randomUUID(), text: g.text.trim(), area: g.area, done: false }
      const goals = [...s.goals, goal]
      return { goals }
    })
    savePlan({}, get)
  },
  removeGoal: (id) => {
    set((s) => ({ goals: s.goals.filter((g) => g.id !== id) }))
    savePlan({}, get)
  },
  toggleGoal: (id) => {
    set((s) => ({ goals: s.goals.map((g) => (g.id === id ? { ...g, done: !g.done } : g)) }))
    savePlan({}, get)
  },
  clearGoals: () => {
    set({ goals: [] })
    savePlan({}, get)
  },
  reminder: 'off',
  setReminder: (r) => {
    set({ reminder: r })
    savePlan({}, get)
  },
}))

// Journal + Mood + Chat state
export type JournalEntry = {
  id: string
  text: string
  time: string // ISO string
  tag?: 'Journal' | 'Conversation'
}

export type MoodEntry = {
  id: string
  date: string // YYYY-MM-DD
  mood: number // 1-10
  note?: string
}

export type ChatMessage = { id: string; role: 'assistant' | 'user'; text: string; time: string; tag?: 'Conversation' }

type JournalState = {
  journal: JournalEntry[]
  moods: MoodEntry[]
  chat: ChatMessage[]
  addJournal: (text: string) => void
  removeJournal: (id: string) => void
  addMood: (mood: number, note?: string) => void
  setChat: (msgs: ChatMessage[]) => void
  clearJournal: () => void
  clearChat: () => void
}

const JOURNAL_KEY = 'clarity_journal_v1'
const MOOD_KEY = 'clarity_moods_v1'
const CHAT_KEY = 'clarity_chat_v1'

function safeLoad<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    const parsed = JSON.parse(raw)
    return parsed as T
  } catch {
    return fallback
  }
}

function safeSave<T>(key: string, value: T) {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {}
}

export const useJournalStore = create<JournalState>((set, get) => ({
  journal: safeLoad<JournalEntry[]>(JOURNAL_KEY, []),
  moods: safeLoad<MoodEntry[]>(MOOD_KEY, []),
  chat: safeLoad<ChatMessage[]>(CHAT_KEY, []),
  addJournal: (text) => {
    const entry: JournalEntry = { id: crypto.randomUUID(), text: text.trim(), time: new Date().toISOString(), tag: 'Journal' }
    set((s) => {
      const journal = [...s.journal, entry]
      safeSave(JOURNAL_KEY, journal)
      return { journal }
    })
  },
  removeJournal: (id) => {
    set((s) => {
      const journal = s.journal.filter((j) => j.id !== id)
      safeSave(JOURNAL_KEY, journal)
      return { journal }
    })
  },
  addMood: (mood, note) => {
    const d = new Date()
    const date = d.toISOString().slice(0, 10)
    const entry: MoodEntry = { id: crypto.randomUUID(), date, mood, note }
    set((s) => {
      const existingIdx = s.moods.findIndex((m) => m.date === date)
      let moods: MoodEntry[]
      if (existingIdx >= 0) {
        moods = [...s.moods]
        moods[existingIdx] = { ...moods[existingIdx], mood, note }
      } else {
        moods = [...s.moods, entry]
      }
      safeSave(MOOD_KEY, moods)
      return { moods }
    })
  },
  setChat: (msgs) => {
    safeSave(CHAT_KEY, msgs)
    set({ chat: msgs })
  },
  clearJournal: () => {
    set({ journal: [] })
    safeSave(JOURNAL_KEY, [])
  },
  clearChat: () => {
    set({ chat: [] })
    safeSave(CHAT_KEY, [])
  },
}))

// Onboarding / Profile state for Get Started flow
export type Identity = {
  name?: string
  nickname?: string
  dateOfBirth?: string
  favoriteAnimal?: string
  avatarUrl?: string
}

export type ExperienceSignals = {
  copingPreference?: 'talk' | 'think' | 'distract'
  baselineWord?: 'Calm' | 'Energetic' | 'Reflective' | 'Driven' | 'Sensitive' | 'Steady'
  emotionalGranularity?: number // 1-5
  responseStyle?: 'analyze' | 'retry' | 'talk' | 'avoid' | 'reflect'
  journalingFrequency?: 'never' | 'sometimes' | 'weekly' | 'daily'
  grounding?: 'writing' | 'nature' | 'people' | 'action' | 'art' | 'learning' | 'rest'
}

export type GoalsSignals = {
  direction?: 'Healing' | 'Focus' | 'Growth' | 'Balance' | 'Clarity' | 'Connection'
  helpWith?: ('stress' | 'patterns' | 'creativity' | 'track' | 'plan')[]
  progressPreference?: 'small_wins' | 'deep_insights'
  depthComfort?: number // 1-5
  toneStyle?: 'factual' | 'intuitive'
}

export type InnerWorld = {
  controlOrientation?: 'control' | 'flow'
  selfWords?: string[]
  phrase?: 'analyze' | 'feel' | 'act' | 'share'
  surpriseNote?: string
  archetype?: string
}

export type SpacePrefs = {
  checkIns?: 'daily' | 'ad_hoc'
  guideStyle?: 'reflective_questions' | 'just_listen'
  voiceNotes?: boolean
  mood?: 'cool' | 'warm' | 'balanced'
  toneColor?: 'blue' | 'violet' | 'rose'
}

export type OnboardingState = {
  step: number
  identity: Identity
  experience: ExperienceSignals
  goals: GoalsSignals
  inner: InnerWorld
  space: SpacePrefs
  completed: boolean
  setStep: (n: number) => void
  update: (patch: Partial<OnboardingState>) => void
  complete: () => void
  reset: () => void
}

const ONBOARD_KEY = 'clarity_onboarding_v1'

const defaultOnboarding: OnboardingState = {
  step: 0,
  identity: {},
  experience: {},
  goals: {},
  inner: {},
  space: { voiceNotes: false },
  completed: false,
  setStep: () => {},
  update: () => {},
  complete: () => {},
  reset: () => {},
}

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  ...(safeLoad<OnboardingState>(ONBOARD_KEY, defaultOnboarding)),
  setStep: (n) => {
    set({ step: n })
    safeSave(ONBOARD_KEY, { ...get() })
  },
  update: (patch) => {
    set((s) => ({ ...s, ...patch }))
    safeSave(ONBOARD_KEY, { ...get(), ...patch })
  },
  complete: () => {
    set({ completed: true })
    safeSave(ONBOARD_KEY, { ...get(), completed: true })
  },
  reset: () => {
    const cleared = {
      step: 0,
      identity: {},
      experience: {},
      goals: {},
      inner: {},
      space: { voiceNotes: false },
      completed: false,
    }
    set(cleared as Partial<OnboardingState>)
    safeSave(ONBOARD_KEY, cleared as any)
  },
}))
