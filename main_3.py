from fastmcp import FastMCP
import os
import aiosqlite
import asyncio
import aiofiles
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
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
        # Add column if missing
        try:
            await db.execute("ALTER TABLE expenses ADD COLUMN paid_by TEXT DEFAULT ''")
        except aiosqlite.OperationalError:
            pass
        await db.commit()


# Initialize database at startup
asyncio.run(init_db())


@mcp.tool()
async def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = "", paid_by: str = ""):
    """Add a new expense entry to the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note, paid_by) VALUES (?,?,?,?,?,?)",
            (date, amount, category, subcategory, note, paid_by)
        )
        await db.commit()
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    """List expense entries within an inclusive date range."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT id, date, amount, category, subcategory, note, paid_by
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


@mcp.tool()
async def summarize(start_date: str, end_date: str, category: str = None):
    """Summarize expenses by category within an inclusive date range."""
    async with aiosqlite.connect(DB_PATH) as db:
        query = "SELECT category, SUM(amount) AS total_amount FROM expenses WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " GROUP BY category ORDER BY category ASC"
        cur = await db.execute(query, params)
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


@mcp.tool()
async def delete_expense(expense_id: int):
    """Delete an expense entry by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await db.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": "Expense not found"}
        return {"status": "ok", "deleted_id": expense_id}


@mcp.tool()
async def edit_expense(expense_id: int, date=None, amount=None, category=None, subcategory=None, note=None, paid_by=None):
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

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": "Expense not found"}
        return {"status": "ok", "updated_id": expense_id}


@mcp.resource("expense://categories", mime_type="application/json")
async def categories():
    """Return categories.json content asynchronously."""
    async with aiofiles.open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        content = await f.read()
    return content


if __name__ == "__main__":
    # Use asyncio-friendly run
    mcp.run(transport='http', host="0.0.0.0", port=8000)
