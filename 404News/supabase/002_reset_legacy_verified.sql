-- Optional. Run once in the Supabase SQL editor.
-- Older stories were saved as verified without being cross-checked. This resets them so the database
-- no longer claims verification that never happened. The app already hides the badge for these stories.
update public.articles
set verified = false, confidence = 0
where verified = true
  and (agent_log is null or agent_log::text not like '%"verification"%');
