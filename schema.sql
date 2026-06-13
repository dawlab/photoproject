-- Wklej to w Supabase → SQL Editor → Run

create table photos (
  id bigint primary key generated always as identity,
  day integer unique not null,
  title text not null,
  description text default '',
  mood text default '',
  filename text not null,
  thumb text not null,
  display text,
  shot_at timestamptz,
  exif_make text, exif_model text, exif_lens text,
  exif_focal text, exif_aperture text, exif_shutter text, exif_iso text,
  width integer, height integer,
  created_at timestamptz default now()
);

create table galleries (
  id bigint primary key generated always as identity,
  title text not null,
  description text default '',
  cover_photo_id bigint references photos(id) on delete set null,
  created_at timestamptz default now()
);

create table gallery_photos (
  gallery_id bigint references galleries(id) on delete cascade,
  photo_id bigint references photos(id) on delete cascade,
  position integer default 0,
  primary key (gallery_id, photo_id)
);

create table nav_links (
  id bigint primary key generated always as identity,
  title text not null,
  url text not null unique,
  position integer default 0
);

insert into nav_links (title, url, position) values
  ('Zdjęcia', '/', 0),
  ('Galerie', '/galerie.html', 1),
  ('Nastroje i nawyki', '/nastroje.html', 2);

create table habits (
  id bigint primary key generated always as identity,
  name text not null,
  description text default '',
  active boolean default true,
  created_at timestamptz default now()
);

create table habit_logs (
  habit_id bigint references habits(id) on delete cascade,
  photo_id bigint references photos(id) on delete cascade,
  done boolean default false,
  primary key (habit_id, photo_id)
);

create table profile (
  id integer primary key default 1 check (id = 1),
  name text default 'Moje 365',
  bio text default '',
  location text default '',
  website text default '',
  avatar text default '',
  follow_url text default '',
  follow_label text default 'Obserwuj'
);

insert into profile (id) values (1);

create table site_settings (
  key text primary key,
  value text default ''
);

insert into site_settings (key, value) values
  ('meta_title', '365 – Projekt fotograficzny'),
  ('meta_description', 'Codziennie jedno zdjęcie.'),
  ('og_image', '');

-- RLS: wszyscy mogą czytać, tylko zalogowani mogą pisać
alter table photos enable row level security;
alter table galleries enable row level security;
alter table gallery_photos enable row level security;
alter table nav_links enable row level security;
alter table habits enable row level security;
alter table habit_logs enable row level security;
alter table profile enable row level security;
alter table site_settings enable row level security;

create policy "public read" on photos for select using (true);
create policy "public read" on galleries for select using (true);
create policy "public read" on gallery_photos for select using (true);
create policy "public read" on nav_links for select using (true);
create policy "public read" on habits for select using (true);
create policy "public read" on habit_logs for select using (true);
create policy "public read" on profile for select using (true);
create policy "public read" on site_settings for select using (true);

create policy "auth write" on photos for all using (auth.role() = 'authenticated');
create policy "auth write" on galleries for all using (auth.role() = 'authenticated');
create policy "auth write" on gallery_photos for all using (auth.role() = 'authenticated');
create policy "auth write" on nav_links for all using (auth.role() = 'authenticated');
create policy "auth write" on habits for all using (auth.role() = 'authenticated');
create policy "auth write" on habit_logs for all using (auth.role() = 'authenticated');
create policy "auth write" on profile for all using (auth.role() = 'authenticated');
create policy "auth write" on site_settings for all using (auth.role() = 'authenticated');
