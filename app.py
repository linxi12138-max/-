from pathlib import Path
from functools import wraps
import hmac
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.update(
	SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or "family-menu-local-development-only",
	# 可通过部署环境的 ADMIN_PASSWORD 覆盖；默认值按家庭管理员约定设置。
	ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD") or "222313",
	SESSION_COOKIE_HTTPONLY=True,
	SESSION_COOKIE_SAMESITE="Lax",
	SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
)
ROOT = Path(__file__).resolve().parent
DB = ROOT / "instance" / "family_menu.db"
UPLOADS = ROOT / "static" / "uploads"
CATEGORIES = ["荤菜", "素菜", "海鲜", "汤", "面食", "饭", "主食", "凉菜", "其他"]
ALLOWED = {"jpg", "jpeg", "png", "webp"}

# 首次运行时自动准备的家庭菜单。每项都可在管理员后台继续编辑、补充图片和做法。
STARTER_DISHES = [
	("猪肉粉丝鹿茸菇炖土豆（贴饼子）", "荤菜", "一锅炖得软烂入味，配贴饼子更香。", "猪肉、粉丝、鹿茸菇、土豆、玉米面", "猪肉炒香后加土豆和鹿茸菇炖熟，放入粉丝；最后贴上玉米面饼焖熟。"),
	("煎豆腐鸡蛋", "荤菜", "外香里嫩，简单又下饭。", "豆腐、鸡蛋、葱花", "豆腐煎至金黄，倒入蛋液，小火煎熟后撒葱花。"),
	("灯笼椒炒肉", "荤菜", "椒香清爽，肉片鲜嫩。", "灯笼椒、猪肉、蒜、生抽", "肉片滑炒至变色盛出，灯笼椒炒断生后回锅调味。"),
	("火腿金针菇青椒", "荤菜", "咸鲜脆嫩的快手小炒。", "火腿、金针菇、青椒、蒜", "火腿炒香，加入青椒和金针菇，大火翻炒调味。"),
	("西葫芦猪肉饼", "荤菜", "鲜嫩多汁的家常肉饼。", "西葫芦、猪肉末、鸡蛋、面粉", "西葫芦擦丝挤水后拌肉末，压成小饼，煎至两面金黄。"),
	("白菜粉丝", "素菜", "清甜爽口，粉丝吸满汤汁。", "白菜、粉丝、蒜、蚝油", "粉丝泡软；白菜炒软后加入粉丝和调味料焖熟。"),
	("胡萝卜炒肉", "荤菜", "色彩明快、甜脆下饭。", "胡萝卜、猪肉、葱姜", "肉丝滑炒后盛出，胡萝卜炒熟，再回锅同炒。"),
	("土豆肉片", "荤菜", "土豆绵软，肉片咸香。", "土豆、猪肉、青椒、蒜", "土豆片煎软，肉片炒熟后与青椒一同回锅翻炒。"),
	("肉末茄子", "荤菜", "酱香浓郁的米饭搭子。", "茄子、猪肉末、蒜、豆瓣酱", "茄子煎软，肉末炒散后加调料，与茄子焖至入味。"),
	("葱烧大排", "荤菜", "葱香扑鼻、肉质软嫩。", "大排、大葱、姜、生抽、老抽", "大排煎香后加葱姜和调味料，小火焖至软嫩。"),
	("清蒸虾", "海鲜", "原汁原味，鲜甜清爽。", "鲜虾、姜、葱、料酒", "虾去虾线后铺姜片，水开上锅蒸至变红即可。"),
	("蒸鲈鱼", "海鲜", "鱼肉细嫩，清鲜不腻。", "鲈鱼、姜丝、葱丝、蒸鱼豉油", "鱼处理干净后蒸熟，倒掉汤汁，淋豉油和热油。"),
	("蛏子炒芦笋", "海鲜", "鲜甜蛏子配清脆芦笋。", "蛏子、芦笋、蒜、姜", "蛏子焯至开口取肉，芦笋炒断生后与蛏肉快炒。"),
	("蛏子韭菜拌饭", "海鲜", "海味和韭香拌进热米饭。", "蛏子、韭菜、米饭、鸡蛋", "蛏肉炒香，加入韭菜和调味料，与热米饭拌匀。"),
	("西红柿鸡蛋汤", "汤", "酸甜开胃的经典热汤。", "西红柿、鸡蛋、葱花", "西红柿煮出汤汁后加水，水开淋蛋液，撒葱花。"),
	("猪肉丸子汤", "汤", "清鲜暖胃，丸子弹嫩。", "猪肉馅、青菜、姜、淀粉", "肉馅挤成丸子下锅煮熟，加入青菜和盐调味。"),
	("金针菇豆腐汤", "汤", "低负担又鲜美的一碗汤。", "金针菇、嫩豆腐、葱花", "清水煮开后加入豆腐和金针菇，煮熟调味。"),
	("奶香馒头", "面食", "松软带着淡淡奶香。", "面粉、牛奶、酵母、糖", "面团发酵后整形，二次醒发，上锅蒸熟。"),
	("韭菜盒子", "面食", "外皮酥软，内馅鲜香。", "韭菜、鸡蛋、粉丝、面粉", "馅料拌匀包入面皮，平底锅小火烙至两面金黄。"),
	("饺子", "面食", "热腾腾的团圆味道。", "饺子皮、肉馅、蔬菜", "调好馅料包成饺子，水开下锅煮至浮起。"),
	("酱肉包子", "面食", "酱香浓厚、蓬松暄软。", "面粉、猪肉、甜面酱、葱", "发面包入炒香的酱肉馅，醒发后蒸熟。"),
	("小锅焖饭", "饭", "米粒饱满，锅底微焦更香。", "大米、蔬菜、腊味或肉类", "食材与淘洗好的米一同入小锅，焖至熟透后翻松。"),
]

def admin_required(view):
	@wraps(view)
	def wrapped(*args, **kwargs):
		if not session.get("admin_logged_in"):
			return redirect(url_for("admin_login"))
		return view(*args, **kwargs)
	return wrapped

def dbopen():
	db = sqlite3.connect(DB)
	db.row_factory = sqlite3.Row
	db.execute("PRAGMA foreign_keys=ON")
	return db

def init_db():
	(ROOT / "instance").mkdir(exist_ok=True)
	UPLOADS.mkdir(parents=True, exist_ok=True)
	with dbopen() as db:
		db.executescript("""CREATE TABLE IF NOT EXISTS dish(id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, description TEXT DEFAULT '', ingredients TEXT DEFAULT '', instructions TEXT DEFAULT '', image TEXT DEFAULT '', order_count INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
		CREATE TABLE IF NOT EXISTS rating(id INTEGER PRIMARY KEY, dish_id INTEGER NOT NULL REFERENCES dish(id) ON DELETE CASCADE, score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5), created_at TEXT DEFAULT CURRENT_TIMESTAMP);
		CREATE TABLE IF NOT EXISTS order_history(id INTEGER PRIMARY KEY, dish_id INTEGER NOT NULL REFERENCES dish(id) ON DELETE CASCADE, created_at TEXT DEFAULT CURRENT_TIMESTAMP);""")
		# Earlier installs may have an order_history table without a timestamp.
		# Keep those records usable when the date-grouped history is introduced.
		history_columns = {row["name"] for row in db.execute("PRAGMA table_info(order_history)")}
		if "created_at" not in history_columns:
			db.execute("ALTER TABLE order_history ADD COLUMN created_at TEXT")
		db.execute("UPDATE order_history SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at='' ")
		for dish in STARTER_DISHES:
			if not db.execute("SELECT 1 FROM dish WHERE name=?", (dish[0],)).fetchone():
				db.execute("INSERT INTO dish(name,category,description,ingredients,instructions) VALUES(?,?,?,?,?)", dish)

def listing(sort="new"):
	order = {"popular": "d.order_count DESC", "rating": "avg DESC", "new": "d.created_at DESC"}.get(sort, "d.created_at DESC")
	with dbopen() as db:
		return db.execute(f"SELECT d.*, COALESCE(ROUND(AVG(r.score),1),0) avg FROM dish d LEFT JOIN rating r ON r.dish_id=d.id GROUP BY d.id ORDER BY {order}").fetchall()

def current_cart():
	"""Return the validated cart stored in the signed browser session."""
	cart = {}
	for key, quantity in session.get("cart", {}).items():
		try:
			dish_id, amount = int(key), int(quantity)
		except (TypeError, ValueError):
			continue
		if dish_id > 0 and 0 < amount <= 99:
			cart[str(dish_id)] = amount
	return cart

def cart_items():
	cart = current_cart()
	if not cart:
		return []
	ids = [int(key) for key in cart]
	placeholders = ",".join("?" for _ in ids)
	with dbopen() as db:
		rows = db.execute(f"SELECT * FROM dish WHERE id IN ({placeholders})", ids).fetchall()
	by_id = {row["id"]: row for row in rows}
	return [{"dish": by_id[dish_id], "quantity": cart[str(dish_id)]} for dish_id in ids if dish_id in by_id]

@app.context_processor
def inject_cart_count():
	return {"cart_count": sum(current_cart().values())}
def save(dish_id=None):
	name, category = request.form.get("name", "").strip(), request.form.get("category", "")
	if not name or category not in CATEGORIES:
		flash("请填写菜名并选择分类")
		return redirect(request.url)
	image = ""
	f = request.files.get("image")
	if f and f.filename:
		ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
		if ext not in ALLOWED:
			flash("图片仅支持 jpg、jpeg、png、webp")
			return redirect(request.url)
		image = secure_filename(f.filename)
		f.save(UPLOADS / image)
	fields = (name, category, request.form.get("description", ""), request.form.get("ingredients", ""), request.form.get("instructions", ""))
	with dbopen() as db:
		if dish_id:
			if image: db.execute("UPDATE dish SET name=?,category=?,description=?,ingredients=?,instructions=?,image=? WHERE id=?", (*fields,image,dish_id))
			else: db.execute("UPDATE dish SET name=?,category=?,description=?,ingredients=?,instructions=? WHERE id=?", (*fields,dish_id))
		else: db.execute("INSERT INTO dish(name,category,description,ingredients,instructions,image) VALUES(?,?,?,?,?,?)", (*fields,image))
	flash("已保存")
	return redirect(url_for("admin"))

@app.get("/")
def index():
	sort, category = request.args.get("sort", "new"), request.args.get("category", "")
	query = request.args.get("q", "").strip()
	dishes = [d for d in listing(sort) if not category or d["category"] == category]
	if query:
		dishes = [d for d in dishes if query.lower() in d["name"].lower() or query.lower() in d["description"].lower()]
	return render_template("index.html", dishes=dishes, categories=CATEGORIES, sort=sort, category=category, query=query, cart_dishes=cart_items(), show_cart=request.args.get("cart") == "1")

@app.get("/dish/<int:id>")
def detail(id):
	with dbopen() as db: dish = db.execute("SELECT d.*,COALESCE(ROUND(AVG(r.score),1),0) avg FROM dish d LEFT JOIN rating r ON r.dish_id=d.id WHERE d.id=? GROUP BY d.id", (id,)).fetchone()
	if not dish: return "菜品不存在", 404
	return render_template("dish_detail.html", dish=dish)

@app.get("/cart")
def cart():
	return redirect(url_for("index", cart=1))

@app.post("/cart/add/<int:id>")
@app.post("/order/<int:id>")
def cart_add(id):
	with dbopen() as db:
		if not db.execute("SELECT id FROM dish WHERE id=?", (id,)).fetchone(): return "菜品不存在", 404
	cart = current_cart()
	key = str(id)
	cart[key] = min(cart.get(key, 0) + 1, 99)
	session["cart"] = cart
	flash("已加入购物车，请确认后提交点餐。")
	return redirect(url_for("index", cart=1))

@app.post("/cart/update")
def cart_update():
	cart = current_cart()
	remove_id = request.form.get("remove_id", type=int)
	if remove_id:
		cart.pop(str(remove_id), None)
	else:
		for key, value in request.form.items():
			if key.startswith("quantity_"):
				try: dish_id, quantity = int(key.removeprefix("quantity_")), int(value)
				except ValueError: continue
				if quantity <= 0: cart.pop(str(dish_id), None)
				elif quantity <= 99: cart[str(dish_id)] = quantity
	session["cart"] = cart
	flash("购物车已更新。")
	return redirect(url_for("index", cart=1))

@app.post("/cart/confirm")
def cart_confirm():
	items = cart_items()
	if not items:
		flash("购物车还是空的，先选几道菜吧。")
		return redirect(url_for("index"))
	with dbopen() as db:
		for item in items:
			dish_id, quantity = item["dish"]["id"], item["quantity"]
			db.execute("UPDATE dish SET order_count=order_count+? WHERE id=?", (quantity, dish_id))
			db.executemany("INSERT INTO order_history(dish_id,created_at) VALUES(?,CURRENT_TIMESTAMP)", [(dish_id,)] * quantity)
	session.pop("cart", None)
	flash("点餐已确认，已加入今天的点餐记录！")
	return redirect(url_for("index"))
@app.post("/rate/<int:id>")
def rate(id):
	score = request.form.get("score", type=int)
	if score not in range(1, 6): flash("请选择 1 至 5 星")
	else:
		with dbopen() as db: db.execute("INSERT INTO rating(dish_id,score) VALUES(?,?)", (id, score))
		flash("评分已保存")
	return redirect(url_for("detail", id=id))

@app.get("/ranking")
def ranking(): return render_template("ranking.html", popular=listing("popular"), rated=listing("rating"))

@app.get("/orders")
def orders():
	try:
		with dbopen() as db:
			rows = db.execute("""SELECT substr(datetime(h.created_at, '+8 hours'),1,10) AS order_date, d.name, d.image, COUNT(*) AS quantity, MAX(datetime(h.created_at, '+8 hours')) AS last_order_at FROM order_history h JOIN dish d ON d.id=h.dish_id GROUP BY order_date, d.id ORDER BY order_date DESC, last_order_at DESC""").fetchall()
	except sqlite3.DatabaseError:
		with dbopen() as db:
			rows = db.execute("""SELECT '历史记录' AS order_date, d.name, d.image, COUNT(*) AS quantity, NULL AS last_order_at FROM order_history h JOIN dish d ON d.id=h.dish_id GROUP BY d.id ORDER BY MAX(h.id) DESC""").fetchall()
	order_days = []
	for row in rows:
		if not order_days or order_days[-1]["date"] != row["order_date"]:
			order_days.append({"date": row["order_date"], "items": []})
		order_days[-1]["items"].append(row)
	return render_template("orders.html", order_days=order_days)
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
	if session.get("admin_logged_in"):
		return redirect(url_for("admin"))
	if request.method == "POST":
		admin_password = app.config["ADMIN_PASSWORD"]
		if not admin_password:
			flash("尚未配置管理员密码，请设置 ADMIN_PASSWORD 环境变量。")
		elif hmac.compare_digest(request.form.get("password", ""), admin_password):
			session["admin_logged_in"] = True
			return redirect(url_for("admin"))
		else:
			flash("管理员密码错误")
	return render_template("login.html")

@app.post("/admin/logout")
@admin_required
def admin_logout():
	session.clear()
	flash("已退出登录")
	return redirect(url_for("admin_login"))

@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
	if request.method == "POST":
		with dbopen() as db: db.execute("DELETE FROM dish WHERE id=?", (request.form.get("id", type=int),))
		flash("菜品已删除")
		return redirect(url_for("admin"))
	return render_template("admin.html", dishes=listing())

@app.route("/admin/add", methods=["GET", "POST"])
@admin_required
def add_dish():
	if request.method == "POST": return save()
	return render_template("add_dish.html", categories=CATEGORIES, dish=None)

@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_dish(id):
	with dbopen() as db: dish = db.execute("SELECT * FROM dish WHERE id=?", (id,)).fetchone()
	if not dish: return "菜品不存在", 404
	if request.method == "POST": return save(id)
	return render_template("edit_dish.html", categories=CATEGORIES, dish=dish)

init_db()
if __name__ == "__main__": app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
