import json
import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="MAD FASHION — Catalog Microservice",
    description="Микросервис управления каталогом одежды, аксессуаров, новинками и ценами (BYN)",
    version="3.0.0",
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
    brand: str = Field(default="PATRIZIA PEPE", description="Бренд")
    name: str = Field(..., description="Название модели")
    gender: str = Field(default="ДЛЯ НЕЁ", description="Раздел: ДЛЯ НЕЁ или ДЛЯ НЕГО")
    category: str = Field(..., description="Категория одежды или аксессуаров")
    subcategory: str = Field(default="Коллекция Осень 2026", description="Подкатегория")
    collection: str = Field(default="Осень 2026", description="Коллекция / Сезон")
    retail_price: float = Field(..., gt=0, description="Розничная цена (BYN)")
    sizes: List[str] = Field(default=["XS", "S", "M", "L"], description="Доступные размеры")
    color: str = Field(default="Черный", description="Цвет")
    is_new: bool = Field(default=True, description="Отображать в блоке НОВИНКИ на главной")
    image_main: str = Field(default="", description="Основное фото")
    image_model: str = Field(default="", description="Второе фото (на модели)")
    brand_story: str = Field(default="", description="Описание О БРЕНДЕ")
    description: str = Field(default="", description="Описание и состав")
    care: str = Field(default="Деликатная чистка. Бережное хранение.", description="Уход и детали")
    boutique_name: str = Field(default="Бутик «PATRIZIA PEPE»", description="Название бутика")
    boutique_address: str = Field(default="САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65", description="Адрес салона")


class ProductPriceUpdate(BaseModel):
    retail_price: float = Field(..., gt=0, description="Новая цена товара в BYN")
    name: Optional[str] = None
    is_new: Optional[bool] = None


class Product(ProductCreate):
    id: str


PATRIZIA_STORY = (
    "Patrizia Pepe - это премиум-бренд с особым итальянским стилем. В нем соседствуют легкость и "
    "экстравагантность, роскошь и минимализм, романтика и любовь к самовыражению. Начав свой путь в 1993 г, "
    "семейная пара пришла к успеху и всемирному признанию. Коллекции бренда представляют собой микс высокого "
    "качества и тщательно продуманных деталей."
)

GIUSEPPE_STORY = (
    "Giuseppe di Morabito — миланский бренд класса люкс, основанный в 2015 году. Бренд сочетает классическое "
    "итальянское портновское искусство с утонченным кроем и выразительными силуэтами."
)

DEFAULT_PRODUCTS = [
    # ==================== ДЛЯ НЕЁ (ОДЕЖДА + АКСЕССУАРЫ) ====================
    {
        "id": "prod-1",
        "sku": "PP-317948",
        "brand": "PATRIZIA PEPE",
        "name": "Темно-синее мини-платье",
        "gender": "ДЛЯ НЕЁ",
        "category": "Платья",
        "subcategory": "Облегающее",
        "collection": "Осень 2026",
        "retail_price": 1050.0,
        "sizes": ["XS", "S", "M", "L"],
        "color": "Темно-синий",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Облегающее мини-платье с открытыми плечами и мягкой драпировкой по всей длине.",
        "care": "Сухая чистка. Гладить при низкой температуре.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-2",
        "sku": "GDM-10021",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Двубортное приталенное пальто",
        "gender": "ДЛЯ НЕЁ",
        "category": "Верхняя одежда",
        "subcategory": "Пальто",
        "collection": "Осень 2026",
        "retail_price": 3850.0,
        "sizes": ["S", "M", "L"],
        "color": "Черный",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1548624313-0396c75e4b1a?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Приталенное двубортное пальто макси из 100% итальянской шерсти с четкой линией плеча.",
        "care": "Только профессиональная сухая чистка.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-3",
        "sku": "GDM-10022",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Асимметричные серьги-пуссеты со стразами",
        "gender": "ДЛЯ НЕЁ",
        "category": "Бижутерия",
        "subcategory": "Серьги",
        "collection": "Осень 2026",
        "retail_price": 550.0,
        "sizes": ["ONE SIZE"],
        "color": "Серебристый",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1635767798638-3e25273a8236?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Акцентные серьги с кристаллами паве и серебристым покрытием. Сделано в Италии.",
        "care": "Хранить в индивидуальном футляре.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-4",
        "sku": "GDM-10023",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Джемпер из мериноса с кружевом",
        "gender": "ДЛЯ НЕЁ",
        "category": "Джемперы",
        "subcategory": "Трикотаж",
        "collection": "Осень 2026",
        "retail_price": 2500.0,
        "sizes": ["XS", "S", "M"],
        "color": "Коричневый",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Джемпер из мериносовой шерсти с высоким воротом и вставкой из тонкого кружева шантильи.",
        "care": "Ручная стирка или сухая чистка.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-5",
        "sku": "GDM-10024",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Брюки-палаццо с защипами",
        "gender": "ДЛЯ НЕЁ",
        "category": "Брюки",
        "subcategory": "Палаццо",
        "collection": "Осень 2026",
        "retail_price": 1850.0,
        "sizes": ["XS", "S", "M", "L"],
        "color": "Бежевый",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Классические широкие брюки-палаццо с высокой посадкой и глубокими защипами у пояса.",
        "care": "Деликатная химчистка.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-6",
        "sku": "PP-312277",
        "brand": "PATRIZIA PEPE",
        "name": "Кожаная мини-сумка бьюти-кейс",
        "gender": "ДЛЯ НЕЁ",
        "category": "Сумки",
        "subcategory": "Мини-сумки",
        "collection": "Осень 2026",
        "retail_price": 980.0,
        "sizes": ["ONE SIZE"],
        "color": "Черный",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Стеганая кожаная сумка-кейс из мягкой телячьей кожи наппа с фирменной биркой.",
        "care": "Уход кремом для натуральной кожи.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-7",
        "sku": "PP-50119",
        "brand": "PATRIZIA PEPE",
        "name": "Кожаный ремень с пряжкой Fly",
        "gender": "ДЛЯ НЕЁ",
        "category": "Ремни",
        "subcategory": "Аксессуары",
        "collection": "Осень 2026",
        "retail_price": 490.0,
        "sizes": ["S", "M", "L"],
        "color": "Коричневый",
        "is_new": False,
        "image_main": "https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Ремень из гладкой итальянской кожи с фирменной металлической пряжкой.",
        "care": "Беречь от влаги.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-8",
        "sku": "GDM-50881",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Шелковый платок с монограммой",
        "gender": "ДЛЯ НЕЁ",
        "category": "Платки и шарфы",
        "subcategory": "Аксессуары",
        "collection": "Осень 2026",
        "retail_price": 620.0,
        "sizes": ["ONE SIZE"],
        "color": "Бежевый",
        "is_new": False,
        "image_main": "https://images.unsplash.com/photo-1601924994987-69e26d50dc26?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1584030373081-f37b7bb4fa8e?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Платок-каре из 100% натурального шелка твил в пудрово-бежевой гамме.",
        "care": "Только сухая чистка.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-9",
        "sku": "PP-77810",
        "brand": "PATRIZIA PEPE",
        "name": "Солнцезащитные очки в черепаховой оправе",
        "gender": "ДЛЯ НЕЁ",
        "category": "Солнцезащитные очки",
        "subcategory": "Оптика",
        "collection": "Осень 2026",
        "retail_price": 790.0,
        "sizes": ["ONE SIZE"],
        "color": "Коричневый",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1508296695146-257a814070b4?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Очки из итальянского ацетата с градиентными линзами и 100% защитой UV400.",
        "care": "Протирать салфеткой из микрофибры.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },

    # ==================== ДЛЯ НЕГО (МУЖСКАЯ КОЛЛЕКЦИЯ) ====================
    {
        "id": "prod-10",
        "sku": "GDM-M-201",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Мужское кашемировое пальто графитового оттенка",
        "gender": "ДЛЯ НЕГО",
        "category": "Верхняя одежда",
        "subcategory": "Пальто мужское",
        "collection": "Осень 2026",
        "retail_price": 4100.0,
        "sizes": ["M", "L", "XL"],
        "color": "Черный",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1544022613-e87ca75a784a?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Классическое однобортное мужское пальто из смеси шерсти и кашемира.",
        "care": "Профессиональная химчистка.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-11",
        "sku": "PP-M-202",
        "brand": "PATRIZIA PEPE",
        "name": "Мужской шерстяной пиджак шоколадного оттенка",
        "gender": "ДЛЯ НЕГО",
        "category": "Пиджаки",
        "subcategory": "Костюмы и пиджаки",
        "collection": "Осень 2026",
        "retail_price": 2350.0,
        "sizes": ["M", "L", "XL"],
        "color": "Коричневый",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1593030761757-71fae45fa0e7?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Приталенный мужской пиджак из тонкой итальянской шерсти Virgin Wool.",
        "care": "Сухая чистка.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-12",
        "sku": "GDM-M-203",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Мужской джемпер крупной вязки (Тауп)",
        "gender": "ДЛЯ НЕГО",
        "category": "Джемперы",
        "subcategory": "Трикотаж мужской",
        "collection": "Осень 2026",
        "retail_price": 1480.0,
        "sizes": ["S", "M", "L", "XL"],
        "color": "Бежевый",
        "is_new": True,
        "image_main": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Мягкий джемпер из мериносовой шерсти в светло-бежевом оттенке.",
        "care": "Ручная стирка при 30°C.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-13",
        "sku": "PP-M-204",
        "brand": "PATRIZIA PEPE",
        "name": "Мужской кожаный картхолдер",
        "gender": "ДЛЯ НЕГО",
        "category": "Кошельки и картхолдеры",
        "subcategory": "Аксессуары",
        "collection": "Осень 2026",
        "retail_price": 420.0,
        "sizes": ["ONE SIZE"],
        "color": "Черный",
        "is_new": False,
        "image_main": "https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Компактный картхолдер из натуральной сафьяновой кожи на 6 отделений.",
        "care": "Сухая чистка мягкой тканью.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    }
]


def load_products() -> List[dict]:
    if not os.path.exists(DATA_FILE):
        save_products(DEFAULT_PRODUCTS)
        return DEFAULT_PRODUCTS
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data or len(data) < 10 or "is_new" not in data[0]:
        save_products(DEFAULT_PRODUCTS)
        return DEFAULT_PRODUCTS
    return data


def save_products(products: List[dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "catalog-service", "port": 8001}


@app.get("/products", response_model=List[Product])
def get_products(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None, description="Список категорий через запятую"),
    brand: Optional[str] = Query(None, description="Список брендов через запятую"),
    color: Optional[str] = Query(None, description="Список цветов через запятую"),
    gender: Optional[str] = Query(None, description="ДЛЯ НЕЁ или ДЛЯ НЕГО"),
    size: Optional[str] = Query(None, description="Список размеров через запятую"),
    only_new: Optional[bool] = Query(None, description="Только новинки"),
    sort: Optional[str] = Query(None),
):
    products = load_products()
    result = []

    categories_filter = [c.strip().lower() for c in category.split(",") if c.strip()] if category else []
    brands_filter = [b.strip().lower() for b in brand.split(",") if b.strip()] if brand else []
    colors_filter = [c.strip().lower() for c in color.split(",") if c.strip()] if color else []
    sizes_filter = [s.strip().upper() for s in size.split(",") if s.strip()] if size else []

    for p in products:
        if search:
            q = search.lower()
            if (
                q not in p["name"].lower()
                and q not in p.get("brand", "").lower()
                and q not in p["sku"].lower()
                and q not in p.get("description", "").lower()
            ):
                continue
        if gender and p.get("gender", "ДЛЯ НЕЁ").lower() != gender.lower():
            continue
        if categories_filter and p["category"].lower() not in categories_filter:
            continue
        if brands_filter and p.get("brand", "").lower() not in brands_filter:
            continue
        if colors_filter and p.get("color", "").lower() not in colors_filter:
            continue
        if sizes_filter:
            prod_sizes = [s.upper() for s in p.get("sizes", [])]
            if not any(sf in prod_sizes for sf in sizes_filter):
                continue
        if only_new is True and not p.get("is_new", False):
            continue
        result.append(p)

    if sort == "price_asc":
        result.sort(key=lambda x: x["retail_price"])
    elif sort == "price_desc":
        result.sort(key=lambda x: x["retail_price"], reverse=True)

    return result


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str):
    products = load_products()
    for p in products:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Товар не найден")


@app.post("/products", response_model=Product, status_code=201)
def create_product(payload: ProductCreate):
    products = load_products()
    new_prod = payload.model_dump()
    new_prod["id"] = f"prod-{uuid.uuid4().hex[:6]}"
    if not new_prod.get("image_main"):
        new_prod["image_main"] = "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?auto=format&fit=crop&w=900&q=85"
    if not new_prod.get("image_model"):
        new_prod["image_model"] = new_prod["image_main"]
    if not new_prod.get("brand_story"):
        new_prod["brand_story"] = PATRIZIA_STORY
    products.insert(0, new_prod)
    save_products(products)
    return new_prod


@app.patch("/products/{product_id}", response_model=Product)
def update_product_price(product_id: str, payload: ProductPriceUpdate):
    products = load_products()
    for p in products:
        if p["id"] == product_id:
            p["retail_price"] = round(float(payload.retail_price), 2)
            if payload.name is not None and payload.name.strip():
                p["name"] = payload.name.strip()
            if payload.is_new is not None:
                p["is_new"] = payload.is_new
            save_products(products)
            return p
    raise HTTPException(status_code=404, detail="Товар не найден")


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    products = load_products()
    filtered = [p for p in products if p["id"] != product_id]
    if len(filtered) == len(products):
        raise HTTPException(status_code=404, detail="Товар не найден")
    save_products(filtered)
    return {"deleted": True, "id": product_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
