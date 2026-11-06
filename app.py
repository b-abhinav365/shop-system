import os
import sqlite3
from functools import wraps
from flask import Flask, g, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer');
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL, stock INTEGER NOT NULL, category TEXT);
CREATE TABLE IF NOT EXISTS cart(user_id INTEGER, product_id INTEGER, qty INTEGER NOT NULL, PRIMARY KEY(user_id, product_id));
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, total REAL, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS order_items(order_id INTEGER, product_id INTEGER, name TEXT, price REAL, qty INTEGER);
"""

SAMPLE = [("Laptop", 55000, 100, "Electronics"), ("Headphones", 1500, 100, "Electronics"),
          ("Notebook", 50, 500, "Stationery"), ("Backpack", 1200, 100, "Accessories")]


def to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def create_app(db_path=None):
    app = Flask(__name__, static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["DB"] = db_path or os.environ.get("DB_PATH", "shop.db")

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close(_):
        d = g.pop("db", None)
        if d:
            d.close()

    with app.app_context():
        d = db()
        d.executescript(SCHEMA)
        if not d.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
            d.execute("INSERT INTO users(username,password,role) VALUES('admin',?,'admin')",
                      (generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123")),))
        if not d.execute("SELECT 1 FROM products").fetchone():
            d.executemany("INSERT INTO products(name,price,stock,category) VALUES(?,?,?,?)", SAMPLE)
        d.commit()

    def auth(admin=False):
        def deco(f):
            @wraps(f)
            def wrap(*a, **k):
                if "uid" not in session:
                    return jsonify(error="Login required"), 401
                if admin and session.get("role") != "admin":
                    return jsonify(error="Admin access required"), 403
                return f(*a, **k)
            return wrap
        return deco

    def body():
        return request.get_json(silent=True) or {}

    def product(pid):
        return db().execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()

    @app.get("/")
    def index():
        return send_from_directory("static", "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    # ---------- Customer registration / login ----------
    @app.post("/api/register")
    def register():
        d = body()
        u, p = (d.get("username") or "").strip(), d.get("password") or ""
        if not u or len(p) < 4:
            return jsonify(error="Username required and password must be 4+ characters"), 400
        try:
            db().execute("INSERT INTO users(username,password) VALUES(?,?)", (u, generate_password_hash(p)))
            db().commit()
        except sqlite3.IntegrityError:
            return jsonify(error="Username already exists"), 409
        return jsonify(message="Customer registered"), 201

    @app.post("/api/login")
    def login():
        d = body()
        row = db().execute("SELECT * FROM users WHERE username=?", (d.get("username"),)).fetchone()
        if row and check_password_hash(row["password"], d.get("password") or ""):
            session["uid"], session["role"] = row["id"], row["role"]
            return jsonify(message="Login successful", role=row["role"])
        return jsonify(error="Invalid credentials"), 401

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(message="Logged out")

    # ---------- Catalogue and search ----------
    @app.get("/api/products")
    def catalogue():
        return jsonify([dict(r) for r in db().execute("SELECT * FROM products ORDER BY id")])

    @app.get("/api/products/search")
    def search():
        q = "%" + request.args.get("q", "").strip() + "%"
        rows = [dict(r) for r in db().execute(
            "SELECT * FROM products WHERE name LIKE ? OR category LIKE ? ORDER BY id", (q, q))]
        return jsonify(message="Product displayed" if rows else "No products found", results=rows)

    # ---------- Cart ----------
    @app.post("/api/cart")
    @auth()
    def cart_add():
        d = body()
        pid, qty = to_int(d.get("product_id")), to_int(d.get("qty", 1))
        if pid is None or qty is None or qty < 1:
            return jsonify(error="Valid product_id and qty (>=1) required"), 400
        p = product(pid)
        if not p:
            return jsonify(error="Product not found"), 404
        row = db().execute("SELECT qty FROM cart WHERE user_id=? AND product_id=?", (session["uid"], pid)).fetchone()
        new_qty = qty + (row["qty"] if row else 0)
        if new_qty > p["stock"]:
            return jsonify(error="Insufficient stock"), 400
        db().execute("INSERT OR REPLACE INTO cart VALUES(?,?,?)", (session["uid"], pid, new_qty))
        db().commit()
        return jsonify(message="Product added")

    @app.put("/api/cart/<int:pid>")
    @auth()
    def cart_update(pid):
        qty = to_int(body().get("qty"))
        if qty is None or qty < 1:
            return jsonify(error="qty must be 1 or more"), 400
        if not db().execute("SELECT 1 FROM cart WHERE user_id=? AND product_id=?", (session["uid"], pid)).fetchone():
            return jsonify(error="Product not in cart"), 404
        if qty > product(pid)["stock"]:
            return jsonify(error="Insufficient stock"), 400
        db().execute("UPDATE cart SET qty=? WHERE user_id=? AND product_id=?", (qty, session["uid"], pid))
        db().commit()
        return jsonify(message="Cart updated")

    @app.delete("/api/cart/<int:pid>")
    @auth()
    def cart_remove(pid):
        cur = db().execute("DELETE FROM cart WHERE user_id=? AND product_id=?", (session["uid"], pid))
        db().commit()
        if cur.rowcount == 0:
            return jsonify(error="Product not in cart"), 404
        return jsonify(message="Product removed")

    def cart_rows():
        return db().execute(
            "SELECT p.id, p.name, p.price, p.stock, c.qty FROM cart c JOIN products p ON p.id=c.product_id WHERE c.user_id=?",
            (session["uid"],)).fetchall()

    @app.get("/api/cart")
    @auth()
    def cart_view():
        items = [dict(r, subtotal=round(r["price"] * r["qty"], 2)) for r in cart_rows()]
        return jsonify(items=items, total=round(sum(i["subtotal"] for i in items), 2))

    # ---------- Checkout and order history ----------
    @app.post("/api/checkout")
    @auth()
    def checkout():
        rows = cart_rows()
        if not rows:
            return jsonify(error="Cart is empty"), 400
        for r in rows:
            if r["qty"] > r["stock"]:
                return jsonify(error="Insufficient stock for " + r["name"]), 400
        total = round(sum(r["price"] * r["qty"] for r in rows), 2)
        cur = db().execute("INSERT INTO orders(user_id,total) VALUES(?,?)", (session["uid"], total))
        oid = cur.lastrowid
        for r in rows:
            db().execute("INSERT INTO order_items VALUES(?,?,?,?,?)", (oid, r["id"], r["name"], r["price"], r["qty"]))
            db().execute("UPDATE products SET stock=stock-? WHERE id=?", (r["qty"], r["id"]))
        db().execute("DELETE FROM cart WHERE user_id=?", (session["uid"],))
        db().commit()
        return jsonify(message="Order placed", order_id=oid, total=total), 201

    @app.get("/api/orders")
    @auth()
    def orders():
        out = []
        for o in db().execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (session["uid"],)):
            items = [dict(i) for i in db().execute(
                "SELECT product_id,name,price,qty FROM order_items WHERE order_id=?", (o["id"],))]
            out.append(dict(o, items=items))
        return jsonify(message="Order details displayed", orders=out)

    # ---------- Admin product management ----------
    def parse_product(d, partial=False):
        try:
            name = (d.get("name") or "").strip()
            price = float(d["price"]) if "price" in d else None
            stock = int(d["stock"]) if "stock" in d else None
        except (TypeError, ValueError):
            return None
        if not partial and (not name or price is None or stock is None):
            return None
        if (price is not None and price <= 0) or (stock is not None and stock < 0):
            return None
        return name, price, stock, d.get("category")

    @app.post("/api/admin/products")
    @auth(admin=True)
    def admin_add():
        p = parse_product(body())
        if not p:
            return jsonify(error="name, price (>0) and stock (>=0) required"), 400
        cur = db().execute("INSERT INTO products(name,price,stock,category) VALUES(?,?,?,?)", p)
        db().commit()
        return jsonify(message="Product created", id=cur.lastrowid), 201

    @app.put("/api/admin/products/<int:pid>")
    @auth(admin=True)
    def admin_update(pid):
        if not product(pid):
            return jsonify(error="Product not found"), 404
        p = parse_product(body(), partial=True)
        if not p:
            return jsonify(error="Invalid values"), 400
        db().execute("UPDATE products SET name=COALESCE(NULLIF(?,''),name), price=COALESCE(?,price), stock=COALESCE(?,stock), "
                     "category=COALESCE(?,category) WHERE id=?", (*p, pid))
        db().commit()
        return jsonify(message="Product updated")

    @app.delete("/api/admin/products/<int:pid>")
    @auth(admin=True)
    def admin_delete(pid):
        if not product(pid):
            return jsonify(error="Product not found"), 404
        db().execute("DELETE FROM products WHERE id=?", (pid,))
        db().execute("DELETE FROM cart WHERE product_id=?", (pid,))
        db().commit()
        return jsonify(message="Product deleted")

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5001)
