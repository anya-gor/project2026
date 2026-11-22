import json
import os
import uuid
from datetime import date, timedelta
from typing import List, Optional
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AURA Wear — Order & Sales Microservice",
    description="Микросервис оформления заказов и фиксации продаж с учетом себестоимости партий поставщиков",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://127.0.0.1:8001")
WAREHOUSE_SERVICE_URL = os.getenv("WAREHOUSE_SERVICE_URL", "http://127.0.0.1:8002")
DATA_FILE = os.path.join(os.path.dirname(__file__), "orders_db.json")


class OrderCreate(BaseModel):
    product_id: str = Field(..., description="ID модели одежды")
    size: str = Field(..., description="Выбранный размер")
    quantity: int = Field(..., gt=0, description="Количество единиц")
    customer_name: str = Field(default="Розничный покупатель", description="Имя покупателя")


def generate_seed_orders() -> List[dict]:
    today = date.today()
    return [
        {
            "order_id": "ORD-901",
            "product_id": "prod-1",
            "product_name": "Оверсайз худи «Eclipse Heavy»",
            "size": "M",
            "quantity": 3,
            "unit_retail_price": 6900.0,
            "total_revenue": 20700.0,
            "total_supplier_cost": 7200.0,
            "gross_profit": 13500.0,
            "customer_name": "Алексей Смирнов",
            "sale_date": (today - timedelta(days=6)).isoformat(),
            "allocations": [
                {
                    "batch_id": "BATCH-101",
                    "supplier_name": "ООО «Фабрика ТекстильПро»",
                    "quantity": 3,
                    "unit_purchase_price": 2400.0,
                    "subtotal_cost": 7200.0,
                }
            ],
        },
        {
            "order_id": "ORD-902",
            "product_id": "prod-2",
            "product_name": "Футболка «Core Boxy Fit»",
            "size": "M",
            "quantity": 4,
            "unit_retail_price": 3200.0,
            "total_revenue": 12800.0,
            "total_supplier_cost": 3800.0,
            "gross_profit": 9000.0,
            "customer_name": "Мария Волкова",
            "sale_date": (today - timedelta(days=4)).isoformat(),
            "allocations": [
                {
                    "batch_id": "BATCH-104",
                    "supplier_name": "АО «CottonCraft Иваново»",
                    "quantity": 4,
                    "unit_purchase_price": 950.0,
                    "subtotal_cost": 3800.0,
                }
            ],
        },
        {
            "order_id": "ORD-903",
            "product_id": "prod-3",
            "product_name": "Джинсы Wide-Leg «Raw Indigo»",
            "size": "M",
            "quantity": 2,
            "unit_retail_price": 8500.0,
            "total_revenue": 17000.0,
            "total_supplier_cost": 6600.0,
            "gross_profit": 10400.0,
            "customer_name": "Дмитрий Орлов",
            "sale_date": (today - timedelta(days=2)).isoformat(),
            "allocations": [
                {
                    "batch_id": "BATCH-106",
                    "supplier_name": "Фабрика «DenimFactory Юг»",
                    "quantity": 2,
                    "unit_purchase_price": 3300.0,
                    "subtotal_cost": 6600.0,
                }
            ],
        },
        {
            "order_id": "ORD-904",
            "product_id": "prod-4",
            "product_name": "Бомбер «Cyber Shell Waterproof»",
            "size": "L",
            "quantity": 1,
            "unit_retail_price": 12900.0,
            "total_revenue": 12900.0,
            "total_supplier_cost": 5200.0,
            "gross_profit": 7700.0,
            "customer_name": "Екатерина Лебедева",
            "sale_date": (today - timedelta(days=1)).isoformat(),
            "allocations": [
                {
                    "batch_id": "BATCH-107",
                    "supplier_name": "TechWear Manufacturing",
                    "quantity": 1,
                    "unit_purchase_price": 5200.0,
                    "subtotal_cost": 5200.0,
                }
            ],
        },
    ]


def load_orders() -> List[dict]:
    if not os.path.exists(DATA_FILE):
        seed = generate_seed_orders()
        save_orders(seed)
        return seed
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_orders(orders: List[dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "order-service", "port": 8003}


@app.get("/orders")
def list_orders(
    start_date: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
):
    orders = load_orders()
    result = []
    for o in orders:
        if start_date and o["sale_date"] < start_date:
            continue
        if end_date and o["sale_date"] > end_date:
            continue
        result.append(o)
    return result


@app.post("/orders", status_code=201)
def create_order(payload: OrderCreate):
    """
    Межсервисная операция оформления заказа:
    1. Проверяет модель и розничную цену в Catalog Service (:8001)
    2. Списывает размер по FIFO в Warehouse Service (:8002) и получает закупочную себестоимость партий
    3. Фиксирует продажу и рассчитывает прибыль
    """
    with httpx.Client(timeout=10.0) as client:
        # 1. Запрос в Catalog Service
        try:
            cat_resp = client.get(f"{CATALOG_SERVICE_URL}/products/{payload.product_id}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Catalog Service недоступен: {e}")

        if cat_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Модель одежды не найдена в Catalog Service")
        product = cat_resp.json()

        # 2. Запрос в Warehouse Service на списание по FIFO
        try:
            wh_resp = client.post(
                f"{WAREHOUSE_SERVICE_URL}/stock/deduct-sale",
                json={
                    "product_id": payload.product_id,
                    "size": payload.size.upper(),
                    "quantity": payload.quantity,
                },
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Warehouse Service недоступен: {e}")

        if wh_resp.status_code != 200:
            err_detail = wh_resp.json().get("detail", "Ошибка списания со склада")
            raise HTTPException(status_code=wh_resp.status_code, detail=err_detail)

        deduction = wh_resp.json()

    unit_price = float(product["retail_price"])
    total_revenue = round(unit_price * payload.quantity, 2)
    total_supplier_cost = float(deduction["total_supplier_cost"])
    gross_profit = round(total_revenue - total_supplier_cost, 2)

    new_order = {
        "order_id": f"ORD-{uuid.uuid4().hex[:5].upper()}",
        "product_id": payload.product_id,
        "product_name": product["name"],
        "size": payload.size.upper(),
        "quantity": payload.quantity,
        "unit_retail_price": unit_price,
        "total_revenue": total_revenue,
        "total_supplier_cost": total_supplier_cost,
        "gross_profit": gross_profit,
        "customer_name": payload.customer_name or "Розничный покупатель",
        "sale_date": date.today().isoformat(),
        "allocations": deduction["allocations"],
    }

    orders = load_orders()
    orders.insert(0, new_order)
    save_orders(orders)
    return new_order


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
