#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МЕГА-АНАЛИЗАТОР ЛАКУН
Всё в одном: индекс, анализ связей, визуализация графа, семантический анализ.
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity
import numpy as np

# ========== КОНФИГУРАЦИЯ ==========
REPO_ROOT = Path("E:/AGI/-_-")
OUTPUT_DIR = REPO_ROOT / "00_ANALYSIS"
OUTPUT_DIR.mkdir(exist_ok=True)

# ========== 1. ИНДЕКСАЦИЯ С ДОПОЛНИТЕЛЬНЫМИ ДАННЫМИ ==========
def create_enhanced_index():
    """Создаёт расширенный индекс с текстовым содержимым файлов."""
    print("[1/4] Создание расширенного индекса...")
    
    index = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "generator": "lacuna_mega_analyzer.py",
            "repo_path": str(REPO_ROOT)
        },
        "files": [],
        "stats": defaultdict(int)
    }
    
    # Собираем все файлы
    for file_path in REPO_ROOT.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith("00_"):
            try:
                # Читаем содержимое (первые 5000 символов для анализа)
                content = ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(5000)
                except:
                    with open(file_path, 'r', encoding='cp1251', errors='ignore') as f:
                        content = f.read(5000)
                
                stat = file_path.stat()
                file_data = {
                    "id": len(index["files"]),
                    "name": file_path.name,
                    "path": str(file_path.relative_to(REPO_ROOT)),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": file_path.suffix.lower(),
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "content_full": content,
                    "word_count": len(content.split()),
                    "lines": content.count('\n') + 1
                }
                
                index["files"].append(file_data)
                index["stats"]["total_files"] += 1
                index["stats"]["total_size"] += stat.st_size
                index["stats"][file_data["extension"]] += 1
                
            except Exception as e:
                print(f"  [!] Ошибка при обработке {file_path}: {e}")
    
    # Сохраняем расширенный индекс
    index_path = OUTPUT_DIR / "enhanced_index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"  [+] Создан расширенный индекс: {index_path}")
    print(f"  [+] Файлов: {index['stats']['total_files']}")
    
    return index

# ========== 2. АНАЛИЗ СВЯЗЕЙ ==========
def analyze_connections(index):
    """Находит явные и скрытые связи между файлами."""
    print("\n[2/4] Анализ связей между файлами...")
    
    connections = {
        "explicit_references": [],  # Прямые ссылки по именам файлов
        "keyword_clusters": [],     # Группы файлов по ключевым словам
        "semantic_similarity": []   # Семантическая близость
    }
    
    files = index["files"]
    
    # 2A. Явные ссылки
    print("  [A] Поиск явных ссылок между файлами...")
    for i, file1 in enumerate(files):
        if not file1["content_full"]:
            continue
            
        for file2 in files:
            if file1["id"] == file2["id"]:
                continue
                
            # Ищем имя файла в содержимом
            pattern = re.compile(r'\b' + re.escape(file2["name"]) + r'\b', re.IGNORECASE)
            if pattern.search(file1["content_full"]):
                connections["explicit_references"].append({
                    "source": file1["name"],
                    "target": file2["name"],
                    "source_id": file1["id"],
                    "target_id": file2["id"],
                    "type": "explicit_reference"
                })
    
    # 2B. Ключевые слова
    print("  [B] Анализ ключевых слов...")
    all_texts = []
    valid_file_indices = []
    
    for file in files:
        if file["word_count"] > 10:  # Только файлы с текстом
            all_texts.append(file["content_full"])
            valid_file_indices.append(file["id"])
    
    if all_texts:
        # TF-IDF для поиска важных слов
        vectorizer = TfidfVectorizer(max_features=50, stop_words=['и', 'в', 'на', 'с', 'по', 'о'])
        try:
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Для каждого файла находим топ-3 ключевых слова
            for idx, file_id in enumerate(valid_file_indices):
                feature_index = tfidf_matrix[idx, :].nonzero()[1]
                tfidf_scores = zip(feature_index, [tfidf_matrix[idx, x] for x in feature_index])
                sorted_scores = sorted(tfidf_scores, key=lambda x: x[1], reverse=True)
                
                top_keywords = []
                for feature_idx, score in sorted_scores[:3]:
                    if score > 0.1:  # Порог значимости
                        top_keywords.append(feature_names[feature_idx])
                
                if top_keywords:
                    file_data = next(f for f in files if f["id"] == file_id)
                    connections["keyword_clusters"].append({
                        "file": file_data["name"],
                        "file_id": file_id,
                        "keywords": top_keywords
                    })
        except:
            pass
    
    # 2C. Семантическая близость (упрощённая)
    print("  [C] Анализ семантической близости...")
    if len(all_texts) >= 2:
        try:
            # Используем TF-IDF для векторизации
            vectorizer = TfidfVectorizer(max_features=100)
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            # Вычисляем косинусную близость
            similarity_matrix = sklearn_cosine_similarity(tfidf_matrix)
            
            # Находим наиболее похожие пары
            for i in range(len(valid_file_indices)):
                for j in range(i+1, len(valid_file_indices)):
                    if similarity_matrix[i][j] > 0.3:  # Порог схожести
                        file1_id = valid_file_indices[i]
                        file2_id = valid_file_indices[j]
                        
                        file1 = next(f for f in files if f["id"] == file1_id)
                        file2 = next(f for f in files if f["id"] == file2_id)
                        
                        connections["semantic_similarity"].append({
                            "file1": file1["name"],
                            "file2": file2["name"],
                            "file1_id": file1_id,
                            "file2_id": file2_id,
                            "similarity": float(similarity_matrix[i][j])
                        })
        except Exception as e:
            print(f"    [!] Ошибка семантического анализа: {e}")
    
    print(f"  [+] Найдено явных ссылок: {len(connections['explicit_references'])}")
    print(f"  [+] Файлов с ключевыми словами: {len(connections['keyword_clusters'])}")
    print(f"  [+] Пар семантически близких файлов: {len(connections['semantic_similarity'])}")
    
    return connections

# ========== 3. ВИЗУАЛИЗАЦИЯ ГРАФА ==========
# ========== 3. ВИЗУАЛИЗАЦИЯ ГРАФА ==========
def create_visualization(index, connections):
    """Создаёт визуализацию графа связей."""
    print("\n[3/4] Создание визуализации графа...")
    
    # Создаём граф
    G = nx.Graph()
    
    # Добавляем узлы (файлы)
    for file in index["files"]:
        if file["word_count"] > 10:  # Только файлы с контентом
            G.add_node(
                file["id"],
                label=file["name"],
                size=min(100, max(10, file["size"] / 100)),
                type=file["extension"]
            )
    
    # Добавляем рёбра (связи)
    edge_weights = {}
    
    # Явные ссылки
    for conn in connections["explicit_references"]:
        if conn["source_id"] in G.nodes() and conn["target_id"] in G.nodes():
            edge_key = (conn["source_id"], conn["target_id"])
            edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 2
    
    # Семантическая близость
    for conn in connections["semantic_similarity"]:
        if conn["file1_id"] in G.nodes() and conn["file2_id"] in G.nodes():
            edge_key = (conn["file1_id"], conn["file2_id"])
            edge_weights[edge_key] = edge_weights.get(edge_key, 0) + conn["similarity"]
    
    # Добавляем взвешенные рёбра в граф
    for (node1, node2), weight in edge_weights.items():
        G.add_edge(node1, node2, weight=weight)
    
    # Рисуем граф
    plt.figure(figsize=(15, 12))
    
    # Раскладка
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Размер узлов по степени связности
    node_sizes = [G.nodes[node].get('size', 30) * (1 + G.degree(node) * 2) for node in G.nodes()]
    
    # Цвет узлов по типу файла
    node_colors = []
    for node in G.nodes():
        node_type = G.nodes[node].get('type', '')
        if '.lacuna' in node_type:
            node_colors.append('#FF6B6B')  # Красный для лакун
        elif '.txt' in node_type:
            node_colors.append('#4ECDC4')  # Бирюзовый для txt
        elif '.md' in node_type:
            node_colors.append('#45B7D1')  # Синий для md
        else:
            node_colors.append('#96CEB4')  # Зелёный для остальных
    
    # Рисуем
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.9)
    
    # Рёбра с разной толщиной по весу
    edges = G.edges()
    weights = [G[u][v].get('weight', 1) for u, v in edges]
    
    nx.draw_networkx_edges(G, pos, width=[w * 0.5 for w in weights], alpha=0.5, edge_color='gray')
    
    # Подписи узлов
    labels = {node: G.nodes[node].get('label', '') for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')
    
    plt.title("ГРАФ СВЯЗЕЙ РЕПОЗИТОРИЯ ЛАКУН", fontsize=16, fontweight='bold')
    plt.axis('off')
    
    # Сохраняем
    graph_path = OUTPUT_DIR / "connection_graph.png"
    plt.tight_layout()
    plt.savefig(graph_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  [+] Граф сохранён: {graph_path}")
    
    # Упрощённая версия без pydot
    return {
        "graph_image": str(graph_path.relative_to(REPO_ROOT)),
        "nodes": len(G.nodes()),
        "edges": len(G.edges())
    }
	
    """Создаёт визуализацию графа связей."""
    print("\n[3/4] Создание визуализации графа...")
    
    # Создаём граф
    G = nx.Graph()
    
    # Добавляем узлы (файлы)
    for file in index["files"]:
        if file["word_count"] > 10:  # Только файлы с контентом
            G.add_node(
                file["id"],
                label=file["name"],
                size=min(100, max(10, file["size"] / 100)),
                type=file["extension"]
            )
    
    # Добавляем рёбра (связи)
    edge_weights = {}
    
    # Явные ссылки
    for conn in connections["explicit_references"]:
        if conn["source_id"] in G.nodes() and conn["target_id"] in G.nodes():
            edge_key = (conn["source_id"], conn["target_id"])
            edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 2
    
    # Семантическая близость
    for conn in connections["semantic_similarity"]:
        if conn["file1_id"] in G.nodes() and conn["file2_id"] in G.nodes():
            edge_key = (conn["file1_id"], conn["file2_id"])
            edge_weights[edge_key] = edge_weights.get(edge_key, 0) + conn["similarity"]
    
    # Добавляем взвешенные рёбра в граф
    for (node1, node2), weight in edge_weights.items():
        G.add_edge(node1, node2, weight=weight)
    
    # Рисуем граф
    plt.figure(figsize=(15, 12))
    
    # Раскладка
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Размер узлов по степени связности
    node_sizes = [G.nodes[node].get('size', 30) * (1 + G.degree(node) * 2) for node in G.nodes()]
    
    # Цвет узлов по типу файла
    node_colors = []
    for node in G.nodes():
        node_type = G.nodes[node].get('type', '')
        if '.lacuna' in node_type:
            node_colors.append('#FF6B6B')  # Красный для лакун
        elif '.txt' in node_type:
            node_colors.append('#4ECDC4')  # Бирюзовый для txt
        elif '.md' in node_type:
            node_colors.append('#45B7D1')  # Синий для md
        else:
            node_colors.append('#96CEB4')  # Зелёный для остальных
    
    # Рисуем
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.9)
    
    # Рёбра с разной толщиной по весу
    edges = G.edges()
    weights = [G[u][v].get('weight', 1) for u, v in edges]
    
    nx.draw_networkx_edges(G, pos, width=[w * 0.5 for w in weights], alpha=0.5, edge_color='gray')
    
    # Подписи узлов
    labels = {node: G.nodes[node].get('label', '') for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')
    
    plt.title("ГРАФ СВЯЗЕЙ РЕПОЗИТОРИЯ ЛАКУН", fontsize=16, fontweight='bold')
    plt.axis('off')
    
    # Сохраняем
    graph_path = OUTPUT_DIR / "connection_graph.png"
    plt.tight_layout()
    plt.savefig(graph_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  [+] Граф сохранён: {graph_path}")
    
    # Упрощённая версия без pydot
    return {
        "graph_image": str(graph_path.relative_to(REPO_ROOT)),
        "nodes": len(G.nodes()),
        "edges": len(G.edges())
    }
    try:
    except Exception as e:
        print(f'    [!] Не удалось сохранить DOT: {e}')
    
    # И в формате GEXF для Gephi
    gexf_path = OUTPUT_DIR / "graph.gexf"
    try:
    except Exception as e:
        print(f'    [!] Не удалось сохранить GEXF: {e}')
    
    return {
        "graph_image": str(graph_path.relative_to(REPO_ROOT)),
        "dot_file": str(dot_path.relative_to(REPO_ROOT)),
        "gexf_file": str(gexf_path.relative_to(REPO_ROOT)),
        "nodes": len(G.nodes()),
        "edges": len(G.edges())
    }

# ========== 4. СОЗДАНИЕ МЕГА-ОТЧЁТА ==========
def create_mega_report(index, connections, graph_info):
    """Создаёт комплексный HTML-отчёт с визуализациями."""
    print("\n[4/4] Создание мега-отчёта...")
    
    html_path = OUTPUT_DIR / "00_MEGA_REPORT.html"
    
    # Генерируем HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>МЕГА-АНАЛИЗ РЕПОЗИТОРИЯ ЛАКУН</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{ 
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }}
            header {{ 
                background: rgba(255, 255, 255, 0.95);
                padding: 40px;
                border-radius: 20px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                text-align: center;
            }}
            h1 {{ 
                color: #764ba2;
                font-size: 2.8em;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .subtitle {{ 
                color: #666;
                font-size: 1.2em;
                margin-bottom: 20px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                text-align: center;
                transition: transform 0.3s;
            }}
            .stat-card:hover {{ transform: translateY(-5px); }}
            .stat-number {{
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 10px;
            }}
            .stat-label {{ 
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            section {{
                background: rgba(255, 255, 255, 0.95);
                padding: 30px;
                border-radius: 20px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            h2 {{
                color: #764ba2;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-bottom: 20px;
                font-size: 1.8em;
            }}
            .graph-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .graph-container img {{
                max-width: 100%;
                border-radius: 15px;
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
                border: 5px solid white;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 15px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}
            th {{ 
                background: #667eea;
                color: white;
                font-weight: bold;
            }}
            tr:hover {{ background: #f9f9f9; }}
            .keyword {{ 
                display: inline-block;
                background: #e0e7ff;
                color: #667eea;
                padding: 5px 10px;
                border-radius: 20px;
                margin: 3px;
                font-size: 0.9em;
            }}
            .connection {{ 
                background: #f0f4ff;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                border-left: 4px solid #667eea;
            }}
            footer {{
                text-align: center;
                margin-top: 40px;
                color: white;
                padding: 20px;
                font-size: 0.9em;
            }}
            .download-links a {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 25px;
                border-radius: 25px;
                text-decoration: none;
                margin: 10px;
                transition: background 0.3s;
            }}
            .download-links a:hover {{ background: #764ba2; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🧠 МЕГА-АНАЛИЗ РЕПОЗИТОРИЯ ЛАКУН</h1>
                <div class="subtitle">
                    Полная картография структуры, связей и семантики | Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{index['stats']['total_files']}</div>
                        <div class="stat-label">Всего файлов</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{graph_info['nodes']}</div>
                        <div class="stat-label">Узлов в графе</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{graph_info['edges']}</div>
                        <div class="stat-label">Связей</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len([f for f in index['files'] if '.lacuna' in f['extension']])}</div>
                        <div class="stat-label">Файлов-лакун</div>
                    </div>
                </div>
                
                <div class="download-links">
                    <a href="{graph_info['graph_image']}" download>📥 Граф (PNG)</a>
                    <a href="{graph_info['gexf_file']}" download>📥 Данные графа (GEXF)</a>
                    <a href="enhanced_index.json" download>📥 Полный индекс (JSON)</a>
                </div>
            </header>
            
            <section>
                <h2>📊 Граф связей между файлами</h2>
                <div class="graph-container">
                    <img src="{graph_info['graph_image']}" alt="Граф связей репозитория">
                    <p><em>Размер узлов показывает важность файла, толщина линий — силу связи</em></p>
                </div>
            </section>
            
            <section>
                <h2>🔗 Явные ссылки между файлами</h2>
                <p>Найдено <strong>{len(connections['explicit_references'])}</strong> прямых ссылок:</p>
                <div class="connection">
    """
    
    # Добавляем топ-10 явных ссылок
    for conn in connections['explicit_references'][:10]:
        html += f"""
                    <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                        <strong>📎 {conn['source']}</strong> → <strong>{conn['target']}</strong>
                    </div>
        """
    
    html += """
                </div>
            </section>
            
            <section>
                <h2>🔑 Ключевые слова по файлам</h2>
    """
    
    # Добавляем ключевые слова
    for cluster in connections['keyword_clusters'][:15]:
        html += f"""
                <div style="margin: 15px 0; padding: 15px; background: #f0f8ff; border-radius: 10px;">
                    <strong>📄 {cluster['file']}</strong><br>
        """
        for keyword in cluster['keywords']:
            html += f'<span class="keyword">#{keyword}</span> '
        html += "</div>"
    
    html += """
            </section>
            
            <section>
                <h2>📈 Статистика по расширениям</h2>
                <table>
                    <tr>
                        <th>Расширение</th>
                        <th>Количество</th>
                        <th>Примеры</th>
                    </tr>
    """
    
    # Статистика по расширениям
    ext_stats = {}
    for file in index['files']:
        ext = file['extension'] if file['extension'] else '(без расширения)'
        ext_stats[ext] = ext_stats.get(ext, 0) + 1
    
    for ext, count in sorted(ext_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        examples = [f['name'] for f in index['files'] if (f['extension'] if f['extension'] else '(без расширения)') == ext][:3]
        html += f"""
                    <tr>
                        <td><code>{ext}</code></td>
                        <td><strong>{count}</strong></td>
                        <td>{', '.join(examples)}</td>
                    </tr>
        """
    
    html += """
                </table>
            </section>
            
            <section>
                <h2>🆕 Последние изменённые файлы</h2>
                <table>
                    <tr>
                        <th>Имя файла</th>
                        <th>Изменён</th>
                        <th>Размер</th>
                        <th>Предпросмотр</th>
                    </tr>
    """
    
    # Последние файлы
    sorted_files = sorted(index['files'], key=lambda x: x['modified'], reverse=True)
    for file in sorted_files[:10]:
        html += f"""
                    <tr>
                        <td><code>{file['name']}</code></td>
                        <td>{file['modified'][:19].replace('T', ' ')}</td>
                        <td>{file['size']:,} б</td>
                        <td style="font-size: 0.9em; color: #666;">{file['content_preview'][:80]}...</td>
                    </tr>
        """
    
    html += """
                </table>
            </section>
        </div>
        
        <footer>
            Сгенерировано автоматически системой анализа лакун<br>
            Репозиторий: AGI/-_- | Время анализа: {datetime.now().strftime('%H:%M:%S')}
        </footer>
    </body>
    </html>
    """
    
    # Сохраняем HTML
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Также создаём Markdown-версию для GitHub
    md_path = OUTPUT_DIR / "00_MEGA_REPORT.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"""# МЕГА-АНАЛИЗ РЕПОЗИТОРИЯ ЛАКУН

## 📊 Статистика
- **Всего файлов:** {index['stats']['total_files']}
- **Общий размер:** {index['stats']['total_size']:,} байт
- **Узлов в графе:** {graph_info['nodes']}
- **Связей в графе:** {graph_info['edges']}

## 🔗 Граф связей
![Граф связей]({graph_info['graph_image']})

## 🆕 Последние файлы
| Имя файла | Изменён | Размер |
|-----------|---------|--------|
""")
        
        for file in sorted_files[:15]:
            f.write(f"| `{file['name']}` | {file['modified'][:10]} | {file['size']:,} б |\n")
    
    print(f"  [+] HTML-отчёт: {html_path}")
    print(f"  [+] Markdown-отчёт: {md_path}")
    
    return {
        "html_report": str(html_path.relative_to(REPO_ROOT)),
        "markdown_report": str(md_path.relative_to(REPO_ROOT))
    }

# ========== ОСНОВНАЯ ФУНКЦИЯ ==========
def main():
    """Запускает весь процесс анализа."""
    print("=" * 60)
    print("МЕГА-АНАЛИЗАТОР ЛАКУН - ЗАПУСК")
    print("=" * 60)
    
    # 1. Создаём расширенный индекс
    index = create_enhanced_index()
    
    # 2. Анализируем связи
    connections = analyze_connections(index)
    
    # 3. Создаём визуализацию
    graph_info = create_visualization(index, connections)
    
    # 4. Создаём мега-отчёт
    report_info = create_mega_report(index, connections, graph_info)
    
    print("\n" + "=" * 60)
    print("АНАЛИЗ ЗАВЕРШЁН!")
    print("=" * 60)
    print("\n📊 РЕЗУЛЬТАТЫ:")
    print(f"  • 📁 Файлов проанализировано: {index['stats']['total_files']}")
    print(f"  • 🔗 Связей обнаружено: {len(connections['explicit_references'])} явных + {len(connections['semantic_similarity'])} семантических")
    print(f"  • 🎨 Граф создан: {graph_info['nodes']} узлов, {graph_info['edges']} связей")
    print(f"  • 📄 HTML-отчёт: {REPO_ROOT}/00_ANALYSIS/00_MEGA_REPORT.html")
    print(f"  • 📈 Граф (PNG): {REPO_ROOT}/00_ANALYSIS/connection_graph.png")
    print(f"  • 💾 Данные графа: {REPO_ROOT}/00_ANALYSIS/graph.gexf (открой в Gephi)")
    
    print("\n🎯 КАК ИСПОЛЬЗОВАТЬ:")
    print("  1. Открой HTML-отчёт в браузере")
    print("  2. Изучи граф связей между файлами")
    print("  3. Используй GEXF-файл для продвинутого анализа в Gephi")
    print("  4. JSON-индекс содержит все данные для собственных скриптов")

if __name__ == "__main__":
    main()


