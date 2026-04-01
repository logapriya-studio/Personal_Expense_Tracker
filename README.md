# Money Manager — User Auth Module

## 📁 Project Structure
```
money_manager/
├── app.py                  # Flask backend
├── schema.sql              # MySQL database setup
├── requirements.txt        # Python dependencies
└── templates/
    ├── login.html          # Login page
    ├── register.html       # Registration page
    └── dashboard.html      # Dashboard (after login)
```

## 🚀 Setup Instructions

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up MySQL database
Open MySQL and run:
```bash
mysql -u root -p < schema.sql
```
Or manually paste the contents of `schema.sql` into MySQL Workbench.

### 3. Update DB credentials in app.py
Edit the `DB_CONFIG` section:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',       # ← your MySQL username
    'password': '',       # ← your MySQL password
    'database': 'money_manager'
}
```

### 4. Run the Flask app
```bash
python app.py
```

### 5. Open in browser
```
http://127.0.0.1:5000
```

## 🔐 Features
- User Registration with validation
- Secure password hashing (Werkzeug)
- Login with Remember Me
- Flash messages for errors/success
- Auto-login after registration
- Session management
- Last login tracking
