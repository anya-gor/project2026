import json
import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AURA Wear — Catalog Microservice",
    description="Микросервис управления каталогом моделей одежды, коллекциями, категориями и поиска",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "catalog_db.json")


class ProductCreate(BaseModel):
    sku: str = Field(..., description="Артикул модели")
    name: str = Field(..., description="Название модели одежды")
    category: str = Field(..., description="Категория (Худи, Футболки, Брюки, Верхняя одежда, Аксессуары)")
    collection: str = Field(..., description="Коллекция / Дроп")
    retail_price: float = Field(..., gt=0, description="Розничная цена продажи (руб.)")
    sizes: List[str] = Field(default=["S", "M", "L", "XL"], description="Доступная размерная сетка")
    color: str = Field(default="Black", description="Цвет")
    description: str = Field(default="", description="Описание модели и состава ткани")


class Product(ProductCreate):
    id: str


DEFAULT_PRODUCTS = [
    {
        "id": "prod-1",
        "sku": "AW-HD-001",
        "name": "Оверсайз худи «Eclipse Heavy»",
        "category": "Худи и свитшоты",
        "collection": "SS26 Street",
        "retail_price": 6900.0,
        "sizes": ["S", "M", "L", "XL"],
        "color": "Графитовый черный",
        "description": "Плотность футера 480 г/м², 100% хлопок пенье, спущенное плечо."
    },
    {
        "id": "prod-2",
        "sku": "AW-TS-002",
        "name": "Футболка «Core Boxy Fit»",
        "category": "Футболки",
        "collection": "Basic Capsule",
        "retail_price": 3200.0,
        "sizes": ["XS", "S", "M", "L", "XL"],
        "color": "Молочный экрю",
        "description": "Плотный хлопок 260 г/м², свободный крой, усиленный ворот."
    },
    {
        "id": "prod-3",
        "sku": "AW-DN-003",
        "name": "Джинсы Wide-Leg «Raw Indigo»",
        "category": "Брюки и деним",
        "collection": "SS26 Street",
        "retail_price": 8500.0,
        "sizes": ["S", "M", "L"],
        "color": "Темный индиго",
        "description": "Японский селвидж-деним 14 oz, широкий силуэт."
    },
    {
        "id": "prod-4",
        "sku": "AW-JK-004",
        "name": "Бомбер «Cyber Shell Waterproof»",
        "category": "Верхняя одежда",
        "collection": "Limited Drop",
        "retail_price": 12900.0,
        "sizes": ["M", "L", "XL"],
        "color": "Оливковый хаки",
        "description": "Мембранная ткань с защитой от ветра и влаги, металлическая фурнитура."
    },
    {
        "id": "prod-5",
        "sku": "AW-SW-005",
        "name": "Свитшот «Minimal Fog»",
        "category": "Худи и свитшоты",
        "collection": "Autumn Drop",
        "retail_price": 5400.0,
        "sizes": ["XS", "S", "M", "L"],
        "color": "Холодный серый",
        "description": "Мягкий хлопок с эффектом варки garment-dyed."
    },
    {
        "id": "prod-6",
        "sku": "AW-AC-006",
        "name": "Кепка «AURA Vintage washed»",
        "category": "Аксессуары",
        "collection": "Basic Capsule",
        "retail_price": 2400.0,
        "sizes": ["ONE SIZE"],
        "color": "Винтажный серый",
        "description": "100% твил, объемная вышивка логотипа бренда."
    }
]


def load_products() -> List[dict]:
    if not os.path.exists(DATA_FILE):
        save_products(DEFAULT_PRODUCTS)
        return DEFAULT_PRODUCTS
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_products(products: List[dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "catalog-service", "port": 8001}


@app.get("/products", response_model=List[Product])
def get_products(
    search: Optional[str] = Query(None, description="Поиск по названию, артикулу или описанию"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    collection: Optional[str] = Query(None, description="Фильтр по коллекции"),
    size: Optional[str] = Query(None, description="Фильтр по размеру"),
    max_price: Optional[float] = Query(None, description="Максимальная розничная цена"),
):
    products = load_products()
    result = []
    for p in products:
        if search:
            q = search.lower()
            if q not in p["name"].lower() and q not in p["sku"].lower() and q not in p.get("description", "").lower():
                continue
        if category and p["category"].lower() != category.lower():
            continue
        if collection and p["collection"].lower() != collection.lower():
            continue
        if size and size.upper() not in [s.upper() for s in p.get("sizes", [])]:
            continue
        if max_price is not None and p["retail_price"] > max_price:
            continue
        result.append(p)
    return result


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str):
    products = load_products()
    for p in products:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Модель одежды не найдена")


@app.post("/products", response_model=Product, status_code=201)
def create_product(payload: ProductCreate):
    products = load_products()
    new_prod = payload.model_dump()
    new_prod["id"] = f"prod-{uuid.uuid4().hex[:6]}"
    products.append(new_prod)
    save_products(products)
    return new_prod


@app.get("/meta/filters")
def get_filter_options():
    products = load_products()
    categories = sorted(list({p["category"] for p in products}))
    collections = sorted(list({p["collection"] for p in products}))
    sizes = ["XS", "S", "M", "L", "XL", "ONE SIZE"]
    return {
        "categories": categories,
        "collections": collections,
        "sizes": sizes,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
