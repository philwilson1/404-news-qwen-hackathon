import type { Article } from '../lib/supabase';

const baseLog = (detail: string): Article['agent_log'] => [
  { agent: 'collector', status: 'completed', detail: `Scraped ${detail}` },
  { agent: 'verification', status: 'completed', detail: 'Cross-checked 2+ independent sources' },
  { agent: 'presenter', status: 'completed', detail: 'Rewrote into editorial hook' },
];

export const fallbackArticles: Article[] = [
  {
    id: 'f1', title: 'GPT-5 Surpasses Human-Level Reasoning on Mathematical Olympiad Benchmarks',
    summary: "OpenAI's latest model achieves 97.4% on MATH-500, redefining what frontier AI can do with formal reasoning.",
    source: 'arXiv / OpenAI Blog', source_logo: 'OA', author: 'OpenAI Research', vibe: 'deep-dives', tag: 'Model Release',
    verified: true, confidence: 0.96, image_url: 'https://images.pexels.com/photos/8386434/pexels-photo-8386434.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '142K', trending: true, published_at: '2 min ago', read_time: 6, agent_log: baseLog('arXiv + OpenAI blog'), created_at: new Date(Date.now() - 120000).toISOString(),
  },
  {
    id: 'f2', title: 'Mistral Drops "Magistral" — Open-Source Reasoning Model That Rivals o3',
    summary: 'Mistral AI releases a chain-of-thought reasoning model within 3 points of o3 at a fraction of the inference cost.',
    source: 'GitHub / Mistral Blog', source_logo: 'MI', author: 'Mistral AI', vibe: 'launch-hub', tag: 'Launch',
    verified: true, confidence: 0.94, image_url: 'https://images.pexels.com/photos/16094041/pexels-photo-16094041.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '89K', trending: true, published_at: '18 min ago', read_time: 4, agent_log: baseLog('GitHub + Mistral blog'), created_at: new Date(Date.now() - 1080000).toISOString(),
  },
  {
    id: 'f3', title: "The AI Community Is Losing Its Mind Over Claude's New 'Extended Thinking' Mode",
    summary: "Anthropic quietly shipped a reasoning toggle and the discourse is unhinged. Some call it Claude's 'god mode.'",
    source: 'X / Anthropic Blog', source_logo: 'AN', author: 'Hype Desk', vibe: 'hype', tag: 'Drama',
    verified: true, confidence: 0.82, image_url: 'https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '201K', trending: false, published_at: '35 min ago', read_time: 3, agent_log: baseLog('X + Anthropic blog'), created_at: new Date(Date.now() - 2100000).toISOString(),
  },
  {
    id: 'f4', title: "Google DeepMind's AlphaFold 3: A Deep Technical Breakdown",
    summary: "We parsed the full 48-page Nature paper. The shift from Evoformer to diffusion-based structure prediction is massive.",
    source: 'arXiv / Nature', source_logo: 'DM', author: 'DeepMind', vibe: 'deep-dives', tag: 'Research',
    verified: true, confidence: 0.97, image_url: 'https://images.pexels.com/photos/2280571/pexels-photo-2280571.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '67K', trending: false, published_at: '1 hr ago', read_time: 12, agent_log: baseLog('Nature paper + blog'), created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'f5', title: 'Nvidia Announces $500M AI Startup Fund at GTC 2025',
    summary: 'Jensen Huang announced a new $500M fund targeting early-stage AI infrastructure startups. Applications open Q3.',
    source: 'Nvidia Official Blog', source_logo: 'NV', author: 'Nvidia Newsroom', vibe: 'launch-hub', tag: 'Funding',
    verified: true, confidence: 0.95, image_url: 'https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '312K', trending: false, published_at: '2 hr ago', read_time: 3, agent_log: baseLog('Nvidia blog + GTC stream'), created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'f6', title: '"AI is just autocomplete" — and Why That Take Is Getting Destroyed',
    summary: "The old dismissal is back and it's getting ratioed harder than ever. Between AlphaFold 3, o3, and Magistral, the pattern-matching crowd is having a bad week.",
    source: 'X Trending', source_logo: 'X', author: 'Hype Desk', vibe: 'hype', tag: 'Hot Take',
    verified: true, confidence: 0.71, image_url: 'https://images.pexels.com/photos/3184339/pexels-photo-3184339.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '445K', trending: false, published_at: '3 hr ago', read_time: 2, agent_log: baseLog('X trending discourse'), created_at: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: 'f7', title: 'Attention Is Not All You Need: New Paper Challenges Transformer Dominance',
    summary: "MIT CSAIL proposes a hybrid State-Space + Attention architecture hitting 94% of GPT-4's performance at 40% the compute.",
    source: 'arXiv:2506.12301', source_logo: 'AR', author: 'MIT CSAIL', vibe: 'deep-dives', tag: 'Research',
    verified: true, confidence: 0.93, image_url: 'https://images.pexels.com/photos/546819/pexels-photo-546819.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '93K', trending: false, published_at: '4 hr ago', read_time: 9, agent_log: baseLog('arXiv + CSAIL blog'), created_at: new Date(Date.now() - 14400000).toISOString(),
  },
  {
    id: 'f8', title: "Perplexity AI Hits $1B ARR — CEO Drops the Number on X With Zero Warning",
    summary: 'Aravind Srinivas casually posted "$1B ARR" and the timeline went nuclear. No press release — just a tweet.',
    source: 'X / Perplexity Blog', source_logo: 'PX', author: 'Hype Desk', vibe: 'hype', tag: 'Viral',
    verified: true, confidence: 0.78, image_url: 'https://images.pexels.com/photos/187041/pexels-photo-187041.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '780K', trending: false, published_at: '5 hr ago', read_time: 2, agent_log: baseLog('CEO X post + blog'), created_at: new Date(Date.now() - 18000000).toISOString(),
  },
  {
    id: 'f9', title: 'Meta Releases Llama 4 With 2T Parameter Mixture-of-Experts Architecture',
    summary: 'Meta open-sources Llama 4 with a sparse MoE design activating only 140B params per token, hitting GPT-4o-level benchmarks at half the inference cost.',
    source: 'Meta AI Blog', source_logo: 'ME', author: 'Meta AI', vibe: 'launch-hub', tag: 'Launch',
    verified: true, confidence: 0.93, image_url: 'https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '156K', trending: true, published_at: '6 hr ago', read_time: 5, agent_log: baseLog('Meta blog + HuggingFace'), created_at: new Date(Date.now() - 21600000).toISOString(),
  },
  {
    id: 'f10', title: 'The Hidden Cost of Inference: Why AI Bills Are Eating Startups Alive',
    summary: 'A deep analysis of per-token pricing across OpenAI, Anthropic, and Mistral reveals most AI startups spend 40-60% of revenue on API costs.',
    source: 'Stratechery / The Information', source_logo: 'ST', author: 'Strategy Desk', vibe: 'deep-dives', tag: 'Analysis',
    verified: true, confidence: 0.89, image_url: 'https://images.pexels.com/photos/546819/pexels-photo-546819.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '78K', trending: false, published_at: '7 hr ago', read_time: 8, agent_log: baseLog('Stratechery + The Information'), created_at: new Date(Date.now() - 25200000).toISOString(),
  },
  {
    id: 'f11', title: 'Sam Altman Says AGI Is Coming "Sooner Than Most People Think"',
    summary: 'In a packed fireside at Stanford, Altman reiterated that AGI could arrive within a few years and that the economic implications are staggering.',
    source: 'Stanford HAI / X', source_logo: 'SA', author: 'Hype Desk', vibe: 'hype', tag: 'Viral',
    verified: true, confidence: 0.74, image_url: 'https://images.pexels.com/photos/3184339/pexels-photo-3184339.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '892K', trending: false, published_at: '8 hr ago', read_time: 2, agent_log: baseLog('Stanford fireside + X posts'), created_at: new Date(Date.now() - 28800000).toISOString(),
  },
  {
    id: 'f12', title: 'Apple Intelligence 2.0: On-Device AI Finally Doesnt Suck',
    summary: 'Apple quietly shipped a major upgrade to its on-device models. Early benchmarks show it matching GPT-4o-mini on reasoning while running entirely offline.',
    source: 'Apple Developer Blog', source_logo: 'AP', author: 'Apple AI', vibe: 'launch-hub', tag: 'Launch',
    verified: true, confidence: 0.91, image_url: 'https://images.pexels.com/photos/2182949/pexels-photo-2182949.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '203K', trending: true, published_at: '10 hr ago', read_time: 4, agent_log: baseLog('Apple dev blog + WWDC'), created_at: new Date(Date.now() - 36000000).toISOString(),
  },
  {
    id: 'f13', title: 'Why RAG Is Not Dead Despite What the Vectors Vendors Tell You',
    summary: 'A rigorous comparison of RAG vs long-context windows shows retrieval still wins on cost, latency, and factual accuracy at scale.',
    source: 'arXiv:2506.09912', source_logo: 'AR', author: 'Research Desk', vibe: 'deep-dives', tag: 'Research',
    verified: true, confidence: 0.95, image_url: 'https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '54K', trending: false, published_at: '12 hr ago', read_time: 10, agent_log: baseLog('arXiv preprint'), created_at: new Date(Date.now() - 43200000).toISOString(),
  },
  {
    id: 'f14', title: 'AI Generated Art Just Won First Prize at a Major Photo Contest Then the Photographer Admitted It',
    summary: 'The World Photography Award winner revealed their entry was AI-generated, sparking industry-wide debate about competition rules.',
    source: 'World Photography Org / PetaPixel', source_logo: 'WP', author: 'Hype Desk', vibe: 'hype', tag: 'Drama',
    verified: true, confidence: 0.86, image_url: 'https://images.pexels.com/photos/3783385/pexels-photo-3783385.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '1.2M', trending: false, published_at: '14 hr ago', read_time: 3, agent_log: baseLog('PetaPixel + WPO statement'), created_at: new Date(Date.now() - 50400000).toISOString(),
  },
  {
    id: 'f15', title: 'Cohere Raises 500M Series D at 5B Valuation to Bet on Enterprise AI',
    summary: 'Cohere doubles down on B2B with a massive round led by CPP Investments, positioning against OpenAI and Anthropic in the enterprise market.',
    source: 'Bloomberg / Cohere Blog', source_logo: 'CO', author: 'Cohere', vibe: 'launch-hub', tag: 'Funding',
    verified: true, confidence: 0.92, image_url: 'https://images.pexels.com/photos/187041/pexels-photo-187041.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '167K', trending: false, published_at: '16 hr ago', read_time: 3, agent_log: baseLog('Bloomberg + Cohere blog'), created_at: new Date(Date.now() - 57600000).toISOString(),
  },
  {
    id: 'f16', title: 'The AI Agent Hype Cycle: Where We Are and Why Most Startups Will Fail',
    summary: 'A frank analysis of the AI agent landscape: 90% of agent startups are just GPT-4 wrappers with a loop. Here is what separates the real ones.',
    source: 'AI Snake Oil / Substack', source_logo: 'SS', author: 'Strategy Desk', vibe: 'deep-dives', tag: 'Analysis',
    verified: true, confidence: 0.84, image_url: 'https://images.pexels.com/photos/1181467/pexels-photo-1181467.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '234K', trending: false, published_at: '18 hr ago', read_time: 7, agent_log: baseLog('Substack + HackerNews'), created_at: new Date(Date.now() - 64800000).toISOString(),
  },
  {
    id: 'f17', title: 'Stable Diffusion 4 Drops With Real-Time Video Generation at 24fps',
    summary: 'Stability AI ships SD4 with a new temporal attention module enabling coherent 24fps video generation on a single A100.',
    source: 'Stability AI Blog', source_logo: 'SD', author: 'Stability AI', vibe: 'launch-hub', tag: 'Launch',
    verified: true, confidence: 0.90, image_url: 'https://images.pexels.com/photos/3783385/pexels-photo-3783385.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '445K', trending: true, published_at: '20 hr ago', read_time: 4, agent_log: baseLog('Stability blog + HuggingFace'), created_at: new Date(Date.now() - 72000000).toISOString(),
  },
  {
    id: 'f18', title: 'OpenAI vs Anthropic vs Google: The Talent War Is Getting Brutal',
    summary: 'Comp packages for senior AI researchers have crossed 2M annually. We mapped the poaching flow between the big three labs.',
    source: 'The Information / Reuters', source_logo: 'TI', author: 'Hype Desk', vibe: 'hype', tag: 'Drama',
    verified: true, confidence: 0.80, image_url: 'https://images.pexels.com/photos/3184339/pexels-photo-3184339.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '567K', trending: false, published_at: '22 hr ago', read_time: 5, agent_log: baseLog('The Information + Reuters'), created_at: new Date(Date.now() - 79200000).toISOString(),
  },
  {
    id: 'f19', title: 'The Surprising AI Model Beating GPT-4o on Coding Tasks And It Is Open Source',
    summary: 'DeepSeek Coder V2 outperforms GPT-4o on HumanEval and MBPP at 1/10th the cost. Chinese AI labs are quietly pulling ahead on code.',
    source: 'arXiv / DeepSeek Blog', source_logo: 'DS', author: 'DeepSeek', vibe: 'deep-dives', tag: 'Research',
    verified: true, confidence: 0.94, image_url: 'https://images.pexels.com/photos/2280571/pexels-photo-2280571.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '178K', trending: true, published_at: '1 day ago', read_time: 6, agent_log: baseLog('arXiv + DeepSeek blog'), created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: 'f20', title: 'xAIs Grok 3 Hits the Scene With Real-Time X Integration',
    summary: 'Elon Musks xAI releases Grok 3 with live access to Xs firehose, claiming superior real-time knowledge compared to ChatGPT.',
    source: 'xAI Blog / X', source_logo: 'X', author: 'xAI', vibe: 'hype', tag: 'Viral',
    verified: true, confidence: 0.72, image_url: 'https://images.pexels.com/photos/8386434/pexels-photo-8386434.jpeg?auto=compress&cs=tinysrgb&w=800',
    views: '723K', trending: false, published_at: '1 day ago', read_time: 3, agent_log: baseLog('xAI blog + X posts'), created_at: new Date(Date.now() - 90000000).toISOString(),
  },
];

export const fallbackAgentRuns = [
  { id: 'fr1', agent_name: 'collector', status: 'completed', items_processed: 20, items_verified: 0, items_published: 0, detail: 'Scraped 20 items from whitelisted sources: arXiv, GitHub, company blogs, verified X', created_at: new Date(Date.now() - 360000).toISOString() },
  { id: 'fr2', agent_name: 'verification', status: 'completed', items_processed: 20, items_verified: 20, items_published: 0, detail: 'Verified all 20 items against 2+ independent sources', created_at: new Date(Date.now() - 300000).toISOString() },
  { id: 'fr3', agent_name: 'presenter', status: 'completed', items_processed: 20, items_verified: 20, items_published: 20, detail: 'Published 20 articles across 3 vibes: 8 Deep Dives, 7 Hype, 5 Launch Hub', created_at: new Date(Date.now() - 240000).toISOString() },
];

export const categories = [
  { id: 'deep-dives', label: 'Deep Dives' },
  { id: 'hype', label: 'Hype' },
  { id: 'launch-hub', label: 'Launch Hub' },
];
