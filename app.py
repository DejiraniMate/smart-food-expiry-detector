# ============================================================
# Smart Food Expiry Detector – Food Waste Reduction System
# app.py — Main Flask Application
# ============================================================
# Run this file with: python app.py
# Then open your browser at: http://127.0.0.1:5000
# ============================================================

from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, date, timedelta
import matplotlib
matplotlib.use('Agg')   # Use non-interactive backend (required for Flask)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import base64

# ── App Setup ─────────────────────────────────────────────
app = Flask(__name__)
DATABASE = 'food_expiry.db'


# ── Database Helpers ──────────────────────────────────────

def get_db_connection():
    """Open a connection to the SQLite database and return rows as dicts."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   # Allows column access by name
    return conn


def init_db():
    """
    Create the food_items table if it doesn't already exist.
    Called once when the app starts.
    """
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS food_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name     TEXT    NOT NULL,
            purchase_date DATE    NOT NULL,
            shelf_life    INTEGER NOT NULL,
            expiry_date   DATE    NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


# ── Status & Color Helpers ────────────────────────────────

def calculate_status(expiry_date_str):
    """
    Given an expiry date string (YYYY-MM-DD), return:
      - days_remaining  (int)
      - status          (str: 'Fresh' | 'Expiring Soon' | 'Expired')
      - row_class       (str: CSS class name for row colour)
      - badge_class     (str: CSS class name for status badge)
    """
    today = date.today()
    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
    days_remaining = (expiry_date - today).days

    if days_remaining < 0:
        status     = 'Expired'
        row_class  = 'row-expired'
        badge_class = 'badge-expired'
    elif days_remaining <= 2:
        status     = 'Expiring Soon'
        row_class  = 'row-expiring'
        badge_class = 'badge-expiring'
    else:
        status     = 'Fresh'
        row_class  = 'row-fresh'
        badge_class = 'badge-fresh'

    return days_remaining, status, row_class, badge_class


def enrich_items(rows):
    """
    Take raw DB rows and attach computed fields:
    days_remaining, status, row_class, badge_class.
    Returns a list of plain dicts ready for the template.
    """
    enriched = []
    for row in rows:
        item = dict(row)   # Convert sqlite3.Row → regular dict
        dr, status, row_class, badge_class = calculate_status(item['expiry_date'])
        item['days_remaining'] = dr
        item['status']         = status
        item['row_class']      = row_class
        item['badge_class']    = badge_class
        enriched.append(item)
    return enriched


# ── Chart Generation ──────────────────────────────────────

def generate_chart(fresh, expiring, expired):
    """
    Create a pie/donut chart showing food status distribution.
    Converts the matplotlib figure to a base64 PNG string so it
    can be embedded directly in HTML without saving a file.
    """
    labels = []
    sizes  = []
    colors = []

    # Only include non-zero segments to keep the chart clean
    if fresh > 0:
        labels.append(f'Fresh\n({fresh})')
        sizes.append(fresh)
        colors.append('#2ecc71')

    if expiring > 0:
        labels.append(f'Expiring Soon\n({expiring})')
        sizes.append(expiring)
        colors.append('#f39c12')

    if expired > 0:
        labels.append(f'Expired\n({expired})')
        sizes.append(expired)
        colors.append('#e74c3c')

    # If there is no data yet, show a placeholder chart
    if not sizes:
        labels  = ['No Items Yet']
        sizes   = [1]
        colors  = ['#bdc3c7']

    fig, ax = plt.subplots(figsize=(6, 5), facecolor='#0f1724')
    ax.set_facecolor('#0f1724')

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=140,
        pctdistance=0.75,
        wedgeprops=dict(width=0.55, edgecolor='#0f1724', linewidth=3)
    )

    for t in texts:
        t.set_color('#e0e6f0')
        t.set_fontsize(10)
        t.set_fontweight('bold')

    for at in autotexts:
        at.set_color('white')
        at.set_fontsize(9)
        at.set_fontweight('bold')

    ax.set_title('Food Status Distribution', color='#e0e6f0',
                 fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()

    # Convert figure → PNG bytes → base64 string
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight',
                facecolor='#0f1724')
    buffer.seek(0)
    chart_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)   # Free memory

    return chart_b64


# ── Routes ────────────────────────────────────────────────

@app.route('/')
def dashboard():
    """
    Main dashboard: lists all food items with live status,
    plus a summary report and the status-distribution chart.
    """
    conn  = get_db_connection()
    rows  = conn.execute(
        'SELECT * FROM food_items ORDER BY expiry_date ASC'
    ).fetchall()
    conn.close()

    items = enrich_items(rows)

    # ── Compute report stats ─────────────────────────────
    total    = len(items)
    fresh    = sum(1 for i in items if i['status'] == 'Fresh')
    expiring = sum(1 for i in items if i['status'] == 'Expiring Soon')
    expired  = sum(1 for i in items if i['status'] == 'Expired')

    waste_pct = round((expired / total) * 100, 1) if total > 0 else 0.0

    # ── Generate chart ───────────────────────────────────
    chart_b64 = generate_chart(fresh, expiring, expired)

    return render_template(
        'dashboard.html',
        items      = items,
        total      = total,
        fresh      = fresh,
        expiring   = expiring,
        expired    = expired,
        waste_pct  = waste_pct,
        chart_b64  = chart_b64,
        today      = date.today().isoformat()
    )


@app.route('/add', methods=['POST'])
def add_item():
    """
    Handle the Add Food form submission.
    - Reads food_name, purchase_date, shelf_life from the form
    - Calculates expiry_date = purchase_date + shelf_life days
    - Inserts the new record into the database
    - Redirects back to the dashboard
    """
    food_name     = request.form['food_name'].strip()
    purchase_date = request.form['purchase_date']       # e.g. "2025-06-01"
    shelf_life    = int(request.form['shelf_life'])

    # ── Expiry date calculation ──────────────────────────
    purchase_dt = datetime.strptime(purchase_date, '%Y-%m-%d').date()
    expiry_dt   = purchase_dt + timedelta(days=shelf_life)
    expiry_date = expiry_dt.isoformat()                 # e.g. "2025-06-08"

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO food_items (food_name, purchase_date, shelf_life, expiry_date) '
        'VALUES (?, ?, ?, ?)',
        (food_name, purchase_date, shelf_life, expiry_date)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    """
    Delete a single food item by its primary-key ID.
    Redirects back to the dashboard after deletion.
    """
    conn = get_db_connection()
    conn.execute('DELETE FROM food_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/report')
def report():
    """
    Standalone report page (same data as the dashboard report section,
    but rendered on its own page — useful for printing / sharing).
    """
    conn  = get_db_connection()
    rows  = conn.execute('SELECT * FROM food_items').fetchall()
    conn.close()

    items    = enrich_items(rows)
    total    = len(items)
    fresh    = sum(1 for i in items if i['status'] == 'Fresh')
    expiring = sum(1 for i in items if i['status'] == 'Expiring Soon')
    expired  = sum(1 for i in items if i['status'] == 'Expired')
    waste_pct = round((expired / total) * 100, 1) if total > 0 else 0.0
    chart_b64 = generate_chart(fresh, expiring, expired)

    return render_template(
        'report.html',
        total     = total,
        fresh     = fresh,
        expiring  = expiring,
        expired   = expired,
        waste_pct = waste_pct,
        chart_b64 = chart_b64
    )


# ── Entry Point ───────────────────────────────────────────

if __name__ == '__main__':
    init_db()           # Create table on first run
    app.run(debug=True) # Visit http://127.0.0.1:5000
