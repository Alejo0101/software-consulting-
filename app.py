import os
import re
import socket
import ipaddress
import json
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import requests
from bs4 import BeautifulSoup

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


def is_public_host(host):
    """Evita que el lector de URLs acceda a localhost o redes privadas."""
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
        return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)
    except (OSError, ValueError):
        return False


def read_public_page(url, expected_host):
    """Lee HTML público limitado, siguiendo como máximo una redirección del mismo host."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    if parsed.hostname.lower() != expected_host.lower() or not is_public_host(parsed.hostname):
        return None

    response = requests.get(
        url,
        timeout=(4, 7),
        allow_redirects=False,
        headers={"User-Agent": "Mozilla/5.0 (compatible; DirectorioSoftware/1.0)"},
        stream=True,
    )
    if response.is_redirect:
        next_url = urljoin(url, response.headers.get("Location", ""))
        response.close()
        redirected = urlparse(next_url)
        same_site = (
            redirected.hostname
            and (
                redirected.hostname.lower() == expected_host.lower()
                or redirected.hostname.lower().endswith("." + expected_host.lower())
                or expected_host.lower().endswith("." + redirected.hostname.lower())
            )
        )
        if (
            redirected.scheme not in ("http", "https")
            or not same_site
            or not is_public_host(redirected.hostname)
        ):
            return None
        response = requests.get(
            next_url,
            timeout=(4, 7),
            allow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DirectorioSoftware/1.0)"},
            stream=True,
        )

    response.raise_for_status()
    if "html" not in response.headers.get("Content-Type", "").lower():
        response.close()
        return None

    chunks = []
    size = 0
    for chunk in response.iter_content(8192):
        size += len(chunk)
        if size > 1_000_000:
            break
        chunks.append(chunk)
    response.close()
    return BeautifulSoup(b"".join(chunks), "html.parser")


def find_business(value):
    """Encuentra Organization/LocalBusiness donde sea que esté anidado en JSON-LD."""
    if isinstance(value, list):
        for item in value:
            found = find_business(item)
            if found:
                return found
    elif isinstance(value, dict):
        kind = value.get("@type", "")
        if isinstance(kind, list):
            kind = " ".join(str(item) for item in kind)
        if any(term in str(kind).lower() for term in (
            "organization", "localbusiness", "corporation", "professionalservice"
        )):
            return value
        for child in value.values():
            if isinstance(child, (dict, list)):
                found = find_business(child)
                if found:
                    return found
    return None


def get_structured_business(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            business = find_business(json.loads(script.string or script.get_text()))
        except (json.JSONDecodeError, TypeError):
            continue
        if business:
            address = business.get("address", {})
            if isinstance(address, dict):
                parts = ("streetAddress", "addressLocality", "addressRegion", "postalCode")
                address = ", ".join(
                    str(address.get(key, "")).strip()
                    for key in parts if address.get(key)
                )
            elif not isinstance(address, str):
                address = ""
            return {
                "name": str(business.get("name", "")).strip(),
                "phone": str(business.get("telephone", "")).strip(),
                "address": address.strip(),
            }
    return {}


def extract_contact_details(soup):
    details = {"phone": "", "address": ""}

    # Microdatos, etiquetas <address> y enlaces tel: suelen sobrevivir a layouts distintos.
    phone_link = soup.select_one('a[href^="tel:"]')
    if phone_link:
        details["phone"] = phone_link.get("href", "")[4:].strip()
        if not details["phone"]:
            details["phone"] = phone_link.get_text(" ", strip=True)

    address_node = soup.select_one(
        '[itemprop="address"], address, [class*="address" i], [id*="address" i]'
    )
    if address_node:
        details["address"] = address_node.get_text(" ", strip=True)

    # Busca etiquetas explícitas como "Dirección: ..." en páginas de contacto.
    text = soup.get_text("\n", strip=True)
    if not details["address"]:
        match = re.search(
            r"(?:direcci[oó]n|address|ubicaci[oó]n|location)\s*[:\-]?\s*([^\n]{6,150})",
            text,
            re.IGNORECASE,
        )
        if match:
            details["address"] = match.group(1).strip(" :-|·")

    # Teléfonos colombianos móviles o fijos; se usa solo como respaldo.
    if not details["phone"]:
        match = re.search(
            r"(?<!\d)(?:\+?57[\s().-]*)?(?:3\d{2}[\s().-]?\d{3}[\s().-]?\d{4}|60[1-8][\s().-]?\d{3}[\s().-]?\d{4}|\(?[1-8]\)?[\s().-]*\d{3}[\s.-]?\d{4}|[1-8]\d{2}[\s().-]?\d{4})(?!\d)",
            text,
        )
        if match:
            details["phone"] = match.group(0).strip()

    return details


@app.post("/api/preview-url")
def preview_url():
    raw_url = (request.get_json(silent=True) or {}).get("url", "").strip()
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return jsonify({"error": "Escribe una URL completa que comience con http:// o https://."}), 400
    if parsed.username or parsed.password:
        return jsonify({"error": "La URL no puede incluir credenciales."}), 400
    if not is_public_host(parsed.hostname):
        return jsonify({"error": "No se puede consultar una dirección local o privada."}), 400

    try:
        host = parsed.hostname
        home_soup = read_public_page(raw_url, host)
        if not home_soup:
            return jsonify({"error": "La página no devolvió contenido HTML."}), 415

        pages = [home_soup]
        # Muchos sitios ponen dirección y teléfono en una subpágina de contacto.
        contact_links = []
        for link in home_soup.select("a[href]"):
            label = " ".join((link.get_text(" ", strip=True), link.get("href", ""))).lower()
            if any(word in label for word in (
                "contact", "contacto", "contáct", "ubicacion", "ubicación", "location", "about", "nosotros"
            )):
                candidate = urljoin(raw_url, link.get("href", ""))
                if urlparse(candidate).hostname and urlparse(candidate).hostname.lower() == host.lower():
                    if candidate not in contact_links and candidate != raw_url:
                        contact_links.append(candidate)
            if len(contact_links) >= 4:
                break

        for contact_url in contact_links:
            try:
                page = read_public_page(contact_url, host)
                if page:
                    pages.append(page)
            except requests.RequestException:
                continue
    except requests.RequestException:
        return jsonify({"error": "No se pudo leer el sitio. Verifica la URL o completa la ficha manualmente."}), 502

    home = home_soup

    def meta(soup, *selectors):
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                value = element.get("content", "").strip()
                if value:
                    return value
        return ""

    result = {
        "name": meta(home, 'meta[property="og:site_name"]', 'meta[name="application-name"]'),
        "specialty": meta(home, 'meta[name="description"]', 'meta[property="og:description"]'),
        "address": "",
        "phone": "",
    }
    if not result["name"] and home.title:
        result["name"] = home.title.get_text(" ", strip=True).split(" | ")[0].split(" — ")[0]

    for page in pages:
        structured = get_structured_business(page)
        extracted = extract_contact_details(page)
        for field in ("name", "address", "phone"):
            result[field] = result[field] or structured.get(field, "") or extracted.get(field, "")

    return jsonify(result)


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
