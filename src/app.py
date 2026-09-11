from flask import Flask
from db import get_db

app = Flask(__name__)


@app.route("/")
def index():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) AS n FROM Product").fetchone()["n"]
    conn.close()
    return f"Connexion OK — {count} produits en base."


if __name__ == "__main__":
    app.run(debug=True)
