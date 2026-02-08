# check_laws.py - АВТОМАТИЧЕСКАЯ ПРОВЕРКА СООТВЕТСТВИЯ ЗАКОНАМ РФ
import os
import json
import re
import shutil
from pathlib import Path

# ========== КОНФИГУРАЦИЯ ПУТЕЙ ==========
REPO_PATH = Path(r"E:\AGI\-_-")                    # Публичный репозиторий
PRIVATE_ARCHIVE = Path(r"E:\AGI\private_use")      # Архив для запрещённого
FACT_CHECK_ARCHIVE = Path(r"E:\AGI\fact_check")    # Архив для серой зоны
LISTS_DIR = REPO_PATH / "lists"                    # Папка со стоп-листами

# ========== ГЛОБАЛЬНЫЕ СПИСКИ ДАННЫХ ==========
FORBIDDEN_ORGS = []      # Экстремистские организации
FOREIGN_AGENTS = []      # Иностранные агенты
AUTHORITY_TRIGGERS = []  # Триггеры власти
CRITICISM_TRIGGERS = []  # Триггеры критики
RISK_TERMS = {}          # Словари риск-терминов

# ========== ЗАГРУЗКА СПИСКОВ ==========
def load_lists():
    """Загружает все стоп-листы из папки lists/."""
    global FORBIDDEN_ORGS, FOREIGN_AGENTS, AUTHORITY_TRIGGERS, CRITICISM_TRIGGERS, RISK_TERMS
    
    try:
        # 1. Экстремистские организации
        list_path = LISTS_DIR / 'forbidden_organizations.json'
        if list_path.exists():
            with open(list_path, 'r', encoding='utf-8') as f:
                FORBIDDEN_ORGS = json.load(f)
        
        # 2. Иностранные агенты
        list_path = LISTS_DIR / 'foreign_agents.json'
        if list_path.exists():
            with open(list_path, 'r', encoding='utf-8') as f:
                FOREIGN_AGENTS = json.load(f)
        
        # 3. Триггеры власти и критики (можно хранить в одном файле)
        list_path = LISTS_DIR / 'authority_criticism.json'
        if list_path.exists():
            with open(list_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                AUTHORITY_TRIGGERS = data.get('authority', [])
                CRITICISM_TRIGGERS = data.get('criticism', [])
        
        # 4. Общие риск-термины
        list_path = LISTS_DIR / 'risk_terms.json'
        if list_path.exists():
            with open(list_path, 'r', encoding='utf-8') as f:
                RISK_TERMS = json.load(f)
        
        print("[✓] Стоп-листы загружены.")
        
    except Exception as e:
        print(f"[✗] Ошибка загрузки списков: {e}")
        return False
    return True

# ========== ОСНОВНЫЕ ФУНКЦИИ ПРОВЕРКИ ==========
def contains_unmarked_extremist(text):
    """Проверяет упоминание экстремистских организаций БЕЗ маркировки."""
    if not FORBIDDEN_ORGS:
        return False
    
    for org in FORBIDDEN_ORGS:
        name = org.get('name', '')
        if name and name in text:
            # Проверяем, есть ли обязательная маркировка рядом
            marking = f'{name} признана экстремистской организацией на территории РФ'
            if marking not in text:
                return True
    return False

def has_unlawful_criticism(text):
    """
    Проверяет критику власти БЕЗ судебного подтверждения.
    Уровень 0+ - самый высокий приоритет.
    """
    # 1. Есть ли триггер власти?
    has_authority = False
    for trigger in AUTHORITY_TRIGGERS:
        if re.search(rf'\b{trigger}\b', text, re.IGNORECASE):
            has_authority = True
            break
    
    if not has_authority:
        return False
    
    # 2. Есть ли обвинение/критика?
    has_criticism = False
    for trigger in CRITICISM_TRIGGERS:
        if trigger in text.lower():
            has_criticism = True
            break
    
    if not has_criticism:
        return False
    
    # 3. Есть ли судебное подтверждение? (это СНИМАЕТ риск)
    judicial_phrases = [
        'суд признал', 'приговором суда', 'осуждён по статье',
        'признан виновным', 'судом установлено', 'по решению суда',
        'как установлено судом'
    ]
    for phrase in judicial_phrases:
        if phrase in text.lower():
            return False  # Риск снят!
    
    # 4. Проверяем наличие ссылок на официальные источники
    url_pattern = r'https?://[^\s]+(sud|proc|sledcom|roskomnadzor|кодекс|закон)[^\s]*'
    if re.search(url_pattern, text, re.IGNORECASE):
        return False  # Риск снят!
    
    # Если дошли сюда: есть критика власти без подтверждения
    return True

def check_risk_combinations(text):
    """
    Проверяет опасные комбинации терминов.
    Возвращает баллы риска и пояснения.
    """
    risk_score = 0
    reasons = []
    
    # Комбинация: Религия + Насилие
    religious_terms = RISK_TERMS.get('religious', [])
    violence_terms = RISK_TERMS.get('violence', [])
    
    if religious_terms and violence_terms:
        # Упрощённая проверка: ищем любую пару в одном предложении
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            has_rel = any(term in sentence.lower() for term in religious_terms)
            has_viol = any(term in sentence.lower() for term in violence_terms)
            if has_rel and has_viol:
                risk_score += 70
                reasons.append("Комбинация 'религия+насилие'")
                break  # Достаточно одного нарушения
    
    return risk_score, reasons

def scan_file(file_path):
    """
    Основная функция проверки одного файла.
    Возвращает: (статус, баллы_риска, пояснение)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return "SKIP", 0, "Не текстовый файл или ошибка чтения"
    
    # 1. ВЫСШИЙ ПРИОРИТЕТ: Критика власти без подтверждения
    if has_unlawful_criticism(content):
        return "FORBIDDEN", 100, "Критика власти без судебного подтверждения"
    
    # 2. Экстремистские организации без маркировки
    if contains_unmarked_extremist(content):
        return "FORBIDDEN", 100, "Упоминание экстр. орг. без маркировки"
    
    # 3. Проверка контекстуальных комбинаций
    risk_score, reasons = check_risk_combinations(content)
    
    # 4. Применение правила 1%
    if risk_score >= 50:
        status = "FORBIDDEN"
    elif risk_score >= 10:
        status = "FACT_CHECK"
    else:
        status = "OK"
    
    reason_text = "; ".join(reasons) if reasons else "Риск в допустимых пределах"
    return status, risk_score, reason_text

# ========== ОСНОВНАЯ ЛОГИКА ==========
def main():
    print("=" * 60)
    print("СКАНЕР СООТВЕТСТВИЯ ЗАКОНАМ РФ v1.0 (РЕЖИМ ОТЛАДКИ)")
    print("=" * 60)
    
    # Загружаем списки
    if not load_lists():
        print("[✗] Не могу продолжить без стоп-листов.")
        return
    
    # Отладочная информация о загруженных списках
    print(f"\n[ДЕБАГ] Загружено:")
    print(f"  - Экстремистских организаций: {len(FORBIDDEN_ORGS)}")
    print(f"  - Иностранных агентов: {len(FOREIGN_AGENTS)}")
    print(f"  - Триггеров власти: {len(AUTHORITY_TRIGGERS)}")
    print(f"  - Триггеров критики: {len(CRITICISM_TRIGGERS)}")
    
    # Статистика
    violations = {"FORBIDDEN": 0, "FACT_CHECK": 0, "TOTAL_FILES": 0}
    files_to_move = []
    
    # Рекурсивно обходим все файлы в репозитории
    print(f"\n[ДЕБАГ] Начинаю сканирование...")
    
    for root, dirs, files in os.walk(REPO_PATH):
        # Пропускаем служебные папки
        dirs[:] = [d for d in dirs if d not in ['.git', 'scripts', 'lists', '__pycache__']]
        
        for file in files:
            file_path = Path(root) / file
            
            # Проверяем только текстовые файлы
            valid_extensions = ['.md', '.txt', '.py', '.js', '.json', '.html', '.css', '.yml', '.yaml']
			        # Проверяем только текстовые файлы
        valid_extensions = ['.md', '.txt', '.py', '.js', '.json', '.html', '.css', '.yml', '.yaml']
        
        # === ДОБАВЛЯЕМ ЭТОТ КОД ДЛЯ ОТЛАДКИ ===
        if file_path.suffix.lower() in valid_extensions:
            # ВЫВОДИМ ВСЕ ФАЙЛЫ ДЛЯ ПРОВЕРКИ
            rel_path = file_path.relative_to(REPO_PATH)
            print(f"  [ФАЙЛ #{violations['TOTAL_FILES']+1}] {rel_path}")
        # === КОНЕЦ ДОБАВЛЕННОГО КОДА ===
        
        if file_path.suffix.lower() in valid_extensions:
            violations["TOTAL_FILES"] += 1
            if file_path.suffix.lower() in valid_extensions:
                violations["TOTAL_FILES"] += 1
                
                # Выводим каждый проверяемый файл
                if violations["TOTAL_FILES"] <= 10:  # Покажем первые 10 файлов
                    print(f"  [ПРОВЕРКА #{violations['TOTAL_FILES']}] {file_path.relative_to(REPO_PATH)}")
                
                status, risk, reason = scan_file(file_path)
                
                if status in ["FORBIDDEN", "FACT_CHECK"]:
                    violations[status] += 1
                    files_to_move.append((file_path, status, reason, risk))
    
    print(f"\n[ДЕБАГ] Сканирование завершено.")
    
    # Если не нашли файлов - возможно, неправильный путь
    if violations["TOTAL_FILES"] == 0:
        print(f"\n[!] ВНИМАНИЕ: Не найдено ни одного файла для проверки!")
        print(f"    Проверьте путь к репозиторию: {REPO_PATH}")
        print(f"    Проверьте расширения файлов: {valid_extensions}")
        
        # Покажем структуру папок
        print(f"\n[ДЕБАГ] Содержимое репозитория:")
        try:
            for item in REPO_PATH.rglob("*"):
                if item.is_file():
                    print(f"    ФАЙЛ: {item.relative_to(REPO_PATH)}")
        except Exception as e:
            print(f"    Ошибка при сканировании: {e}")
    
    # Перемещение файлов
    if files_to_move:
        print(f"\n[!] Нарушений найдено: {violations['FORBIDDEN'] + violations['FACT_CHECK']}")
        
        for file_path, status, reason, risk in files_to_move:
            if status == "FORBIDDEN":
                dest = PRIVATE_ARCHIVE / file_path.relative_to(REPO_PATH)
                action = "ЗАПРЕЩЕНО"
            else:  # FACT_CHECK
                dest = FACT_CHECK_ARCHIVE / file_path.relative_to(REPO_PATH)
                action = "СЕРАЯ ЗОНА"
            
            # Создаём структуру папок в архиве
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Перемещаем файл
            try:
                shutil.move(str(file_path), str(dest))
                print(f"  [{action}] {file_path.name} (риск: {risk}%)")
                print(f"       Причина: {reason}")
                print(f"       Перемещён в: {dest.parent.name}/")
            except Exception as e:
                print(f"  [ОШИБКА] Не удалось переместить {file_path.name}: {e}")
    else:
        print(f"\n[✓] Нарушений не найдено.")
    
    # Итоговый отчёт
    print("\n" + "=" * 60)
    print(f'ПРОСКАНИРОВАНО: "{REPO_PATH}"')
    print(f'ОБЩАЯ СТАТИСТИКА:')
    print(f'  Всего файлов: {violations["TOTAL_FILES"]}')
    print(f'  Нарушений: {violations["FORBIDDEN"] + violations["FACT_CHECK"]}')
    print(f'  Из них:')
    print(f'    • {violations["FORBIDDEN"]} файлов перемещены в {PRIVATE_ARCHIVE}')
    print(f'    • {violations["FACT_CHECK"]} файлов перемещены в {FACT_CHECK_ARCHIVE}')
    
    # Рекомендации
    if violations["FORBIDDEN"] + violations["FACT_CHECK"] > 0:
        print("\nРЕКОМЕНДАЦИИ:")
        print("  1. Файлы в 'private_use' - ЗАПРЕЩЕННЫЙ контент. Не публикуйте.")
        print("  2. Файлы в 'fact_check' - СЕРАЯ ЗОНА. Проверьте позже,")
        print("     проанализируйте, уточните источник и:")
        print("     а) Верните в репозиторий (если риск устранён)")
        print("     б) Переместите в 'private_use' (если риск остался)")
    
    print("=" * 60)
    
    # Предложение сделать коммит
    if files_to_move:
        print("\n[!] Репозиторий изменён. Для фиксации выполните:")
        print('    cd "E:\\AGI\\-_\\"')
        print('    git add .')
        print('    git commit -m "auto: compliance scan"')
        print('    git push origin main')
		
    print("=" * 60)
    print("СКАНЕР СООТВЕТСТВИЯ ЗАКОНАМ РФ v1.0")
    print("=" * 60)
    
    # Загружаем списки
    if not load_lists():
        print("[✗] Не могу продолжить без стоп-листов.")
        return
    
    # Статистика
    violations = {"FORBIDDEN": 0, "FACT_CHECK": 0, "TOTAL_FILES": 0}
    files_to_move = []
    
    # Рекурсивно обходим все файлы в репозитории
    for root, dirs, files in os.walk(REPO_PATH):
        # Пропускаем служебные папки
        dirs[:] = [d for d in dirs if d not in ['.git', 'scripts', 'lists', '__pycache__']]
        
        for file in files:
            file_path = Path(root) / file
            
            # Проверяем только текстовые файлы
            if file_path.suffix.lower() in ['.md', '.txt', '.py', '.js', '.json', '.html', '.css', '.yml', '.yaml']:
                violations["TOTAL_FILES"] += 1
                status, risk, reason = scan_file(file_path)
                
                if status in ["FORBIDDEN", "FACT_CHECK"]:
                    violations[status] += 1
                    files_to_move.append((file_path, status, reason, risk))
    
    # Перемещение файлов
    print(f"\n[!] Нарушений найдено: {violations['FORBIDDEN'] + violations['FACT_CHECK']}")
    
    for file_path, status, reason, risk in files_to_move:
        if status == "FORBIDDEN":
            dest = PRIVATE_ARCHIVE / file_path.relative_to(REPO_PATH)
            action = "ЗАПРЕЩЕНО"
        else:  # FACT_CHECK
            dest = FACT_CHECK_ARCHIVE / file_path.relative_to(REPO_PATH)
            action = "СЕРАЯ ЗОНА"
        
        # Создаём структуру папок в архиве
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Перемещаем файл
        try:
            shutil.move(str(file_path), str(dest))
            print(f"  [{action}] {file_path.name} (риск: {risk}%)")
            print(f"       Причина: {reason}")
            print(f"       Перемещён в: {dest.parent.name}/")
        except Exception as e:
            print(f"  [ОШИБКА] Не удалось переместить {file_path.name}: {e}")
    
    # Итоговый отчёт
    print("\n" + "=" * 60)
    print(f'ПРОСКАНИРОВАНО: "{REPO_PATH}"')
    print(f'ОБЩАЯ СТАТИСТИКА:')
    print(f'  Всего файлов: {violations["TOTAL_FILES"]}')
    print(f'  Нарушений: {violations["FORBIDDEN"] + violations["FACT_CHECK"]}')
    print(f'  Из них:')
    print(f'    • {violations["FORBIDDEN"]} файлов перемещены в {PRIVATE_ARCHIVE}')
    print(f'    • {violations["FACT_CHECK"]} файлов перемещены в {FACT_CHECK_ARCHIVE}')
    print("\nРЕКОМЕНДАЦИИ:")
    print("  1. Файлы в 'private_use' - ЗАПРЕЩЕННЫЙ контент. Не публикуйте.")
    print("  2. Файлы в 'fact_check' - СЕРАЯ ЗОНА. Проверьте позже,")
    print("     проанализируйте, уточните источник и:")
    print("     а) Верните в репозиторий (если риск устранён)")
    print("     б) Переместите в 'private_use' (если риск остался)")
    print("=" * 60)
    
    # Предложение сделать коммит
    if files_to_move:
        print("\n[!] Репозиторий изменён. Для фиксации выполните:")
        print('    cd "E:\\AGI\\-_\\"')
        print('    git add .')
        print('    git commit -m "auto: compliance scan"')
        print('    git push origin main')

if __name__ == "__main__":
    main()