-- ═══ Projekt Lepiej — konfiguracja Supabase ═══════════════════════════════════
-- Uruchom całość w Supabase Dashboard → SQL Editor → Run.
-- Skrypt jest idempotentny — można go bezpiecznie uruchomić ponownie.

-- ── Newsletter ────────────────────────────────────────────────────────────────
create table if not exists public.newsletter_subscribers (
  id bigint generated always as identity primary key,
  name text not null,
  email text not null unique,
  consent boolean not null default true,
  created_at timestamptz not null default now()
);

alter table public.newsletter_subscribers enable row level security;

-- Każdy może się zapisać, ale wyłącznie z zaznaczoną zgodą.
drop policy if exists "public can subscribe" on public.newsletter_subscribers;
create policy "public can subscribe" on public.newsletter_subscribers
  for insert to anon, authenticated
  with check (consent = true);

-- Tylko zalogowany admin widzi listę i może usuwać.
drop policy if exists "admin can read" on public.newsletter_subscribers;
create policy "admin can read" on public.newsletter_subscribers
  for select to authenticated using (true);

drop policy if exists "admin can delete" on public.newsletter_subscribers;
create policy "admin can delete" on public.newsletter_subscribers
  for delete to authenticated using (true);

-- ── Ustawienia: linki social media (puste = ikona ukryta na stronie głównej) ──
insert into public.site_settings (key, value) values
  ('social_youtube', ''),
  ('social_instagram', ''),
  ('social_tiktok', '')
on conflict (key) do nothing;

-- ── Menu: feed zdjęć przenosi się z index.html na projekt-365.html ───────────
update public.nav_links
  set title = 'Projekt 365', url = 'projekt-365.html'
  where url = 'index.html';

-- ── Rebranding domyślnych meta (tylko jeśli nigdy nie były zmieniane) ─────────
update public.site_settings
  set value = 'Projekt Lepiej'
  where key = 'meta_title' and value = '365 – Projekt fotograficzny';

update public.site_settings
  set value = 'Moje miejsce w internecie o dążeniu do bycia lepszym.'
  where key = 'meta_description' and value = 'Codziennie jedno zdjęcie.';
