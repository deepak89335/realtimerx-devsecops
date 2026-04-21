from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os

app = Flask(__name__)

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///pharmacy.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ── Models ──────────────────────────────────────────────────────────────────

class Drug(db.Model):
    __tablename__ = "drugs"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    batch_no    = db.Column(db.String(60), nullable=False, unique=True)
    quantity    = db.Column(db.Integer, nullable=False, default=0)
    unit        = db.Column(db.String(20), nullable=False, default="units")
    expiry_date = db.Column(db.Date, nullable=False)
    supplier    = db.Column(db.String(120), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "batch_no":    self.batch_no,
            "quantity":    self.quantity,
            "unit":        self.unit,
            "expiry_date": self.expiry_date.isoformat(),
            "supplier":    self.supplier,
            "created_at":  self.created_at.isoformat(),
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

LOW_STOCK_THRESHOLD = int(os.environ.get("LOW_STOCK_THRESHOLD", 10))
EXPIRY_WARNING_DAYS = int(os.environ.get("EXPIRY_WARNING_DAYS", 30))


def days_until_expiry(expiry: date) -> int:
    return (expiry - date.today()).days


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return "Pharmacy API is running"

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.route("/api/drugs", methods=["GET"])
def list_drugs():
    drugs = Drug.query.all()
    return jsonify([d.to_dict() for d in drugs])


@app.route("/api/drugs/<int:drug_id>", methods=["GET"])
def get_drug(drug_id):
    drug = Drug.query.get_or_404(drug_id)
    return jsonify(drug.to_dict())


@app.route("/api/drugs", methods=["POST"])
def add_drug():
    data = request.get_json(force=True)
    required = ["name", "batch_no", "quantity", "expiry_date"]
    missing = [f for f in required if f not in data]
    if missing:
        abort(400, description=f"Missing fields: {', '.join(missing)}")

    try:
        expiry = date.fromisoformat(data["expiry_date"])
    except ValueError:
        abort(400, description="expiry_date must be YYYY-MM-DD")

    drug = Drug(
        name        = data["name"],
        batch_no    = data["batch_no"],
        quantity    = int(data["quantity"]),
        unit        = data.get("unit", "units"),
        expiry_date = expiry,
        supplier    = data.get("supplier"),
    )
    db.session.add(drug)
    db.session.commit()
    return jsonify(drug.to_dict()), 201


@app.route("/api/drugs/<int:drug_id>", methods=["PATCH"])
def update_stock(drug_id):
    drug = Drug.query.get_or_404(drug_id)
    data = request.get_json(force=True)
    if "quantity" in data:
        drug.quantity = int(data["quantity"])
    if "supplier" in data:
        drug.supplier = data["supplier"]
    db.session.commit()
    return jsonify(drug.to_dict())


@app.route("/api/drugs/<int:drug_id>", methods=["DELETE"])
def delete_drug(drug_id):
    drug = Drug.query.get_or_404(drug_id)
    db.session.delete(drug)
    db.session.commit()
    return jsonify({"deleted": drug_id})


@app.route("/api/alerts/low-stock")
def low_stock_alerts():
    drugs = Drug.query.filter(Drug.quantity <= LOW_STOCK_THRESHOLD).all()
    return jsonify({
        "threshold": LOW_STOCK_THRESHOLD,
        "count":     len(drugs),
        "drugs":     [d.to_dict() for d in drugs],
    })


@app.route("/api/alerts/expiring-soon")
def expiring_soon():
    all_drugs = Drug.query.all()
    expiring = [
        {**d.to_dict(), "days_left": days_until_expiry(d.expiry_date)}
        for d in all_drugs
        if 0 <= days_until_expiry(d.expiry_date) <= EXPIRY_WARNING_DAYS
    ]
    return jsonify({
        "warning_days": EXPIRY_WARNING_DAYS,
        "count":        len(expiring),
        "drugs":        expiring,
    })


@app.route("/api/alerts/expired")
def expired_drugs():
    all_drugs = Drug.query.all()
    expired = [
        {**d.to_dict(), "days_overdue": abs(days_until_expiry(d.expiry_date))}
        for d in all_drugs
        if days_until_expiry(d.expiry_date) < 0
    ]
    return jsonify({"count": len(expired), "drugs": expired})


# ── Startup ───────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG", "false") == "true")
