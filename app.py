from flask import Flask, request, redirect, session, jsonify, render_template_string
import sqlite3, uuid, os, requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

ADMIN_PASSWORD = "123456"  # เปลี่ยนรหัสแอดมินตรงนี้
DISCORD_WEBHOOK = ""       # ใส่ Discord webhook ถ้ามี

LTC_ADDRESS = "ใส่กระเป๋า LTC"
USDT_ADDRESS = "ใส่กระเป๋า USDT"

PRODUCTS = [
    {"id": "boostfps", "name": "Boost FPS Pack", "price": 99, "stock": "ลิงก์โหลด / คีย์สินค้า"},
    {"id": "discordbot", "name": "Discord Bot Setup", "price": 299, "stock": "ติดต่อแอดมินเพื่อรับงาน"},
    {"id": "premium", "name": "Premium Package", "price": 499, "stock": "ของพรีเมียมส่งหลังแอดมินยืนยัน"},
]

def db():
    con = sqlite3.connect("shop.db")
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        discord TEXT,
        product_id TEXT,
        product_name TEXT,
        price INTEGER,
        pay_type TEXT,
        txid TEXT UNIQUE,
        status TEXT,
        created_at TEXT
    )
    """)
    con.commit()
    con.close()

def notify_discord(text):
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": text}, timeout=5)
        except:
            pass

@app.route("/")
def home():
    return render_template_string(HTML, products=PRODUCTS)

@app.route("/checkout", methods=["POST"])
def checkout():
    discord = request.form.get("discord", "").strip()
    product_id = request.form.get("product_id")
    pay_type = request.form.get("pay_type")

    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product or not discord:
        return redirect("/")

    order_id = str(uuid.uuid4())[:8].upper()
    address = LTC_ADDRESS if pay_type == "ltc" else USDT_ADDRESS

    con = db()
    con.execute("""
    INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id,
        discord,
        product["id"],
        product["name"],
        product["price"],
        pay_type,
        "",
        "WAIT_TXID",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    con.commit()
    con.close()

    notify_discord(
        f"🛒 มีออเดอร์ใหม่\n"
        f"Order: `{order_id}`\n"
        f"Discord: `{discord}`\n"
        f"สินค้า: **{product['name']}**\n"
        f"ราคา: `{product['price']} บาท`\n"
        f"จ่ายด้วย: `{pay_type.upper()}`"
    )

    return render_template_string(PAYMENT, order_id=order_id, product=product, address=address, pay_type=pay_type)

@app.route("/submit_txid", methods=["POST"])
def submit_txid():
    order_id = request.form.get("order_id", "").strip()
    txid = request.form.get("txid", "").strip()

    if not txid:
        return "กรอก TXID ก่อน"

    con = db()

    used = con.execute("SELECT * FROM orders WHERE txid=?", (txid,)).fetchone()
    if used:
        con.close()
        return "TXID นี้ถูกใช้ไปแล้ว"

    order = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        con.close()
        return "ไม่เจอออเดอร์"

    con.execute("UPDATE orders SET txid=?, status=? WHERE id=?", (txid, "WAIT_ADMIN", order_id))
    con.commit()
    con.close()

    notify_discord(
        f"💸 ลูกค้าส่ง TXID แล้ว\n"
        f"Order: `{order_id}`\n"
        f"TXID: `{txid}`\n"
        f"สถานะ: รอแอดมินตรวจ"
    )

    return render_template_string(DONE, order_id=order_id)

@app.route("/track/<order_id>")
def track(order_id):
    con = db()
    order = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    con.close()
    if not order:
        return "ไม่เจอออเดอร์"
    return render_template_string(TRACK, order=order)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        return "รหัสผิด"

    if not session.get("admin"):
        return render_template_string(LOGIN)

    con = db()
    orders = con.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    con.close()
    return render_template_string(ADMIN, orders=orders)

@app.route("/admin/approve/<order_id>")
def approve(order_id):
    if not session.get("admin"):
        return redirect("/admin")

    con = db()
    order = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    product = next((p for p in PRODUCTS if p["id"] == order["product_id"]), None)

    con.execute("UPDATE orders SET status=? WHERE id=?", ("PAID_DELIVERED", order_id))
    con.commit()
    con.close()

    notify_discord(
        f"✅ อนุมัติออเดอร์แล้ว\n"
        f"Order: `{order_id}`\n"
        f"ลูกค้า: `{order['discord']}`\n"
        f"สินค้า: **{order['product_name']}**"
    )

    return render_template_string(DELIVER, order=order, product=product)

@app.route("/admin/reject/<order_id>")
def reject(order_id):
    if not session.get("admin"):
        return redirect("/admin")

    con = db()
    con.execute("UPDATE orders SET status=? WHERE id=?", ("REJECTED", order_id))
    con.commit()
    con.close()

    notify_discord(f"❌ ปฏิเสธออเดอร์ `{order_id}`")
    return redirect("/admin")

HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>SyncZone Shop</title>
<style>
body{margin:0;background:#0b0b12;color:white;font-family:Arial}
.header{padding:30px;text-align:center;background:#151525}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;padding:30px}
.card{background:#181827;border-radius:20px;padding:25px;box-shadow:0 0 20px #000}
button{background:#5865F2;color:white;border:0;padding:12px;border-radius:12px;width:100%;font-size:16px;cursor:pointer}
input,select{width:100%;padding:12px;border-radius:12px;border:0;margin:8px 0}
.price{color:#00ff99;font-size:24px}
a{color:#8ea2ff}
</style>
</head>
<body>
<div class="header">
<h1>SyncZone Shop</h1>
<p>ร้านขายของอัตโนมัติ จ่าย LTC / USDT</p>
<a href="/admin">Admin</a>
</div>

<div class="grid">
{% for p in products %}
<div class="card">
<h2>{{p.name}}</h2>
<div class="price">{{p.price}} บาท</div>
<form method="POST" action="/checkout">
<input name="discord" placeholder="Discord ของมึง เช่น user#0001" required>
<input type="hidden" name="product_id" value="{{p.id}}">
<select name="pay_type">
<option value="ltc">Litecoin LTC</option>
<option value="usdt">USDT</option>
</select>
<button>ซื้อเลย</button>
</form>
</div>
{% endfor %}
</div>
</body>
</html>
"""

PAYMENT = """
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>Payment</title>
<style>
body{background:#0b0b12;color:white;font-family:Arial;text-align:center;padding:30px}
.box{max-width:500px;margin:auto;background:#181827;padding:25px;border-radius:20px}
input{width:100%;padding:12px;border-radius:12px;border:0;margin-top:10px}
button{background:#00b894;color:white;border:0;padding:12px;border-radius:12px;width:100%;margin-top:10px}
.code{background:#000;padding:12px;border-radius:10px;word-break:break-all}
</style>
</head>
<body>
<div class="box">
<h1>ชำระเงิน</h1>
<p>Order: <b>{{order_id}}</b></p>
<p>สินค้า: {{product.name}}</p>
<p>ราคา: {{product.price}} บาท</p>
<p>จ่ายด้วย: {{pay_type.upper()}}</p>

<h3>โอนไปที่กระเป๋านี้</h3>
<div class="code">{{address}}</div>

<img src="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={{address}}" style="margin-top:15px">

<form method="POST" action="/submit_txid">
<input type="hidden" name="order_id" value="{{order_id}}">
<input name="txid" placeholder="วาง TXID ตรงนี้" required>
<button>ส่ง TXID ให้แอดมินตรวจ</button>
</form>

<p><a href="/track/{{order_id}}">เช็คสถานะออเดอร์</a></p>
</div>
</body>
</html>
"""

DONE = """
<body style="background:#0b0b12;color:white;font-family:Arial;text-align:center;padding:40px">
<h1>ส่ง TXID แล้ว</h1>
<p>Order {{order_id}} รอแอดมินตรวจ</p>
<a style="color:#8ea2ff" href="/track/{{order_id}}">เช็คสถานะ</a>
</body>
"""

TRACK = """
<body style="background:#0b0b12;color:white;font-family:Arial;text-align:center;padding:40px">
<h1>สถานะออเดอร์</h1>
<p>Order: <b>{{order.id}}</b></p>
<p>สินค้า: {{order.product_name}}</p>
<p>ราคา: {{order.price}} บาท</p>
<p>สถานะ: <b>{{order.status}}</b></p>
<p>TXID: {{order.txid}}</p>
<a style="color:#8ea2ff" href="/">กลับหน้าร้าน</a>
</body>
"""

LOGIN = """
<body style="background:#0b0b12;color:white;font-family:Arial;text-align:center;padding:40px">
<h1>Admin Login</h1>
<form method="POST">
<input name="password" type="password" placeholder="รหัสแอดมิน" style="padding:12px;border-radius:10px">
<button style="padding:12px;border-radius:10px">เข้า</button>
</form>
</body>
"""

ADMIN = """
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>Admin</title>
<style>
body{background:#0b0b12;color:white;font-family:Arial;padding:20px}
table{width:100%;border-collapse:collapse;background:#181827}
td,th{padding:10px;border-bottom:1px solid #333}
a{color:white;padding:7px 10px;border-radius:8px;text-decoration:none}
.ok{background:#00b894}.no{background:#d63031}
</style>
</head>
<body>
<h1>Admin Dashboard</h1>
<table>
<tr>
<th>Order</th><th>Discord</th><th>สินค้า</th><th>ราคา</th><th>จ่าย</th><th>TXID</th><th>สถานะ</th><th>จัดการ</th>
</tr>
{% for o in orders %}
<tr>
<td>{{o.id}}</td>
<td>{{o.discord}}</td>
<td>{{o.product_name}}</td>
<td>{{o.price}}</td>
<td>{{o.pay_type}}</td>
<td>{{o.txid}}</td>
<td>{{o.status}}</td>
<td>
<a class="ok" href="/admin/approve/{{o.id}}">อนุมัติ</a>
<a class="no" href="/admin/reject/{{o.id}}">ปฏิเสธ</a>
</td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

DELIVER = """
<body style="background:#0b0b12;color:white;font-family:Arial;text-align:center;padding:40px">
<h1>อนุมัติแล้ว</h1>
<p>ส่งข้อมูลนี้ให้ลูกค้า</p>
<div style="background:#111;padding:20px;border-radius:15px;max-width:600px;margin:auto">
<p><b>{{product.stock}}</b></p>
</div>
<p><a style="color:#8ea2ff" href="/admin">กลับแอดมิน</a></p>
</body>
"""

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
