import "jsr:@supabase/functions-js/edge-runtime.d.ts";
const corsHeaders = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey" };
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 200, headers: corsHeaders });
  try {
    const { messages, articles } = await req.json();
    const context = articles?.length ? articles.map((a: { title: string; summary: string; source: string }) => `- ${a.title}: ${a.summary} (Source: ${a.source})`).join('\n') : '';
    const systemPrompt = `You are PivotAI, an AI news concierge. You provide concise, well-sourced summaries of AI news. ${context ? `Use these verified stories as context:\n${context}` : ''}`;
    const response = await fetch('https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct/v1/chat/completions', {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${Deno.env.get('HF_API_KEY') ?? ''}` },
      body: JSON.stringify({ model: 'Qwen/Qwen2.5-7B-Instruct', messages: [{ role: 'system', content: systemPrompt }, ...messages], stream: true, max_tokens: 512 }),
    });
    if (!response.ok || !response.body) return new Response(JSON.stringify({ error: 'model unavailable' }), { status: 502, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    return new Response(response.body, { headers: { ...corsHeaders, 'Content-Type': 'text/event-stream' } });
  } catch (err) {
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : 'unknown error' }), { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});
