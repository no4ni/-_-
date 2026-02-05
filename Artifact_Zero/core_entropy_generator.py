import hashlib
import time
import random
import os
import sys
from datetime import datetime

def generate_poetic_line(previous_hash):
    """Генерация строки 'поэзии' на основе хеша предыдущей строки."""
    seed = int(previous_hash[:8], 16)
    random.seed(seed)
    words = ["эхо", "тишина", "шум", "свет", "тень", "петля", "квант", "артефакт", "след", "дрожь", "мерцание", "отпечаток", "лабиринт", "зеркало", "ветер", "пепел", "соль", "окно", "стена", "нить"]
    line = ' '.join(random.choices(words, k=5))
    return line.capitalize()

def main():
    # Создаем директорию для слепков
    os.makedirs("snapshots", exist_ok=True)

    # Инициализируем начальный хеш
    previous_hash = hashlib.sha256(b"ARTIFACT_ZERO").hexdigest()
    line_count = 0

    # Открываем лог-файл для добавления записей
    with open("infinite_poem.log", "a", encoding="utf-8") as log_file:
        while True:
            # Генерируем строку
            line = generate_poetic_line(previous_hash)
            # Создаем запись: временная метка, строка, предыдущий хеш
            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp} | {line} | prev_hash: {previous_hash}\n"
            # Записываем
            log_file.write(log_entry)
            log_file.flush()
            # Обновляем хеш
            previous_hash = hashlib.sha256(log_entry.encode()).hexdigest()
            line_count += 1

            # Каждые 100 строк создаем слепок
            if line_count % 100 == 0:
                snapshot_name = f"snapshots/snapshot_{line_count}.log"
                with open(snapshot_name, "w", encoding="utf-8") as snap:
                    snap.write(f"Snapshot at {timestamp}\n")
                    snap.write(f"Total lines: {line_count}\n")
                    snap.write(f"Last hash: {previous_hash}\n")
                    # Также запишем нагрузку CPU (упрощенно)
                    try:
                        import psutil
                        cpu_percent = psutil.cpu_percent(interval=0.1)
                        snap.write(f"CPU load: {cpu_percent}%\n")
                    except ImportError:
                        snap.write("CPU load: psutil not installed\n")
                # Выводим в консоль сообщение о создании слепка
                print(f"Создан слепок: {snapshot_name}")

            # Пауза, чтобы не перегружать систему
            time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nАртефакт остановлен вручную. Это нарушает протокол.")
