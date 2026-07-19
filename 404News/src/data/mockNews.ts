export type VibeCategory = 'deep-dives' | 'hype' | 'launch-hub';

export const categories = [
  { id: 'deep-dives', label: 'Deep Dives', icon: 'BookOpen' },
  { id: 'hype', label: 'Hype & Drama', icon: 'Flame' },
  { id: 'launch-hub', label: 'Launch Hub', icon: 'Rocket' },
] as const;

export const sideCategories = [
  { id: 'sports', label: 'Sports', icon: 'Trophy', coming: true, note: 'FIFA World Cup vertical — pending data licensing' },
  { id: 'fashion', label: 'Fashion', icon: 'Shirt', coming: true, note: 'Runway drops & trend cycles' },
  { id: 'finance', label: 'Finance', icon: 'CircleDollarSign', coming: true, note: 'Markets, cost of living & business' },
  { id: 'education', label: 'Education', icon: 'GraduationCap', coming: true, note: 'Courses, scholarships & learning' },
  { id: 'entertainment', label: 'Entertainment', icon: 'Clapperboard', coming: true, note: 'Pop culture & media' },
  { id: 'health', label: 'Health', icon: 'Stethoscope', coming: true, note: 'Wellness & medical breakthroughs' },
] as const;

export const trendingTags = ['#GPT5', '#Magistral', '#AlphaFold3', '#o3', '#NvidiaGTC'];
