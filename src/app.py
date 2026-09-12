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
        conn.execute("DELETE FROM Product WHERE id = ?", (product_id,))
        conn.commit()
        flash("Produit supprimé.", "success")
    except sqlite3.IntegrityError:
        flash("Impossible de supprimer ce produit : il est référencé dans au moins une commande.", "danger")
    finally:
        conn.close()
    return redirect(url_for("products"))


if __name__ == "__main__":
    app.run(debug=True)
