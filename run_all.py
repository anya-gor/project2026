import subprocess
import sys
import time
import os
import webbrowser

SERVICES = [
    ("Catalog Service (:8001)", os.path.join("services", "catalog_service", "main.py"), 8001),
    ("Warehouse Service (:8002)", os.path.join("services", "warehouse_service", "main.py"), 8002),
    ("Order Service (:8003)", os.path.join("services", "order_service", "main.py"), 8003),
    ("API Gateway & Web UI (:8000)", os.path.join("gateway_frontend", "main.py"), 8000),
]


def free_ports_on_windows():
    """Освобождает порты 8000-8003 и останавливает старые копии микросервисов перед новым запуском."""
    if os.name != "nt":
        return
    my_pid = os.getpid()
    try:
        cmd = (
            f"Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
            f"Where-Object {{ $_.ProcessId -ne {my_pid} -and $_.CommandLine -match 'run_all\\.py|catalog_service|warehouse_service|order_service|gateway_frontend' }} | "
            f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=6)
        time.sleep(1.0)
    except Exception:
        pass


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    processes = []

    print("=" * 68)
    print(" MONROE — Запуск микросервисной архитектуры")
    print("=" * 68)

    free_ports_on_windows()

    try:
        for name, script_rel_path, _ in SERVICES:
            script_path = os.path.join(base_dir, script_rel_path)
            print(f"[+] Запуск {name} -> {script_rel_path}")
            proc = subprocess.Popen([sys.executable, script_path], cwd=base_dir)
            processes.append([name, script_path, proc])
            time.sleep(0.5)

        url = "http://127.0.0.1:8000"
        print("\n" + "=" * 68)
        print(" Все 4 микросервиса успешно запущены!")
        print(f" Сайт доступен по адресу: {url}")
        print(" Для остановки нажмите Ctrl+C")
        print("=" * 68 + "\n")

        if "--no-browser" not in sys.argv:
            try:
                webbrowser.open(url)
            except Exception:
                pass

        while True:
            time.sleep(2)
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
