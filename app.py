import os
import sqlite3
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, abort, session, redirect, render_template
from PIL import Image, ExifTags

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.environ.get('DATA_DIR', BASE_DIR)
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
THUMB_DIR  = os.path.join(DATA_DIR, 'thumbnails')
DB_PATH    = os.path.join(DATA_DIR, 'photos.db')

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

ADMIN_PASSWORD_DEFAULT = os.environ.get('ADMIN_PASSWORD', 'zdjecia365')

def get_admin_password():
    with get_db() as conn:
        row = conn.execute("SELECT value FROM site_settings WHERE key='admin_password'").fetchone()
        return row['value'] if row and row['value'] else ADMIN_PASSWORD_DEFAULT

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

ALLOWED = {'jpg', 'jpeg', 'png', 'webp', 'heic'}

# ─── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day INTEGER UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            mood TEXT,
            filename TEXT NOT NULL,
            thumb TEXT NOT NULL,
            display TEXT,
            shot_at TEXT,
            exif_make TEXT, exif_model TEXT, exif_lens TEXT,
            exif_focal TEXT, exif_aperture TEXT, exif_shutter TEXT, exif_iso TEXT,
            width INTEGER, height INTEGER,
            created_at TEXT
        )''')
        # add display column if missing (migration)
        try: conn.execute('ALTER TABLE photos ADD COLUMN display TEXT')
        except: pass
        conn.execute('''CREATE TABLE IF NOT EXISTS galleries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, description TEXT,
            cover_photo_id INTEGER, created_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS gallery_photos (
            gallery_id INTEGER, photo_id INTEGER, position INTEGER DEFAULT 0,
            PRIMARY KEY (gallery_id, photo_id)
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS nav_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, url TEXT NOT NULL UNIQUE, position INTEGER DEFAULT 0
        )''')
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_nav_url ON nav_links(url)")
        except: pass
        for title, url, pos in [('Zdjęcia','/',0),('Galerie','/galerie',1),('Nastroje i nawyki','/nastroje',2)]:
            conn.execute('INSERT OR IGNORE INTO nav_links (title,url,position) VALUES (?,?,?)', (title,url,pos))
        conn.execute('''CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, description TEXT DEFAULT "",
            active INTEGER DEFAULT 1, created_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
            habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
            photo_id INTEGER REFERENCES photos(id) ON DELETE CASCADE,
            done INTEGER DEFAULT 0,
            PRIMARY KEY (habit_id, photo_id)
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id=1),
            name TEXT DEFAULT "Moje 365", bio TEXT DEFAULT "",
            location TEXT DEFAULT "", website TEXT DEFAULT "",
            avatar TEXT DEFAULT "", follow_url TEXT DEFAULT "",
            follow_label TEXT DEFAULT "Obserwuj"
        )''')
        conn.execute('INSERT OR IGNORE INTO profile (id) VALUES (1)')
        conn.execute('''CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY, value TEXT DEFAULT ""
        )''')
        for key, val in [
            ('meta_title', '365 – Projekt fotograficzny'),
            ('meta_description', 'Codziennie jedno zdjęcie.'),
            ('og_image', ''),
        ]:
            conn.execute('INSERT OR IGNORE INTO site_settings (key,value) VALUES (?,?)', (key,val))

# ─── Auth ──────────────────────────────────────────────────────────────────────

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            if request.path.startswith('/api/admin'):
                return jsonify({'error': 'unauthorized'}), 401
            return redirect('/new-day/login')
        return f(*args, **kwargs)
    return decorated

# ─── Image helpers ─────────────────────────────────────────────────────────────

def auto_orient(img):
    try:
        exif = img._getexif()
        if exif:
            for tag, val in exif.items():
                if ExifTags.TAGS.get(tag) == 'Orientation':
                    rotations = {3: 180, 6: 270, 8: 90}
                    if val in rotations:
                        img = img.rotate(rotations[val], expand=True)
                    break
    except Exception:
        pass
    return img

def make_thumb(src_path, thumb_path, width=500):
    img = Image.open(src_path).convert('RGB')
    img = auto_orient(img)
    img.thumbnail((width, width * 5), Image.LANCZOS)
    img.save(thumb_path, 'WEBP', quality=72, method=6)

def make_display(src_path, disp_path, max_side=1920):
    img = Image.open(src_path).convert('RGB')
    img = auto_orient(img)
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    img.save(disp_path, 'WEBP', quality=82, method=4)

def extract_exif(path):
    data = {}
    try:
        img = Image.open(path)
        raw = img._getexif()
        if not raw:
            w, h = img.size; data['width'] = w; data['height'] = h; return data
        tags = {ExifTags.TAGS.get(k, k): v for k, v in raw.items()}
        make  = str(tags.get('Make',  '')).strip()
        model = str(tags.get('Model', '')).strip()
        # remove make prefix from model if duplicated
        if model.lower().startswith(make.lower()):
            model = model[len(make):].strip()
        data['make']  = make
        data['model'] = model
        data['lens']  = str(tags.get('LensModel', '')).strip()

        focal = tags.get('FocalLength')
        if focal:
            try: data['focal'] = f"{round(focal[0]/focal[1])} mm"
            except: pass

        aperture = tags.get('FNumber')
        if aperture:
            try: data['aperture'] = f"f/{aperture[0]/aperture[1]:.1f}"
            except: pass

        shutter = tags.get('ExposureTime')
        if shutter:
            try:
                n, d = shutter
                data['shutter'] = f"1/{round(d/n)} s" if n == 1 or d/n > 1 else f"{n/d:.1f} s"
            except: pass

        iso = tags.get('ISOSpeedRatings')
        if iso: data['iso'] = str(iso)

        dt = tags.get('DateTimeOriginal') or tags.get('DateTime')
        if dt:
            try: data['shot_at'] = datetime.strptime(str(dt), '%Y:%m:%d %H:%M:%S').isoformat()
            except: pass

        w, h = img.size; data['width'] = w; data['height'] = h
    except Exception:
        pass
    return data

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED

def get_site_settings():
    with get_db() as conn:
        rows = conn.execute('SELECT key, value FROM site_settings').fetchall()
    s = {r['key']: r['value'] for r in rows}
    return {
        'meta_title':       s.get('meta_title', '365'),
        'meta_description': s.get('meta_description', ''),
        'og_image_url':     f"/uploads/{s['og_image']}" if s.get('og_image') else '',
    }

# ─── Static files ──────────────────────────────────────────────────────────────

@app.route('/uploads/<path:filename>')
def serve_upload(filename): return send_from_directory(UPLOAD_DIR, filename)

@app.route('/thumbnails/<path:filename>')
def serve_thumb(filename): return send_from_directory(THUMB_DIR, filename)

# ─── Public API ────────────────────────────────────────────────────────────────

@app.route('/api/photos')
def api_photos():
    page = int(request.args.get('page', 1))
    per  = int(request.args.get('per', 30))
    offset = (page - 1) * per
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0]
        rows  = conn.execute('SELECT * FROM photos ORDER BY day DESC LIMIT ? OFFSET ?', (per, offset)).fetchall()
    return jsonify({'total': total, 'page': page, 'per': per, 'photos': [dict(r) for r in rows]})

@app.route('/api/photos/<int:photo_id>')
def api_photo(photo_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM photos WHERE id=?', (photo_id,)).fetchone()
        if not row: abort(404)
        logs = conn.execute('''
            SELECT h.id, h.name, h.description, hl.done
            FROM habits h
            LEFT JOIN habit_logs hl ON hl.habit_id=h.id AND hl.photo_id=?
            WHERE h.active=1 ORDER BY h.id
        ''', (photo_id,)).fetchall()
    result = dict(row)
    result['habits'] = [dict(l) for l in logs]
    return jsonify(result)

@app.route('/api/profile')
def api_profile():
    with get_db() as conn:
        p = conn.execute('SELECT * FROM profile WHERE id=1').fetchone()
        total_photos    = conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0]
        total_galleries = conn.execute('SELECT COUNT(*) FROM galleries').fetchone()[0]
        days = [r[0] for r in conn.execute('SELECT day FROM photos ORDER BY day DESC').fetchall()]
    streak = 0
    if days:
        streak = 1
        for i in range(len(days)-1):
            if days[i] - days[i+1] == 1: streak += 1
            else: break
    result = dict(p) if p else {}
    result.update({'total_photos': total_photos, 'total_galleries': total_galleries, 'streak': streak})
    return jsonify(result)

@app.route('/api/settings')
def api_settings():
    return jsonify(get_site_settings())

@app.route('/api/galleries')
def api_galleries():
    with get_db() as conn:
        rows = conn.execute('''
            SELECT g.*, COUNT(gp.photo_id) as photo_count, p.thumb as cover_thumb
            FROM galleries g
            LEFT JOIN gallery_photos gp ON gp.gallery_id = g.id
            LEFT JOIN photos p ON p.id = g.cover_photo_id
            GROUP BY g.id ORDER BY g.created_at DESC
        ''').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/galleries/<int:gid>')
def api_gallery(gid):
    with get_db() as conn:
        g = conn.execute('SELECT * FROM galleries WHERE id=?', (gid,)).fetchone()
        if not g: abort(404)
        photos = conn.execute('''
            SELECT p.* FROM photos p
            JOIN gallery_photos gp ON gp.photo_id = p.id
            WHERE gp.gallery_id = ? ORDER BY gp.position, p.day
        ''', (gid,)).fetchall()
    return jsonify({**dict(g), 'photos': [dict(p) for p in photos]})

@app.route('/api/photos/<int:photo_id>/memories')
def api_memories(photo_id):
    with get_db() as conn:
        p = conn.execute('SELECT COALESCE(shot_at, created_at) as dt FROM photos WHERE id=?', (photo_id,)).fetchone()
        if not p or not p['dt']:
            return jsonify([])
        base = p['dt'][:10]  # YYYY-MM-DD
        intervals = [
            ('Tydzień temu',   "date(?, '-7 days')"),
            ('Miesiąc temu',   "date(?, '-1 month')"),
            ('Rok temu',       "date(?, '-1 year')"),
            ('2 lata temu',    "date(?, '-2 years')"),
            ('3 lata temu',    "date(?, '-3 years')"),
        ]
        memories = []
        for label, expr in intervals:
            row = conn.execute(f'''
                SELECT id, title, thumb, day FROM photos
                WHERE date(COALESCE(shot_at, created_at)) = {expr}
                AND id != ?
                LIMIT 1
            ''', (base, photo_id)).fetchone()
            if row:
                memories.append({'label': label, **dict(row)})
    return jsonify(memories)

@app.route('/api/nav')
def api_nav():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM nav_links ORDER BY position, id').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/nav', methods=['POST'])
@require_admin
def api_nav_create():
    data = request.json or {}
    title = (data.get('title') or '').strip()
    url   = (data.get('url')   or '').strip()
    if not title or not url: return jsonify({'error': 'title and url required'}), 400
    with get_db() as conn:
        pos = (conn.execute('SELECT MAX(position) FROM nav_links').fetchone()[0] or 0) + 1
        cur = conn.execute('INSERT INTO nav_links (title,url,position) VALUES (?,?,?)', (title,url,pos))
    return jsonify({'ok': True, 'id': cur.lastrowid}), 201

@app.route('/api/admin/nav/<int:nid>', methods=['PUT'])
@require_admin
def api_nav_update(nid):
    data = request.json or {}
    fields = ['title','url','position']
    updates = {k: data[k] for k in fields if k in data}
    if not updates: return jsonify({'error': 'nothing'}), 400
    sets = ', '.join(f'{k}=?' for k in updates)
    with get_db() as conn:
        conn.execute(f'UPDATE nav_links SET {sets} WHERE id=?', (*updates.values(), nid))
    return jsonify({'ok': True})

@app.route('/api/admin/nav/<int:nid>', methods=['DELETE'])
@require_admin
def api_nav_delete(nid):
    with get_db() as conn:
        conn.execute('DELETE FROM nav_links WHERE id=?', (nid,))
    return jsonify({'ok': True})

@app.route('/api/habits')
def api_habits():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM habits WHERE active=1 ORDER BY id').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/stats')
def api_stats():
    year     = request.args.get('year', type=int)
    habit_id = request.args.get('habit_id', type=int)
    with get_db() as conn:
        years = [r[0] for r in conn.execute(
            "SELECT DISTINCT strftime('%Y', COALESCE(shot_at, created_at)) as y FROM photos WHERE y IS NOT NULL ORDER BY y DESC"
        ).fetchall()]
        base_filter = "strftime('%Y', COALESCE(shot_at, created_at))=?" if year else "1=1"
        params = (str(year),) if year else ()

        if habit_id:
            # Habit calendar: only photos that have a log for this habit
            cal_rows = conn.execute(f'''
                SELECT date(COALESCE(p.shot_at, p.created_at)) as d, hl.done, p.id
                FROM photos p
                JOIN habit_logs hl ON hl.photo_id = p.id AND hl.habit_id = ?
                WHERE {base_filter}
                ORDER BY d
            ''', (habit_id, *params)).fetchall()
            done_count = sum(1 for r in cal_rows if r[1])
            fail_count = sum(1 for r in cal_rows if not r[1])
            calendar = [{'date': r[0], 'done': bool(r[1]), 'id': r[2]} for r in cal_rows if r[0]]
            return jsonify({'years': years, 'calendar': calendar,
                            'done_count': done_count, 'fail_count': fail_count, 'is_habit': True})
        else:
            mood_rows = conn.execute(
                f"SELECT mood, COUNT(*) FROM photos WHERE mood!='' AND {base_filter} GROUP BY mood", params
            ).fetchall()
            cal_rows = conn.execute(
                f"SELECT date(COALESCE(shot_at, created_at)) as d, mood, id FROM photos WHERE {base_filter} ORDER BY d", params
            ).fetchall()
            total = sum(r[1] for r in mood_rows) or 1
            moods    = {r[0]: round(r[1] / total * 100) for r in mood_rows}
            calendar = [{'date': r[0], 'mood': r[1], 'id': r[2]} for r in cal_rows if r[0]]
            return jsonify({'years': years, 'moods': moods, 'calendar': calendar, 'is_habit': False})

# ─── Admin auth ────────────────────────────────────────────────────────────────

@app.route('/new-day/login', methods=['GET'])
def admin_login_page(): return render_template('login.html', **get_site_settings())

@app.route('/new-day/login', methods=['POST'])
def admin_login():
    data = request.json or {}
    if data.get('password') == get_admin_password():
        session['admin'] = True
        return jsonify({'ok': True})
    return jsonify({'error': 'Złe hasło'}), 401

@app.route('/new-day/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'ok': True})

# ─── Admin API ─────────────────────────────────────────────────────────────────

@app.route('/api/admin/photos', methods=['POST'])
@require_admin
def api_add_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['photo']
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    day   = request.form.get('day', '').strip()
    title = request.form.get('title', '').strip()
    if not day or not title:
        return jsonify({'error': 'day and title required'}), 400
    day = int(day)
    ext   = file.filename.rsplit('.', 1)[1].lower()
    fname = f"day{day:04d}.{ext}"
    tname = f"day{day:04d}_thumb.webp"
    dname = f"day{day:04d}_display.webp"
    fpath = os.path.join(UPLOAD_DIR, fname)
    tpath = os.path.join(THUMB_DIR,  tname)
    dpath = os.path.join(UPLOAD_DIR, dname)

    file.save(fpath)
    exif = extract_exif(fpath)
    make_thumb(fpath, tpath)
    make_display(fpath, dpath)
    # Use manually entered date if EXIF has no date
    if not exif.get('shot_at') and request.form.get('manual_date'):
        exif['shot_at'] = request.form['manual_date'] + 'T00:00:00'

    with get_db() as conn:
        try:
            conn.execute('''
                INSERT INTO photos (day, title, description, mood, filename, thumb, display,
                    shot_at, exif_make, exif_model, exif_lens, exif_focal,
                    exif_aperture, exif_shutter, exif_iso, width, height, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            ''', (day, title, request.form.get('description',''), request.form.get('mood',''),
                  fname, tname, dname,
                  exif.get('shot_at'), exif.get('make'), exif.get('model'),
                  exif.get('lens'), exif.get('focal'), exif.get('aperture'),
                  exif.get('shutter'), exif.get('iso'), exif.get('width'), exif.get('height')))
        except sqlite3.IntegrityError:
            return jsonify({'error': f'Dzień {day} już istnieje'}), 409
        photo_id_new = conn.execute('SELECT id FROM photos WHERE day=?', (day,)).fetchone()[0]
        _save_habit_logs(conn, photo_id_new, request.form)
    return jsonify({'ok': True, 'day': day}), 201

def _save_habit_logs(conn, photo_id, form):
    habits = conn.execute('SELECT id FROM habits WHERE active=1').fetchall()
    for h in habits:
        key = f'habit_{h["id"]}'
        if key in form:
            done = 1 if form[key] in ('1', 'true', 'on') else 0
            conn.execute('INSERT OR REPLACE INTO habit_logs (habit_id, photo_id, done) VALUES (?,?,?)',
                         (h['id'], photo_id, done))

@app.route('/api/admin/photos/<int:photo_id>', methods=['PUT'])
@require_admin
def api_update_photo(photo_id):
    data = request.json or {}
    fields  = ['title', 'description', 'mood', 'shot_at']
    updates = {k: data[k] for k in fields if k in data}
    if 'shot_at' in updates and updates['shot_at']:
        updates['shot_at'] = updates['shot_at'][:10] + 'T00:00:00'
    # Handle habit_logs if present
    habit_logs = data.get('habit_logs')  # {habit_id: done}
    with get_db() as conn:
        if updates:
            sets = ', '.join(f'{k}=?' for k in updates)
            conn.execute(f'UPDATE photos SET {sets} WHERE id=?', (*updates.values(), photo_id))
        if habit_logs:
            for hid, done in habit_logs.items():
                conn.execute('INSERT OR REPLACE INTO habit_logs (habit_id, photo_id, done) VALUES (?,?,?)',
                             (int(hid), photo_id, 1 if done else 0))
    return jsonify({'ok': True})

@app.route('/api/admin/photos/<int:photo_id>', methods=['DELETE'])
@require_admin
def api_delete_photo(photo_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM photos WHERE id=?', (photo_id,)).fetchone()
        if not row: abort(404)
        conn.execute('DELETE FROM photos WHERE id=?', (photo_id,))
    for d, n in [(UPLOAD_DIR, row['filename']), (THUMB_DIR, row['thumb']), (UPLOAD_DIR, row['display'] or '')]:
        if n:
            p = os.path.join(d, n)
            if os.path.exists(p): os.remove(p)
    return jsonify({'ok': True})

@app.route('/api/admin/galleries', methods=['POST'])
@require_admin
def api_create_gallery():
    data  = request.json or {}
    title = (data.get('title') or '').strip()
    if not title: return jsonify({'error': 'title required'}), 400
    with get_db() as conn:
        cur = conn.execute("INSERT INTO galleries (title, description, created_at) VALUES (?,?,datetime('now'))",
                           (title, data.get('description', '')))
    return jsonify({'ok': True, 'id': cur.lastrowid}), 201

@app.route('/api/admin/galleries/<int:gid>', methods=['PUT'])
@require_admin
def api_update_gallery(gid):
    data = request.json or {}
    fields  = ['title', 'description', 'cover_photo_id']
    updates = {k: data[k] for k in fields if k in data}
    if not updates: return jsonify({'error': 'nothing to update'}), 400
    sets = ', '.join(f'{k}=?' for k in updates)
    with get_db() as conn:
        conn.execute(f'UPDATE galleries SET {sets} WHERE id=?', (*updates.values(), gid))
    return jsonify({'ok': True})

@app.route('/api/admin/galleries/<int:gid>', methods=['DELETE'])
@require_admin
def api_delete_gallery(gid):
    with get_db() as conn:
        conn.execute('DELETE FROM galleries WHERE id=?', (gid,))
    return jsonify({'ok': True})

@app.route('/api/admin/galleries/<int:gid>/photos', methods=['POST'])
@require_admin
def api_gallery_add_photo(gid):
    data = request.json or {}
    pid  = data.get('photo_id')
    if not pid: return jsonify({'error': 'photo_id required'}), 400
    with get_db() as conn:
        g = conn.execute('SELECT cover_photo_id FROM galleries WHERE id=?', (gid,)).fetchone()
        conn.execute('INSERT OR IGNORE INTO gallery_photos (gallery_id, photo_id) VALUES (?,?)', (gid, pid))
        if g and not g['cover_photo_id']:
            conn.execute('UPDATE galleries SET cover_photo_id=? WHERE id=?', (pid, gid))
    return jsonify({'ok': True})

@app.route('/api/admin/galleries/<int:gid>/photos/<int:pid>', methods=['DELETE'])
@require_admin
def api_gallery_remove_photo(gid, pid):
    with get_db() as conn:
        conn.execute('DELETE FROM gallery_photos WHERE gallery_id=? AND photo_id=?', (gid, pid))
        g = conn.execute('SELECT cover_photo_id FROM galleries WHERE id=?', (gid,)).fetchone()
        if g and g['cover_photo_id'] == pid:
            first = conn.execute('SELECT photo_id FROM gallery_photos WHERE gallery_id=? ORDER BY position LIMIT 1', (gid,)).fetchone()
            conn.execute('UPDATE galleries SET cover_photo_id=? WHERE id=?', (first['photo_id'] if first else None, gid))
    return jsonify({'ok': True})

@app.route('/api/admin/profile', methods=['PUT'])
@require_admin
def api_update_profile():
    data   = request.json or {}
    fields = ['name', 'bio', 'location', 'website', 'follow_url', 'follow_label']
    updates = {k: data[k] for k in fields if k in data}
    if not updates: return jsonify({'error': 'nothing to update'}), 400
    sets = ', '.join(f'{k}=?' for k in updates)
    with get_db() as conn:
        conn.execute(f'UPDATE profile SET {sets} WHERE id=1', list(updates.values()))
    return jsonify({'ok': True})

@app.route('/api/admin/profile/avatar', methods=['POST'])
@require_admin
def api_update_avatar():
    if 'avatar' not in request.files: return jsonify({'error': 'no file'}), 400
    file = request.files['avatar']
    fname = 'avatar.webp'
    path  = os.path.join(UPLOAD_DIR, fname)
    file.save(path)
    img = Image.open(path).convert('RGB')
    img.thumbnail((300, 300), Image.LANCZOS)
    img.save(path, 'WEBP', quality=85)
    with get_db() as conn:
        conn.execute("UPDATE profile SET avatar=? WHERE id=1", (fname,))
    return jsonify({'ok': True, 'avatar': fname})

@app.route('/api/admin/habits', methods=['POST'])
@require_admin
def api_create_habit():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    if not name: return jsonify({'error': 'name required'}), 400
    with get_db() as conn:
        cur = conn.execute("INSERT INTO habits (name, description, created_at) VALUES (?,?,datetime('now'))",
                           (name, data.get('description', '')))
    return jsonify({'ok': True, 'id': cur.lastrowid}), 201

@app.route('/api/admin/habits/<int:hid>', methods=['PUT'])
@require_admin
def api_update_habit(hid):
    data = request.json or {}
    fields = ['name', 'description', 'active']
    updates = {k: data[k] for k in fields if k in data}
    if not updates: return jsonify({'error': 'nothing'}), 400
    sets = ', '.join(f'{k}=?' for k in updates)
    with get_db() as conn:
        conn.execute(f'UPDATE habits SET {sets} WHERE id=?', (*updates.values(), hid))
    return jsonify({'ok': True})

@app.route('/api/admin/habits/<int:hid>', methods=['DELETE'])
@require_admin
def api_delete_habit(hid):
    with get_db() as conn:
        conn.execute('UPDATE habits SET active=0 WHERE id=?', (hid,))
    return jsonify({'ok': True})

@app.route('/api/admin/password', methods=['PUT'])
@require_admin
def api_change_password():
    data = request.json or {}
    current = data.get('current', '')
    new_pw  = data.get('new', '').strip()
    if current != get_admin_password():
        return jsonify({'error': 'Obecne hasło jest nieprawidłowe'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': 'Nowe hasło musi mieć co najmniej 6 znaków'}), 400
    with get_db() as conn:
        conn.execute('INSERT OR REPLACE INTO site_settings (key,value) VALUES (?,?)', ('admin_password', new_pw))
    return jsonify({'ok': True})

@app.route('/api/admin/settings', methods=['PUT'])
@require_admin
def api_update_settings():
    data   = request.json or {}
    fields = ['meta_title', 'meta_description', 'og_image']
    for key in fields:
        if key in data:
            with get_db() as conn:
                conn.execute('INSERT OR REPLACE INTO site_settings (key,value) VALUES (?,?)', (key, data[key]))
    return jsonify({'ok': True})

# ─── Pages ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index(): return render_template('index.html', **get_site_settings())

@app.route('/galerie')
def galleries_page(): return render_template('galleries.html', **get_site_settings())

@app.route('/galeria/<int:gid>')
def gallery_page(gid): return render_template('gallery.html', **get_site_settings())

@app.route('/nastroje')
def moods_page(): return render_template('moods.html', **get_site_settings())

@app.route('/photo/<int:photo_id>')
def photo_page(photo_id): return render_template('photo.html', **get_site_settings())

@app.route('/new-day')
@app.route('/new-day/')
@require_admin
def admin(): return render_template('admin.html', **get_site_settings())

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(debug=False, port=port)
