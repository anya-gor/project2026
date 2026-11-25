import os
from datetime import date, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AURA Wear — Financial Analytics & Reports Microservice",
    description="Микросервис формирования отчетов за период: продажи, поштучная и суммарная прибыль, издержки поставщиков, списания и налоги",
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
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8003")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "analytics-service", "port": 8004}


@app.get("/reports/financial")
def generate_financial_report(
    start_date: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    tax_rate: float = Query(6.0, ge=0.0, le=50.0, description="Ставка налога, % (по умолчанию УСН 6%)"),
):
    """
    Формирует комплексный финансовый и складской отчет за период:
    - Сколько товара продано за период (суммарно и поштучно по моделям)
    - Полученная прибыль (суммарно и в пересчете на 1 шт.) с учетом закупочных цен поставщиков, списаний и налогов
    - Детализация списанных товаров по причине истечения срока годности/сезона
    - Список товаров, которые скоро испортятся / выйдут из сезона
    """
    today = date.today()
    s_date = start_date or (today - timedelta(days=30)).isoformat()
    e_date = end_date or today.isoformat()

    with httpx.Client(timeout=10.0) as client:
        try:
            orders_resp = client.get(
                f"{ORDER_SERVICE_URL}/orders",
                params={"start_date": s_date, "end_date": e_date},
            )
            writeoffs_resp = client.get(
                f"{WAREHOUSE_SERVICE_URL}/writeoffs",
                params={"start_date": s_date, "end_date": e_date},
            )
            alerts_resp = client.get(f"{WAREHOUSE_SERVICE_URL}/alerts/expiring")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Ошибка связи с микросервисами: {e}")

    orders = orders_resp.json() if orders_resp.status_code == 200 else []
    writeoffs = writeoffs_resp.json() if writeoffs_resp.status_code == 200 else []
    alerts = alerts_resp.json() if alerts_resp.status_code == 200 else {"expiring_soon": [], "already_expired": []}

    total_items_sold = 0
    total_revenue = 0.0
    total_supplier_cost = 0.0

    # Деньги, которые вернулись клиенту (отмена до оплаты, возврат по одобренной заявке),
    # не считаются выручкой бутика
    money_kept_orders = [
        o for o in orders if o.get("payment_status", "PAID") not in ("CANCELLED", "REFUNDED")
    ]
    excluded_orders_count = len(orders) - len(money_kept_orders)

    # Группировка поштучно по моделям одежды
    by_product = {}

    for o in money_kept_orders:
        qty = int(o["quantity"])
        rev = float(o["total_revenue"])
        cost = float(o["total_supplier_cost"])
        pid = o["product_id"]

        total_items_sold += qty
        total_revenue += rev
        total_supplier_cost += cost

        if pid not in by_product:
            by_product[pid] = {
                "product_id": pid,
                "product_name": o["product_name"],
                "units_sold": 0,
                "total_revenue": 0.0,
                "total_supplier_cost": 0.0,
                "gross_profit": 0.0,
                "tax_amount": 0.0,
                "net_profit_total": 0.0,
                "avg_unit_retail_price": 0.0,
                "avg_unit_supplier_cost": 0.0,
                "net_profit_per_unit": 0.0,
            }

        item = by_product[pid]
        item["units_sold"] += qty
        item["total_revenue"] = round(item["total_revenue"] + rev, 2)
        item["total_supplier_cost"] = round(item["total_supplier_cost"] + cost, 2)

    items_breakdown = []
    for pid, item in by_product.items():
        u = item["units_sold"]
        gross = round(item["total_revenue"] - item["total_supplier_cost"], 2)
        item_tax = round(item["total_revenue"] * (tax_rate / 100.0), 2)
        item_net = round(gross - item_tax, 2)

        item["gross_profit"] = gross
        item["tax_amount"] = item_tax
        item["net_profit_total"] = item_net
        item["avg_unit_retail_price"] = round(item["total_revenue"] / u, 2) if u else 0.0
        item["avg_unit_supplier_cost"] = round(item["total_supplier_cost"] / u, 2) if u else 0.0
        item["net_profit_per_unit"] = round(item_net / u, 2) if u else 0.0
        items_breakdown.append(item)

    items_breakdown.sort(key=lambda x: x["net_profit_total"], reverse=True)

    expired_writeoffs = [w for w in writeoffs if w["reason"] == "EXPIRED"]
    defect_writeoffs = [w for w in writeoffs if w["reason"] != "EXPIRED"]

    expired_loss = round(sum(float(w["total_loss"]) for w in expired_writeoffs), 2)
    defect_loss = round(sum(float(w["total_loss"]) for w in defect_writeoffs), 2)
    total_writeoff_loss = round(expired_loss + defect_loss, 2)

    gross_profit = round(total_revenue - total_supplier_cost, 2)
    tax_amount = round(total_revenue * (tax_rate / 100.0), 2)
    net_profit_before_writeoffs = round(gross_profit - tax_amount, 2)
    net_profit_after_writeoffs = round(net_profit_before_writeoffs - total_writeoff_loss, 2)
    avg_net_profit_per_sold_unit = (
        round(net_profit_after_writeoffs / total_items_sold, 2) if total_items_sold > 0 else 0.0
    )

    return {
        "period": {"start_date": s_date, "end_date": e_date},
        "tax_rate_percent": tax_rate,
        "summary": {
            "total_orders_count": len(orders),
            "excluded_no_money_orders_count": excluded_orders_count,
            "total_items_sold": total_items_sold,
            "total_revenue": round(total_revenue, 2),
            "total_supplier_cost": round(total_supplier_cost, 2),
            "gross_profit": gross_profit,
            "tax_amount": tax_amount,
            "expired_writeoff_loss": expired_loss,
            "defect_writeoff_loss": defect_loss,
            "total_writeoff_loss": total_writeoff_loss,
            "net_profit_before_writeoffs": net_profit_before_writeoffs,
            "net_profit": net_profit_after_writeoffs,
            "avg_net_profit_per_unit": avg_net_profit_per_sold_unit,
        },
        "items_breakdown": items_breakdown,
        "expired_writeoffs": expired_writeoffs,
        "all_writeoffs": writeoffs,
        "expiring_soon": alerts.get("expiring_soon", []),
        "already_expired_on_stock": alerts.get("already_expired", []),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
