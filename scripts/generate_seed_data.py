"""
JMEA Industry Intelligence Platform - PoC seed data generator.
Simulated members + buyers, anchored to real Jamaica reference stats.
Deterministic (seeded). Outputs: CSVs, SQLite DB, and a combined JSON for the demo dashboard.
"""
import csv, json, random, sqlite3, os

random.seed(20260711)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed-data")
os.makedirs(OUT, exist_ok=True)

PARISHES = ["Kingston", "St. Andrew", "St. Catherine", "Clarendon", "Manchester",
            "St. Elizabeth", "Westmoreland", "St. James", "Trelawny", "St. Ann",
            "St. Mary", "Portland", "St. Thomas", "Hanover"]
# rough parish centroids for map (lat, lon)
PARISH_LL = {
    "Kingston": (17.978, -76.792), "St. Andrew": (18.028, -76.75), "St. Catherine": (18.04, -77.0),
    "Clarendon": (17.96, -77.24), "Manchester": (18.04, -77.51), "St. Elizabeth": (18.05, -77.75),
    "Westmoreland": (18.22, -78.13), "St. James": (18.47, -77.92), "Trelawny": (18.35, -77.6),
    "St. Ann": (18.43, -77.2), "St. Mary": (18.36, -76.9), "Portland": (18.18, -76.45),
    "St. Thomas": (17.98, -76.35), "Hanover": (18.4, -78.13),
}

SECTORS = {
    "Agro-processing": {
        "products": ["scotch bonnet pepper sauce", "jerk seasoning", "canned ackee", "dried fruit snacks",
                     "cassava flour", "plantain chips", "coconut oil", "honey", "guava jam", "sorrel concentrate"],
        "unit": "cases/month", "cap": (800, 12000), "kwh": (4000, 60000), "energy_pct": (8, 18),
    },
    "Food & Beverage": {
        "products": ["fruit juices", "spring water", "baked goods", "spice blends", "roasted coffee",
                     "rum cream liqueur", "frozen patties", "yogurt", "sauces & marinades", "ginger beer"],
        "unit": "cases/month", "cap": (1500, 40000), "kwh": (15000, 250000), "energy_pct": (10, 22),
    },
    "Packaging": {
        "products": ["corrugated boxes", "PET bottles", "labels & shrink sleeves", "food-grade containers",
                     "paper bags", "moulded pulp trays"],
        "unit": "000 units/month", "cap": (50, 900), "kwh": (30000, 400000), "energy_pct": (14, 26),
    },
    "Furniture & Wood": {
        "products": ["hotel casegoods", "outdoor furniture", "kitchen cabinets", "mattresses",
                     "office furniture", "wooden souvenirs"],
        "unit": "pieces/month", "cap": (60, 1500), "kwh": (8000, 90000), "energy_pct": (7, 15),
    },
    "Personal Care & Chemicals": {
        "products": ["castor oil cosmetics", "soaps & body care", "household cleaners", "sanitizers",
                     "hair care products", "essential oils"],
        "unit": "cases/month", "cap": (400, 9000), "kwh": (6000, 80000), "energy_pct": (9, 17),
    },
    "Construction Inputs": {
        "products": ["concrete blocks", "PVC pipes & fittings", "roof sheeting", "paints & coatings",
                     "steel fabrication", "aggregate & mortar mixes"],
        "unit": "tonnes/month", "cap": (100, 5000), "kwh": (40000, 600000), "energy_pct": (16, 30),
    },
    "Light Manufacturing": {
        "products": ["garments & uniforms", "footwear", "electrical assemblies", "signage",
                     "plastic housewares", "candles"],
        "unit": "units/month", "cap": (1000, 30000), "kwh": (5000, 70000), "energy_pct": (8, 16),
    },
}

NAME_A = ["Blue Mahoe", "Yallahs", "Cockpit", "Liguanea", "Rio Bueno", "Bamboo Walk", "Doctor's Cave",
          "Nine Rivers", "Silver Hill", "Great Bay", "Mona Ridge", "Cane River", "Flagstaff", "Roaring River",
          "Santa Cruz", "Port Royal", "Blue Lagoon", "Dry Harbour", "Junction", "Windward", "Palisadoes",
          "Accompong", "Bull Bay", "Golden Grove", "Retreat", "Cedar Valley", "Spur Tree", "Fern Gully",
          "Black River", "Long Bay", "Treasure Beach", "Hope Valley", "Constant Spring", "Halfway Tree",
          "Bog Walk", "Ewarton", "Old Harbour", "May Pen", "Mandeville Ridge", "Lucea Bay",
          "Discovery", "Runaway", "Ocho Rios", "Annotto", "Buff Bay", "Morant", "Serge Island", "Wag Water",
          "Ferry Hill", "Caymanas", "Hellshire", "Portmore", "Stony Hill", "Papine", "Gordon Town",
          "Irish Town", "Newcastle", "Content Gap", "Mavis Bank", "Trident", "Firefly", "Galina",
          "Oracabessa", "Robins Bay", "Salt Marsh", "Martha Brae", "Duncans", "Rio Grande", "Moore Town",
          "Charles Town"]
NAME_B = {
    "Agro-processing": ["Foods", "Agro Processors", "Farm Foods", "Provisions", "Harvest Co.", "Preserves"],
    "Food & Beverage": ["Beverages", "Foods", "Bottling Co.", "Bakery Ltd", "Coffee Works", "Creamery"],
    "Packaging": ["Packaging", "Containers", "Box Works", "Print & Pack"],
    "Furniture & Wood": ["Furniture Co.", "Woodworks", "Furnishings", "Joinery"],
    "Personal Care & Chemicals": ["Botanicals", "Care Products", "Chemicals Ltd", "Naturals"],
    "Construction Inputs": ["Building Products", "Concrete Works", "Industrial Supplies", "Fabricators"],
    "Light Manufacturing": ["Manufacturing", "Industries", "Apparel Co.", "Products Ltd"],
}
CERT_POOL = ["HACCP", "FSSC 22000", "ISO 9001", "BSJ Certified", "US FDA Registered", "Organic (USDA)", "GMP"]
EXPORT_MARKETS = ["USA", "Canada", "UK", "Cayman Islands", "Trinidad & Tobago", "Barbados", "Panama", "Netherlands"]
JMD_PER_KWH = 62.0   # ~US$0.238/kWh @ ~J$156/US$ commercial blended
FX = 156.0

sector_counts = {"Agro-processing": 14, "Food & Beverage": 16, "Packaging": 8, "Furniture & Wood": 8,
                 "Personal Care & Chemicals": 9, "Construction Inputs": 8, "Light Manufacturing": 9}

used_names = set()
members = []
mid = 0
for sector, n in sector_counts.items():
    cfg = SECTORS[sector]
    for _ in range(n):
        mid += 1
        while True:
            name = f"{random.choice(NAME_A)} {random.choice(NAME_B[sector])}"
            if name not in used_names:
                used_names.add(name); break
        parish = random.choice(PARISHES)
        lat, lon = PARISH_LL[parish]
        lat += random.uniform(-0.05, 0.05); lon += random.uniform(-0.05, 0.05)
        products = random.sample(cfg["products"], k=random.randint(1, 3))
        cap = random.randint(*cfg["cap"])
        util = random.randint(45, 95)
        spare = round(cap * (100 - util) / 100)
        employees = random.choice([random.randint(5, 15), random.randint(16, 50), random.randint(51, 200), random.randint(201, 450)])
        size = "Micro" if employees <= 15 else "Small" if employees <= 50 else "Medium" if employees <= 200 else "Large"
        n_certs = random.choices([0, 1, 2, 3, 4], weights=[25, 30, 25, 15, 5])[0]
        certs = random.sample(CERT_POOL, k=n_certs)
        lead = random.choice([7, 10, 14, 21, 30, 45])
        exp_status = random.choices(["Exporting", "Export-ready", "Domestic"], weights=[30, 25, 45])[0]
        markets = random.sample(EXPORT_MARKETS, k=random.randint(1, 4)) if exp_status == "Exporting" else []
        kwh = random.randint(*cfg["kwh"])
        gen_pct = random.choices([0, 5, 10, 20, 35], weights=[40, 25, 15, 12, 8])[0]
        energy_cost_jmd = round(kwh * JMD_PER_KWH * (1 + gen_pct / 100 * 0.6))
        energy_pct = round(random.uniform(*cfg["energy_pct"]), 1)
        renewable = random.choices(["None", "Solar (partial)", "Solar + storage"], weights=[65, 28, 7])[0]

        # Export readiness subscores (0-100)
        s_cert = min(100, 20 + n_certs * 20 + (10 if "HACCP" in certs or "FSSC 22000" in certs else 0))
        s_pkg = random.randint(30, 95)
        s_log = random.randint(25, 95)
        s_qms = min(100, random.randint(20, 60) + (30 if "ISO 9001" in certs or "GMP" in certs else 0))
        s_hist = 90 if exp_status == "Exporting" else 55 if exp_status == "Export-ready" else random.randint(5, 30)
        s_capa = min(100, round((100 - util) * 1.8 + 20))
        readiness = round(0.25 * s_cert + 0.15 * s_pkg + 0.15 * s_log + 0.15 * s_qms + 0.20 * s_hist + 0.10 * s_capa)
        band = "Export Ready" if readiness >= 75 else "Near Ready" if readiness >= 55 else "Developing" if readiness >= 35 else "Early Stage"
        tier3 = random.random() < (0.75 if exp_status != "Domestic" else 0.45)

        members.append({
            "member_id": f"M{mid:03d}", "company": name, "sector": sector, "parish": parish,
            "lat": round(lat, 4), "lon": round(lon, 4), "products": "; ".join(products),
            "capacity": cap, "capacity_unit": cfg["unit"], "utilization_pct": util, "spare_capacity": spare,
            "employees": employees, "size_band": size, "certifications": "; ".join(certs) if certs else "None",
            "lead_time_days": lead, "export_status": exp_status,
            "export_markets": "; ".join(markets) if markets else "",
            "monthly_kwh": kwh, "generator_share_pct": gen_pct, "monthly_energy_cost_jmd": energy_cost_jmd,
            "energy_pct_of_prod_cost": energy_pct, "renewable_adoption": renewable,
            "score_certifications": s_cert, "score_packaging": s_pkg, "score_logistics": s_log,
            "score_quality_systems": s_qms, "score_export_history": s_hist, "score_capacity_headroom": s_capa,
            "readiness_score": readiness, "readiness_band": band,
            "matching_opt_in": tier3,
        })

# ---- Buyers / requests (tourism-heavy, per proposal) ----
buyer_rows = [
    ("B001", "Azure Sands Resort (240 rooms)", "Hotel", "St. James", "scotch bonnet pepper sauce; jerk seasoning; sauces & marinades", "Agro-processing", "HACCP", 900, "cases/month", 21),
    ("B002", "Azure Sands Resort (240 rooms)", "Hotel", "St. James", "fruit juices; ginger beer", "Food & Beverage", "HACCP", 1400, "cases/month", 14),
    ("B003", "Palm Cove Villas Group", "Hotel", "St. Ann", "baked goods; frozen patties", "Food & Beverage", "", 700, "cases/month", 7),
    ("B004", "Palm Cove Villas Group", "Hotel", "St. Ann", "outdoor furniture; hotel casegoods", "Furniture & Wood", "", 350, "pieces/month", 45),
    ("B005", "Windwave Hotels (3 properties)", "Hotel", "Westmoreland", "soaps & body care; hair care products", "Personal Care & Chemicals", "GMP", 600, "cases/month", 21),
    ("B006", "Windwave Hotels (3 properties)", "Hotel", "Westmoreland", "spring water", "Food & Beverage", "", 2500, "cases/month", 14),
    ("B007", "IslandFresh Distributors", "Distributor", "Kingston", "plantain chips; dried fruit snacks; guava jam", "Agro-processing", "US FDA Registered", 1600, "cases/month", 30),
    ("B008", "IslandFresh Distributors", "Distributor", "Kingston", "PET bottles; labels & shrink sleeves", "Packaging", "", 300, "000 units/month", 21),
    ("B009", "Ministry procurement: school furniture", "Government", "St. Catherine", "office furniture; kitchen cabinets", "Furniture & Wood", "BSJ Certified", 800, "pieces/month", 60),
    ("B010", "North Coast Highway Phase 4", "Project developer", "Trelawny", "concrete blocks; aggregate & mortar mixes", "Construction Inputs", "BSJ Certified", 2200, "tonnes/month", 30),
    ("B011", "Caribe Duty-Free Retail", "Retailer", "St. James", "roasted coffee; rum cream liqueur; wooden souvenirs", "Food & Beverage", "", 450, "cases/month", 21),
    ("B012", "US specialty grocer (export order)", "Export buyer", "USA", "scotch bonnet pepper sauce; jerk seasoning", "Agro-processing", "US FDA Registered", 2000, "cases/month", 45),
    ("B013", "Cruise port F&B concession", "Hotel", "St. James", "spice blends; sorrel concentrate; honey", "Agro-processing", "HACCP", 500, "cases/month", 14),
    ("B014", "New 400-room resort fit-out", "Project developer", "Hanover", "hotel casegoods; mattresses", "Furniture & Wood", "", 1200, "pieces/month", 90),
    ("B015", "Regional supermarket chain (CARICOM)", "Export buyer", "Trinidad & Tobago", "household cleaners; sanitizers", "Personal Care & Chemicals", "GMP", 900, "cases/month", 30),
]
buyers = [dict(zip(["request_id", "buyer", "buyer_type", "location", "products_needed", "sector",
                    "required_cert", "monthly_volume", "volume_unit", "max_lead_time_days"], r)) for r in buyer_rows]

# ---- Matching (transparent scoring, mirrors proposal capability 02) ----
def match_score(m, b):
    if m["sector"] != b["sector"]:
        return None
    need = set(p.strip() for p in b["products_needed"].split(";"))
    have = set(p.strip() for p in m["products"].split(";"))
    overlap = len(need & have)
    if overlap == 0:
        return None
    s_product = 100 * overlap / len(need)
    s_cert = 100 if (not b["required_cert"] or b["required_cert"] in m["certifications"]) else 0
    s_cap = min(100, 100 * m["spare_capacity"] / b["monthly_volume"]) if b["monthly_volume"] else 100
    s_lead = 100 if m["lead_time_days"] <= b["max_lead_time_days"] else max(0, 100 - 4 * (m["lead_time_days"] - b["max_lead_time_days"]))
    total = round(0.35 * s_product + 0.25 * s_cert + 0.25 * s_cap + 0.15 * s_lead)
    return {"request_id": b["request_id"], "member_id": m["member_id"], "company": m["company"],
            "opt_in": m["matching_opt_in"], "product_fit": round(s_product), "cert_met": s_cert == 100,
            "capacity_cover_pct": round(s_cap), "lead_time_ok": m["lead_time_days"] <= b["max_lead_time_days"],
            "match_score": total}

matches = []
for b in buyers:
    cands = [x for x in (match_score(m, b) for m in members) if x]
    cands.sort(key=lambda x: -x["match_score"])
    matches.extend(cands[:8])

# ---- Reference data (real, sourced) ----
reference = {
    "sources_note": "Real reference figures anchoring the simulated member data.",
    "jamaica_total_exports_usd_m": {"2023": 2001.8, "2024": 1867.2, "source": "STATIN via MFAFT/Jamaica Observer"},
    "manufacturing_gdp_share_pct": {"value": 8.5, "year": 2022, "source": "Do Business Jamaica / PIOJ"},
    "manufacturing_export_earnings_usd_m": {"value": 961.3, "year": 2022, "source": "Do Business Jamaica"},
    "commercial_electricity_usd_per_kwh": {"value": 0.238, "asof": "Sep 2025", "source": "GlobalPetrolPrices.com",
                                           "comparators": {"USA": 0.128, "Trinidad & Tobago": 0.05, "Dominican Republic": 0.19, "Barbados": 0.30}},
    "food_import_bill_usd_b": {"value": 1.3, "year": 2024, "hri_share_pct": 60, "substitutable_pct": "20-25",
                               "substitutable_usd_m": 350, "source": "USDA FAS / Ministry of Agriculture / Gleaner"},
    "top_export_destinations": ["USA", "Russia", "Netherlands", "Canada", "Iceland"],
    "fx_jmd_per_usd": FX,
}

# ---- Write CSVs ----
def write_csv(name, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

write_csv("members.csv", members)
write_csv("buyer_requests.csv", buyers)
write_csv("matches.csv", matches)

# ---- SQLite ----
db = os.path.join(OUT, "jmea_poc.db")
if os.path.exists(db): os.remove(db)
con = sqlite3.connect(db)
def load(table, rows):
    cols = list(rows[0].keys())
    con.execute(f"CREATE TABLE {table} ({', '.join(c + ' TEXT' for c in cols)})")
    con.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(cols))})",
                    [[str(r[c]) for c in cols] for r in rows])
load("members", members); load("buyer_requests", buyers); load("matches", matches)
con.commit(); con.close()

# ---- Combined JSON for dashboard embedding ----
with open(os.path.join(OUT, "seed_data.json"), "w", encoding="utf-8") as f:
    json.dump({"members": members, "buyers": buyers, "matches": matches, "reference": reference}, f, indent=1)

print(f"members={len(members)} buyers={len(buyers)} matches={len(matches)}")
print("readiness bands:", {b: sum(1 for m in members if m['readiness_band'] == b) for b in ['Export Ready','Near Ready','Developing','Early Stage']})
print("sector totals:", {s: sum(1 for m in members if m['sector'] == s) for s in sector_counts})
avg_e = sum(m['energy_pct_of_prod_cost'] for m in members) / len(members)
print(f"avg energy % of prod cost: {avg_e:.1f}")
