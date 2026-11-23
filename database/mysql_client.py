import json
import os
import socket
import time
import pymysql
from pymysql.cursors import DictCursor

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.1.31")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD_ENV = os.getenv("MYSQL_PASSWORD", None)
MYSQL_DB = os.getenv("MYSQL_DATABASE", "monroe_db")

_working_password = None
_working_host = MYSQL_HOST
_last_port_check_time = 0.0
_last_port_open = False


def _is_mysql_port_open() -> bool:
    global _last_port_check_time, _last_port_open, _working_host
    now = time.time()
    if now - _last_port_check_time < 3.0:
        return _last_port_open
    _last_port_check_time = now
    for host_candidate in [MYSQL_HOST, "127.0.1.31", "MySQL-8.4", "127.0.0.1"]:
        try:
            with socket.create_connection((host_candidate, MYSQL_PORT), timeout=0.15):
                _working_host = host_candidate
                _last_port_open = True
                return True
        except OSError:
            continue
    _last_port_open = False
    return False


def _get_server_connection(include_db: bool = True):
    """
    Устанавливает соединение с MySQL в Open Server.
    Если порт 3306 закрыт (Open Server еще не запущен), мгновенно возвращает ошибку без задержки.
    """
    if not _is_mysql_port_open():
        raise ConnectionError(f"Порт MySQL {MYSQL_HOST}:{MYSQL_PORT} закрыт (Open Server не запущен)")
    global _working_password
    candidates = [MYSQL_PASSWORD_ENV] if MYSQL_PASSWORD_ENV is not None else (
        [_working_password, "", "root"] if _working_password is not None else ["", "root"]
    )
    last_err = None
    for pwd in candidates:
        if pwd is None:
            continue
        try:
            kwargs = {
                "host": _working_host,
                "port": MYSQL_PORT,
                "user": MYSQL_USER,
                "password": pwd,
                "charset": "utf8mb4",
                "cursorclass": DictCursor,
                "connect_timeout": 1.5,
                "autocommit": True,
            }
            if include_db:
                kwargs["database"] = MYSQL_DB
            conn = pymysql.connect(**kwargs)
            _working_password = pwd
            return conn
        except pymysql.err.OperationalError as e:
            # Если база еще не создана (код 1049 Unknown database)
            if include_db and e.args and e.args[0] == 1049:
                _working_password = pwd
                init_mysql_schema()
                return pymysql.connect(
                    host=_working_host,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=pwd,
                    database=MYSQL_DB,
                    charset="utf8mb4",
                    cursorclass=DictCursor,
                    connect_timeout=1.5,
                    autocommit=True,
                )
            last_err = e
        except Exception as e:
            last_err = e
    raise ConnectionError(f"MySQL (Open Server) на {MYSQL_HOST}:{MYSQL_PORT} недоступен: {last_err}")


def check_mysql_status() -> dict:
    try:
        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS ver;")
            row = cur.fetchone()
            cur.execute("SHOW TABLES;")
            tables = [list(t.values())[0] for t in cur.fetchall()]
        conn.close()
        return {
            "online": True,
            "database": MYSQL_DB,
            "host": f"{MYSQL_HOST}:{MYSQL_PORT}",
            "version": row["ver"] if row else "MySQL",
            "tables_count": len(tables),
            "tables": tables,
        }
    except Exception as e:
        return {
            "online": False,
            "database": MYSQL_DB,
            "host": f"{MYSQL_HOST}:{MYSQL_PORT}",
            "error": str(e),
        }


def init_mysql_schema():
    """Создает базу данных monroe_db и 4 основные таблицы (users, user_addresses, products, orders) в MySQL."""
    conn = _get_server_connection(include_db=False)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            cur.execute(f"USE `{MYSQL_DB}`;")

            # Убираем лишние складские таблицы списаний, чтобы в DBeaver было ровно 4 чистые таблицы сайта
            cur.execute("DROP TABLE IF EXISTS `writeoffs`;")
            cur.execute("DROP TABLE IF EXISTS `supply_batches`;")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS `users` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `login` VARCHAR(64) NOT NULL UNIQUE,
                    `country` VARCHAR(64) NOT NULL DEFAULT 'Беларусь',
                    `password` VARCHAR(128) NOT NULL,
                    `name` VARCHAR(128) NOT NULL DEFAULT '',
                    `email` VARCHAR(128) NOT NULL DEFAULT '',
                    `role` VARCHAR(16) NOT NULL DEFAULT 'user',
                    `addresses_json` TEXT,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS `user_addresses` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `user_login` VARCHAR(64) NOT NULL,
                    `address_text` VARCHAR(255) NOT NULL,
                    `is_primary` TINYINT(1) NOT NULL DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS `products` (
                    `id` VARCHAR(32) PRIMARY KEY,
                    `sku` VARCHAR(64) NOT NULL,
                    `brand` VARCHAR(128) NOT NULL,
                    `name` VARCHAR(255) NOT NULL,
                    `gender` VARCHAR(32) NOT NULL DEFAULT 'ДЛЯ НЕЁ',
                    `category` VARCHAR(128) NOT NULL,
                    `subcategory` VARCHAR(128) NOT NULL DEFAULT '',
                    `collection` VARCHAR(128) NOT NULL DEFAULT 'Осень 2026',
                    `retail_price` DOUBLE NOT NULL,
                    `sizes_json` TEXT NOT NULL,
                    `stock_by_size_json` TEXT,
                    `color` VARCHAR(64) NOT NULL DEFAULT 'Черный',
                    `is_new` TINYINT(1) NOT NULL DEFAULT 1,
                    `image_main` TEXT NOT NULL,
                    `image_model` TEXT NOT NULL,
                    `brand_story` TEXT,
                    `description` TEXT,
                    `care` TEXT,
                    `boutique_name` VARCHAR(128),
                    `boutique_address` VARCHAR(255)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS `orders` (
                    `order_id` VARCHAR(32) PRIMARY KEY,
                    `product_id` VARCHAR(32) NOT NULL,
                    `product_name` VARCHAR(255) NOT NULL,
                    `size` VARCHAR(32) NOT NULL,
                    `quantity` INT NOT NULL,
                    `unit_retail_price` DOUBLE NOT NULL,
                    `total_revenue` DOUBLE NOT NULL,
                    `total_supplier_cost` DOUBLE NOT NULL DEFAULT 0,
                    `gross_profit` DOUBLE NOT NULL DEFAULT 0,
                    `customer_name` VARCHAR(128) NOT NULL,
                    `city` VARCHAR(128) DEFAULT '',
                    `delivery_method` VARCHAR(128) DEFAULT '',
                    `payment_method` VARCHAR(128) DEFAULT '',
                    `email` VARCHAR(128) DEFAULT '',
                    `phone` VARCHAR(64) DEFAULT '',
                    `address` VARCHAR(255) DEFAULT '',
                    `comment` TEXT,
                    `sale_date` VARCHAR(32) NOT NULL,
                    `return_status` VARCHAR(32) DEFAULT 'NONE',
                    `return_reason` VARCHAR(255) DEFAULT '',
                    `allocations_json` TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS `order_returns` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `order_id` VARCHAR(32) NOT NULL UNIQUE,
                    `product_id` VARCHAR(32) NOT NULL,
                    `product_name` VARCHAR(255) NOT NULL,
                    `size` VARCHAR(32) NOT NULL,
                    `quantity` INT NOT NULL,
                    `customer_name` VARCHAR(128) NOT NULL,
                    `reason` VARCHAR(255) NOT NULL,
                    `status` VARCHAR(32) NOT NULL DEFAULT 'RETURN_REQUESTED',
                    `restocked_to_store` TINYINT(1) NOT NULL DEFAULT 0,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
    finally:
        conn.close()


# ==================== СИНХРОНИЗАЦИЯ КАТАЛОГА (PRODUCTS) ====================
def mysql_load_products(default_products: list) -> list | None:
    try:
        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM `products`;")
            cnt = cur.fetchone()["cnt"]
            if cnt == 0:
                mysql_save_products(default_products)
            cur.execute("SELECT * FROM `products`;")
            rows = cur.fetchall()
        conn.close()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "sku": r["sku"],
                "brand": r["brand"],
                "name": r["name"],
                "gender": r["gender"],
                "category": r["category"],
                "subcategory": r["subcategory"],
                "collection": r["collection"],
                "retail_price": float(r["retail_price"]),
                "sizes": json.loads(r["sizes_json"] or '["S","M"]'),
                "color": r["color"],
                "is_new": bool(r["is_new"]),
                "image_main": r["image_main"],
                "image_model": r["image_model"],
                "brand_story": r["brand_story"] or "",
                "description": r["description"] or "",
                "care": r["care"] or "",
                "boutique_name": r["boutique_name"] or "",
                "boutique_address": r["boutique_address"] or "",
            })
        return result
    except Exception:
        return None


def mysql_save_products(products: list) -> bool:
    try:
        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM `products`;")
            for p in products:
                cur.execute(
                    """
                    INSERT INTO `products` (
                        `id`, `sku`, `brand`, `name`, `gender`, `category`, `subcategory`,
                        `collection`, `retail_price`, `sizes_json`, `color`, `is_new`,
                        `image_main`, `image_model`, `brand_story`, `description`, `care`,
                        `boutique_name`, `boutique_address`
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
                    """,
                    (
                        p["id"], p["sku"], p.get("brand", "PATRIZIA PEPE"), p["name"],
                        p.get("gender", "ДЛЯ НЕЁ"), p["category"], p.get("subcategory", ""),
                        p.get("collection", "Осень 2026"), float(p["retail_price"]),
                        json.dumps(p.get("sizes", ["S", "M"]), ensure_ascii=False),
                        p.get("color", "Черный"), 1 if p.get("is_new", True) else 0,
                        p.get("image_main", ""), p.get("image_model", ""),
                        p.get("brand_story", ""), p.get("description", ""), p.get("care", ""),
                        p.get("boutique_name", ""), p.get("boutique_address", ""),
                    ),
                )
        conn.close()
        return True
    except Exception:
        return False


# ==================== СИНХРОНИЗАЦИЯ ПОЛЬЗОВАТЕЛЕЙ (USERS) ====================
def mysql_load_users(default_users: list) -> list | None:
    try:
        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM `users`;")
            if cur.fetchone()["cnt"] == 0:
                mysql_save_users(default_users)
            cur.execute("SELECT * FROM `users`;")
            rows = cur.fetchall()
        conn.close()
        result = []
        for r in rows:
            result.append({
                "login": r["login"],
                "country": r["country"],
                "password": r["password"],
                "name": r["name"],
                "email": r["email"],
                "role": r["role"],
                "addresses": json.loads(r["addresses_json"] or "[]"),
            })
        return result
    except Exception:
        return None


def mysql_save_users(users: list) -> bool:
    try:
        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM `user_addresses`;")
            cur.execute("DELETE FROM `users`;")
            for u in users:
                cur.execute(
                    """
                    INSERT INTO `users` (`login`, `country`, `password`, `name`, `email`, `role`, `addresses_json`)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        u["login"], u.get("country", "Беларусь"), u["password"],
                        u.get("name", ""), u.get("email", ""), u.get("role", "user"),
                        json.dumps(u.get("addresses", []), ensure_ascii=False),
                    ),
                )
                for a in u.get("addresses", []):
                    cur.execute(
                        """
                        INSERT INTO `user_addresses` (`user_login`, `address_text`, `is_primary`)
                        VALUES (%s, %s, %s);
                        """,
                        (u["login"], a.get("text", ""), 1 if a.get("is_primary") else 0),
                    )
        conn.close()
        return True
    except Exception:
        return False


def mysql_load_batches(default_batches: list) -> list | None:
    return None


def mysql_save_batches(batches: list) -> bool:
    """Синхронизирует точные остатки по размерам (XS, S, M, L, XL) прямо в столбец stock_by_size_json таблицы products."""
    try:
        stock_by_prod = {}
        for b in batches:
            if b.get("remaining_quantity", 0) <= 0:
                continue
            pid = b["product_id"]
            sz = b["size"]
            if pid not in stock_by_prod:
                stock_by_prod[pid] = {}
            stock_by_prod[pid][sz] = stock_by_prod[pid].get(sz, 0) + int(b["remaining_quantity"])

        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            for pid, sz_map in stock_by_prod.items():
                cur.execute(
                    "UPDATE `products` SET `stock_by_size_json` = %s WHERE `id` = %s;",
                    (json.dumps(sz_map, ensure_ascii=False), pid),
                )
        conn.close()
        return True
    except Exception:
        return False


# ==================== СИНХРОНИЗАЦИЯ ЗАКАЗОВ (ORDERS) ====================
def mysql_load_orders(default_orders: list) -> list | None:
    try:
        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM `orders`;")
            if cur.fetchone()["cnt"] == 0:
                mysql_save_orders(default_orders)
            cur.execute("SELECT * FROM `orders` ORDER BY `sale_date` DESC;")
            rows = cur.fetchall()
        conn.close()
        result = []
        for r in rows:
            result.append({
                "order_id": r["order_id"],
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "size": r["size"],
                "quantity": int(r["quantity"]),
                "unit_retail_price": float(r["unit_retail_price"]),
                "total_revenue": float(r["total_revenue"]),
                "total_supplier_cost": float(r["total_supplier_cost"]),
                "gross_profit": float(r["gross_profit"]),
                "customer_name": r["customer_name"],
                "city": r["city"],
                "delivery_method": r["delivery_method"],
                "payment_method": r["payment_method"],
                "email": r["email"],
                "phone": r["phone"],
                "address": r["address"],
                "comment": r["comment"],
                "sale_date": str(r["sale_date"]),
                "return_status": r.get("return_status") or "NONE",
                "return_reason": r.get("return_reason") or "",
                "allocations": json.loads(r["allocations_json"] or "[]"),
            })
        return result
    except Exception:
        return None


def mysql_save_orders(orders: list) -> bool:
    try:
        conn = _get_server_connection(include_db=True)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM `order_returns`;")
            cur.execute("DELETE FROM `orders`;")
            for o in orders:
                r_status = o.get("return_status", "NONE")
                r_reason = o.get("return_reason", "")
                cur.execute(
                    """
                    INSERT INTO `orders` (
                        `order_id`, `product_id`, `product_name`, `size`, `quantity`,
                        `unit_retail_price`, `total_revenue`, `total_supplier_cost`, `gross_profit`,
                        `customer_name`, `city`, `delivery_method`, `payment_method`,
                        `email`, `phone`, `address`, `comment`, `sale_date`,
                        `return_status`, `return_reason`, `allocations_json`
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
                    """,
                    (
                        o["order_id"], o["product_id"], o["product_name"], o["size"], int(o["quantity"]),
                        float(o["unit_retail_price"]), float(o["total_revenue"]),
                        float(o.get("total_supplier_cost", 0)), float(o.get("gross_profit", 0)),
                        o.get("customer_name", ""), o.get("city", ""), o.get("delivery_method", ""),
                        o.get("payment_method", ""), o.get("email", ""), o.get("phone", ""),
                        o.get("address", ""), o.get("comment", ""), str(o["sale_date"]),
                        r_status, r_reason,
                        json.dumps(o.get("allocations", []), ensure_ascii=False),
                    ),
                )
                # Если по заказу оформлена заявка на возврат или принято решение админом — пишем и в таблицу order_returns
                if r_status != "NONE":
                    is_defect = "брак" in r_reason.lower()
                    restocked = 1 if (r_status == "RETURN_APPROVED" and not is_defect) else 0
                    cur.execute(
                        """
                        INSERT INTO `order_returns` (
                            `order_id`, `product_id`, `product_name`, `size`, `quantity`,
                            `customer_name`, `reason`, `status`, `restocked_to_store`
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            o["order_id"], o["product_id"], o["product_name"], o["size"],
                            int(o["quantity"]), o.get("customer_name", ""), r_reason, r_status, restocked,
                        ),
                    )
        conn.close()
        return True
    except Exception:
        return False
