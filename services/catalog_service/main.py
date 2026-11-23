import json
import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="MAD FASHION — Catalog Microservice",
    description="Микросервис каталога одежды, брендов, категорий и фильтрации (в BYN)",
    version="2.0.0",
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
    name: str = Field(..., description="Название модели одежды")
    gender: str = Field(default="ДЛЯ НЕЁ", description="Раздел (ДЛЯ НЕЁ / ДЛЯ НЕГО)")
    category: str = Field(..., description="Категория (Платья, Верхняя одежда, Джемперы, Брюки, Аксессуары и др.)")
    subcategory: str = Field(default="Облегающее", description="Подкатегория")
    collection: str = Field(default="FW 2026", description="Коллекция / Сезон")
    retail_price: float = Field(..., gt=0, description="Розничная цена (BYN)")
    sizes: List[str] = Field(default=["XS", "S", "M", "L"], description="Доступные размеры")
    color: str = Field(default="Черный", description="Цвет")
    image_main: str = Field(default="", description="Основное фото изделия")
    image_model: str = Field(default="", description="Фото на модели")
    brand_story: str = Field(default="", description="Описание О БРЕНДЕ")
    description: str = Field(default="", description="Описание и состав")
    care: str = Field(default="Деликатная стирка при 30°C или химчистка.", description="Уход и детали")
    boutique_name: str = Field(default="Бутик «PATRIZIA PEPE»", description="Название бутика")
    boutique_address: str = Field(default="САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65", description="Адрес салона")


class Product(ProductCreate):
    id: str


PATRIZIA_STORY = (
    "Patrizia Pepe - это премиум-бренд с особым итальянским стилем. В нем соседствуют легкость и "
    "экстравагантность, роскошь и минимализм, романтика и любовь к самовыражению. Патриция Пепе - это не просто "
    "бренд с историей, а фамильный бизнес, прошедший через тернии к звездам. Начав свой путь в 1993 г, семейная "
    "пара пришла к успеху и всемирному признанию. Сочетание отменного качества, упорной работы и веры в себя "
    "постепенно привело Клаудио Орреа и его жену Патрицию Бамби к модному олимпу.\n\n"
    "Философия бренда Patrizia Pepe - это выбор! И не только настроения и свободы, но также повседневного комфорта "
    "или роскоши для особого случая. Коллекции Патриции Пепе представляют собой микс высокого качества и тщательно "
    "продуманных деталей."
)

GIUSEPPE_STORY = (
    "Giuseppe di Morabito — миланский бренд класса люкс, основанный в 2015 году. Бренд сочетает классическое "
    "итальянское портновское искусство с авангардным кроем, драпировками, стразами и выразительными силуэтами."
)

DEFAULT_PRODUCTS = [
    {
        "id": "prod-1",
        "sku": "PP-317948",
        "brand": "PATRIZIA PEPE",
        "name": "Темно-синее мини-платье",
        "gender": "ДЛЯ НЕЁ",
        "category": "Платья",
        "subcategory": "Облегающее",
        "collection": "SS26 Runway",
        "retail_price": 1050.0,
        "sizes": ["XS", "S", "M", "L"],
        "color": "Темно-синий",
        "image_main": "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Облегающее мини-платье с открытыми плечами и мягкой драпировкой по всей длине. Эластичная вискоза премиум-класса подчеркивает силуэт.",
        "care": "Сухая чистка. Не отбеливать. Гладить при низкой температуре с изнаночной стороны.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-2",
        "sku": "GDM-10021",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Двубортное черное приталенное пальто",
        "gender": "ДЛЯ НЕЁ",
        "category": "Верхняя одежда",
        "subcategory": "Пальто",
        "collection": "FW26 Milan",
        "retail_price": 3850.0,
        "sizes": ["S", "M", "L"],
        "color": "Черный",
        "image_main": "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1548624313-0396c75e4b1a?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Приталенное двубортное пальто макси из 100% итальянской шерсти с четкой линией плеча и шелковой подкладкой.",
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
        "category": "Аксессуары",
        "subcategory": "Украшения",
        "collection": "Crystal Capsule",
        "retail_price": 550.0,
        "sizes": ["ONE SIZE"],
        "color": "Серебристый",
        "image_main": "https://images.unsplash.com/photo-1635767798638-3e25273a8236?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Акцентные серьги с кристаллами паве и серебристым покрытием. Сделано в Италии.",
        "care": "Хранить в индивидуальном футляре, избегать контакта с парфюмом.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-4",
        "sku": "GDM-10023",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Черный джемпер с кружевом",
        "gender": "ДЛЯ НЕЁ",
        "category": "Джемперы",
        "subcategory": "Трикотаж",
        "collection": "FW26 Milan",
        "retail_price": 2500.0,
        "sizes": ["XS", "S", "M"],
        "color": "Черный",
        "image_main": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Джемпер из мериносовой шерсти с высоким воротом на асимметричной молнии и вставкой из тонкого кружева шантильи.",
        "care": "Ручная стирка в прохладной воде или сухая чистка.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-5",
        "sku": "GDM-10024",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Черные брюки-палаццо с защипами",
        "gender": "ДЛЯ НЕЁ",
        "category": "Брюки",
        "subcategory": "Палаццо",
        "collection": "FW26 Milan",
        "retail_price": 1850.0,
        "sizes": ["XS", "S", "M", "L"],
        "color": "Черный",
        "image_main": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Классические широкие брюки-палаццо с высокой посадкой и глубокими защипами у пояса.",
        "care": "Деликатная химчистка, отпаривание.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-6",
        "sku": "PP-40112",
        "brand": "PATRIZIA PEPE",
        "name": "Черное платье-мини с драпировкой и жемчугом",
        "gender": "ДЛЯ НЕЁ",
        "category": "Платья",
        "subcategory": "Вечернее",
        "collection": "Evening Capsule",
        "retail_price": 1690.0,
        "sizes": ["XS", "S", "M"],
        "color": "Черный",
        "image_main": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Вечернее платье с длинным рукавом, закрытым воротом и асимметричной сборкой на юбке.",
        "care": "Только деликатная сухая чистка.",
        "boutique_name": "Бутик «PATRIZIA PEPE»",
        "boutique_address": "САЛОН «PATRIZIA PEPE» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-7",
        "sku": "GDM-10029",
        "brand": "GIUSEPPE DI MORABITO",
        "name": "Атласный корсетный топ на косточках",
        "gender": "ДЛЯ НЕЁ",
        "category": "Топы",
        "subcategory": "Корсеты",
        "collection": "SS26 Runway",
        "retail_price": 1420.0,
        "sizes": ["XS", "S", "M"],
        "color": "Черный",
        "image_main": "https://images.unsplash.com/photo-1551163943-3f6a855d1153?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=85",
        "brand_story": GIUSEPPE_STORY,
        "description": "Структурный корсетный топ из плотного шелкового сатина с вертикальными рельефами.",
        "care": "Сухая чистка.",
        "boutique_name": "Бутик «MAD FASHION»",
        "boutique_address": "САЛОН «MAD FASHION» Г. МИНСК, ПР. ПОБЕДИТЕЛЕЙ, 65"
    },
    {
        "id": "prod-8",
        "sku": "PP-312277",
        "brand": "PATRIZIA PEPE",
        "name": "Кожаная мини-сумка бьюти-кейс",
        "gender": "ДЛЯ НЕЁ",
        "category": "Аксессуары",
        "subcategory": "Сумки",
        "collection": "SS26 Runway",
        "retail_price": 980.0,
        "sizes": ["ONE SIZE"],
        "color": "Черный",
        "image_main": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=900&q=85",
        "image_model": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=900&q=85",
        "brand_story": PATRIZIA_STORY,
        "description": "Стеганая кожаная сумка-кейс из мягкой телячьей кожи наппа с фирменной биркой и ручкой сверху.",
        "care": "Протирать мягкой сухой салфеткой, использовать крем для натуральной кожи.",
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
    if not data or "brand" not in data[0]:
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
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    size: Optional[str] = Query(None),
    sort: Optional[str] = Query(None, description="stylist | price_asc | price_desc"),
):
    products = load_products()
    result = []
    categories_filter = [c.strip().lower() for c in category.split(",") if c.strip()] if category else []

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
        if categories_filter and p["category"].lower() not in categories_filter:
            continue
        if brand and p.get("brand", "").lower() != brand.lower():
            continue
        if color and p.get("color", "").lower() != color.lower():
            continue
        if gender and p.get("gender", "ДЛЯ НЕЁ").lower() != gender.lower():
            continue
        if size and size.upper() not in [s.upper() for s in p.get("sizes", [])]:
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
    raise HTTPException(status_code=404, detail="Модель одежды не найдена")


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
    products.append(new_prod)
    save_products(products)
    return new_prod


@app.get("/meta/filters")
def get_filter_options():
    products = load_products()
    categories = [
        "Верхняя одежда", "Платья", "Джинсы", "Блузы", "Джемперы",
        "Пиджаки", "Юбки", "Брюки", "Топы", "Боди", "Футболки",
        "Комбинезоны", "Белье", "Шорты", "Купальники и пляжная одежда", "Костюмы", "Аксессуары"
    ]
    brands = sorted(list({p.get("brand", "PATRIZIA PEPE") for p in products}))
    colors = sorted(list({p.get("color", "Черный") for p in products}))
    sizes = ["XS", "S", "M", "L", "XL", "ONE SIZE"]
    return {
        "categories": categories,
        "brands": brands,
        "colors": colors,
        "sizes": sizes,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
