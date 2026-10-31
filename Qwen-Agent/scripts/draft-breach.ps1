# Lists this week's breach stories, lets you pick one, and asks the AI to draft a card (saved as a draft).
# Run from the Qwen-Agent folder:
#   powershell -ExecutionPolicy Bypass -File .\scripts\draft-breach.ps1
param([string]$Api = "https://four04-news.onrender.com", [int]$Days = 7)

$secret = $env:PIPELINE_SECRET
if (-not $secret) { $secret = Read-Host "Pipeline secret" }
$h = @{ "X-Pipeline-Secret" = $secret }

function Show-Error($e) {
  if ($e.ErrorDetails.Message) { Write-Host ("Server said: " + $e.ErrorDetails.Message) -ForegroundColor Red }
  else { Write-Host $e.Exception.Message -ForegroundColor Red }
}

Write-Host "Looking for breach stories (the first request can take a minute if Render is asleep)..."
try { $r = Invoke-RestMethod -Uri "$Api/breaches/candidates?days=$Days" -Headers $h } catch { Show-Error $_; return }

if (-not $r.candidates -or $r.candidates.Count -eq 0) { Write-Host "No new breach stories found."; return }
for ($i = 0; $i -lt $r.candidates.Count; $i++) {
  $c = $r.candidates[$i]
  Write-Host ("{0}. [{1} outlet(s)] {2}" -f ($i + 1), $c.outlets, $c.title)
}
if ($r.feeds_failed) { Write-Host ("Feeds that failed: " + ($r.feeds_failed -join ", ")) -ForegroundColor Yellow }

$n = [int](Read-Host "Number to draft (0 to quit)")
if ($n -lt 1 -or $n -gt $r.candidates.Count) { return }
$pick = $r.candidates[$n - 1]
Write-Host "Reading these reports:"; $pick.draft_urls | ForEach-Object { Write-Host ("  " + $_) }

$body = @{ urls = @($pick.draft_urls) } | ConvertTo-Json
try { $res = Invoke-RestMethod -Method Post -Uri "$Api/breaches/draft" -Headers $h -ContentType "application/json" -Body $body } catch { Show-Error $_; return }

Write-Host ("Saved draft: " + $res.slug) -ForegroundColor Green
$res.warnings | ForEach-Object { Write-Host ("WARNING: " + $_) -ForegroundColor Yellow }
Write-Host "Check the card in Supabase (Table Editor > breaches). To publish it, run in the SQL editor:"
Write-Host ("update public.breaches set status = 'published', last_checked_on = current_date where slug = '" + $res.slug + "';")
