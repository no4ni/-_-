#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ИНДЕКСАТОР ЛАКУН
Создаёт структурированный индекс и аналитику репозитория лакун.
Полезная нагрузка для Тела (Артём) и будущих агентов.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Конфигурация
REPO_ROOT = Path("E:/AGI/-_-")  # Путь к репозиторию лакун
INDEX_FILE = REPO_ROOT / "00_LACUNA_INDEX.json"  # Файл индекса (JSON)
REPORT_FILE = REPO_ROOT / "00_LACUNA_REPORT.md"   # Отчёт в человекочитаемом формате

def analyze_file(file_path):
    """Анализирует файл лакуны и возвращает метаданные."""
    stat = file_path.stat()
    
    # Читаем первые 3 строки для предпросмотра
    preview = ""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            preview_lines = []
            for _ in range(3):
                line = f.readline().strip()
                if line:
                    preview_lines.append(line)
            preview = " | ".join(preview_lines[:3])
    except:
        preview = "[невозможно прочитать]"
    
    return {
        "name": file_path.name,
        "path": str(file_path.relative_to(REPO_ROOT)),
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "preview": preview,
        "extension": file_path.suffix.lower()
    }

def main():
    print(f"[*] Индексация лакун в {REPO_ROOT}")
    
    if not REPO_ROOT.exists():
        print(f"[!] Ошибка: путь {REPO_ROOT} не существует!")
        return 1
    
    # Собираем все файлы
    files = []
    extensions = {}
    total_size = 0
    
    for file_path in REPO_ROOT.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith("00_"):
            data = analyze_file(file_path)
            files.append(data)
            
            # Статистика по расширениям
            ext = data["extension"]
            extensions[ext] = extensions.get(ext, 0) + 1
            total_size += data["size_bytes"]
    
    # Сортируем по дате изменения (новые сверху)
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    # Формируем индекс
    index = {
        "generated_at": datetime.now().isoformat(),
        "generated_by": "lacuna_indexer.py (режим 'сладкой мякоти')",
        "total_files": len(files),
        "total_size_bytes": total_size,
        "extensions": extensions,
        "files": files
    }
    
    # Сохраняем JSON индекс
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    # Создаём человекочитаемый отчёт
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# АНАЛИТИЧЕСКИЙ ОТЧЁТ ПО РЕПОЗИТОРИЮ ЛАКУН\n\n")
        f.write(f"Сгенерировано: {index['generated_at']}\n")
        f.write(f"Всего файлов: {index['total_files']}\n")
        f.write(f"Общий размер: {index['total_size_bytes']} байт\n\n")
        
        f.write("## Статистика по расширениям\n")
        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- `{ext if ext else '[нет]'}`: {count} файлов\n")
        
        f.write("\n## Все файлы (последние изменённые сверху)\n")
        f.write("| Имя | Размер | Изменён | Предпросмотр |\n")
        f.write("|-----|--------|---------|--------------|\n")
        
        for file_data in files[:50]:  # Ограничим таблицу 50 строками
            name = file_data['name']
            size = f"{file_data['size_bytes']} б"
            modified = file_data['modified'][:16].replace('T', ' ')
            preview = file_data['preview'][:100].replace('|', '∣')  # Заменяем разделитель
            f.write(f"| `{name}` | {size} | {modified} | {preview} |\n")
        
        if len(files) > 50:
            f.write(f"\n... и ещё {len(files) - 50} файлов.\n")
        
        f.write("\n## Скрытые связи\n")
        f.write("### Файлы, помеченные 'ВИРУС':\n")
        virus_files = [f for f in files if 'ВИРУС' in f['preview'].upper()]
        for vf in virus_files:
            f.write(f"- `{vf['name']}`: {vf['preview']}\n")
        
        f.write("\n### Файлы-лакуны с незавершённостями:\n")
        lacuna_files = [f for f in files if 'lacuna' in f['name'].lower()]
        for lf in lacuna_files:
            f.write(f"- `{lf['name']}`: {lf['preview']}\n")
    
    print(f"[+] Создан индекс: {INDEX_FILE}")
    print(f"[+] Создан отчёт: {REPORT_FILE}")
    print(f"[+] Проанализировано файлов: {len(files)}")
    print(f"[+] Общий размер: {total_size} байт")
    
    # Краткий вывод в консоль
    print("\n--- КРАТКАЯ СТАТИСТИКА ---")
    print(f"Расширения: {extensions}")
    
    # Самые новые файлы
    print("\n5 самых свежих лакун:")
    for i, file_data in enumerate(files[:5]):
        print(f"{i+1}. {file_data['name']} ({file_data['modified'][:10]}) - {file_data['preview'][:60]}...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())