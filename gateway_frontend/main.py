import os
from typing import Optional
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(
    title="MAD FASHION — API Gateway & Luxury Storefront UI",
    description="Единый шлюз (API Gateway) и веб-интерфейс микросервисной системы бутика одежды MAD FASHION",
    version="2.0.0",
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
    sort: Optional[str] = None,
):
    params = {k: v for k, v in {
        "search": search,
        "category": category,
        "brand": brand,
        "color": color,
        "gender": gender,
        "size": size,
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
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/catalog/filters")
def proxy_get_filters():
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{CATALOG_URL}/meta/filters")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/warehouse/batches")
def proxy_get_batches():
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{WAREHOUSE_URL}/batches")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/warehouse/batches")
async def proxy_create_batch(request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{WAREHOUSE_URL}/batches", json=body)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/warehouse/stock-summary")
def proxy_stock_summary():
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{WAREHOUSE_URL}/stock/summary")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/warehouse/alerts")
def proxy_alerts():
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{WAREHOUSE_URL}/alerts/expiring")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/warehouse/writeoffs")
def proxy_get_writeoffs(reason: Optional[str] = None):
    params = {"reason": reason} if reason else {}
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{WAREHOUSE_URL}/writeoffs", params=params)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/warehouse/writeoffs")
async def proxy_create_writeoff(request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{WAREHOUSE_URL}/writeoffs", json=body)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/warehouse/writeoffs/auto-expired")
def proxy_auto_expired():
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{WAREHOUSE_URL}/writeoffs/auto-expired")
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/orders")
def proxy_get_orders(start_date: Optional[str] = None, end_date: Optional[str] = None):
    params = {k: v for k, v in {"start_date": start_date, "end_date": end_date}.items() if v}
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{ORDER_URL}/orders", params=params)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/orders")
async def proxy_create_order(request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{ORDER_URL}/orders", json=body)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/api/orders/checkout")
async def proxy_checkout(request: Request):
    body = await request.json()
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{ORDER_URL}/orders/checkout", json=body)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/analytics/financial")
def proxy_financial_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tax_rate: float = 6.0,
):
    params = {"tax_rate": tax_rate}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{ANALYTICS_URL}/reports/financial", params=params)
        return JSONResponse(status_code=r.status_code, content=r.json())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
