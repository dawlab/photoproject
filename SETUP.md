# Konfiguracja: Supabase + GitHub Pages

## 1. Supabase — baza danych

Wejdź na supabase.com → Twój projekt → **SQL Editor** → wklej zawartość pliku `schema.sql` → kliknij **Run**.

## 2. Supabase — Storage (bucket na zdjęcia)

W Supabase → **Storage** → utwórz dwa buckety:

| Nazwa | Public |
|---|---|
| `photos` | ✅ tak |
| `thumbnails` | ✅ tak |

## 3. Supabase — konto admina

W Supabase → **Authentication** → **Users** → **Add user**:
- Email: twój email
- Password: twoje hasło
- Kliknij **Create user**

To jest konto do logowania w `/admin.html`.

## 4. GitHub Pages

1. Utwórz nowe repozytorium na GitHub (może być publiczne lub prywatne)
2. Wrzuć wszystkie pliki projektu (bez `app.py`, `requirements.txt`, `Procfile`, `railway.toml` — te są zbędne)
3. W ustawieniach repo → **Pages** → Source: **Deploy from a branch** → Branch: `main` → Folder: `/ (root)`
4. Po chwili strona będzie dostępna pod `https://twoja-nazwa.github.io/nazwa-repo/`

## 5. Linki w menu

Po uruchomieniu strony zaloguj się do `/admin.html` i w zakładce **Menu** sprawdź czy linki nawigacji są poprawne (powinny wskazywać na `.html` pliki).

## Pliki które możesz usunąć (stary Flask)

- `app.py`
- `requirements.txt`
- `Procfile`
- `railway.toml`
- `templates/` (cały folder)
- `uploads/`, `thumbnails/` (lokalne zdjęcia — wgraj je ręcznie przez panel admina)
- `photos.db`
