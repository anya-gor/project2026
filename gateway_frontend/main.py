import os
from datetime import date, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(
    title="MAD FASHION — API Gateway & Luxury Storefront UI",
    description="Единый шлюз (API Gateway) и веб-интерфейс микросервисной системы бутика одежды MAD FASHION",
    version="3.0.0",
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


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


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
        # Автоматически регистрируем стартовый остаток в Warehouse Service, чтобы товар можно было сразу купить
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


@app.post("/api/orders/checkout")
async def proxy_checkout(request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{ORDER_URL}/orders/checkout", json=body)
        return JSONResponse(status_code=r.status_code, content=r.json())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
