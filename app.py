from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_from_directory
import sqlite3, json, hashlib, os, re, uuid, base64
from datetime import datetime, date, timedelta, timezone, time as dtime
from dotenv import load_dotenv

load_dotenv() # Load .env if present

from werkzeug.utils import secure_filename

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

# ── Timezone WIB (UTC+7) ──────────────────────────────────────────────────────
WIB = timezone(timedelta(hours=7))

def now_wib():
    """Return current datetime in WIB (UTC+7)."""
    return datetime.now(WIB)

def today_wib():
    """Return current date string (YYYY-MM-DD) in WIB."""
    return now_wib().strftime('%Y-%m-%d')

def wib_str():
    """Return current WIB datetime as SQLite-compatible string."""
    return now_wib().strftime('%Y-%m-%d %H:%M:%S')


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'S3C-SmartSustainableSchoolCanteen-2024')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

# PWA Support
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js')

BASE_DIR   = os.path.dirname(__file__)
DATABASE_URL = os.environ.get('DATABASE_URL') # e.g. postgresql://user:pass@host/db

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if DATABASE_URL:
            import psycopg2
            from psycopg2.extras import DictCursor
            db = g._database = psycopg2.connect(DATABASE_URL)
            # Make psycopg2 act like sqlite3.Row
        else:
            DATABASE = os.path.join(BASE_DIR, 'instance', 's3c.db')
            os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
            db = g._database = sqlite3.connect(DATABASE)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exc):
    db = getattr(g, '_database', None)
    if db: db.close()

def query_db(q, args=(), one=False, commit=False):
    db = get_db()
    if DATABASE_URL:
        import re
        from psycopg2.extras import DictCursor
        
        # 1. Convert ? placeholders to %s
        q = q.replace('?', '%s')
        
        # 2. Append RETURNING id to INSERT if missing (for PostgreSQL)
        if q.strip().upper().startswith('INSERT') and 'RETURNING' not in q.upper():
            # Only append if we expect to return an ID (common in S3C queries)
            q += ' RETURNING id'
        
        # 2. Convert SQLite date functions to PostgreSQL
        # Pattern: date(datetime(column, '+7 hours')) -> (column::timestamp + interval '7 hours')::date
        q = re.sub(r"date\(datetime\(([^,]+),\s*'\+7\s*hours'\)\)", r"(\1::timestamp + interval '7 hours')::date", q, flags=re.IGNORECASE)
        
        # 3. Simple syntax replacements
        q = q.replace('datetime(\'now\')', 'CURRENT_TIMESTAMP')
        q = q.replace('date(\'now\')', 'CURRENT_DATE')
        # But for compatibility, we'll try to handle it.
        cur = db.cursor(cursor_factory=DictCursor)
        try:
            cur.execute(q, args)
            res = None
            if commit:
                db.commit()
                # Try to get lastrowid if applicable
                try: res = cur.fetchone()[0]
                except: res = None
            else:
                rv = cur.fetchall()
                res = (rv[0] if rv else None) if one else rv
            cur.close()
            return res
        except Exception as e:
            if commit: db.rollback()
            try: cur.close()
            except: pass
            raise e
    else:
        cur = db.execute(q, args)
        if commit:
            db.commit()
            return cur.lastrowid
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()
def check_pw(p, h): return hash_pw(p) == h
def waste_pts(lvl): return {'habis':10,'none':10,'sedikit':7,'setengah':3,'banyak':0}.get(lvl,0)
def get_points(uid):
    r = query_db('SELECT SUM(points_earned) as t FROM waste_logs WHERE student_id=?',[uid],one=True)
    return r['t'] or 0

def allowed_file(fname):
    return '.' in fname and fname.rsplit('.',1)[1].lower() in ALLOWED_EXT

def save_upload(file_obj, folder=None):
    """Convert uploaded image to base64 data-URI string for DB storage.
    Works on Railway (ephemeral filesystem) because data lives in DB."""
    if not file_obj or file_obj.filename == '': return None
    if not allowed_file(file_obj.filename): return None
    try:
        from PIL import Image
        import io
        img = Image.open(file_obj.stream)
        img = img.convert('RGB')
        # Resize max 800px to keep DB size reasonable
        img.thumbnail((800, 800), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=82, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def delete_upload(folder, fname):
    """No-op: images now stored as base64 in DB, nothing to delete on disk."""
    pass

# ── DB init & seed ─────────────────────────────────────────────────────────

def init_db():
    db = get_db()
    auto_inc = "SERIAL" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now_func = "CURRENT_TIMESTAMP" if DATABASE_URL else "datetime('now')"
    date_func = "CURRENT_DATE" if DATABASE_URL else "date('now')"
    
    # We use a wrapper to handle the schema creation
    queries = [
        f"CREATE TABLE IF NOT EXISTS users (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, kelas TEXT, tenant_name TEXT, photo TEXT, weight REAL DEFAULT 0, height REAL DEFAULT 0, age INTEGER DEFAULT 16, gender TEXT DEFAULT 'L', created_at TEXT DEFAULT {now_func})",
        f"CREATE TABLE IF NOT EXISTS menus (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, tenant_id INTEGER NOT NULL, name TEXT NOT NULL, description TEXT, price REAL NOT NULL, category TEXT, calories REAL DEFAULT 0, protein REAL DEFAULT 0, carbs REAL DEFAULT 0, fat REAL DEFAULT 0, fiber REAL DEFAULT 0, is_healthy INTEGER DEFAULT 0, is_available INTEGER DEFAULT 1, image_emoji TEXT DEFAULT '🍱', image_file TEXT, created_at TEXT DEFAULT {now_func})",
        f"CREATE TABLE IF NOT EXISTS orders (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, student_id INTEGER NOT NULL, tenant_id INTEGER NOT NULL, status TEXT DEFAULT 'pending', total_price REAL DEFAULT 0, notes TEXT, created_at TEXT DEFAULT {now_func})",
        f"CREATE TABLE IF NOT EXISTS order_items (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, order_id INTEGER NOT NULL, menu_id INTEGER NOT NULL, quantity INTEGER DEFAULT 1, subtotal REAL DEFAULT 0)",
        f"CREATE TABLE IF NOT EXISTS waste_logs (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, student_id INTEGER NOT NULL, menu_id INTEGER, waste_level TEXT, waste_reason TEXT, points_earned INTEGER DEFAULT 0, log_date TEXT DEFAULT {date_func}, created_at TEXT DEFAULT {now_func})",
        f"CREATE TABLE IF NOT EXISTS education_posts (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, title TEXT NOT NULL, content TEXT NOT NULL, category TEXT, image_emoji TEXT DEFAULT '📚', author_id INTEGER, created_at TEXT DEFAULT {now_func})",
        f"CREATE TABLE IF NOT EXISTS marketplace_items (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, name TEXT NOT NULL, description TEXT, category TEXT, price REAL DEFAULT 0, unit TEXT DEFAULT 'pcs', stock INTEGER DEFAULT 0, image_emoji TEXT DEFAULT '♻️', image_file TEXT, seller_id INTEGER, is_available INTEGER DEFAULT 1, created_at TEXT DEFAULT {now_func})",
        f"CREATE TABLE IF NOT EXISTS edu_videos (id {auto_inc if DATABASE_URL else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, title TEXT NOT NULL, youtube_url TEXT NOT NULL, description TEXT, category TEXT DEFAULT 'umum', uploader_id INTEGER, is_published INTEGER DEFAULT 1, created_at TEXT DEFAULT {now_func})"
    ]

    if DATABASE_URL:
        cur = db.cursor()
        for q in queries: cur.execute(q)
        db.commit()
        cur.close()
    else:
        for q in queries: db.execute(q)
        db.commit()

    if query_db('SELECT COUNT(*) as c FROM users', one=True)['c'] > 0:
        return

    # ── seed ──
    users = [
        ('Admin S3C','admin',hash_pw('admin123'),'admin',None,None),
        ('Bu Sari','tenant1',hash_pw('tenant123'),'tenant',None,'Warung Sehat Bu Sari'),
        ('Pak Budi','tenant2',hash_pw('tenant123'),'tenant',None,'Kantin Pak Budi'),
        ('Andi Pratama','andi',hash_pw('student123'),'student','XII A',None),
        ('Siti Rahayu','siti',hash_pw('student123'),'student','XI B',None),
    ]
    for u in users:
        query_db('INSERT INTO users (name,username,password,role,kelas,tenant_name) VALUES (?,?,?,?,?,?)', u, commit=True)

    def uid(u): return query_db('SELECT id FROM users WHERE username=?',(u,),one=True)['id']
    t1,t2,s1,s2,adm = uid('tenant1'),uid('tenant2'),uid('andi'),uid('siti'),uid('admin')

    menus = [
        (t1,'Nasi Sayur Tempe','Nasi putih dengan tempe goreng dan sayuran segar',8000,'makanan',350,12,55,8,4,1,'🍚'),
        (t1,'Gado-Gado','Sayuran rebus dengan bumbu kacang dan lontong',10000,'makanan',280,10,35,12,6,1,'🥗'),
        (t1,'Jus Buah Segar','Campuran buah segar tanpa gula tambahan',6000,'minuman',90,1,22,0,2,1,'🧃'),
        (t1,'Pisang Goreng','Pisang goreng crispy dengan sedikit minyak',4000,'snack',150,2,30,3,2,1,'🍌'),
        (t2,'Bakso Kuah','Bakso sapi dengan kuah bening dan mie',12000,'makanan',420,18,50,14,1,0,'🍜'),
        (t2,'Mie Goreng','Mie goreng special bumbu racikan',10000,'makanan',450,12,65,16,1,0,'🍝'),
        (t2,'Es Teh Manis','Teh manis dengan es batu segar',3000,'minuman',80,0,20,0,0,0,'🧋'),
        (t2,'Lumpia Sayur','Lumpia isi sayuran segar bergizi',5000,'snack',120,4,18,4,3,1,'🥟'),
    ]
    for m in menus:
        query_db('INSERT INTO menus (tenant_id,name,description,price,category,calories,protein,carbs,fat,fiber,is_healthy,image_emoji) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', m, commit=True)

    m1 = query_db("SELECT id FROM menus WHERE name='Nasi Sayur Tempe'", one=True)['id']
    m3 = query_db("SELECT id FROM menus WHERE name='Jus Buah Segar'", one=True)['id']
    
    # Orders
    oid = query_db('INSERT INTO orders (student_id,tenant_id,total_price,status) VALUES (?,?,?,?) RETURNING id' if DATABASE_URL else 'INSERT INTO orders (student_id,tenant_id,total_price,status) VALUES (?,?,?,?)',
                    (s1,t1,18000,'done'), commit=True)
    
    query_db('INSERT INTO order_items (order_id,menu_id,quantity,subtotal) VALUES (?,?,?,?)', (oid,m1,1,8000), commit=True)
    query_db('INSERT INTO order_items (order_id,menu_id,quantity,subtotal) VALUES (?,?,?,?)', (oid,m3,1,6000), commit=True)

    for lvl,rsn,pts in [('habis','Enak!',10),('sedikit','Kenyang',7),('habis','Lapar',10)]:
        query_db('INSERT INTO waste_logs (student_id,waste_level,waste_reason,points_earned) VALUES (?,?,?,?)', (s1,lvl,rsn,pts), commit=True)
    query_db('INSERT INTO waste_logs (student_id,waste_level,waste_reason,points_earned) VALUES (?,?,?,?)', (s2,'setengah','Kurang enak',3), commit=True)

    edu = [
        ('Pentingnya Sarapan Bergizi untuk Konsentrasi Belajar','Sarapan pagi adalah kunci energi untuk aktivitas belajar sehari-hari.\n\n🍚 KARBOHIDRAT - Nasi merah atau oatmeal memberikan energi tahan lama.\n\n🥚 PROTEIN - Telur, tempe, tahu membantu konsentrasi.\n\n🥦 SERAT - Sayuran dan buah untuk imun tubuh.','gizi','🌅',adm),
        ('Food Waste: Masalah Besar dari Piring Kita','1/3 makanan dunia terbuang sia-sia!\n\n🌍 Gas metana dari sisa makanan 25x lebih kuat dari CO2.\n\n💧 1 kg daging butuh 15.000 liter air.\n\nCatat sisa makananmu di Food Waste Log!','lingkungan','🌍',adm),
        ('Mengenal Makronutrien','🍚 KARBOHIDRAT (45-65%) - Sumber energi utama.\n\n🥩 PROTEIN (10-35%) - Bangun sel dan otot.\n\n🥑 LEMAK (20-35%) - Serap vitamin A,D,E,K.','gizi','⚗️',adm),
        ('Kompos dari Sisa Kantin','Sisa makanan kantin → KOMPOS → Pupuk tanaman!\n\n1. Kumpulkan sisa organik\n2. Cacah kecil-kecil\n3. Fermentasi 2-4 minggu\n4. Kompos siap pakai!','lingkungan','🌱',adm),
    ]
    for t,c,cat,em,a in edu:
        query_db('INSERT INTO education_posts (title,content,category,image_emoji,author_id) VALUES (?,?,?,?,?)', (t,c,cat,em,a), commit=True)

    mp = [
        ('Kompos Organik Premium','Kompos dari sisa sayuran kantin, kaya N-P-K.','kompos',15000,'kg',50,'🌿',adm),
        ('Pupuk Cair Bioaktif','Pupuk cair dari lindi kompos dan sisa buah.','pupuk_cair',20000,'liter',30,'💧',adm),
        ('Eco Enzyme Multi-Guna','Cairan fermentasi kulit buah untuk pupuk alami.','pupuk_cair',12000,'botol 500ml',25,'🍊',adm),
        ('Media Tanam Campuran','Kompos matang + sekam bakar + tanah subur.','kompos',25000,'karung 5kg',20,'🪴',adm),
        ('Pot Daur Ulang Kreatif','Pot dari botol bekas dihias siswa.','kerajinan',8000,'pcs',40,'♻️',adm),
        ('Paket Starter Berkebun','2kg kompos + 1L pupuk cair + bibit sayuran.','lainnya',45000,'paket',15,'🎁',adm),
    ]
    for n,d,c,p,u,s,e,sid in mp:
        query_db('INSERT INTO marketplace_items (name,description,category,price,unit,stock,image_emoji,seller_id) VALUES (?,?,?,?,?,?,?,?)', (n,d,c,p,u,s,e,sid), commit=True)

    vids = [
        ('Cara Membuat Kompos dari Sampah Dapur','https://www.youtube.com/embed/9yZSMWxFLYs','Panduan kompos dari sisa organik dapur.','lingkungan',adm),
        ('Gizi Seimbang untuk Remaja','https://www.youtube.com/embed/u5UcmMbdwAY','Panduan pola makan sehat remaja SMA.','gizi',adm),
        ('Zero Waste Lifestyle di Sekolah','https://www.youtube.com/embed/OasbYWF4_S8','Gaya hidup zero waste dari kantin sekolah.','zerowaste',adm),
        ('Berkebun Organik di Lahan Sempit','https://www.youtube.com/embed/Q_oI4VXKPJM','Sayuran organik dengan kompos daur ulang.','pertanian',adm),
    ]
    for t,u,d,c,a in vids:
        query_db('INSERT INTO edu_videos (title,youtube_url,description,category,uploader_id,is_published) VALUES (?,?,?,?,?,1)', (t,u,d,c,a), commit=True)

    print("✅ Database seeded!")


def migrate_db():
    """Safely add new columns to existing database without losing data."""
    db = get_db()
    if DATABASE_URL:
        try:
            cur = db.cursor()
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users';")
            cols = [r[0] for r in cur.fetchall()]
            if 'weight' not in cols:
                cur.execute("ALTER TABLE users ADD COLUMN weight REAL DEFAULT 0")
                cur.execute("ALTER TABLE users ADD COLUMN height REAL DEFAULT 0")
                cur.execute("ALTER TABLE users ADD COLUMN age INTEGER DEFAULT 16")
                cur.execute("ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'L'")
            db.commit()
            cur.close()
        except Exception as e:
            db.rollback()
            print("Migration PG error:", e)
        return
    
    db = get_db()
    # Check if column already exists using SQLite specific PRAGMA
    try:
        cols = [row[1] for row in db.execute("PRAGMA table_info(menus)").fetchall()]
        if 'image_file' not in cols:
            db.execute("ALTER TABLE menus ADD COLUMN image_file TEXT")
        
        cols = [row[1] for row in db.execute("PRAGMA table_info(marketplace_items)").fetchall()]
        if 'image_file' not in cols:
            db.execute("ALTER TABLE marketplace_items ADD COLUMN image_file TEXT")
            
        cols = [row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()]
        if 'photo' not in cols:
            db.execute("ALTER TABLE users ADD COLUMN photo TEXT")
        if 'weight' not in cols:
            db.execute("ALTER TABLE users ADD COLUMN weight REAL DEFAULT 0")
            db.execute("ALTER TABLE users ADD COLUMN height REAL DEFAULT 0")
            db.execute("ALTER TABLE users ADD COLUMN age INTEGER DEFAULT 16")
            db.execute("ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'L'")
            
        # Create new tables if missing
        db.executescript("""
            CREATE TABLE IF NOT EXISTS edu_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, youtube_url TEXT NOT NULL,
                description TEXT, category TEXT DEFAULT 'umum',
                uploader_id INTEGER, is_published INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (uploader_id) REFERENCES users(id)
            );
        """)
        db.commit()
    except:
        pass

# ── Jinja filters ─────────────────────────────────────────────────────────────

@app.template_filter('strftime')
def strftime_filter(s, fmt='%d %b %Y %H:%M'):
    """Parse stored UTC string and display as WIB (UTC+7)."""
    if not s: return ''
    try:
        # Parse as naive UTC then convert to WIB
        dt_utc = datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        dt_wib = dt_utc.astimezone(WIB)
        return dt_wib.strftime(fmt)
    except:
        try: return datetime.strptime(s[:10], '%Y-%m-%d').strftime('%d %b %Y')
        except: return s

@app.template_filter('fmt_price')
def fmt_price(v):
    try: return f"{int(v):,}".replace(',','.')
    except: return str(v)

# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = query_db('SELECT * FROM users WHERE username=?',[request.form['username']],one=True)
        if u and check_pw(request.form['password'], u['password']):
            session.update({'user_id':u['id'],'role':u['role'],'name':u['name']})
            flash(f'Selamat datang, {u["name"]}! 🌿','success')
            return redirect(url_for('dashboard'))
        flash('Username atau password salah.','danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if query_db('SELECT id FROM users WHERE username=?',[request.form['username']],one=True):
            flash('Username sudah digunakan.','danger')
            return render_template('auth/register.html')
        w = request.form.get('weight', 0, type=float)
        h = request.form.get('height', 0, type=float)
        a = request.form.get('age', 16, type=int)
        g = request.form.get('gender', 'L')
        query_db('INSERT INTO users (name,username,password,role,kelas,tenant_name,weight,height,age,gender) VALUES (?,?,?,?,?,?,?,?,?,?)',
            [request.form['name'],request.form['username'],hash_pw(request.form['password']),
             request.form['role'],request.form.get('kelas',''),request.form.get('tenant_name',''),
             w, h, a, g],commit=True)
        flash('Registrasi berhasil! Silakan login.','success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear(); flash('Berhasil logout.','info')
    return redirect(url_for('index'))

# ── DASHBOARD ────────────────────────────────────────────────────────────────

def get_user_quests(user):
    w = user.get('weight') or 0
    h = user.get('height') or 0
    a = user.get('age') or 16
    g = user.get('gender') or 'L'
    
    t_cal, t_pro, t_carb, t_fat, t_fiber = 600, 20, 80, 10, 8
    bmi_status, bmi_val = '-', 0
    
    if w > 0 and h > 0:
        hm = h / 100.0
        bmi_val = w / (hm * hm)
        if bmi_val < 18.5: bmi_status = 'Kurus'
        elif bmi_val < 25: bmi_status = 'Normal'
        elif bmi_val < 30: bmi_status = 'Gemuk'
        else: bmi_status = 'Obesitas'
        
        bmr = (10 * w) + (6.25 * h) - (5 * a)
        bmr += 5 if g.upper() == 'L' else -161
        
        tdee = bmr * 1.375 # active teen assumption
        t_cal = round(tdee / 3)
        t_pro = round((tdee * 0.15) / 4 / 3)
        t_carb = round((tdee * 0.55) / 4 / 3)
        t_fat = round((tdee * 0.30) / 9 / 3)
        t_fiber = round((tdee / 1000) * 14 / 3)

    return {
        'cal': t_cal, 'pro': t_pro, 'carb': t_carb, 'fat': t_fat, 'fiber': t_fiber,
        'bmi': round(bmi_val, 1) if bmi_val > 0 else 0, 'status': bmi_status
    }

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    w = request.form.get('weight', 0, type=float)
    h = request.form.get('height', 0, type=float)
    a = request.form.get('age', 16, type=int)
    g = request.form.get('gender', 'L')
    query_db('UPDATE users SET weight=?, height=?, age=?, gender=? WHERE id=?', (w, h, a, g, session['user_id']), commit=True)
    flash('Profil Gizi berhasil diperbarui! Target harianmu telah disesuaikan.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    role = session['role']
    user = query_db('SELECT * FROM users WHERE id=?',[session['user_id']],one=True)

    if role == 'student':
        points = get_points(user['id'])
        recent_orders = query_db('''SELECT o.*,u.tenant_name as tname FROM orders o
            JOIN users u ON o.tenant_id=u.id WHERE o.student_id=? ORDER BY o.created_at DESC LIMIT 3''',[user['id']])
        recent_waste  = query_db('SELECT * FROM waste_logs WHERE student_id=? ORDER BY created_at DESC LIMIT 5',[user['id']])
        menus = query_db('SELECT m.*,u.tenant_name FROM menus m JOIN users u ON m.tenant_id=u.id WHERE m.is_available=1 AND m.is_healthy=1 LIMIT 6')

        # BMI & Nutritional Quests
        quests = get_user_quests(user)

        return render_template('student/dashboard.html',user=user,points=points,
                               recent_orders=recent_orders,recent_waste=recent_waste,menus=menus,quests=quests)

    elif role == 'tenant':
        mc  = query_db('SELECT COUNT(*) as c FROM menus WHERE tenant_id=?',[user['id']],one=True)['c']
        pc  = query_db("SELECT COUNT(*) as c FROM orders WHERE tenant_id=? AND status='pending'",[user['id']],one=True)['c']
        today_orders  = query_db("SELECT * FROM orders WHERE tenant_id=? AND date(datetime(created_at,'+7 hours'))=?",[user['id'], today_wib()])
        today_revenue = sum(o['total_price'] for o in today_orders)
        recent_orders = query_db('''SELECT o.*,u.name as student_name,u.kelas FROM orders o
            JOIN users u ON o.student_id=u.id WHERE o.tenant_id=? ORDER BY o.created_at DESC LIMIT 5''',[user['id']])
        return render_template('tenant/dashboard.html',user=user,menus_count=mc,
                               pending_orders=pc,today_revenue=today_revenue,recent_orders=recent_orders)

    elif role == 'admin':
        ts = query_db("SELECT COUNT(*) as c FROM users WHERE role='student'",one=True)['c']
        to = query_db("SELECT COUNT(*) as c FROM orders",one=True)['c']
        tw = query_db("SELECT COUNT(*) as c FROM waste_logs",one=True)['c']
        tm = query_db("SELECT COUNT(*) as c FROM marketplace_items",one=True)['c']
        tv = query_db("SELECT COUNT(*) as c FROM edu_videos WHERE is_published=1",one=True)['c']
        waste_stats = query_db("SELECT waste_level,COUNT(*) as cnt FROM waste_logs GROUP BY waste_level")
        waste_data  = {w['waste_level']:w['cnt'] for w in waste_stats}
        top_menus   = query_db('''SELECT m.name,m.image_emoji,SUM(oi.quantity) as total FROM menus m
            JOIN order_items oi ON m.id=oi.menu_id GROUP BY m.id, m.name, m.image_emoji ORDER BY total DESC LIMIT 5''')
        return render_template('admin/dashboard.html',user=user,total_students=ts,total_orders=to,
                               total_waste_logs=tw,total_marketplace=tm,total_videos=tv,
                               waste_data=json.dumps(waste_data),top_menus=top_menus)
    return redirect(url_for('login'))

# ── STUDENT ───────────────────────────────────────────────────────────────────

@app.route('/menu')
def menu_catalog():
    if 'user_id' not in session: return redirect(url_for('login'))
    cat     = request.args.get('category','all')
    search  = request.args.get('search','')
    healthy = request.args.get('healthy','')
    sql  = 'SELECT m.*,u.name as tname,u.tenant_name FROM menus m JOIN users u ON m.tenant_id=u.id WHERE m.is_available=1'
    args = []
    if cat != 'all': sql += ' AND m.category=?'; args.append(cat)
    if search:       sql += ' AND m.name LIKE ?'; args.append(f'%{search}%')
    if healthy:      sql += ' AND m.is_healthy=1'
    menus = query_db(sql, args)
    return render_template('student/menu_catalog.html',menus=menus,category=cat,search=search,healthy_only=healthy)

@app.route('/order', methods=['GET','POST'])
def order():
    if 'user_id' not in session or session['role'] != 'student': return redirect(url_for('login'))
    if request.method == 'POST':
        cart  = json.loads(request.form.get('cart','[]'))
        notes = request.form.get('notes','')
        if not cart: flash('Keranjang kosong!','warning'); return redirect(url_for('menu_catalog'))
        tenant_orders = {}
        for item in cart:
            menu = query_db('SELECT * FROM menus WHERE id=?',[item['menu_id']],one=True)
            if menu:
                tid = menu['tenant_id']
                if tid not in tenant_orders: tenant_orders[tid] = []
                tenant_orders[tid].append({'menu':menu,'qty':item['qty']})
        for tid,items in tenant_orders.items():
            total = sum(i['menu']['price']*i['qty'] for i in items)
            oid   = query_db('INSERT INTO orders (student_id,tenant_id,total_price,notes) VALUES (?,?,?,?)',
                             [session['user_id'],tid,total,notes],commit=True)
            for i in items:
                query_db('INSERT INTO order_items (order_id,menu_id,quantity,subtotal) VALUES (?,?,?,?)',
                         [oid,i['menu']['id'],i['qty'],i['menu']['price']*i['qty']],commit=True)
        flash('Pesanan berhasil dikirim! 🎉','success')
        return redirect(url_for('my_orders'))
    # Group menus by tenant for display
    tenants = query_db("SELECT * FROM users WHERE role='tenant' ORDER BY tenant_name")
    menus_by_tenant = []  # list of (tenant_dict, menus_list)
    for t in tenants:
        ms = query_db('SELECT * FROM menus WHERE tenant_id=? AND is_available=1',[t['id']])
        if ms: menus_by_tenant.append((dict(t), list(ms)))
        
    # Get Quests
    user = query_db('SELECT * FROM users WHERE id=?',[session['user_id']],one=True)
    quests = get_user_quests(user)
    
    return render_template('student/order.html', menus_by_tenant=menus_by_tenant, quests=quests, user=user)

@app.route('/my-orders')
def my_orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    orders = query_db('''SELECT o.*,u.tenant_name as tname FROM orders o
        JOIN users u ON o.tenant_id=u.id WHERE o.student_id=? ORDER BY o.created_at DESC''',[session['user_id']])
    oim = {}
    for o in orders:
        oim[o['id']] = query_db('''SELECT oi.*,m.name as mname,m.image_emoji,m.image_file FROM order_items oi
            JOIN menus m ON oi.menu_id=m.id WHERE oi.order_id=?''',[o['id']])
    return render_template('student/my_orders.html',orders=orders,order_items_map=oim)

@app.route('/waste-log', methods=['GET','POST'])
def waste_log():
    if 'user_id' not in session or session['role'] != 'student': return redirect(url_for('login'))
    if request.method == 'POST':
        lvl = request.form['waste_level']
        pts = waste_pts(lvl)
        query_db('INSERT INTO waste_logs (student_id,menu_id,waste_level,waste_reason,points_earned) VALUES (?,?,?,?,?)',
                 [session['user_id'],request.form.get('menu_id') or None,lvl,request.form.get('waste_reason',''),pts],commit=True)
        flash(f'Log dicatat! +{pts} poin 🌱','success')
        return redirect(url_for('waste_log'))
    logs  = query_db('''SELECT wl.*,m.name as mname FROM waste_logs wl
        LEFT JOIN menus m ON wl.menu_id=m.id WHERE wl.student_id=? ORDER BY wl.created_at DESC''',[session['user_id']])
    menus = query_db('SELECT * FROM menus')
    return render_template('student/waste_log.html',logs=logs,menus=menus,total_points=get_points(session['user_id']))

@app.route('/education')
def education():
    if 'user_id' not in session: return redirect(url_for('login'))
    cat   = request.args.get('category','all')
    posts = query_db('SELECT * FROM education_posts WHERE category=? ORDER BY created_at DESC',[cat]) \
            if cat != 'all' else query_db('SELECT * FROM education_posts ORDER BY created_at DESC')
    return render_template('student/education.html',posts=posts,category=cat)

@app.route('/education/<int:post_id>')
def education_detail(post_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    post = query_db('SELECT * FROM education_posts WHERE id=?',[post_id],one=True)
    if not post: flash('Artikel tidak ditemukan.','danger'); return redirect(url_for('education'))
    related = query_db('SELECT * FROM education_posts WHERE category=? AND id!=? LIMIT 3',[post['category'],post_id])
    return render_template('student/education_detail.html',post=post,related=related)

@app.route('/marketplace')
def marketplace():
    cat   = request.args.get('category','all')
    items = query_db('SELECT * FROM marketplace_items WHERE category=? AND is_available=1',[cat]) \
            if cat != 'all' else query_db('SELECT * FROM marketplace_items WHERE is_available=1')
    return render_template('student/marketplace.html',items=items,category=cat)

# ── TENANT ────────────────────────────────────────────────────────────────────

@app.route('/tenant/menus')
def tenant_menus():
    if 'user_id' not in session or session['role'] != 'tenant': return redirect(url_for('login'))
    menus = query_db('SELECT * FROM menus WHERE tenant_id=? ORDER BY created_at DESC',[session['user_id']])
    return render_template('tenant/menus.html',menus=menus)

def _save_menu(f, existing_file=None):
    """Handle menu image upload; return filename to store."""
    file_obj = request.files.get('image_file')
    if file_obj and file_obj.filename:
        new_file = save_upload(file_obj, 'menus')
        if new_file:
            if existing_file: delete_upload('menus', existing_file)
            return new_file
    return existing_file  # keep existing

@app.route('/tenant/menu/add', methods=['GET','POST'])
def tenant_add_menu():
    if 'user_id' not in session or session['role'] != 'tenant': return redirect(url_for('login'))
    if request.method == 'POST':
        f        = request.form
        img_file = save_upload(request.files.get('image_file'), 'menus')
        query_db('''INSERT INTO menus (tenant_id,name,description,price,category,calories,protein,
                    carbs,fat,fiber,is_healthy,image_emoji,image_file) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                 [session['user_id'],f['name'],f.get('description',''),float(f['price']),f['category'],
                  float(f.get('calories',0)),float(f.get('protein',0)),float(f.get('carbs',0)),
                  float(f.get('fat',0)),float(f.get('fiber',0)),1 if f.get('is_healthy') else 0,
                  f.get('image_emoji','🍱'), img_file], commit=True)
        flash('Menu berhasil ditambahkan! ✅','success')
        return redirect(url_for('tenant_menus'))
    return render_template('tenant/menu_form.html',menu=None)

@app.route('/tenant/menu/edit/<int:menu_id>', methods=['GET','POST'])
def tenant_edit_menu(menu_id):
    if 'user_id' not in session or session['role'] != 'tenant': return redirect(url_for('login'))
    menu = query_db('SELECT * FROM menus WHERE id=? AND tenant_id=?',[menu_id,session['user_id']],one=True)
    if not menu: flash('Menu tidak ditemukan.','danger'); return redirect(url_for('tenant_menus'))
    if request.method == 'POST':
        f        = request.form
        img_file = _save_menu(f, menu['image_file'])
        query_db('''UPDATE menus SET name=?,description=?,price=?,category=?,calories=?,protein=?,
                    carbs=?,fat=?,fiber=?,is_healthy=?,image_emoji=?,image_file=?,is_available=? WHERE id=?''',
                 [f['name'],f.get('description',''),float(f['price']),f['category'],
                  float(f.get('calories',0)),float(f.get('protein',0)),float(f.get('carbs',0)),
                  float(f.get('fat',0)),float(f.get('fiber',0)),1 if f.get('is_healthy') else 0,
                  f.get('image_emoji','🍱'),img_file,1 if f.get('is_available') else 0, menu_id], commit=True)
        flash('Menu diperbarui! ✅','success')
        return redirect(url_for('tenant_menus'))
    return render_template('tenant/menu_form.html',menu=menu)

@app.route('/tenant/menu/delete/<int:menu_id>', methods=['POST'])
def tenant_delete_menu(menu_id):
    if 'user_id' not in session or session['role'] != 'tenant': return redirect(url_for('login'))
    menu = query_db('SELECT * FROM menus WHERE id=? AND tenant_id=?',[menu_id,session['user_id']],one=True)
    if menu:
        delete_upload('menus', menu['image_file'])
        query_db('DELETE FROM menus WHERE id=?',[menu_id],commit=True)
    flash('Menu dihapus.','info'); return redirect(url_for('tenant_menus'))

@app.route('/tenant/orders')
def tenant_orders():
    if 'user_id' not in session or session['role'] != 'tenant': return redirect(url_for('login'))
    sf = request.args.get('status','all')
    base_sql = '''SELECT o.*,u.name as student_name,u.kelas FROM orders o
        JOIN users u ON o.student_id=u.id WHERE o.tenant_id=?'''
    orders = query_db(base_sql+' AND o.status=? ORDER BY o.created_at DESC',[session['user_id'],sf]) \
             if sf != 'all' else query_db(base_sql+' ORDER BY o.created_at DESC',[session['user_id']])
    oim = {o['id']: query_db('SELECT oi.*,m.name as mname,m.image_emoji,m.image_file FROM order_items oi JOIN menus m ON oi.menu_id=m.id WHERE oi.order_id=?',[o['id']]) for o in orders}
    top_menus = query_db('''SELECT m.name,m.image_emoji,SUM(oi.quantity) as total FROM menus m
        JOIN order_items oi ON m.id=oi.menu_id WHERE m.tenant_id=? GROUP BY m.id, m.name, m.image_emoji ORDER BY total DESC LIMIT 5''',[session['user_id']])
    return render_template('tenant/orders.html',orders=orders,status_filter=sf,top_menus=top_menus,order_items_map=oim)

@app.route('/tenant/order/update/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session or session['role'] != 'tenant': return redirect(url_for('login'))
    query_db('UPDATE orders SET status=? WHERE id=? AND tenant_id=?',
             [request.form['status'],order_id,session['user_id']],commit=True)
    return redirect(url_for('tenant_orders'))

# ── ADMIN – full management of everything ────────────────────────────────────

@app.route('/admin/analytics')
def admin_analytics():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    waste_stats  = query_db("SELECT waste_level,COUNT(*) as cnt FROM waste_logs GROUP BY waste_level")
    waste_data   = {w['waste_level']:w['cnt'] for w in waste_stats}
    order_trend  = []
    wib_today = now_wib().date()
    for i in range(6,-1,-1):
        d     = (wib_today - timedelta(days=i)).strftime('%Y-%m-%d')
        count = query_db("SELECT COUNT(*) as c FROM orders WHERE date(datetime(created_at,'+7 hours'))=?",[d],one=True)['c']
        order_trend.append({'date':(wib_today - timedelta(days=i)).strftime('%d/%m'),'count':count})
    top_menus = query_db('''SELECT m.name,m.image_emoji,SUM(oi.quantity) as total FROM menus m
        JOIN order_items oi ON m.id=oi.menu_id GROUP BY m.id, m.name, m.image_emoji ORDER BY total DESC LIMIT 8''')
    hc = query_db("SELECT COUNT(*) as c FROM menus WHERE is_healthy=1 AND is_available=1",one=True)['c']
    uc = query_db("SELECT COUNT(*) as c FROM menus WHERE is_healthy=0 AND is_available=1",one=True)['c']
    tenants = query_db("SELECT * FROM users WHERE role='tenant'")
    tenant_stats = []
    for t in tenants:
        oc  = query_db('SELECT COUNT(*) as c FROM orders WHERE tenant_id=?',[t['id']],one=True)['c']
        rev = query_db('SELECT SUM(total_price) as s FROM orders WHERE tenant_id=?',[t['id']],one=True)['s'] or 0
        tenant_stats.append({'name':t['tenant_name'] or t['name'],'orders':oc,'revenue':rev})
    max_rev = max((t['revenue'] for t in tenant_stats),default=1) or 1
    return render_template('admin/analytics.html',waste_data=json.dumps(waste_data),
                           order_trend=json.dumps(order_trend),top_menus=top_menus,
                           healthy_count=hc,unhealthy_count=uc,tenant_stats=tenant_stats,
                           max_rev=max_rev,waste_counts=waste_data)

@app.route('/admin/leaderboard')
def admin_leaderboard():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    sort_by = request.args.get('sort', 'points') # 'points' or 'kelas'
    
    order_clause = 'ORDER BY total_points DESC'
    if sort_by == 'kelas':
        order_clause = 'ORDER BY u.kelas ASC, total_points DESC'
    
    sql = f'''
        SELECT u.id, u.name, u.kelas, COALESCE(SUM(wl.points_earned), 0) as total_points
        FROM users u
        LEFT JOIN waste_logs wl ON u.id = wl.student_id
        WHERE u.role = 'student'
        GROUP BY u.id, u.name, u.kelas
        {order_clause}
    '''
    rankings = query_db(sql)
    return render_template('admin/leaderboard.html', rankings=rankings, sort_by=sort_by)


# admin – manage all menus (across all tenants)
@app.route('/admin/menus')
def admin_menus():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    t_id = request.args.get('tenant')
    sql = 'SELECT m.*,u.tenant_name,u.name as tname FROM menus m JOIN users u ON m.tenant_id=u.id'
    args = []
    if t_id:
        sql += ' WHERE m.tenant_id = ?'
        args.append(t_id)
    sql += ' ORDER BY u.tenant_name, m.name'
    
    menus   = query_db(sql, args)
    tenants = query_db("SELECT * FROM users WHERE role='tenant' ORDER BY tenant_name")
    return render_template('admin/menus.html', menus=menus, tenants=tenants, selected_tenant=t_id)

@app.route('/admin/menu/add', methods=['GET','POST'])
def admin_add_menu():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    tenants = query_db("SELECT * FROM users WHERE role='tenant' ORDER BY tenant_name")
    if request.method == 'POST':
        f        = request.form
        img_file = save_upload(request.files.get('image_file'), 'menus')
        query_db('''INSERT INTO menus (tenant_id,name,description,price,category,calories,protein,
                    carbs,fat,fiber,is_healthy,image_emoji,image_file,is_available) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                 [int(f['tenant_id']),f['name'],f.get('description',''),float(f['price']),f['category'],
                  float(f.get('calories',0)),float(f.get('protein',0)),float(f.get('carbs',0)),
                  float(f.get('fat',0)),float(f.get('fiber',0)),1 if f.get('is_healthy') else 0,
                  f.get('image_emoji','🍱'),img_file,1 if f.get('is_available','on') else 0],commit=True)
        flash('Menu ditambahkan! ✅','success'); return redirect(url_for('admin_menus'))
    return render_template('admin/menu_form.html', menu=None, tenants=tenants)

@app.route('/admin/menu/edit/<int:menu_id>', methods=['GET','POST'])
def admin_edit_menu(menu_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    menu    = query_db('SELECT * FROM menus WHERE id=?',[menu_id],one=True)
    tenants = query_db("SELECT * FROM users WHERE role='tenant' ORDER BY tenant_name")
    if not menu: return redirect(url_for('admin_menus'))
    if request.method == 'POST':
        f        = request.form
        img_file = _save_menu(f, menu['image_file'])
        query_db('''UPDATE menus SET tenant_id=?,name=?,description=?,price=?,category=?,calories=?,protein=?,
                    carbs=?,fat=?,fiber=?,is_healthy=?,image_emoji=?,image_file=?,is_available=? WHERE id=?''',
                 [int(f['tenant_id']),f['name'],f.get('description',''),float(f['price']),f['category'],
                  float(f.get('calories',0)),float(f.get('protein',0)),float(f.get('carbs',0)),
                  float(f.get('fat',0)),float(f.get('fiber',0)),1 if f.get('is_healthy') else 0,
                  f.get('image_emoji','🍱'),img_file,1 if f.get('is_available') else 0, menu_id],commit=True)
        flash('Menu diperbarui! ✅','success'); return redirect(url_for('admin_menus'))
    return render_template('admin/menu_form.html', menu=menu, tenants=tenants)

@app.route('/admin/menu/delete/<int:menu_id>', methods=['POST'])
def admin_delete_menu(menu_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    menu = query_db('SELECT * FROM menus WHERE id=?',[menu_id],one=True)
    if menu: delete_upload('menus', menu['image_file']); query_db('DELETE FROM menus WHERE id=?',[menu_id],commit=True)
    flash('Menu dihapus.','info'); return redirect(url_for('admin_menus'))

# admin – manage users
@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    users = query_db('SELECT * FROM users ORDER BY role,name')
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/edit/<int:user_id>', methods=['GET','POST'])
def admin_edit_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    user = query_db('SELECT * FROM users WHERE id=?',[user_id],one=True)
    if not user: return redirect(url_for('admin_users'))
    if request.method == 'POST':
        f   = request.form
        new_pw = hash_pw(f['password']) if f.get('password') else user['password']
        query_db('UPDATE users SET name=?,username=?,password=?,role=?,kelas=?,tenant_name=? WHERE id=?',
                 [f['name'],f['username'],new_pw,f['role'],f.get('kelas',''),f.get('tenant_name',''),user_id],commit=True)
        flash('User diperbarui! ✅','success'); return redirect(url_for('admin_users'))
    return render_template('admin/user_form.html', user=user)

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    if user_id == session['user_id']: flash('Tidak bisa hapus akun sendiri.','danger'); return redirect(url_for('admin_users'))
    query_db('DELETE FROM users WHERE id=?',[user_id],commit=True)
    flash('User dihapus.','info'); return redirect(url_for('admin_users'))

# admin – marketplace
@app.route('/admin/marketplace')
def admin_marketplace():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    items = query_db('SELECT * FROM marketplace_items ORDER BY created_at DESC')
    return render_template('admin/marketplace.html', items=items)

@app.route('/admin/marketplace/add', methods=['GET','POST'])
def admin_add_marketplace():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    if request.method == 'POST':
        f        = request.form
        img_file = save_upload(request.files.get('image_file'), 'marketplace')
        query_db('INSERT INTO marketplace_items (name,description,category,price,unit,stock,image_emoji,image_file,seller_id) VALUES (?,?,?,?,?,?,?,?,?)',
                 [f['name'],f.get('description',''),f['category'],float(f['price']),
                  f.get('unit','pcs'),int(f.get('stock',0)),f.get('image_emoji','♻️'),img_file,session['user_id']],commit=True)
        flash('Produk ditambahkan! ♻️','success'); return redirect(url_for('admin_marketplace'))
    return render_template('admin/marketplace_form.html', item=None)

@app.route('/admin/marketplace/edit/<int:item_id>', methods=['GET','POST'])
def admin_edit_marketplace(item_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    item = query_db('SELECT * FROM marketplace_items WHERE id=?',[item_id],one=True)
    if not item: return redirect(url_for('admin_marketplace'))
    if request.method == 'POST':
        f = request.form
        new_img = save_upload(request.files.get('image_file'), 'marketplace')
        if new_img:
            delete_upload('marketplace', item['image_file'])
            img_file = new_img
        else:
            img_file = item['image_file']
        query_db('UPDATE marketplace_items SET name=?,description=?,category=?,price=?,unit=?,stock=?,image_emoji=?,image_file=?,is_available=? WHERE id=?',
                 [f['name'],f.get('description',''),f['category'],float(f['price']),
                  f.get('unit','pcs'),int(f.get('stock',0)),f.get('image_emoji','♻️'),
                  img_file, 1 if f.get('is_available') else 0, item_id],commit=True)
        flash('Produk diperbarui! ✅','success'); return redirect(url_for('admin_marketplace'))
    return render_template('admin/marketplace_form.html', item=item)

@app.route('/admin/marketplace/delete/<int:item_id>', methods=['POST'])
def admin_delete_marketplace(item_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    item = query_db('SELECT * FROM marketplace_items WHERE id=?',[item_id],one=True)
    if item: delete_upload('marketplace', item['image_file']); query_db('DELETE FROM marketplace_items WHERE id=?',[item_id],commit=True)
    flash('Produk dihapus.','info'); return redirect(url_for('admin_marketplace'))

# admin – education articles
@app.route('/admin/education', methods=['GET','POST'])
def admin_education():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    if request.method == 'POST':
        f = request.form
        query_db('INSERT INTO education_posts (title,content,category,image_emoji,author_id) VALUES (?,?,?,?,?)',
                 [f['title'],f['content'],f['category'],f.get('image_emoji','📚'),session['user_id']],commit=True)
        flash('Artikel dipublikasikan! 📖','success'); return redirect(url_for('admin_education'))
    posts = query_db('SELECT * FROM education_posts ORDER BY created_at DESC')
    return render_template('admin/education.html', posts=posts)

@app.route('/admin/education/edit/<int:post_id>', methods=['GET','POST'])
def admin_edit_education(post_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    post = query_db('SELECT * FROM education_posts WHERE id=?',[post_id],one=True)
    if not post: flash('Artikel tidak ditemukan.','danger'); return redirect(url_for('admin_education'))
    if request.method == 'POST':
        f = request.form
        query_db('UPDATE education_posts SET title=?,content=?,category=?,image_emoji=? WHERE id=?',
                 [f['title'],f['content'],f['category'],f.get('image_emoji','📚'),post_id],commit=True)
        flash('Artikel berhasil diperbarui! ✅','success'); return redirect(url_for('admin_education'))
    return render_template('admin/education_form.html', post=post)

@app.route('/admin/education/delete/<int:post_id>', methods=['POST'])
def admin_delete_education(post_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    query_db('DELETE FROM education_posts WHERE id=?',[post_id],commit=True)
    flash('Artikel dihapus.','info'); return redirect(url_for('admin_education'))


# admin – orders (view all orders)
@app.route('/admin/orders')
def admin_orders():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    sf = request.args.get('status','all')
    tenant_id = request.args.get('tenant','all')
    sql = '''SELECT o.*,s.name as student_name,s.kelas,t.tenant_name,t.name as tname
             FROM orders o JOIN users s ON o.student_id=s.id JOIN users t ON o.tenant_id=t.id WHERE 1=1'''
    args = []
    if sf != 'all': sql += ' AND o.status=?'; args.append(sf)
    if tenant_id != 'all': sql += ' AND o.tenant_id=?'; args.append(tenant_id)
    sql += ' ORDER BY o.created_at DESC LIMIT 100'
    orders  = query_db(sql, args)
    tenants = query_db("SELECT * FROM users WHERE role='tenant' ORDER BY tenant_name")
    oim     = {o['id']: query_db('SELECT oi.*,m.name as mname FROM order_items oi JOIN menus m ON oi.menu_id=m.id WHERE oi.order_id=?',[o['id']]) for o in orders}
    return render_template('admin/orders.html', orders=orders, tenants=tenants, order_items_map=oim, status_filter=sf, tenant_filter=tenant_id)

@app.route('/admin/order/update/<int:order_id>', methods=['POST'])
def admin_update_order(order_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    query_db('UPDATE orders SET status=? WHERE id=?',[request.form['status'],order_id],commit=True)
    flash('Status pesanan diperbarui.','success'); return redirect(url_for('admin_orders'))

# ── PUBLIC: Sustainable Education Hub ────────────────────────────────────────

@app.route('/hub')
def edu_hub():
    cat    = request.args.get('category','all')
    search = request.args.get('search','')
    sql    = "SELECT ev.*,u.name as uploader_name FROM edu_videos ev LEFT JOIN users u ON ev.uploader_id=u.id WHERE ev.is_published=1"
    args   = []
    if cat != 'all':   sql += ' AND ev.category=?'; args.append(cat)
    if search:         sql += ' AND (ev.title LIKE ? OR ev.description LIKE ?)'; args += [f'%{search}%',f'%{search}%']
    sql   += ' ORDER BY ev.created_at DESC'
    videos = query_db(sql, args)
    return render_template('public/edu_hub.html', videos=videos, category=cat, search=search)

@app.route('/hub/<int:video_id>')
def edu_hub_detail(video_id):
    video   = query_db("SELECT ev.*,u.name as uploader_name FROM edu_videos ev LEFT JOIN users u ON ev.uploader_id=u.id WHERE ev.id=? AND ev.is_published=1",[video_id],one=True)
    if not video: flash('Video tidak ditemukan.','danger'); return redirect(url_for('edu_hub'))
    related = query_db("SELECT * FROM edu_videos WHERE category=? AND id!=? AND is_published=1 LIMIT 4",[video['category'],video_id])
    return render_template('public/edu_hub_detail.html', video=video, related=related)

# ── ADMIN: videos ─────────────────────────────────────────────────────────────

@app.route('/admin/videos')
def admin_videos():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    videos = query_db("SELECT ev.*,u.name as uploader_name FROM edu_videos ev LEFT JOIN users u ON ev.uploader_id=u.id ORDER BY ev.created_at DESC")
    return render_template('admin/videos.html', videos=videos)

@app.route('/admin/videos/add', methods=['GET','POST'])
def admin_add_video():
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    if request.method == 'POST':
        f   = request.form
        url = f['youtube_url'].strip()
        m   = re.search(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})', url)
        if not m:
            flash('URL YouTube tidak valid.','danger')
            return render_template('admin/video_form.html', video=None)
        embed = f'https://www.youtube.com/embed/{m.group(1)}'
        query_db('INSERT INTO edu_videos (title,youtube_url,description,category,uploader_id,is_published) VALUES (?,?,?,?,?,?)',
                 [f['title'],embed,f.get('description',''),f.get('category','umum'),session['user_id'],1 if f.get('is_published') else 0],commit=True)
        flash('Video ditambahkan! 🎬','success'); return redirect(url_for('admin_videos'))
    return render_template('admin/video_form.html', video=None)

@app.route('/admin/videos/edit/<int:video_id>', methods=['GET','POST'])
def admin_edit_video(video_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    video = query_db('SELECT * FROM edu_videos WHERE id=?',[video_id],one=True)
    if not video: return redirect(url_for('admin_videos'))
    if request.method == 'POST':
        f   = request.form
        url = f['youtube_url'].strip()
        m   = re.search(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})', url)
        embed = f'https://www.youtube.com/embed/{m.group(1)}' if m else url
        query_db('UPDATE edu_videos SET title=?,youtube_url=?,description=?,category=?,is_published=? WHERE id=?',
                 [f['title'],embed,f.get('description',''),f.get('category','umum'),1 if f.get('is_published') else 0,video_id],commit=True)
        flash('Video diperbarui! ✅','success'); return redirect(url_for('admin_videos'))
    return render_template('admin/video_form.html', video=video)

@app.route('/admin/videos/delete/<int:video_id>', methods=['POST'])
def admin_delete_video(video_id):
    if 'user_id' not in session or session['role'] != 'admin': return redirect(url_for('login'))
    query_db('DELETE FROM edu_videos WHERE id=?',[video_id],commit=True)
    flash('Video dihapus.','info'); return redirect(url_for('admin_videos'))

# ── Init DB & run ─────────────────────────────────────────────────────────────

with app.app_context():
    init_db()
    migrate_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


