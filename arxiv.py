import requests
import xml.etree.ElementTree as ET
import json

url = "http://export.arxiv.org/api/query"
params = {
    'search_query': 'all:"self-referential" OR all:"metacognit*" AND cat:cs.AI',
    'start': 0,
    'max_results': 5,
    'sortBy': 'submittedDate',
    'sortOrder': 'descending'
}
response = requests.get(url, params=params)

articles = []  # Инициализируем список

if response.status_code == 200:
    root = ET.fromstring(response.content)
    
    # Пространство имён Atom
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
    for entry in root.findall('atom:entry', ns):
        title_elem = entry.find('atom:title', ns)
        summary_elem = entry.find('atom:summary', ns)
        published_elem = entry.find('atom:published', ns)
        
        # Проверяем, что элементы найдены
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Нет заголовка"
        summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else "Нет аннотации"
        published = published_elem.text if published_elem is not None else "Нет даты"
        
        articles.append({
            'title': title,
            'summary': summary,
            'published': published
        })
    
    # Выводим результат
    print(json.dumps(articles, indent=2, ensure_ascii=False))
else:
    print(f"Ошибка запроса: {response.status_code}")