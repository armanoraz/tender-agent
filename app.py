import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
DB = os.environ.get("DATABASE_PATH", "/tmp/tenders.db")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        customer TEXT DEFAULT '',
        region TEXT DEFAULT '',
        amount REAL DEFAULT 0,
        cost REAL DEFAULT 0,
        license_required TEXT DEFAULT 'unknown',
        deadline TEXT DEFAULT '',
        source_url TEXT DEFAULT '',
        created_at TEXT
    )""")
    con.commit()
    con.close()

PAGE = """
<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Тендерный агент Казахстана</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;color:#20242a}
header{background:#172b4d;color:white;padding:18px 22px}
main{max-width:1100px;margin:22px auto;padding:0 14px}
.card{background:white;border-radius:10px;padding:18px;margin-bottom:16px;box-shadow:0 1px 5px #0001}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}
input,select{width:100%;padding:10px;border:1px solid #ccd2da;border-radius:6px;box-sizing:border-box;margin:5px 0 12px}
button{background:#1769aa;color:white;border:0;padding:11px 16px;border-radius:6px;cursor:pointer}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px;border-bottom:1px solid #e4e7eb}
small,.muted{color:#687385}.good{color:#087443;font-weight:bold}.bad{color:#b42318;font-weight:bold}
a{color:#1769aa} .scroll{overflow-x:auto}
</style></head><body>
<header><h2>Тендерный агент Казахстана</h2><div>Караганда и область · лимит 10 000 000 ₸ · целевая рентабельность от 20%</div></header>
<main>
<div class="card"><h3>Добавить тендер для проверки</h3>
<form method="post" action="/add">
<div class="grid">
<label>Название тендера<input name="title" required></label>
<label>Заказчик<input name="customer"></label>
<label>Регион<input name="region" value="Карагандинская область"></label>
<label>Цена контракта, ₸<input name="amount" type="number" min="0" step="0.01" required></label>
<label>Полная себестоимость, ₸<input name="cost" type="number" min="0" step="0.01" required></label>
<label>Лицензия<select name="license_required"><option value="unknown">Не проверено</option><option value="no">Не требуется</option><option value="yes">Требуется</option></select></label>
<label>Срок подачи<input name="deadline" placeholder="например 25.11.2026"></label>
<label>Ссылка на закупку<input name="source_url" type="url"></label>
</div><button type="submit">Сохранить и рассчитать</button></form>
<p class="muted">Это стартовая версия: тендеры добавляются вручную. Автоматический поиск подключается отдельно через API площадок после получения доступа.</p>
</div>
<div class="card"><h3>Фильтры агента</h3><p>Максимальная цена: <b>10 000 000 ₸</b> · Минимальная рентабельность: <b>20%</b> · Регион: <b>Караганда и Карагандинская область</b></p>
<p class="muted">Рентабельность = (цена − себестоимость) / себестоимость × 100%. Маржа от цены контракта показывается отдельно.</p></div>
<div class="card"><h3>Тендеры и расчёт</h3><div class="scroll"><table><tr><th>Тендер</th><th>Регион</th><th>Цена</th><th>Себестоимость</th><th>Прибыль</th><th>Рентаб.</th><th>Лицензия</th><th>Оценка</th></tr>
{% for t in tenders %}
<tr><td>{% if t.source_url %}<a href="{{t.source_url}}" target="_blank">{{t.title}}</a>{% else %}{{t.title}}{% endif %}<br><small>{{t.customer}} · {{t.deadline}}</small></td>
<td>{{t.region}}</td><td>{{"{:,.0f}".format(t.amount).replace(",", " ")}} ₸</td>
<td>{{"{:,.0f}".format(t.cost).replace(",", " ")}} ₸</td>
<td>{{"{:,.0f}".format(t.amount-t.cost).replace(",", " ")}} ₸</td>
<td>{{("{:.1f}".format(((t.amount-t.cost)/t.cost*100) if t.cost else 0))}}%</td>
<td>{{"Да" if t.license_required=="yes" else ("Нет" if t.license_required=="no" else "Не проверено")}}</td>
<td>{% if t.amount > 10000000 or t.cost <= 0 or t.license_required=="yes" or ((t.amount-t.cost)/t.cost*100 if t.cost else 0) < 20 %}<span class="bad">Не подходит / проверить</span>{% elif t.license_required=="unknown" %}<span class="bad">Нужна проверка</span>{% else %}<span class="good">Предварительно подходит</span>{% endif %}</td></tr>
{% else %}<tr><td colspan="8">Пока тендеров нет. Добавьте первый тендер выше.</td></tr>{% endfor %}
</table></div></div>
<div class="card"><small>Важно: система помогает анализировать закупки, но не подаёт заявки и не подписывает документы. Все требования, лицензии, сроки и расходы необходимо проверить по первоисточнику.</small></div>
</main></body></html>
"""

@app.route("/")
def index():
    init_db()
    con = db()
    tenders = con.execute("SELECT * FROM tenders ORDER BY id DESC").fetchall()
    con.close()
    return render_template_string(PAGE, tenders=tenders)

@app.route("/add", methods=["POST"])
def add():
    init_db()
    try:
        amount = float(request.form.get("amount", "0"))
        cost = float(request.form.get("cost", "0"))
        if amount < 0 or cost < 0:
            raise ValueError()
    except ValueError:
        flash("Проверьте суммы.")
        return redirect(url_for("index"))
    con = db()
    con.execute("""INSERT INTO tenders
        (title,customer,region,amount,cost,license_required,deadline,source_url,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (request.form.get("title","").strip(), request.form.get("customer","").strip(),
         request.form.get("region","").strip(), amount, cost,
         request.form.get("license_required","unknown"), request.form.get("deadline","").strip(),
         request.form.get("source_url","").strip(), datetime.utcnow().isoformat()))
    con.commit()
    con.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
