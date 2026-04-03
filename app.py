from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import re
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'money_manager_secret_key_2025'
app.permanent_session_lifetime = timedelta(days=7)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'money_manager.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now')),
            last_login    TEXT,
            is_active     INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            type        TEXT NOT NULL,
            category    TEXT NOT NULL,
            description TEXT NOT NULL,
            amount      REAL NOT NULL,
            date        TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    conn.commit()
    conn.close()

init_db()

def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── AUTH ROUTES ───────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')
        errors = []
        if not full_name: errors.append('Full name is required.')
        if not is_valid_email(email): errors.append('Enter a valid email.')
        if len(password) < 6: errors.append('Password must be at least 6 characters.')
        if password != confirm: errors.append('Passwords do not match.')
        if errors:
            for e in errors: flash(e, 'error')
            return render_template('register.html', full_name=full_name, email=email)
        conn = get_db()
        try:
            if conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
                flash('Email already exists. Please log in.', 'error')
                return render_template('register.html', full_name=full_name, email=email)
            cur = conn.execute('INSERT INTO users (full_name,email,password_hash) VALUES (?,?,?)',
                               (full_name, email, generate_password_hash(password)))
            conn.commit()
            session.permanent = True
            session['user_id']    = cur.lastrowid
            session['user_name']  = full_name
            session['user_email'] = email
            flash(f'Welcome, {full_name}! Account created successfully.', 'success')
            return redirect(url_for('dashboard'))
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember_me') == 'on'
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html', email=email)
        conn = get_db()
        try:
            user = conn.execute('SELECT * FROM users WHERE email=? AND is_active=1', (email,)).fetchone()
            if user and check_password_hash(user['password_hash'], password):
                conn.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user['id'],))
                conn.commit()
                session.permanent = remember
                session['user_id']    = user['id']
                session['user_name']  = user['full_name']
                session['user_email'] = user['email']
                flash(f'Welcome back, {user["full_name"]}!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid email or password.', 'error')
            return render_template('login.html', email=email)
        finally:
            conn.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    name = session.get('user_name', '')
    session.clear()
    flash(f'Goodbye, {name}! Logged out successfully.', 'info')
    return redirect(url_for('login'))

# ── DASHBOARD ─────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    uid  = session['user_id']
    rows = conn.execute(
        'SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC, id DESC LIMIT 10', (uid,)
    ).fetchall()
    totals = conn.execute(
        'SELECT type, SUM(amount) as total FROM transactions WHERE user_id=? GROUP BY type', (uid,)
    ).fetchall()
    conn.close()
    income = expenses = 0
    for t in totals:
        if t['type'] == 'income':  income   = t['total'] or 0
        if t['type'] == 'expense': expenses = t['total'] or 0
    return render_template('dashboard.html',
        user_name=session['user_name'],
        user_email=session['user_email'],
        transactions=rows,
        income='{:,.0f}'.format(income),
        expenses='{:,.0f}'.format(expenses),
        balance='{:,.0f}'.format(income - expenses)
    )

# ── ADD TRANSACTION ───────────────────────────────────────────

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        tx_type  = request.form.get('type', 'expense')
        category = request.form.get('category', '')
        desc     = request.form.get('description', '').strip()
        amount   = request.form.get('amount', '')
        date     = request.form.get('date', '')
        errors = []
        if not desc:    errors.append('Description is required.')
        if not amount or float(amount) <= 0: errors.append('Enter a valid amount.')
        if not date:    errors.append('Date is required.')
        if errors:
            for e in errors: flash(e, 'error')
            return render_template('add_transaction.html')
        conn = get_db()
        conn.execute(
            'INSERT INTO transactions (user_id,type,category,description,amount,date) VALUES (?,?,?,?,?,?)',
            (session['user_id'], tx_type, category, desc, float(amount), date)
        )
        conn.commit()
        conn.close()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_transaction.html')

# ── REPORTS ───────────────────────────────────────────────────

@app.route('/reports')
@login_required
def reports():
    conn = get_db()
    uid  = session['user_id']
    cat_data = conn.execute('''
        SELECT category, SUM(amount) as total FROM transactions
        WHERE user_id=? AND type='expense' GROUP BY category ORDER BY total DESC
    ''', (uid,)).fetchall()
    monthly_data = conn.execute('''
        SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
        FROM transactions WHERE user_id=? AND type='expense'
        GROUP BY month ORDER BY month DESC LIMIT 6
    ''', (uid,)).fetchall()
    totals = conn.execute(
        'SELECT type, SUM(amount) as total FROM transactions WHERE user_id=? GROUP BY type', (uid,)
    ).fetchall()
    conn.close()
    income = expenses = 0
    for t in totals:
        if t['type'] == 'income':  income   = t['total'] or 0
        if t['type'] == 'expense': expenses = t['total'] or 0
    return render_template('reports.html',
        user_name=session['user_name'],
        user_email=session['user_email'],
        cat_data=cat_data,
        monthly_data=list(reversed(monthly_data)),
        income=income, expenses=expenses,
        balance=income-expenses
    )

# ── BUDGET ────────────────────────────────────────────────────

@app.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    conn = get_db()
    uid  = session['user_id']
    # Ensure budget table exists
    conn.execute('''CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        monthly_limit REAL NOT NULL,
        UNIQUE(user_id, category),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    conn.commit()
    if request.method == 'POST':
        category = request.form.get('category', '')
        limit    = request.form.get('limit', '')
        if category and limit and float(limit) > 0:
            conn.execute('''INSERT INTO budgets (user_id,category,monthly_limit) VALUES (?,?,?)
                ON CONFLICT(user_id,category) DO UPDATE SET monthly_limit=excluded.monthly_limit''',
                (uid, category, float(limit)))
            conn.commit()
            flash(f'Budget for {category} set to ₹{limit}!', 'success')
    budgets = conn.execute('SELECT * FROM budgets WHERE user_id=?', (uid,)).fetchall()
    spent_data = conn.execute('''
        SELECT category, SUM(amount) as spent FROM transactions
        WHERE user_id=? AND type='expense'
        AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        GROUP BY category
    ''', (uid,)).fetchall()
    conn.close()
    spent_map = {r['category']: r['spent'] for r in spent_data}
    budget_info = []
    for b in budgets:
        spent = spent_map.get(b['category'], 0)
        pct   = round((spent / b['monthly_limit']) * 100) if b['monthly_limit'] > 0 else 0
        budget_info.append({
            'category': b['category'],
            'limit': b['monthly_limit'],
            'spent': spent,
            'pct': min(pct, 100),
            'status': 'danger' if pct >= 100 else 'warning' if pct >= 80 else 'safe'
        })
    return render_template('budget.html',
        user_name=session['user_name'],
        user_email=session['user_email'],
        budget_info=budget_info
    )

if __name__ == '__main__':
    app.run(debug=True)