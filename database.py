import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('kontak_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            phone TEXT,
            register_date TEXT,
            trial_end_date TEXT,
            daily_query_count INTEGER,
            last_query_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def register_user(email, phone):
    conn = sqlite3.connect('kontak_users.db')
    c = conn.cursor()
    now = datetime.now()
    trial_end = now + timedelta(days=90)
    
    try:
        c.execute('''
            INSERT INTO users (email, phone, register_date, trial_end_date, daily_query_count, last_query_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, phone, now.strftime('%Y-%m-%d'), trial_end.strftime('%Y-%m-%d'), 0, now.strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()
        return True, "Kayıt Başarılı! KONTAK 3 Ay Ücretsiz Lansman Paketiniz Aktif Edildi."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Bu e-posta adresi zaten bir KONTAK hesabına bağlı!"

def check_and_update_quota(email):
    conn = sqlite3.connect('kontak_users.db')
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    c.execute('SELECT daily_query_count, last_query_date FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return False, "Kullanıcı bulunamadı."
        
    count, last_date = user
    if last_date != today:
        count = 0
        
    if count >= 5:
        conn.close()
        return False, "Günlük 5 ücretsiz KONTAK analiz hakkınızı kullandınız. Yarın tekrar bekleriz!"
        
    c.execute('UPDATE users SET daily_query_count = ?, last_query_date = ? WHERE email = ?', (count + 1, today, email))
    conn.commit()
    conn.close()
    return True, f"KONTAK Analiz Motoru Çalışıyor... (Kalan Hak: {4 - count}/5)"