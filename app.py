from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ------------------- DB INIT -------------------
def init_db():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            complaint TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            description TEXT NOT NULL,
            complete_address TEXT NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Safe migration: add date column if missing (for older DBs)
    cursor.execute("PRAGMA table_info(complaints)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'date' not in cols:
        cursor.execute("ALTER TABLE complaints ADD COLUMN date TEXT")
        conn.commit()

    conn.close()

init_db()

# ------------------- ROUTES -------------------

@app.route('/')
def user():
    return render_template('user.html')

@app.route('/complain', methods=['POST'])
def submit_complaint():
    name = request.form['name']
    email = request.form['email']
    complaint = request.form['complain']
    description = request.form['description']
    complete_address = request.form['complete_address']
    date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO complaints (name, email, complaint, description, complete_address, date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, email, complaint, description, complete_address, date))
    conn.commit()
    conn.close()

    return redirect(url_for('user', success=1))

# ✅ Only ONE my_complaints route
@app.route('/my_complaints')
def my_complaints():
    email = request.args.get('email', '').strip().lower()
    if not email:
        flash("Please enter your email to check complaint status.", "warning")
        return redirect(url_for('user'))

    conn = sqlite3.connect('complaints.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints WHERE LOWER(email) = ?", (email,))
    complaints = cur.fetchall()
    conn.close()

    return render_template('my_complaint.html', complaints=complaints, email=email)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'zaki' and password == 'zaki123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
    in_progress = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]
    conn.close()

    current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    return render_template(
        'admin_dashboard.html',
        total_complaints=total,
        pending_complaints=pending,
        in_progress_complaints=in_progress,
        resolved_complaints=resolved,
        current_time=current_time
    )

# ——— complaint_list route with search ———
@app.route('/complaint_list')
def complaint_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    search_query = request.args.get('search', '').strip().lower()

    conn = sqlite3.connect('complaints.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if search_query:
        wildcard = f"%{search_query}%"
        cur.execute(
            """
            SELECT * FROM complaints
            WHERE LOWER(name) LIKE ?
               OR LOWER(email) LIKE ?
               OR LOWER(complaint) LIKE ?
               OR LOWER(description) LIKE ?
               OR LOWER(complete_address) LIKE ?
            """,
            (wildcard,)*5
        )
    else:
        cur.execute("SELECT * FROM complaints")

    complaints = cur.fetchall()
    conn.close()

    return render_template(
        'complaint_list.html',
        complaints=complaints,
        search_query=search_query
    )

@app.route('/edit_complaint_list')
def edit_complaint_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('complaints.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints")
    complaints = cur.fetchall()
    conn.close()

    return render_template('edit_complaint_list.html', complaints=complaints)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    new_status = request.form['status']
    conn = sqlite3.connect('complaints.db')
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status = ? WHERE id = ?", (new_status, id))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_complaint_list'))

@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('complaints.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM complaints WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_complaint_list'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
