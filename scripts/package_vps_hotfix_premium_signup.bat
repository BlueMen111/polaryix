@echo off
setlocal

set "ROOT=%~dp0.."
set "ZIP=%ROOT%\polaryix-hotfix-premium-signup.zip"
set "STAGING=%TEMP%\polaryix-hotfix-premium-signup"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$root = (Resolve-Path '%ROOT%').Path;" ^
  "$zip = '%ZIP%';" ^
  "$staging = '%STAGING%';" ^
  "if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force };" ^
  "New-Item -ItemType Directory -Path $staging | Out-Null;" ^
  "$files = @(" ^
  "'apps/api/app/api/v1/routes/auth.py'," ^
  "'apps/api/app/api/v1/routes/converter.py'," ^
  "'apps/api/app/core/account_security.py'," ^
  "'apps/api/app/core/auth_store.py'," ^
  "'apps/api/app/core/comments_store.py'," ^
  "'apps/api/app/core/conversion_history.py'," ^
  "'apps/api/app/core/conversion_jobs.py'," ^
  "'apps/api/app/core/payment_notifications.py'," ^
  "'apps/api/app/core/payments_store.py'," ^
  "'apps/api/app/core/premium.py'," ^
  "'apps/api/app/core/public_stats.py'," ^
  "'apps/api/app/infrastructure/storage/analysis_sessions_storage.py'," ^
  "'apps/api/app/infrastructure/storage/analysis_storage.py'," ^
  "'apps/api/app/infrastructure/storage/dashboard_storage.py'," ^
  "'apps/web/next.config.js'," ^
  "'apps/web/src/app/login/page.tsx'," ^
  "'apps/web/src/app/premium/page.tsx'," ^
  "'apps/web/src/app/signup/page.tsx'," ^
  "'apps/web/src/components/Header.module.css'," ^
  "'apps/web/src/components/Header.tsx'," ^
  "'apps/web/src/hooks/useAnalysisSession.ts'," ^
  "'apps/web/src/lib/api.ts'" ^
  ");" ^
  "foreach ($file in $files) {" ^
  "  $src = Join-Path $root $file;" ^
  "  $dst = Join-Path $staging $file;" ^
  "  New-Item -ItemType Directory -Path (Split-Path $dst) -Force | Out-Null;" ^
  "  Copy-Item -LiteralPath $src -Destination $dst -Force;" ^
  "}" ^
  "if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force };" ^
  "Compress-Archive -LiteralPath (Get-ChildItem -LiteralPath $staging -Force).FullName -DestinationPath $zip -CompressionLevel Optimal;" ^
  "Remove-Item -LiteralPath $staging -Recurse -Force;" ^
  "Write-Host ('Created: ' + $zip);"

endlocal
