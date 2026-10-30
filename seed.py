"""Carga inicial idempotente del directorio entregado en el ejercicio."""
from app import companies, client

DATA = [
    ("CODALTEC", "Av. 40 # 24A - 71", "Simulación & Ciberseguridad", "300 639 8324"),
    ("SASOFTCO", "Cra 44B # 18-43 Mz D Ca 15", "ERP a Medida, Apps Mobile", "310 550 7137"),
    ("Ideas Software", "Villavicencio, Meta", "Sistemas Administrativos", "320 494 9937"),
    ("Pegasus Software", "Cra 19A # 35A - 54", "Contabilidad & Facturación POS", "313 466 7526"),
    ("Seobyte", "Villavicencio, Meta", "Desarrollo Web & E-commerce", "310 550 7137"),
    ("Software & Apps Col", "Cr 19B # 22-03 Macarena", "Apps Móviles & Web", "311 482 9001"),
    ("SPS Solutions", "Calle 4A # 17-88 Vizcaya", "Infraestructura TI & Web", "314 511 5938"),
    ("Ingesoft Orinoquía", "Calle 33A # 38-25 Barzal", "ERP & Nómina Electrónica", "(8) 670 4120"),
    ("Synergia Tech", "Cra 39 # 26C-12 7 de Agosto", "E-learning & EdTech", "321 908 4312"),
    ("SoftLlanos", "Calle 15 # 40-08 Camoa", "POS & Inventarios", "312 345 8901"),
    ("Llanotec", "Av. Circunvalar # 35-10", "Software Médico & Salud", "318 765 4321"),
    ("AgroSoft Meta", "Calle 26 Sur # 48-12", "Software Agrícola & Ganadero", "315 890 1234"),
    ("MetaDevs Lab", "Cra 38 # 33B-15 Barzal", "APIs, Cloud & SaaS", "310 987 6543"),
    ("Global Code", "Calle 15 # 37E-22 Esperanza", "E-commerce B2B / B2C", "322 123 4567"),
    ("InnovaApp Tech", "Cra 40 # 20-55 Centauros", "Apps de Logística & Domicilios", "317 654 3210"),
]

for name, address, specialty, phone in DATA:
    companies.update_one({"name": name}, {"$setOnInsert": {
        "name": name, "address": address, "specialty": specialty, "phone": phone, "website": ""
    }}, upsert=True)

print(f"Directorio listo: {companies.count_documents({})} registros en '{companies.full_name}'.")
client.close()
