import subprocess
import sys
import time
import os

SERVICES = [
    ("Catalog Service (:8001)", os.path.join("services", "catalog_service", "main.py")),
    ("Warehouse Service (:8002)", os.path.join("services", "warehouse_service", "main.py")),
    ("Order Service (:8003)", os.path.join("services", "order_service", "main.py")),
    ("Analytics Service (:8004)", os.path.join("services", "analytics_service", "main.py")),
    ("API Gateway & Web UI (:8000)", os.path.join("gateway_frontend", "main.py")),
]


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    processes = []

    print("=" * 68)
    print(" MONROE — Запуск микросервисной архитектуры")
    print("=" * 68)

    try:
        for name, script_rel_path in SERVICES:
            script_path = os.path.join(base_dir, script_rel_path)
            print(f"[+] Запуск {name} -> {script_rel_path}")
            proc = subprocess.Popen([sys.executable, script_path], cwd=base_dir)
            processes.append([name, script_path, proc])
            time.sleep(0.5)

        print("\n" + "=" * 68)
        print(" Все 5 микросервисов успешно запущены!")
        print(" Откройте в браузере: http://localhost:8000")
        print("=" * 68 + "\n")

        while True:
            time.sleep(2)
            # Если какой-то сервис упал (например, порт еще освобождался), автоматически перезапускаем его
            for item in processes:
                name, script_path, proc = item
                if proc.poll() is not None:
                    print(f"[!] Перезапуск {name}...")
                    item[2] = subprocess.Popen([sys.executable, script_path], cwd=base_dir)
    except KeyboardInterrupt:
        print("\n[!] Остановка всех микросервисов...")
        for name, _, proc in processes:
            proc.terminate()
        print("[OK] Все сервисы остановлены.")


if __name__ == "__main__":
    main()
