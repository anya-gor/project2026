import json
import os
import sys
import uuid
from datetime import date, timedelta
from typing import List, Optional
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from database.mysql_client import mysql_load_orders, mysql_save_orders

app = FastAPI(
    title="MONROE — Order & Checkout Microservice",
    description="Микросервис корзины, оформления заказов (BYN) и фиксации себестоимости партий поставщиков",
    version="2.0.0",
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
    product_id: str
    size: str
    quantity: int = Field(..., gt=0)
    customer_name: str = Field(default="Клиент бутика MONROE")
    city: str = Field(default="Минск, Минская область, Беларусь")
    delivery_method: str = Field(default="Доставка курьером")
    payment_method: str = Field(default="Картой при получении")
    email: str = Field(default="")
    phone: str = Field(default="")
    address: str = Field(default="")
    comment: str = Field(default="")
    discount_percent: float = Field(default=0.0, ge=0.0, le=50.0)


class CheckoutCartItem(BaseModel):
    product_id: str
    size: str
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    items: List[CheckoutCartItem]
    city: str = Field(default="Минск, Минская область, Беларусь")
    delivery_method: str = Field(default="Доставка курьером")
    payment_method: str = Field(default="Картой при получении")
    customer_name: str = Field(default="Покупатель MONROE")
    email: str = Field(default="client@monroe.by")
    phone: str = Field(default="+375 29 000-00-00")
    street: str = Field(default="пр. Победителей")
    house: str = Field(default="65")
    apartment: str = Field(default="")
    floor: str = Field(default="")
    comment: str = Field(default="")
    coupon_code: str = Field(default="")


class ReturnRequestPayload(BaseModel):
    reason: str = Field(default="Не подошел размер", description="Причина возврата")


class ReturnDecisionPayload(BaseModel):
    decision: str = Field(..., description="APPROVE (Одобрить) или REJECT (Отклонить)")


def generate_seed_orders() -> List[dict]:
    today = date.today()
    return [
        {
            "order_id": "ORD-701",
            "product_id": "prod-1",
            "product_name": "PATRIZIA PEPE — Темно-синее мини-платье",
            "size": "S",
            "quantity": 2,
            "unit_retail_price": 1050.0,
            "total_revenue": 2100.0,
            "total_supplier_cost": 840.0,
            "gross_profit": 1260.0,
            "customer_name": "Алина Ковалева",
            "city": "Минск, Минская область, Беларусь",
            "delivery_method": "Доставка курьером",
            "payment_method": "Онлайн картой на сайте",
            "sale_date": (today - timedelta(days=5)).isoformat(),
            "allocations": [
                {
                    "batch_id": "BATCH-201",
                    "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
                    "quantity": 2,
                    "unit_purchase_price": 420.0,
                    "subtotal_cost": 840.0,
                }
            ],
        },
        {
            "order_id": "ORD-702",
            "product_id": "prod-2",
            "product_name": "GIUSEPPE DI MORABITO — Двубортное черное приталенное пальто",
            "size": "S",
            "quantity": 1,
            "unit_retail_price": 3850.0,
            "total_revenue": 3850.0,
            "total_supplier_cost": 1650.0,
            "gross_profit": 2200.0,
            "customer_name": "Виктория Савицкая",
            "city": "Минск, Минская область, Беларусь",
            "delivery_method": "Самовывоз",
            "payment_method": "Картой при получении",
            "sale_date": (today - timedelta(days=3)).isoformat(),
            "allocations": [
                {
                    "batch_id": "BATCH-205",
                    "supplier_name": "Morabito Atelier Milano",
                    "quantity": 1,
                    "unit_purchase_price": 1650.0,
                    "subtotal_cost": 1650.0,
                }
            ],
        },
        {
            "order_id": "ORD-703",
            "product_id": "prod-5",
            "product_name": "GIUSEPPE DI MORABITO — Черные брюки-палаццо с защипами",
            "size": "S",
            "quantity": 2,
            "unit_retail_price": 1850.0,
            "total_revenue": 3700.0,
            "total_supplier_cost": 1560.0,
            "gross_profit": 2140.0,
            "customer_name": "Дарья Романова",
            "city": "Минск, Минская область, Беларусь",
            "delivery_method": "Доставка курьером",
            "payment_method": "Экспресс Платежи - ЕРИП",
            "sale_date": (today - timedelta(days=1)).isoformat(),
            "allocations": [
                {
                    "batch_id": "BATCH-209",
                    "supplier_name": "EuroFashion Distribution (Милан)",
                    "quantity": 2,
                    "unit_purchase_price": 780.0,
                    "subtotal_cost": 1560.0,
                }
            ],
        },
    ]


def load_orders() -> List[dict]:
    mysql_data = mysql_load_orders(generate_seed_orders())
    if mysql_data is not None:
        return mysql_data
    if not os.path.exists(DATA_FILE):
        seed = generate_seed_orders()
        save_orders(seed)
        return seed
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data or data[0]["order_id"].startswith("ORD-9"):
        seed = generate_seed_orders()
        save_orders(seed)
        return seed
    return data


def save_orders(orders: List[dict]):
    mysql_save_orders(orders)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "order-service", "port": 8003}


@app.get("/orders")
def list_orders(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
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
    with httpx.Client(timeout=10.0) as client:
        try:
            cat_resp = client.get(f"{CATALOG_SERVICE_URL}/products/{payload.product_id}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Catalog Service недоступен: {e}")

        if cat_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Модель одежды не найдена в Catalog Service")
        product = cat_resp.json()

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

    factor = 1.0 - (payload.discount_percent / 100.0)
    unit_price = round(float(product["retail_price"]) * factor, 2)
    total_revenue = round(unit_price * payload.quantity, 2)
    total_supplier_cost = float(deduction["total_supplier_cost"])
    gross_profit = round(total_revenue - total_supplier_cost, 2)

    full_name = f"{product.get('brand', '')} — {product['name']}".strip(" —")

    new_order = {
        "order_id": f"ORD-{uuid.uuid4().hex[:5].upper()}",
        "product_id": payload.product_id,
        "product_name": full_name,
        "size": payload.size.upper(),
        "quantity": payload.quantity,
        "unit_retail_price": unit_price,
        "total_revenue": total_revenue,
        "total_supplier_cost": total_supplier_cost,
        "gross_profit": gross_profit,
        "customer_name": payload.customer_name or "Клиент бутика MONROE",
        "city": payload.city,
        "delivery_method": payload.delivery_method,
        "payment_method": payload.payment_method,
        "email": payload.email,
        "phone": payload.phone,
        "address": payload.address,
        "comment": payload.comment,
        "sale_date": date.today().isoformat(),
        "return_status": "NONE",
        "return_reason": "",
        "allocations": deduction["allocations"],
    }

    orders = load_orders()
    orders.insert(0, new_order)
    save_orders(orders)
    return new_order


@app.post("/orders/{order_id}/return-request")
def request_order_return(order_id: str, payload: ReturnRequestPayload):
    orders = load_orders()
    for o in orders:
        if o["order_id"] == order_id:
            curr = o.get("return_status", "NONE")
            if curr == "RETURN_APPROVED":
                raise HTTPException(status_code=400, detail="Возврат по этому заказу уже одобрен")
            o["return_status"] = "RETURN_REQUESTED"
            o["return_reason"] = payload.reason
            save_orders(orders)
            return o
    raise HTTPException(status_code=404, detail="Заказ не найден")


@app.post("/orders/{order_id}/return-decision")
def decide_order_return(order_id: str, payload: ReturnDecisionPayload):
    orders = load_orders()
    for o in orders:
        if o["order_id"] == order_id:
            decision = payload.decision.upper()
            if decision == "APPROVE":
                reason = o.get("return_reason", "Не подошел размер")
                is_defect = "брак" in reason.lower()
                with httpx.Client(timeout=10.0) as client:
                    try:
                        client.post(
                            f"{WAREHOUSE_SERVICE_URL}/stock/return-item",
                            json={
                                "product_id": o["product_id"],
                                "size": o["size"],
                                "quantity": o["quantity"],
                                "is_defect": is_defect,
                            },
                        )
                    except Exception:
                        pass
                o["return_status"] = "RETURN_APPROVED"
            else:
                o["return_status"] = "RETURN_REJECTED"
            save_orders(orders)
            return o
    raise HTTPException(status_code=404, detail="Заказ не найден")


@app.post("/orders/checkout", status_code=201)
def checkout_cart(payload: CheckoutRequest):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    discount = 10.0 if payload.coupon_code.strip().upper() in ["MAD10", "SALE10", "VIP10"] else 0.0
    address_str = f"{payload.street}, д. {payload.house}"
    if payload.apartment:
        address_str += f", кв. {payload.apartment}"

    created_orders = []
    for item in payload.items:
        order_obj = create_order(
            OrderCreate(
                product_id=item.product_id,
                size=item.size,
                quantity=item.quantity,
                customer_name=payload.customer_name,
                city=payload.city,
                delivery_method=payload.delivery_method,
                payment_method=payload.payment_method,
                email=payload.email,
                phone=payload.phone,
                address=address_str,
                comment=payload.comment,
                discount_percent=discount,
            )
        )
        created_orders.append(order_obj)

    return {
        "checkout_status": "SUCCESS",
        "orders_created": len(created_orders),
        "discount_applied_percent": discount,
        "total_revenue_byn": round(sum(o["total_revenue"] for o in created_orders), 2),
        "total_supplier_cost_byn": round(sum(o["total_supplier_cost"] for o in created_orders), 2),
        "orders": created_orders,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
