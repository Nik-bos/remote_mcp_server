from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        # Create table if it doesn't exist
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT '',
                paid_by TEXT DEFAULT ''
            )
        """)
        # For existing databases, add column if missing
        try:
            c.execute("ALTER TABLE expenses ADD COLUMN paid_by TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            # Column already exists
            pass


init_db()


@mcp.tool()
def add_expense(date, amount, category, subcategory="", note="", paid_by=""):
    '''Add a new expense entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, paid_by) VALUES (?,?,?,?,?,?)",
            (date, amount, category, subcategory, note, paid_by)
        )
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note, paid_by
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def delete_expense(expense_id: int):
    """Delete an expense entry by ID."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cur.rowcount == 0:
            return {"status": "error", "message": "Expense not found"}
        return {"status": "ok", "deleted_id": expense_id}


@mcp.tool()
def edit_expense(expense_id: int, date=None, amount=None, category=None, subcategory=None, note=None, paid_by=None):
    """Edit an expense entry by ID."""
    fields = []
    params = []

    if date is not None:
        fields.append("date = ?")
        params.append(date)
    if amount is not None:
        fields.append("amount = ?")
        params.append(amount)
    if category is not None:
        fields.append("category = ?")
        params.append(category)
    if subcategory is not None:
        fields.append("subcategory = ?")
        params.append(subcategory)
    if note is not None:
        fields.append("note = ?")
        params.append(note)
    if paid_by is not None:
        fields.append("paid_by = ?")
        params.append(paid_by)

    if not fields:
        return {"status": "error", "message": "No fields to update"}

    params.append(expense_id)
    query = f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?"

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, params)
        if cur.rowcount == 0:
            return {"status": "error", "message": "Expense not found"}
        return {"status": "ok", "updated_id": expense_id}


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run(transport = 'http', host = "0.0.0.0", port = 8000)
    