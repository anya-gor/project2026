import json
import os
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AURA Wear — Warehouse & Batches Microservice",
    description="Микросервис складского учета партий от поставщиков, контроля сроков годности/сезона и списаний",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "warehouse_db.json")
EXPIRING_SOON_DAYS = 14


class BatchCreate(BaseModel):
    product_id: str = Field(..., description="ID модели из каталога")
    product_name: str = Field(..., description="Название модели одежды")
    size: str = Field(..., description="Размер (XS, S, M, L, XL, ONE SIZE)")
    supplier_name: str = Field(..., description="Поставщик / Швейная фабрика")
    purchase_price: float = Field(..., gt=0, description="Закупочная цена за 1 ед. у поставщика (руб.)")
    quantity: int = Field(..., gt=0, description="Количество поступивших единиц")
    arrival_date: Optional[str] = Field(None, description="Дата поступления (YYYY-MM-DD)")
    expiry_date: str = Field(..., description="Срок годности / окончания сезонной реализации (YYYY-MM-DD)")


class SaleDeductRequest(BaseModel):
    product_id: str
    size: str
    quantity: int = Field(..., gt=0)


class WriteOffRequest(BaseModel):
    batch_id: str
    quantity: int = Field(..., gt=0)
    reason: str = Field(
        default="EXPIRED",
        description="Причина списания: EXPIRED (Истечение срока годности/сезона) или DEFECT (Порча / Брак)",
    )
    comment: Optional[str] = Field(default="")


def generate_seed_data() -> dict:
    today = date.today()
    d_minus_25 = (today - timedelta(days=25)).isoformat()
    d_minus_15 = (today - timedelta(days=15)).isoformat()
    d_minus_10 = (today - timedelta(days=10)).isoformat()
    d_minus_5 = (today - timedelta(days=5)).isoformat()

    exp_valid_1 = (today + timedelta(days=60)).isoformat()
    exp_valid_2 = (today + timedelta(days=45)).isoformat()
    exp_soon_1 = (today + timedelta(days=5)).isoformat()
    exp_soon_2 = (today + timedelta(days=9)).isoformat()
    exp_expired_1 = (today - timedelta(days=3)).isoformat()
    exp_expired_2 = (today - timedelta(days=8)).isoformat()

    batches = [
        # Партия 1 и Партия 2 одного и того же худи M от РАЗНЫХ поставщиков по РАЗНОЙ закупочной цене
        {
            "batch_id": "BATCH-101",
            "product_id": "prod-1",
            "product_name": "Оверсайз худи «Eclipse Heavy»",
            "size": "M",
            "supplier_name": "ООО «Фабрика ТекстильПро»",
            "purchase_price": 2400.0,
            "initial_quantity": 15,
            "remaining_quantity": 8,
            "arrival_date": d_minus_25,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-102",
            "product_id": "prod-1",
            "product_name": "Оверсайз худи «Eclipse Heavy»",
            "size": "M",
            "supplier_name": "Швейный цех «Ателье МодаПлюс»",
            "purchase_price": 2850.0,
            "initial_quantity": 10,
            "remaining_quantity": 10,
            "arrival_date": d_minus_10,
            "expiry_date": exp_valid_2,
        },
        {
            "batch_id": "BATCH-103",
            "product_id": "prod-1",
            "product_name": "Оверсайз худи «Eclipse Heavy»",
            "size": "L",
            "supplier_name": "ООО «Фабрика ТекстильПро»",
            "purchase_price": 2450.0,
            "initial_quantity": 12,
            "remaining_quantity": 9,
            "arrival_date": d_minus_15,
            "expiry_date": exp_valid_1,
        },
        # Футболки от разных поставщиков + партия, у которой СКОРО истекает срок сезонной реализации
        {
            "batch_id": "BATCH-104",
            "product_id": "prod-2",
            "product_name": "Футболка «Core Boxy Fit»",
            "size": "M",
            "supplier_name": "АО «CottonCraft Иваново»",
            "purchase_price": 950.0,
            "initial_quantity": 25,
            "remaining_quantity": 14,
            "arrival_date": d_minus_25,
            "expiry_date": exp_soon_1,
        },
        {
            "batch_id": "BATCH-105",
            "product_id": "prod-2",
            "product_name": "Футболка «Core Boxy Fit»",
            "size": "L",
            "supplier_name": "ООО «Трикотаж Люкс»",
            "purchase_price": 1100.0,
            "initial_quantity": 20,
            "remaining_quantity": 16,
            "arrival_date": d_minus_10,
            "expiry_date": exp_valid_2,
        },
        # Джинсы
        {
            "batch_id": "BATCH-106",
            "product_id": "prod-3",
            "product_name": "Джинсы Wide-Leg «Raw Indigo»",
            "size": "M",
            "supplier_name": "Фабрика «DenimFactory Юг»",
            "purchase_price": 3300.0,
            "initial_quantity": 12,
            "remaining_quantity": 7,
            "arrival_date": d_minus_15,
            "expiry_date": exp_valid_1,
        },
        # Бомбер (Скоро истекает срок дропа!)
        {
            "batch_id": "BATCH-107",
            "product_id": "prod-4",
            "product_name": "Бомбер «Cyber Shell Waterproof»",
            "size": "L",
            "supplier_name": "TechWear Manufacturing",
            "purchase_price": 5200.0,
            "initial_quantity": 8,
            "remaining_quantity": 5,
            "arrival_date": d_minus_25,
            "expiry_date": exp_soon_2,
        },
        # Свитшот — партия с УЖЕ ИСТЕКШИМ сроком сезонной годности (доступна для демонстрации списания)
        {
            "batch_id": "BATCH-108",
            "product_id": "prod-5",
            "product_name": "Свитшот «Minimal Fog»",
            "size": "S",
            "supplier_name": "АО «CottonCraft Иваново»",
            "purchase_price": 1950.0,
            "initial_quantity": 10,
            "remaining_quantity": 4,
            "arrival_date": d_minus_25,
            "expiry_date": exp_expired_1,
        },
        # Кепки
        {
            "batch_id": "BATCH-109",
            "product_id": "prod-6",
            "product_name": "Кепка «AURA Vintage washed»",
            "size": "ONE SIZE",
            "supplier_name": "Headwear Studio",
            "purchase_price": 750.0,
            "initial_quantity": 20,
            "remaining_quantity": 15,
            "arrival_date": d_minus_5,
            "expiry_date": exp_valid_1,
        },
    ]

    writeoffs = [
        {
            "writeoff_id": "WO-001",
            "batch_id": "BATCH-108",
            "product_id": "prod-5",
            "product_name": "Свитшот «Minimal Fog»",
            "size": "S",
            "supplier_name": "АО «CottonCraft Иваново»",
            "quantity": 3,
            "purchase_price": 1950.0,
            "total_loss": 5850.0,
            "reason": "EXPIRED",
            "reason_label": "Истечение срока годности / сезона коллекции",
            "comment": "Окончание сезона коллекции Autumn Drop, списание остатка",
            "date": (today - timedelta(days=2)).isoformat(),
        },
        {
            "writeoff_id": "WO-002",
            "batch_id": "BATCH-104",
            "product_id": "prod-2",
            "product_name": "Футболка «Core Boxy Fit»",
            "size": "M",
            "supplier_name": "АО «CottonCraft Иваново»",
            "quantity": 2,
            "purchase_price": 950.0,
            "total_loss": 1900.0,
            "reason": "DEFECT",
            "reason_label": "Порча товара / Производственный брак шва",
            "comment": "Обнаружен дефект окрашивания при инвентаризации",
            "date": (today - timedelta(days=4)).isoformat(),
        },
    ]

    return {"batches": batches, "writeoffs": writeoffs}


def load_db() -> dict:
    if not os.path.exists(DATA_FILE):
        seed = generate_seed_data()
        save_db(seed)
        return seed
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def enrich_batch_status(b: dict) -> dict:
    today = date.today()
    exp_date = date.fromisoformat(b["expiry_date"])
    days_left = (exp_date - today).days
    enriched = dict(b)
    enriched["days_until_expiry"] = days_left
    if b["remaining_quantity"] == 0:
        enriched["status"] = "DEPLETED"
        enriched["status_label"] = "Распродано / Списано"
    elif days_left < 0:
        enriched["status"] = "EXPIRED"
        enriched["status_label"] = f"Срок истек ({abs(days_left)} дн. назад)"
    elif days_left <= EXPIRING_SOON_DAYS:
        enriched["status"] = "EXPIRING_SOON"
        enriched["status_label"] = f"Скоро истекает ({days_left} дн.)"
    else:
        enriched["status"] = "ACTIVE"
        enriched["status_label"] = f"В норме ({days_left} дн.)"
    return enriched


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "warehouse-service", "port": 8002}


@app.get("/batches")
def list_batches(product_id: Optional[str] = None, only_available: bool = False):
    db = load_db()
    result = []
    for b in db["batches"]:
        if product_id and b["product_id"] != product_id:
            continue
        if only_available and b["remaining_quantity"] <= 0:
            continue
        result.append(enrich_batch_status(b))
    return result


@app.post("/batches", status_code=201)
def create_batch(payload: BatchCreate):
    db = load_db()
    arrival = payload.arrival_date or date.today().isoformat()
    new_batch = {
        "batch_id": f"BATCH-{uuid.uuid4().hex[:5].upper()}",
        "product_id": payload.product_id,
        "product_name": payload.product_name,
        "size": payload.size.upper(),
        "supplier_name": payload.supplier_name,
        "purchase_price": payload.purchase_price,
        "initial_quantity": payload.quantity,
        "remaining_quantity": payload.quantity,
        "arrival_date": arrival,
        "expiry_date": payload.expiry_date,
    }
    db["batches"].append(new_batch)
    save_db(db)
    return enrich_batch_status(new_batch)


@app.get("/stock/summary")
def get_stock_summary():
    """Возвращает доступные для продажи (непросроченные) остатки по моделям и размерам."""
    db = load_db()
    summary = {}
    for b in db["batches"]:
        eb = enrich_batch_status(b)
        if eb["remaining_quantity"] <= 0 or eb["status"] == "EXPIRED":
            continue
        pid = eb["product_id"]
        sz = eb["size"]
        if pid not in summary:
            summary[pid] = {"total_available": 0, "sizes": {}}
        summary[pid]["total_available"] += eb["remaining_quantity"]
        summary[pid]["sizes"][sz] = summary[pid]["sizes"].get(sz, 0) + eb["remaining_quantity"]
    return summary


@app.post("/stock/deduct-sale")
def deduct_stock_for_sale(req: SaleDeductRequest):
    """
    Списывает товар при продаже покупателю по методу FIFO (сначала самые ранние поставки).
    Просроченные партии к продаже не допускаются.
    Возвращает точную закупочную себестоимость списанных единиц с учетом цен разных поставщиков.
    """
    db = load_db()
    today = date.today()
    eligible_batches = [
        b for b in db["batches"]
        if b["product_id"] == req.product_id
        and b["size"].upper() == req.size.upper()
        and b["remaining_quantity"] > 0
        and date.fromisoformat(b["expiry_date"]) >= today
    ]
    eligible_batches.sort(key=lambda x: x["arrival_date"])

    total_available = sum(b["remaining_quantity"] for b in eligible_batches)
    if total_available < req.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно непросроченного товара размера {req.size} на складе. Доступно: {total_available} шт., запрошено: {req.quantity} шт."
        )

    need = req.quantity
    total_supplier_cost = 0.0
    allocations = []

    for b in eligible_batches:
        if need <= 0:
            break
        take = min(b["remaining_quantity"], need)
        b["remaining_quantity"] -= take
        need -= take
        cost = round(take * b["purchase_price"], 2)
        total_supplier_cost += cost
        allocations.append({
            "batch_id": b["batch_id"],
            "supplier_name": b["supplier_name"],
            "quantity": take,
            "unit_purchase_price": b["purchase_price"],
            "subtotal_cost": cost,
        })

    save_db(db)
    return {
        "product_id": req.product_id,
        "size": req.size.upper(),
        "deducted_quantity": req.quantity,
        "total_supplier_cost": round(total_supplier_cost, 2),
        "allocations": allocations,
    }


@app.post("/writeoffs", status_code=201)
def write_off_batch_items(req: WriteOffRequest):
    """Списание единиц товара из партии (по причине истечения срока годности/сезона или брака/порчи)."""
    db = load_db()
    target = None
    for b in db["batches"]:
        if b["batch_id"] == req.batch_id:
            target = b
            break
    if not target:
        raise HTTPException(status_code=404, detail="Партия не найдена")
    if target["remaining_quantity"] < req.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"В партии {req.batch_id} осталось только {target['remaining_quantity']} шт."
        )

    target["remaining_quantity"] -= req.quantity
    reason_code = req.reason.upper()
    reason_label = (
        "Истечение срока годности / сезона коллекции"
        if reason_code == "EXPIRED"
        else "Порча товара / Производственный брак"
    )
    loss = round(req.quantity * target["purchase_price"], 2)

    record = {
        "writeoff_id": f"WO-{uuid.uuid4().hex[:5].upper()}",
        "batch_id": target["batch_id"],
        "product_id": target["product_id"],
        "product_name": target["product_name"],
        "size": target["size"],
        "supplier_name": target["supplier_name"],
        "quantity": req.quantity,
        "purchase_price": target["purchase_price"],
        "total_loss": loss,
        "reason": reason_code,
        "reason_label": reason_label,
        "comment": req.comment or reason_label,
        "date": date.today().isoformat(),
    }
    db["writeoffs"].insert(0, record)
    save_db(db)
    return record


@app.post("/writeoffs/auto-expired")
def auto_write_off_all_expired():
    """Автоматически списывает все партии, у которых истек срок годности/сезона."""
    db = load_db()
    today = date.today()
    created_records = []
    for b in db["batches"]:
        if b["remaining_quantity"] > 0 and date.fromisoformat(b["expiry_date"]) < today:
            qty = b["remaining_quantity"]
            b["remaining_quantity"] = 0
            loss = round(qty * b["purchase_price"], 2)
            record = {
                "writeoff_id": f"WO-{uuid.uuid4().hex[:5].upper()}",
                "batch_id": b["batch_id"],
                "product_id": b["product_id"],
                "product_name": b["product_name"],
                "size": b["size"],
                "supplier_name": b["supplier_name"],
                "quantity": qty,
                "purchase_price": b["purchase_price"],
                "total_loss": loss,
                "reason": "EXPIRED",
                "reason_label": "Истечение срока годности / сезона коллекции",
                "comment": f"Автоматическое списание просроченной партии (срок до {b['expiry_date']})",
                "date": today.isoformat(),
            }
            db["writeoffs"].insert(0, record)
            created_records.append(record)
    save_db(db)
    return {
        "written_off_batches_count": len(created_records),
        "records": created_records,
    }


@app.get("/writeoffs")
def list_writeoffs(
    reason: Optional[str] = Query(None, description="Фильтр по причине: EXPIRED или DEFECT"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    db = load_db()
    result = []
    for w in db["writeoffs"]:
        if reason and w["reason"].upper() != reason.upper():
            continue
        if start_date and w["date"] < start_date:
            continue
        if end_date and w["date"] > end_date:
            continue
        result.append(w)
    return result


@app.get("/alerts/expiring")
def get_expiring_and_expired_alerts():
    """
    Возвращает:
    1) Список товаров/партий, которые СКОРО испортятся / выйдут из сезона (<= 14 дней)
    2) Список партий с уже ИСТЕКШИМ сроком, требующих немедленного списания
    """
    db = load_db()
    expiring_soon = []
    already_expired = []
    for b in db["batches"]:
        if b["remaining_quantity"] <= 0:
            continue
        eb = enrich_batch_status(b)
        if eb["status"] == "EXPIRING_SOON":
            expiring_soon.append(eb)
        elif eb["status"] == "EXPIRED":
            already_expired.append(eb)
    return {
        "threshold_days": EXPIRING_SOON_DAYS,
        "expiring_soon": expiring_soon,
        "already_expired": already_expired,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
