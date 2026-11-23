import json
import os
from datetime import date, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(
    title="MAD FASHION — API Gateway & Luxury Storefront UI",
    description="Единый шлюз (API Gateway), сервис профилей/авторизации и веб-интерфейс бутика одежды MAD FASHION",
    version="3.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CATALOG_URL = os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:8001")
WAREHOUSE_URL = os.getenv("WAREHOUSE_SERVICE_URL", "http://127.0.0.1:8002")
ORDER_URL = os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8003")
ANALYTICS_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://127.0.0.1:8004")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users_db.json")

DEFAULT_USERS = [
    {
        "login": "375291111111",
        "country": "Беларусь",
        "password": "admin123",
        "name": "Администратор MAD FASHION",
        "email": "admin@madfashion.by",
        "role": "admin",
        "addresses": [
            {"id": "addr-adm", "text": "г. Минск, пр. Победителей, д. 65 (Салон MAD FASHION)", "is_primary": True},
        ],
    },
    {
        "login": "admin",
        "country": "Беларусь",
        "password": "admin123",
        "name": "Администратор MAD FASHION",
        "email": "admin@madfashion.by",
        "role": "admin",
        "addresses": [
            {"id": "addr-adm", "text": "г. Минск, пр. Победителей, д. 65 (Салон MAD FASHION)", "is_primary": True},
        ],
    },
    {
        "login": "375445658384",
        "country": "Беларусь",
        "password": "123",
        "name": "Анна Ковалева",
        "email": "client@madfashion.by",
        "role": "user",
        "addresses": [
            {"id": "addr-1", "text": "г. Минск, пр. Победителей, д. 65, кв. 12", "is_primary": True},
            {"id": "addr-2", "text": "г. Минск, ул. М. Танка, д. 69, кв. 5", "is_primary": False},
        ],
    },
]


def load_users():
    if not os.path.exists(USERS_FILE):
        save_users(DEFAULT_USERS)
        return DEFAULT_USERS
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    has_phone_admin = any(u["login"] == "375291111111" for u in users)
    if not has_phone_admin:
        save_users(DEFAULT_USERS)
        return DEFAULT_USERS
    return users


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/auth/login")
async def auth_login(request: Request):
    body = await request.json()
    raw_login = str(body.get("login", "")).strip()
    digits_only = "".join(ch for ch in raw_login if ch.isdigit())
    login = digits_only if len(digits_only) >= 7 else raw_login
    password = str(body.get("password", "")).strip()
    country = body.get("country", "Беларусь")

    if not login:
        raise HTTPException(status_code=400, detail="Введите номер телефона")

    users = load_users()
    for u in users:
        if u["login"].lower() == login.lower() or u["login"].lower() == raw_login.lower():
            if u["password"] != password:
                raise HTTPException(status_code=401, detail="Неверный номер телефона или пароль")
            return {"status": "ok", "user": u}

    new_user = {
        "login": login,
        "country": country,
        "password": password or "123",
        "name": login,
        "email": f"{login}@madfashion.by",
        "role": "user",
        "addresses": [
            {"id": "addr-1", "text": "г. Минск, пр. Победителей, д. 65", "is_primary": True},
        ],
    }
    users.append(new_user)
    save_users(users)
    return {"status": "ok", "user": new_user}


@app.post("/api/auth/register")
async def auth_register(request: Request):
    body = await request.json()
    raw_login = str(body.get("login", "")).strip()
    digits_only = "".join(ch for ch in raw_login if ch.isdigit())
    login = digits_only if len(digits_only) >= 7 else raw_login
    password = str(body.get("password", "")).strip()
    country = body.get("country", "Беларусь")
    name = str(body.get("name", "")).strip() or login
    email = str(body.get("email", "")).strip() or f"{login}@madfashion.by"

    if not login or not password:
        raise HTTPException(status_code=400, detail="Заполните номер телефона и пароль")

    users = load_users()
    for u in users:
        if u["login"].lower() == login.lower():
            raise HTTPException(status_code=400, detail="Пользователь с таким номером телефона уже зарегистрирован")

    new_user = {
        "login": login,
        "country": country,
        "password": password,
        "name": name,
        "email": email,
        "role": "user",
        "addresses": [
            {"id": "addr-1", "text": "г. Минск, пр. Победителей, д. 65", "is_primary": True},
        ],
    }
    users.append(new_user)
    save_users(users)
    return {"status": "ok", "user": new_user}


@app.get("/api/system-status")
def check_microservices_health():
    services = [
        {"name": "Catalog Service", "code": "catalog", "url": f"{CATALOG_URL}/health", "port": 8001},
        {"name": "Warehouse Service", "code": "warehouse", "url": f"{WAREHOUSE_URL}/health", "port": 8002},
        {"name": "Order Service", "code": "order", "url": f"{ORDER_URL}/health", "port": 8003},
        {"name": "Analytics Service", "code": "analytics", "url": f"{ANALYTICS_URL}/health", "port": 8004},
    ]
    results = []
    with httpx.Client(timeout=2.5) as client:
        for s in services:
            try:
                r = client.get(s["url"])
                online = r.status_code == 200
            except Exception:
                online = False
            results.append({
                "name": s["name"],
                "code": s["code"],
                "port": s["port"],
                "online": online,
            })
    return {"gateway": "online", "services": results}


@app.get("/api/catalog/products")
def proxy_get_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    color: Optional[str] = None,
    gender: Optional[str] = None,
    size: Optional[str] = None,
    only_new: Optional[bool] = None,
    sort: Optional[str] = None,
):
    params = {k: v for k, v in {
        "search": search,
        "category": category,
        "brand": brand,
        "color": color,
        "gender": gender,
        "size": size,
        "only_new": only_new,
        "sort": sort,
    }.items() if v is not None and v != ""}
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{CATALOG_URL}/products", params=params)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/catalog/products/{product_id}")
def proxy_get_product_detail(product_id: str):
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{CATALOG_URL}/products/{product_id}")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/catalog/products")
async def proxy_create_product(request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{CATALOG_URL}/products", json=body)
        created = r.json()
        if r.status_code == 201 and "id" in created:
            exp_date = (date.today() + timedelta(days=90)).isoformat()
            for sz in created.get("sizes", ["S", "M"]):
                try:
                    client.post(
                        f"{WAREHOUSE_URL}/batches",
                        json={
                            "product_id": created["id"],
                            "product_name": f"{created.get('brand', '')} — {created['name']}",
                            "size": sz,
                            "supplier_name": "Официальная поставка бутика MAD FASHION",
                            "purchase_price": round(float(created["retail_price"]) * 0.45, 2),
                            "quantity": 5,
                            "expiry_date": exp_date,
                        },
                    )
                except Exception:
                    pass
        return JSONResponse(status_code=r.status_code, content=created)


@app.patch("/api/catalog/products/{product_id}")
async def proxy_update_product_price(product_id: str, request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.patch(f"{CATALOG_URL}/products/{product_id}", json=body)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.delete("/api/catalog/products/{product_id}")
def proxy_delete_product(product_id: str):
    with httpx.Client(timeout=10.0) as client:
        r = client.delete(f"{CATALOG_URL}/products/{product_id}")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/warehouse/stock-summary")
def proxy_stock_summary():
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{WAREHOUSE_URL}/stock/summary")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/orders")
def proxy_get_orders():
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{ORDER_URL}/orders")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/orders/checkout")
async def proxy_checkout(request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{ORDER_URL}/orders/checkout", json=body)
        return JSONResponse(status_code=r.status_code, content=r.json())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
