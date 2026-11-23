import json
import os
import sys
import uuid
from datetime import date, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from database.mysql_client import mysql_load_batches, mysql_save_batches

app = FastAPI(
    title="MONROE — Warehouse & Batches Microservice",
    description="Микросервис складского учета партий от поставщиков (в BYN), контроля сроков сезона и списаний",
    version="2.0.0",
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
    supplier_name: str = Field(..., description="Поставщик / Дистрибьютор")
    purchase_price: float = Field(..., gt=0, description="Закупочная цена за 1 ед. у поставщика (BYN)")
    quantity: int = Field(..., gt=0, description="Количество поступивших единиц")
    arrival_date: Optional[str] = Field(None, description="Дата поступления (YYYY-MM-DD)")
    expiry_date: str = Field(..., description="Срок окончания сезонной реализации / годности (YYYY-MM-DD)")


class SaleDeductRequest(BaseModel):
    product_id: str
    size: str
    quantity: int = Field(..., gt=0)


class ReturnStockRequest(BaseModel):
    product_id: str
    size: str
    quantity: int = Field(..., gt=0)
    is_defect: bool = Field(default=False, description="Если брак (True), товар не возвращается в доступный остаток витрины")


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
    exp_soon_1 = (today + timedelta(days=6)).isoformat()
    exp_soon_2 = (today + timedelta(days=11)).isoformat()
    exp_expired_1 = (today - timedelta(days=4)).isoformat()

    batches = [
        # Темно-синее мини-платье PATRIZIA PEPE (от двух разных поставщиков по разной закупочной цене в BYN)
        {
            "batch_id": "BATCH-201",
            "product_id": "prod-1",
            "product_name": "PATRIZIA PEPE — Темно-синее мини-платье",
            "size": "S",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 420.0,
            "initial_quantity": 10,
            "remaining_quantity": 6,
            "arrival_date": d_minus_25,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-202",
            "product_id": "prod-1",
            "product_name": "PATRIZIA PEPE — Темно-синее мини-платье",
            "size": "S",
            "supplier_name": "EuroFashion Distribution (Милан)",
            "purchase_price": 490.0,
            "initial_quantity": 8,
            "remaining_quantity": 8,
            "arrival_date": d_minus_10,
            "expiry_date": exp_valid_2,
        },
        {
            "batch_id": "BATCH-203",
            "product_id": "prod-1",
            "product_name": "PATRIZIA PEPE — Темно-синее мини-платье",
            "size": "XS",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 420.0,
            "initial_quantity": 6,
            "remaining_quantity": 5,
            "arrival_date": d_minus_15,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-204",
            "product_id": "prod-1",
            "product_name": "PATRIZIA PEPE — Темно-синее мини-платье",
            "size": "M",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 430.0,
            "initial_quantity": 6,
            "remaining_quantity": 4,
            "arrival_date": d_minus_15,
            "expiry_date": exp_valid_1,
        },
        # Двубортное черное приталенное пальто GIUSEPPE DI MORABITO
        {
            "batch_id": "BATCH-205",
            "product_id": "prod-2",
            "product_name": "GIUSEPPE DI MORABITO — Двубортное черное приталенное пальто",
            "size": "S",
            "supplier_name": "Morabito Atelier Milano",
            "purchase_price": 1650.0,
            "initial_quantity": 6,
            "remaining_quantity": 4,
            "arrival_date": d_minus_25,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-206",
            "product_id": "prod-2",
            "product_name": "GIUSEPPE DI MORABITO — Двубортное черное приталенное пальто",
            "size": "M",
            "supplier_name": "Luxury Moda Logistics",
            "purchase_price": 1790.0,
            "initial_quantity": 5,
            "remaining_quantity": 5,
            "arrival_date": d_minus_10,
            "expiry_date": exp_soon_1,
        },
        # Асимметричные серьги-пуссеты со стразами
        {
            "batch_id": "BATCH-207",
            "product_id": "prod-3",
            "product_name": "GIUSEPPE DI MORABITO — Асимметричные серьги-пуссеты со стразами",
            "size": "ONE SIZE",
            "supplier_name": "Morabito Atelier Milano",
            "purchase_price": 210.0,
            "initial_quantity": 15,
            "remaining_quantity": 11,
            "arrival_date": d_minus_15,
            "expiry_date": exp_valid_1,
        },
        # Черный джемпер с кружевом (скоро истекает срок сезона)
        {
            "batch_id": "BATCH-208",
            "product_id": "prod-4",
            "product_name": "GIUSEPPE DI MORABITO — Черный джемпер с кружевом",
            "size": "S",
            "supplier_name": "Morabito Atelier Milano",
            "purchase_price": 1100.0,
            "initial_quantity": 7,
            "remaining_quantity": 5,
            "arrival_date": d_minus_25,
            "expiry_date": exp_soon_2,
        },
        # Черные брюки-палаццо с защипами
        {
            "batch_id": "BATCH-209",
            "product_id": "prod-5",
            "product_name": "GIUSEPPE DI MORABITO — Черные брюки-палаццо с защипами",
            "size": "S",
            "supplier_name": "EuroFashion Distribution (Милан)",
            "purchase_price": 780.0,
            "initial_quantity": 10,
            "remaining_quantity": 7,
            "arrival_date": d_minus_15,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-210",
            "product_id": "prod-5",
            "product_name": "GIUSEPPE DI MORABITO — Черные брюки-палаццо с защипами",
            "size": "M",
            "supplier_name": "EuroFashion Distribution (Милан)",
            "purchase_price": 780.0,
            "initial_quantity": 8,
            "remaining_quantity": 6,
            "arrival_date": d_minus_15,
            "expiry_date": exp_valid_1,
        },
        # Остальные товары
        {
            "batch_id": "BATCH-211",
            "product_id": "prod-6",
            "product_name": "PATRIZIA PEPE — Черное платье-мини с драпировкой и жемчугом",
            "size": "S",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 720.0,
            "initial_quantity": 6,
            "remaining_quantity": 5,
            "arrival_date": d_minus_10,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-212",
            "product_id": "prod-7",
            "product_name": "GIUSEPPE DI MORABITO — Атласный корсетный топ на косточках",
            "size": "S",
            "supplier_name": "Morabito Atelier Milano",
            "purchase_price": 590.0,
            "initial_quantity": 6,
            "remaining_quantity": 3,
            "arrival_date": d_minus_25,
            "expiry_date": exp_expired_1,
        },
        {
            "batch_id": "BATCH-213",
            "product_id": "prod-8",
            "product_name": "GIUSEPPE DI MORABITO — Шелковый платок с монограммой",
            "size": "ONE SIZE",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 260.0,
            "initial_quantity": 10,
            "remaining_quantity": 8,
            "arrival_date": d_minus_5,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-214",
            "product_id": "prod-9",
            "product_name": "PATRIZIA PEPE — Солнцезащитные очки",
            "size": "ONE SIZE",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 320.0,
            "initial_quantity": 10,
            "remaining_quantity": 7,
            "arrival_date": d_minus_5,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-215",
            "product_id": "prod-10",
            "product_name": "GIUSEPPE DI MORABITO — Мужское кашемировое пальто",
            "size": "L",
            "supplier_name": "Morabito Atelier Milano",
            "purchase_price": 1800.0,
            "initial_quantity": 6,
            "remaining_quantity": 5,
            "arrival_date": d_minus_5,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-216",
            "product_id": "prod-11",
            "product_name": "PATRIZIA PEPE — Мужской шерстяной пиджак",
            "size": "L",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 1050.0,
            "initial_quantity": 6,
            "remaining_quantity": 5,
            "arrival_date": d_minus_5,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-217",
            "product_id": "prod-12",
            "product_name": "GIUSEPPE DI MORABITO — Мужской джемпер крупной вязки",
            "size": "M",
            "supplier_name": "Morabito Atelier Milano",
            "purchase_price": 650.0,
            "initial_quantity": 8,
            "remaining_quantity": 6,
            "arrival_date": d_minus_5,
            "expiry_date": exp_valid_1,
        },
        {
            "batch_id": "BATCH-218",
            "product_id": "prod-13",
            "product_name": "PATRIZIA PEPE — Мужской кожаный картхолдер",
            "size": "ONE SIZE",
            "supplier_name": "Tessilform S.p.A. (Флоренция, Италия)",
            "purchase_price": 180.0,
            "initial_quantity": 10,
            "remaining_quantity": 9,
            "arrival_date": d_minus_5,
            "expiry_date": exp_valid_1,
        },
        # Дополнительные размеры для всех моделей, чтобы на сайте отображалось точное наличие по размерам XS, S, M, L, XL
        {"batch_id": "BATCH-219", "product_id": "prod-1", "product_name": "PATRIZIA PEPE — Темно-синее мини-платье", "size": "L", "supplier_name": "Tessilform S.p.A.", "purchase_price": 430.0, "initial_quantity": 5, "remaining_quantity": 3, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-220", "product_id": "prod-2", "product_name": "GIUSEPPE DI MORABITO — Двубортное приталенное пальто", "size": "L", "supplier_name": "Morabito Atelier Milano", "purchase_price": 1650.0, "initial_quantity": 4, "remaining_quantity": 2, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-221", "product_id": "prod-4", "product_name": "GIUSEPPE DI MORABITO — Джемпер из мериноса с кружевом", "size": "XS", "supplier_name": "Morabito Atelier Milano", "purchase_price": 1100.0, "initial_quantity": 4, "remaining_quantity": 3, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-222", "product_id": "prod-4", "product_name": "GIUSEPPE DI MORABITO — Джемпер из мериноса с кружевом", "size": "M", "supplier_name": "Morabito Atelier Milano", "purchase_price": 1100.0, "initial_quantity": 6, "remaining_quantity": 4, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-223", "product_id": "prod-5", "product_name": "GIUSEPPE DI MORABITO — Брюки-палаццо с защипами", "size": "XS", "supplier_name": "EuroFashion Distribution", "purchase_price": 780.0, "initial_quantity": 5, "remaining_quantity": 4, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-224", "product_id": "prod-5", "product_name": "GIUSEPPE DI MORABITO — Брюки-палаццо с защипами", "size": "L", "supplier_name": "EuroFashion Distribution", "purchase_price": 780.0, "initial_quantity": 5, "remaining_quantity": 3, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-225", "product_id": "prod-6", "product_name": "PATRIZIA PEPE — Кожаная мини-сумка бьюти-кейс", "size": "ONE SIZE", "supplier_name": "Tessilform S.p.A.", "purchase_price": 410.0, "initial_quantity": 8, "remaining_quantity": 6, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-226", "product_id": "prod-7", "product_name": "PATRIZIA PEPE — Кожаный ремень с пряжкой Fly", "size": "S", "supplier_name": "Tessilform S.p.A.", "purchase_price": 210.0, "initial_quantity": 6, "remaining_quantity": 5, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-227", "product_id": "prod-7", "product_name": "PATRIZIA PEPE — Кожаный ремень с пряжкой Fly", "size": "M", "supplier_name": "Tessilform S.p.A.", "purchase_price": 210.0, "initial_quantity": 8, "remaining_quantity": 7, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-228", "product_id": "prod-7", "product_name": "PATRIZIA PEPE — Кожаный ремень с пряжкой Fly", "size": "L", "supplier_name": "Tessilform S.p.A.", "purchase_price": 210.0, "initial_quantity": 5, "remaining_quantity": 3, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-229", "product_id": "prod-10", "product_name": "GIUSEPPE DI MORABITO — Мужское кашемировое пальто", "size": "M", "supplier_name": "Morabito Atelier Milano", "purchase_price": 1800.0, "initial_quantity": 5, "remaining_quantity": 4, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-230", "product_id": "prod-10", "product_name": "GIUSEPPE DI MORABITO — Мужское кашемировое пальто", "size": "XL", "supplier_name": "Morabito Atelier Milano", "purchase_price": 1800.0, "initial_quantity": 4, "remaining_quantity": 3, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-231", "product_id": "prod-11", "product_name": "PATRIZIA PEPE — Мужские шерстяные брюки со стрелками", "size": "M", "supplier_name": "Tessilform S.p.A.", "purchase_price": 750.0, "initial_quantity": 6, "remaining_quantity": 5, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-232", "product_id": "prod-11", "product_name": "PATRIZIA PEPE — Мужские шерстяные брюки со стрелками", "size": "XL", "supplier_name": "Tessilform S.p.A.", "purchase_price": 750.0, "initial_quantity": 5, "remaining_quantity": 4, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-233", "product_id": "prod-12", "product_name": "GIUSEPPE DI MORABITO — Мужской джемпер крупной вязки", "size": "L", "supplier_name": "Morabito Atelier Milano", "purchase_price": 650.0, "initial_quantity": 7, "remaining_quantity": 5, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-234", "product_id": "prod-12", "product_name": "GIUSEPPE DI MORABITO — Мужской джемпер крупной вязки", "size": "XL", "supplier_name": "Morabito Atelier Milano", "purchase_price": 650.0, "initial_quantity": 5, "remaining_quantity": 3, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-235", "product_id": "prod-13", "product_name": "PATRIZIA PEPE — Мужской кожаный картхолдер", "size": "M", "supplier_name": "Tessilform S.p.A.", "purchase_price": 180.0, "initial_quantity": 8, "remaining_quantity": 6, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-236", "product_id": "prod-13", "product_name": "PATRIZIA PEPE — Мужской кожаный картхолдер", "size": "L", "supplier_name": "Tessilform S.p.A.", "purchase_price": 180.0, "initial_quantity": 6, "remaining_quantity": 5, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-237", "product_id": "prod-14", "product_name": "PATRIZIA PEPE — Мужская рубашка из египетского хлопка", "size": "M", "supplier_name": "Tessilform S.p.A.", "purchase_price": 390.0, "initial_quantity": 8, "remaining_quantity": 6, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-238", "product_id": "prod-14", "product_name": "PATRIZIA PEPE — Мужская рубашка из египетского хлопка", "size": "L", "supplier_name": "Tessilform S.p.A.", "purchase_price": 390.0, "initial_quantity": 8, "remaining_quantity": 7, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-239", "product_id": "prod-14", "product_name": "PATRIZIA PEPE — Мужская рубашка из египетского хлопка", "size": "XL", "supplier_name": "Tessilform S.p.A.", "purchase_price": 390.0, "initial_quantity": 5, "remaining_quantity": 4, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-240", "product_id": "prod-15", "product_name": "GIUSEPPE DI MORABITO — Мужской городской кожаный рюкзак", "size": "L", "supplier_name": "Morabito Atelier Milano", "purchase_price": 850.0, "initial_quantity": 6, "remaining_quantity": 5, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
        {"batch_id": "BATCH-241", "product_id": "prod-15", "product_name": "GIUSEPPE DI MORABITO — Мужской городской кожаный рюкзак", "size": "XL", "supplier_name": "Morabito Atelier Milano", "purchase_price": 850.0, "initial_quantity": 4, "remaining_quantity": 3, "arrival_date": d_minus_5, "expiry_date": exp_valid_1},
    ]

    writeoffs = [
        {
            "writeoff_id": "WO-101",
            "batch_id": "BATCH-212",
            "product_id": "prod-7",
            "product_name": "GIUSEPPE DI MORABITO — Атласный корсетный топ на косточках",
            "size": "S",
            "supplier_name": "Morabito Atelier Milano",
            "quantity": 1,
            "purchase_price": 590.0,
            "total_loss": 590.0,
            "reason": "EXPIRED",
            "reason_label": "Истечение срока годности / сезона коллекции",
            "comment": "Окончание сезонной квоты бутика, перевод в списание",
            "date": (today - timedelta(days=2)).isoformat(),
        },
        {
            "writeoff_id": "WO-102",
            "batch_id": "BATCH-207",
            "product_id": "prod-3",
            "product_name": "GIUSEPPE DI MORABITO — Асимметричные серьги-пуссеты со стразами",
            "size": "ONE SIZE",
            "supplier_name": "Morabito Atelier Milano",
            "quantity": 1,
            "purchase_price": 210.0,
            "total_loss": 210.0,
            "reason": "DEFECT",
            "reason_label": "Порча товара / Повреждение застежки при транспортировке",
            "comment": "Обнаружен дефект крепления кристалла",
            "date": (today - timedelta(days=4)).isoformat(),
        },
    ]

    return {"batches": batches, "writeoffs": writeoffs}


def load_db() -> dict:
    seed = generate_seed_data()
    mysql_batches = mysql_load_batches(seed["batches"])
    if not os.path.exists(DATA_FILE):
        if mysql_batches is not None and len(mysql_batches) > 0:
            seed["batches"] = mysql_batches
        save_db(seed)
        return seed
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data.get("batches") or len(data["batches"]) < 25:
        save_db(seed)
        return seed
    if mysql_batches is not None and len(mysql_batches) >= len(data["batches"]):
        data["batches"] = mysql_batches
    return data


def save_db(data: dict):
    mysql_save_batches(data.get("batches", []))
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
            detail=f"Недостаточно товара размера {req.size} в наличии в бутике. Доступно: {total_available} ед., запрошено: {req.quantity} ед."
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


@app.post("/stock/return-item")
def return_stock_from_customer(req: ReturnStockRequest):
    """
    Возвращает товар обратно в наличие на склад после того, как Администратор одобрил возврат покупателя.
    Если возврат по причине брака (is_defect=True), товар списывается в брак и на витрину не возвращается.
    """
    db = load_db()
    if req.is_defect:
        return {
            "status": "DEFECT_NOT_RESTOCKED",
            "product_id": req.product_id,
            "size": req.size.upper(),
            "restocked_quantity": 0,
        }

    for b in db["batches"]:
        if b["product_id"] == req.product_id and b["size"].upper() == req.size.upper():
            b["remaining_quantity"] += req.quantity
            save_db(db)
            return {
                "status": "RESTOCKED",
                "batch_id": b["batch_id"],
                "product_id": req.product_id,
                "size": req.size.upper(),
                "restocked_quantity": req.quantity,
                "new_remaining": b["remaining_quantity"],
            }

    # Если партии такого размера не было — создаем возвратную партию
    today = date.today()
    new_batch = {
        "batch_id": f"BATCH-RET-{uuid.uuid4().hex[:4].upper()}",
        "product_id": req.product_id,
        "product_name": "Возврат покупателя MONROE",
        "size": req.size.upper(),
        "supplier_name": "Возврат в бутик MONROE",
        "purchase_price": 400.0,
        "initial_quantity": req.quantity,
        "remaining_quantity": req.quantity,
        "arrival_date": today.isoformat(),
        "expiry_date": (today + timedelta(days=90)).isoformat(),
    }
    db["batches"].append(new_batch)
    save_db(db)
    return {
        "status": "RESTOCKED",
        "batch_id": new_batch["batch_id"],
        "product_id": req.product_id,
        "size": req.size.upper(),
        "restocked_quantity": req.quantity,
    }


@app.post("/writeoffs", status_code=201)
def write_off_batch_items(req: WriteOffRequest):
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
            detail=f"В партии {req.batch_id} осталось только {target['remaining_quantity']} ед."
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
    reason: Optional[str] = Query(None),
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
