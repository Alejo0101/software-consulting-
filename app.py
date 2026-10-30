import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()
app = Flask(__name__)
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=2500)
db = client[os.getenv("MONGODB_DATABASE", "directorio_software")]
companies = db["casas"]
companies.create_index("name")


def serialize(doc):
    return {"id": str(doc["_id"]), "name": doc["name"], "address": doc["address"],
            "specialty": doc["specialty"], "phone": doc["phone"], "website": doc.get("website", "")}


def clean_payload(data):
    fields = ("name", "address", "specialty", "phone", "website")
    result = {key: str(data.get(key, "")).strip() for key in fields}
    for key in fields[:4]:
        if not result[key]:
            return None, f"El campo {key} es obligatorio."
    if result["website"]:
        parsed = urlparse(result["website"])
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None, "El sitio web debe comenzar con http:// o https://."
    return result, None


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    try:
        client.admin.command("ping")
        return jsonify({"ok": True, "database": db.name})
    except PyMongoError:
        return jsonify({"ok": False, "message": "No se pudo conectar con MongoDB."}), 503


@app.get("/api/companies")
def list_companies():
    query = request.args.get("q", "").strip()
    regex = re.escape(query)
    cursor = companies.find({"name": {"$regex": regex, "$options": "i"}} if query else {}).sort("name", 1)
    return jsonify([serialize(doc) for doc in cursor])


@app.post("/api/companies")
def create_company():
    data, error = clean_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    result = companies.insert_one(data)
    return jsonify(serialize(companies.find_one({"_id": result.inserted_id}))), 201


@app.put("/api/companies/<company_id>")
def update_company(company_id):
    from bson import ObjectId
    if not ObjectId.is_valid(company_id):
        return jsonify({"error": "Identificador no válido."}), 400
    data, error = clean_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({"error": error}), 400
    result = companies.find_one_and_update({"_id": ObjectId(company_id)}, {"$set": data}, return_document=True)
    if not result:
        return jsonify({"error": "Casa desarrolladora no encontrada."}), 404
    return jsonify(serialize(result))


@app.delete("/api/companies/<company_id>")
def delete_company(company_id):
    from bson import ObjectId
    if not ObjectId.is_valid(company_id):
        return jsonify({"error": "Identificador no válido."}), 400
    result = companies.delete_one({"_id": ObjectId(company_id)})
    if not result.deleted_count:
        return jsonify({"error": "Casa desarrolladora no encontrada."}), 404
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
