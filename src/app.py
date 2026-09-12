import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"


@app.route("/")
def dashboard():
    conn = get_db()

    nb_products = conn.execute("SELECT COUNT(*) AS n FROM Product").fetchone()["n"]
    nb_customers = conn.execute("SELECT COUNT(*) AS n FROM Customer").fetchone()["n"]
    nb_orders = conn.execute("SELECT COUNT(*) AS n FROM CustomerOrder").fetchone()["n"]

    total_revenue = conn.execute("""
        SELECT SUM(oi.quantity * oi.unit_price) AS total
        FROM OrderItem oi
        JOIN CustomerOrder co ON oi.order_id = co.id
        WHERE co.status != 'cancelled'
    """).fetchone()["total"] or 0

    recent_orders = conn.execute("""
        SELECT co.id, c.first_name || ' ' || c.last_name AS customer_name,
               co.order_date, co.status,
               SUM(oi.quantity * oi.unit_price) AS total_amount
        FROM CustomerOrder co
        JOIN Customer c ON co.customer_id = c.id
        JOIN OrderItem oi ON co.id = oi.order_id
        GROUP BY co.id, c.first_name, c.last_name, co.order_date, co.status
        ORDER BY co.order_date DESC
        LIMIT 5
    """).fetchall()

    best_seller = conn.execute("""
        SELECT p.name, SUM(oi.quantity) AS total_sold
        FROM Product p
        JOIN OrderItem oi ON p.id = oi.product_id
        JOIN CustomerOrder co ON oi.order_id = co.id
        WHERE co.status != 'cancelled'
        GROUP BY p.id, p.name
        ORDER BY total_sold DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        nb_products=nb_products,
        nb_customers=nb_customers,
        nb_orders=nb_orders,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
        best_seller=best_seller,
    )


@app.route("/products")
def products():
    conn = get_db()
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", "")
    sort = request.args.get("sort", "name_asc")

    query = """
        SELECT p.id, p.name, p.description, p.price, p.stock,
               c.name AS category_name, p.category_id
        FROM Product p
        JOIN Category c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND p.name LIKE ?"
        params.append(f"%{search}%")

    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    sort_map = {
        "name_asc": "p.name ASC",
        "name_desc": "p.name DESC",
        "price_asc": "p.price ASC",
        "price_desc": "p.price DESC",
    }
    query += " ORDER BY " + sort_map.get(sort, "p.name ASC")

    product_list = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT * FROM Category ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "products.html",
        products=product_list,
        categories=categories,
        search=search,
        category_id=category_id,
        sort=sort,
    )


def validate_product_form(form):
    name = form.get("name", "").strip()
    description = form.get("description", "").strip()
    price_raw = form.get("price", "")
    stock_raw = form.get("stock", "")
    category_id = form.get("category_id", "")

    try:
        price = float(price_raw)
        stock = int(stock_raw)
    except ValueError:
        return None, "Le prix et le stock doivent être des nombres valides."

    if not name:
        return None, "Le nom du produit est obligatoire."
    if price < 0:
        return None, "Le prix ne peut pas être négatif."
    if stock < 0:
        return None, "Le stock ne peut pas être négatif."
    if not category_id:
        return None, "Choisis une catégorie."

    return {
        "name": name,
        "description": description,
        "price": price,
        "stock": stock,
        "category_id": category_id,
    }, None


@app.route("/products/new", methods=["GET", "POST"])
def product_new():
    conn = get_db()
    categories = conn.execute("SELECT * FROM Category ORDER BY name").fetchall()

    if request.method == "POST":
        data, error = validate_product_form(request.form)
        if error:
            conn.close()
            flash(error, "danger")
            return render_template("product_form.html", categories=categories, product=request.form)

        conn.execute(
            "INSERT INTO Product (name, description, price, stock, category_id) VALUES (?, ?, ?, ?, ?)",
            (data["name"], data["description"], data["price"], data["stock"], data["category_id"]),
        )
        conn.commit()
        conn.close()
        flash("Produit créé.", "success")
        return redirect(url_for("products"))

    conn.close()
    return render_template("product_form.html", categories=categories, product=None)


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    conn = get_db()
    categories = conn.execute("SELECT * FROM Category ORDER BY name").fetchall()

    if request.method == "POST":
        data, error = validate_product_form(request.form)
        if error:
            conn.close()
            flash(error, "danger")
            return render_template("product_form.html", categories=categories, product=request.form, product_id=product_id)

        conn.execute(
            "UPDATE Product SET name=?, description=?, price=?, stock=?, category_id=? WHERE id=?",
            (data["name"], data["description"], data["price"], data["stock"], data["category_id"], product_id),
        )
        conn.commit()
        conn.close()
        flash("Produit modifié.", "success")
        return redirect(url_for("products"))

    product = conn.execute("SELECT * FROM Product WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if product is None:
        flash("Produit introuvable.", "danger")
        return redirect(url_for("products"))
    return render_template("product_form.html", categories=categories, product=product, product_id=product_id)


@app.route("/products/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM Product WHERE id = ?", (product_id,))
        conn.commit()
        if cur.rowcount == 0:
            flash("Produit introuvable, rien n'a été supprimé.", "warning")
        else:
            flash("Produit supprimé.", "success")
    except sqlite3.IntegrityError:
        flash("Impossible de supprimer ce produit : il est référencé dans au moins une commande.", "danger")
    finally:
        conn.close()
    return redirect(url_for("products"))


@app.route("/customers")
def customers():
    conn = get_db()
    search = request.args.get("q", "").strip()

    query = """
        SELECT 
            c.id,
            c.first_name || ' ' || c.last_name AS full_name,
            c.email,
            c.city,
            COUNT(DISTINCT co.id) AS nb_orders,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_spent
        FROM Customer c
        LEFT JOIN CustomerOrder co ON c.id = co.customer_id AND co.status != 'cancelled'
        LEFT JOIN OrderItem oi ON co.id = oi.order_id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (c.first_name LIKE ? OR c.last_name LIKE ? OR c.email LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    query += " GROUP BY c.id, c.first_name, c.last_name, c.email, c.city ORDER BY c.last_name"

    customer_list = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("customers.html", customers=customer_list, search=search)


@app.route("/customers/new", methods=["GET", "POST"])
def customer_new():
    conn = get_db()

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        city = request.form.get("city", "").strip()

        if not first_name or not last_name or not email:
            conn.close()
            flash("Prénom, nom et email sont obligatoires.", "danger")
            return render_template("customer_form.html", customer=request.form)

        try:
            conn.execute(
                "INSERT INTO Customer (first_name, last_name, email, city) VALUES (?, ?, ?, ?)",
                (first_name, last_name, email, city),
            )
            conn.commit()
            flash("Client créé.", "success")
        except sqlite3.IntegrityError:
            conn.close()
            flash(f"Un client existe déjà avec l'email {email}.", "danger")
            return render_template("customer_form.html", customer=request.form)

        conn.close()
        return redirect(url_for("customers"))

    conn.close()
    return render_template("customer_form.html", customer=None)


@app.route("/customers/<int:customer_id>")
def customer_detail(customer_id):
    conn = get_db()

    customer = conn.execute("SELECT * FROM Customer WHERE id = ?", (customer_id,)).fetchone()
    if customer is None:
        conn.close()
        flash("Client introuvable.", "danger")
        return redirect(url_for("customers"))

    orders_history = conn.execute("""
        SELECT co.id, co.order_date, co.status,
               SUM(oi.quantity * oi.unit_price) AS total_amount
        FROM CustomerOrder co
        JOIN OrderItem oi ON co.id = oi.order_id
        WHERE co.customer_id = ?
        GROUP BY co.id, co.order_date, co.status
        ORDER BY co.order_date DESC
    """, (customer_id,)).fetchall()

    total_spent = conn.execute("""
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total
        FROM CustomerOrder co
        JOIN OrderItem oi ON co.id = oi.order_id
        WHERE co.customer_id = ? AND co.status != 'cancelled'
    """, (customer_id,)).fetchone()["total"]

    conn.close()

    return render_template("customer_detail.html", customer=customer, orders=orders_history, total_spent=total_spent)


@app.route("/orders")
def orders():
    conn = get_db()
    order_list = conn.execute("""
        SELECT co.id, c.first_name || ' ' || c.last_name AS customer_name,
               co.order_date, co.status,
               SUM(oi.quantity * oi.unit_price) AS total_amount
        FROM CustomerOrder co
        JOIN Customer c ON co.customer_id = c.id
        JOIN OrderItem oi ON co.id = oi.order_id
        GROUP BY co.id, c.first_name, c.last_name, co.order_date, co.status
        ORDER BY co.order_date DESC
    """).fetchall()
    conn.close()
    return render_template("orders.html", orders=order_list)


@app.route("/orders/new", methods=["GET", "POST"])
def order_new():
    conn = get_db()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        products_all = conn.execute("SELECT * FROM Product").fetchall()

        if not customer_id:
            conn.close()
            flash("Choisis un client.", "danger")
            return redirect(url_for("order_new"))

        items = []
        for p in products_all:
            qty_raw = request.form.get(f"qty_{p['id']}", "0")
            try:
                qty = int(qty_raw)
            except ValueError:
                qty = 0
            if qty > 0:
                items.append({"product_id": p["id"], "name": p["name"], "qty": qty,
                              "price": p["price"], "stock": p["stock"]})

        if not items:
            conn.close()
            flash("Sélectionne au moins un produit avec une quantité.", "danger")
            return redirect(url_for("order_new"))

        for item in items:
            if item["qty"] > item["stock"]:
                conn.close()
                flash(f"Stock insuffisant pour {item['name']} (demandé: {item['qty']}, disponible: {item['stock']}).", "danger")
                return redirect(url_for("order_new"))

        try:
            cur = conn.execute(
                "INSERT INTO CustomerOrder (customer_id, order_date, status) VALUES (?, CURRENT_TIMESTAMP, 'pending')",
                (customer_id,),
            )
            order_id = cur.lastrowid

            for item in items:
                conn.execute(
                    "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (order_id, item["product_id"], item["qty"], item["price"]),
                )
                conn.execute(
                    "UPDATE Product SET stock = stock - ? WHERE id = ?",
                    (item["qty"], item["product_id"]),
                )

            conn.commit()
            flash("Commande créée.", "success")
        except Exception:
            conn.rollback()
            flash("Erreur lors de la création de la commande, rien n'a été enregistré.", "danger")
        finally:
            conn.close()

        return redirect(url_for("orders"))

    customers_list = conn.execute("SELECT * FROM Customer ORDER BY last_name").fetchall()
    products_list = conn.execute("SELECT * FROM Product ORDER BY name").fetchall()
    conn.close()
    return render_template("order_form.html", customers=customers_list, products=products_list)


@app.route("/orders/<int:order_id>")
def order_detail(order_id):
    conn = get_db()

    order = conn.execute("""
        SELECT co.id, co.order_date, co.status, c.first_name, c.last_name, c.email
        FROM CustomerOrder co
        JOIN Customer c ON co.customer_id = c.id
        WHERE co.id = ?
    """, (order_id,)).fetchone()

    if order is None:
        conn.close()
        flash("Commande introuvable.", "danger")
        return redirect(url_for("orders"))

    items = conn.execute("""
        SELECT p.name, oi.quantity, oi.unit_price,
               (oi.quantity * oi.unit_price) AS line_total
        FROM OrderItem oi
        JOIN Product p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()

    total = sum(item["line_total"] for item in items)

    conn.close()
    return render_template("order_detail.html", order=order, items=items, total=total)


@app.route("/analytics")
def analytics():
    conn = get_db()

    revenue_by_category = conn.execute("""
        SELECT c.name AS category_name,
               SUM(oi.quantity) AS total_units_sold,
               SUM(oi.quantity * oi.unit_price) AS total_revenue
        FROM Category c
        JOIN Product p ON p.category_id = c.id
        JOIN OrderItem oi ON oi.product_id = p.id
        JOIN CustomerOrder co ON oi.order_id = co.id
        WHERE co.status != 'cancelled'
        GROUP BY c.id, c.name
        ORDER BY total_revenue DESC
    """).fetchall()

    top_customers = conn.execute("""
        SELECT c.first_name || ' ' || c.last_name AS full_name,
               COUNT(DISTINCT co.id) AS nb_orders,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_spent
        FROM Customer c
        LEFT JOIN CustomerOrder co ON c.id = co.customer_id AND co.status != 'cancelled'
        LEFT JOIN OrderItem oi ON co.id = oi.order_id
        GROUP BY c.id, c.first_name, c.last_name
        ORDER BY total_spent DESC
        LIMIT 5
    """).fetchall()

    never_ordered = conn.execute("""
        SELECT p.id, p.name
        FROM Product p
        WHERE NOT EXISTS (
            SELECT 1 FROM OrderItem oi WHERE oi.product_id = p.id
        )
    """).fetchall()

    above_average = conn.execute("""
        WITH order_totals AS (
            SELECT co.id AS order_id, co.order_date, co.status,
                   SUM(oi.quantity * oi.unit_price) AS total_amount
            FROM CustomerOrder co
            JOIN OrderItem oi ON co.id = oi.order_id
            GROUP BY co.id
        )
        SELECT order_id, order_date, status, total_amount
        FROM order_totals
        WHERE total_amount > (SELECT AVG(total_amount) FROM order_totals)
        ORDER BY total_amount DESC
    """).fetchall()

    avg_order_value = conn.execute("""
        SELECT AVG(total_amount) AS avg_value FROM (
            SELECT SUM(oi.quantity * oi.unit_price) AS total_amount
            FROM CustomerOrder co
            JOIN OrderItem oi ON co.id = oi.order_id
            GROUP BY co.id
        )
    """).fetchone()["avg_value"]

    low_stock = conn.execute("""
        SELECT name, stock FROM Product
        WHERE stock < 5
        ORDER BY stock ASC
    """).fetchall()

    sales_by_month = conn.execute("""
        SELECT strftime('%Y-%m', co.order_date) AS month,
               SUM(oi.quantity * oi.unit_price) AS monthly_revenue
        FROM CustomerOrder co
        JOIN OrderItem oi ON co.id = oi.order_id
        WHERE co.status != 'cancelled'
        GROUP BY month
        ORDER BY month
    """).fetchall()

    conn.close()

    return render_template(
        "analytics.html",
        revenue_by_category=revenue_by_category,
        top_customers=top_customers,
        never_ordered=never_ordered,
        above_average=above_average,
        avg_order_value=avg_order_value,
        low_stock=low_stock,
        sales_by_month=sales_by_month,
    )


if __name__ == "__main__":
    app.run(debug=True)
