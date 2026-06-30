# PolarYix Production Checklist

Generated: 2026-06-29

## Must Fix Before Production

- [ ] Set `DEBUG=false` in production.
- [ ] Configure `ADMIN_CLEANUP_TOKEN` with a strong random value.
- [ ] Tighten CORS. Avoid broad `*.vercel.app` and `*.github.io` origins unless every preview domain is trusted.
- [ ] Move auth users/sessions/credits/history/jobs from JSON files to a real database or durable KV store.
- [ ] Add session expiration and cleanup for stale tokens.
- [ ] Add login/signup/OAuth rate limiting.
- [ ] Protect or remove public dataset endpoints if they are not intentionally public.
- [ ] Re-enable CSV injection mitigation or escape dangerous spreadsheet cells during export.
- [ ] Add production cleanup for generated storage folders.
- [ ] Keep link download retention short with `LINK_DOWNLOAD_RETENTION_MINUTES=10`.
- [ ] Ensure storage files are served only through authenticated ownership-checked endpoints.
- [ ] Configure Google OAuth with production callback URLs.
- [ ] Remove temporary test credentials and local test OAuth keys before launch.

## Verified In This Audit

- Workspace downloads check `user_id` ownership before serving files.
- Conversion/image-tool job status and downloads check `user_id` ownership.
- Image watermark logic is centralized in `should_apply_watermark`.
- Premium users are blocked from watermark by `is_premium_user`.
- Background removal and optimize operations do not apply watermark.
- Workspace upload now rejects extensions outside the configured allow-list.
- Anonymous `/converter/usage` no longer reports Premium limits from query parameters.
- Link download HD and 4K now use separate yt-dlp format candidate lists.

## Credits And Abuse

- [ ] Authenticated credits are deducted server-side from `storage/auth/users.json`.
- [ ] Anonymous usage is keyed by `x-polaryix-client-id` when present, otherwise IP.
- [ ] Do not trust browser-only credit counters.
- [ ] Consider rejecting arbitrary `x-polaryix-client-id` values or signing them server-side.
- [ ] Add per-IP and per-account request rate limits for conversions, image tools and link downloads.
- [ ] Add job queue limits per user and per IP to prevent resource exhaustion.

## Premium Rules

- [ ] Premium/VIP must never receive watermark.
- [ ] Free users receive watermark only for `upscale_image` and `remaster_image`.
- [ ] `remove_background` must not apply watermark.
- [ ] `optimize_image` must not apply watermark.
- [ ] 4K/HD link downloads must be gated by backend account state.
- [ ] Verify delivered quality with `quality_delivered` in history after each link download.

## File Handling

- [ ] Keep upload size limits aligned with Free/Basic/Pro limits.
- [ ] Validate filenames with `Path(filename).name`.
- [ ] Validate extensions using the configured allow-list.
- [ ] Parse/verify image files after upload.
- [ ] Keep deletion restricted to files under configured storage paths.
- [ ] Ensure expired/deleted records cannot be downloaded.

## Operations

- [ ] Run `npm run build` before deploy.
- [ ] Run backend syntax/tests before deploy.
- [ ] Monitor RAM during rembg processing.
- [ ] Monitor generated media storage.
- [ ] Schedule cleanup for expired files at least hourly in production.
- [ ] Confirm generated folders are excluded from git.
