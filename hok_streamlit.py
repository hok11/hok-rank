import streamlit as st
import pandas as pd
import json
import os
import math
import subprocess
import requests
import time
import random
from datetime import datetime
from jinja2 import Template

# ================= ⚠️ 配置区域 =================
LOCAL_REPO_PATH = r"D:\python-learn\hok-rank"
GIT_EXECUTABLE_PATH = r"D:\Git\bin\git.exe"
GITHUB_USERNAME = "hok11"
LEADERBOARD_CAPACITY = 10


# ================= 🔧 核心逻辑类 =================

class SkinCrawler:
    def __init__(self, data_path):
        self.save_dir = os.path.join(data_path, "skin_avatars")
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/plain, */*; q=0.01', 'Referer': 'https://image.baidu.com/search/index',
        }

    def fetch_single_image(self, skin):
        safe_name = skin['name'].replace("/", "_").replace("\\", "_").replace(" ", "")
        gif_filename = f"{safe_name}.gif"
        gif_path = os.path.join(self.save_dir, gif_filename)

        if os.path.exists(gif_path):
            current_path = f"skin_avatars/{gif_filename}"
            if skin.get('local_img') != current_path:
                skin['local_img'] = current_path
                return True, f"锁定本地动态头像: {gif_filename}"
            return True, "已存在本地动态头像"

        if skin.get('local_img') and os.path.exists(os.path.join(LOCAL_REPO_PATH, skin['local_img'])):
            return True, "已存在图片"

        parts = skin['name'].split('-')
        keyword = f"{parts[1]} {parts[0]}" if len(parts) >= 2 else skin['name']
        url = "https://image.baidu.com/search/acjson"
        params = {
            "tn": "resultjson_com", "ipn": "rj", "fp": "result", "queryWord": keyword, "cl": "2", "lm": "-1",
            "ie": "utf-8", "oe": "utf-8", "word": keyword, "pn": "0", "rn": "1"
        }
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=5)
            try:
                data = resp.json()
            except:
                data = json.loads(resp.text.replace(r"\'", r"'"))

            if 'data' in data and len(data['data']) > 0 and 'thumbURL' in data['data'][0]:
                img_url = data['data'][0]['thumbURL']
                if not img_url and 'replaceUrl' in data['data'][0]:
                    img_url = data['data'][0]['replaceUrl'][0]['ObjURL']

                if img_url:
                    img_resp = requests.get(img_url, headers=self.headers, timeout=10)
                    file_name = f"{safe_name}.jpg"
                    file_path = os.path.join(self.save_dir, file_name)
                    with open(file_path, 'wb') as f:
                        f.write(img_resp.content)
                    skin['local_img'] = f"skin_avatars/{file_name}"
                    time.sleep(random.uniform(0.5, 1.0))
                    return True, f"下载成功: {file_name}"
            return False, f"未找到图片: {keyword}"
        except Exception as e:
            return False, f"爬取错误: {str(e)}"


class SkinSystem:
    def __init__(self):
        self.all_skins = []
        self.instructions = ["本榜单数据仅供参考", "数据更新时间以页面显示为准"]

        self.default_quality_config = {
            "0": {"price": 800.0, "parent": None, "name": "珍品无双", "scale": 1.1, "bg_color": "#ffdcdc"},
            "1": {"price": 400.0, "parent": None, "name": "无双", "scale": 1.0, "bg_color": "#f3e8ff"},
            "2": {"price": 600.0, "parent": None, "name": "荣耀典藏", "scale": 1.4, "bg_color": "#fff7cd"},
            "3": {"price": 200.0, "parent": None, "name": "珍品传说", "scale": 1.0, "bg_color": "#bfdbfe"},
            "3.5": {"price": 143.0, "parent": None, "name": "传说限定", "scale": 1.1, "bg_color": "#e0f2fe"},
            "4": {"price": 135.0, "parent": None, "name": "传说", "scale": 1.2, "bg_color": "#ffffff"},
            "5": {"price": 71.0, "parent": None, "name": "史诗", "scale": 1.1, "bg_color": "#ffffff"},
            "6": {"price": 48.8, "parent": None, "name": "勇者", "scale": 0.9, "bg_color": "#ffffff"},
        }

        self.quality_config = self.default_quality_config.copy()

        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
        self.desc_dir = os.path.join(LOCAL_REPO_PATH, "skin_descs")
        self.avatar_dir = os.path.join(LOCAL_REPO_PATH, "skin_avatars")

        if not os.path.exists(self.desc_dir): os.makedirs(self.desc_dir)
        if not os.path.exists(self.avatar_dir): os.makedirs(self.avatar_dir)

        self.crawler = SkinCrawler(LOCAL_REPO_PATH)
        self.load_data()

        for k, v in self.default_quality_config.items():
            if k in self.quality_config:
                self.quality_config[k]['price'] = v['price']
            else:
                self.quality_config[k] = v

        self.scan_local_images()
        self._migrate_data_structure()

    def scan_local_images(self):
        updates = 0
        for skin in self.all_skins:
            current_img = skin.get('local_img')
            safe_name = skin['name'].replace("/", "_").replace("\\", "_").replace(" ", "")
            found_path = None
            for ext in ['.gif', '.jpg', '.png', '.jpeg']:
                file_name = f"{safe_name}{ext}"
                full_path = os.path.join(self.avatar_dir, file_name)
                if os.path.exists(full_path):
                    found_path = f"skin_avatars/{file_name}"
                    break

            if found_path and current_img != found_path:
                skin['local_img'] = found_path
                updates += 1

        if updates > 0:
            print(f"🔄 自动挂载了 {updates} 张本地图片")

    def _get_list_price_by_quality(self, q_code):
        q_str = str(q_code)
        if q_str in self.quality_config:
            return self.quality_config[q_str]['price']
        if q_str.endswith(".0"):
            q_clean = q_str[:-2]
            if q_clean in self.quality_config:
                return self.quality_config[q_clean]['price']
        try:
            target_val = float(q_code)
            for k, v in self.quality_config.items():
                try:
                    if math.isclose(float(k), target_val, rel_tol=1e-9):
                        price = v['price']
                        if price <= 0 and v.get('parent'):
                            p_key = str(v['parent'])
                            if p_key in self.quality_config:
                                return self.quality_config[p_key]['price']
                        return price
                except:
                    continue
        except:
            pass
        return 0.0

    def _calculate_real_score(self, rank_score, list_price, real_price):
        if rank_score is None: return None
        if isinstance(rank_score, float) and math.isnan(rank_score): return None
        if real_price <= 0 or list_price <= 0: return None
        return round(rank_score * (real_price / list_price), 1)

    def _migrate_data_structure(self):
        for skin in self.all_skins:
            skin['list_price'] = self._get_list_price_by_quality(skin['quality'])
            if 'real_price' not in skin: skin['real_price'] = skin.get('price', 0.0)
            if 'is_preset' not in skin: skin['is_preset'] = False
            if 'is_discontinued' not in skin: skin['is_discontinued'] = False
            if 'price' in skin: del skin['price']
            cur_score = skin.get('score')
            skin['real_score'] = self._calculate_real_score(cur_score, skin['list_price'], skin['real_price'])
            if 'on_leaderboard' not in skin:
                skin['on_leaderboard'] = True if (
                            skin.get('is_new') or skin.get('is_rerun') or skin.get('is_preset') or skin.get(
                        'is_discontinued')) else False
        self.save_data()

    def _get_base_score(self, x):
        if x <= 0: return 200
        val = (282 / math.sqrt(x)) - 82
        return max(val, 0)

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                if isinstance(loaded, list):
                    self.all_skins = loaded
                elif isinstance(loaded, dict):
                    self.all_skins = loaded.get('skins', loaded.get('total', []))
                    if 'instructions' in loaded: self.instructions = loaded['instructions']
                    if 'quality_config' in loaded: self.quality_config = loaded['quality_config']
                seen = set()
                unique = []
                for s in self.all_skins:
                    if s['name'] not in seen: unique.append(s); seen.add(s['name'])
                self.all_skins = unique
            except:
                self.all_skins = []
        else:
            self.save_data()

    def _get_sort_key(self, skin):
        group_weight = 10 if skin.get('is_discontinued') else (1 if skin.get('is_preset') else 0)
        if group_weight == 0:
            return (group_weight, skin.get('score') is None, -(skin.get('score') or 0))
        return (group_weight, skin.get('quality', 99))

    def save_data(self):
        try:
            for skin in self.all_skins:
                for k, v in skin.items():
                    if isinstance(v, float) and math.isnan(v):
                        skin[k] = None
            with open(self.data_file, 'w', encoding='utf-8') as f:
                self.all_skins.sort(key=self._get_sort_key)
                data_to_save = {
                    "skins": self.all_skins,
                    "instructions": self.instructions,
                    "quality_config": self.quality_config
                }
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"存档失败: {e}")

    def get_total_skins(self):
        data = self.all_skins[:]
        data.sort(key=self._get_sort_key)
        return data

    def get_active_leaderboard(self):
        active = [s for s in self.all_skins if s.get('on_leaderboard', False)]
        active.sort(key=self._get_sort_key)
        return active

    def calculate_insertion_score(self, rank_input, active_list, real_price, growth):
        valid_list = [s for s in active_list if
                      not s.get('is_preset') and not s.get('is_discontinued') and s.get('score') is not None]
        if rank_input == 1:
            old_top1_score = valid_list[0]['score'] if valid_list else 0
            return max(old_top1_score / 0.6, (282 / math.sqrt(1.25)) - 82, real_price * growth * 15)
        p_idx = rank_input - 2
        p_score = 200 if p_idx < 0 else (valid_list[p_idx]['score'] if p_idx < len(valid_list) else 0)
        if rank_input - 1 < len(valid_list):
            next_score = valid_list[rank_input - 1]['score']
            return math.sqrt(p_score * next_score)
        else:
            t = int(rank_input)
            while True:
                val = self._get_base_score(t)
                if val < p_score: return val
                t += 1

    def auto_prune_leaderboard(self):
        active = [s for s in self.all_skins if
                  s.get('on_leaderboard', False) and not s.get('is_preset') and not s.get('is_discontinued')]
        active.sort(key=lambda x: (x.get('score') is None, -(x.get('score') or 0)))
        if len(active) > LEADERBOARD_CAPACITY:
            for skin in active[LEADERBOARD_CAPACITY:]: skin['on_leaderboard'] = False

    def get_header_gifs(self):
        show_dir = os.path.join(LOCAL_REPO_PATH, "show")
        if not os.path.exists(show_dir): return []
        gifs = [f for f in os.listdir(show_dir) if f.lower().endswith('.gif')]
        gifs.sort()
        return gifs

    def generate_html(self):
        self.scan_local_images()
        self.save_data()

        header_gifs = self.get_header_gifs()
        desc_files = {}
        if os.path.exists(self.desc_dir):
            for f in os.listdir(self.desc_dir): desc_files[os.path.splitext(f)[0]] = f

        display_skins = self.all_skins[:]
        display_skins.sort(key=self._get_sort_key)

        for skin in display_skins:
            skin['desc_img'] = desc_files.get(skin['name'])
            raw_q = skin['quality']
            q_key = str(raw_q)
            if q_key in self.quality_config:
                pass
            elif q_key.endswith('.0') and q_key[:-2] in self.quality_config:
                q_key = q_key[:-2]
            else:
                try:
                    f_val = float(raw_q)
                    for k in self.quality_config:
                        if math.isclose(float(k), f_val, rel_tol=1e-9):
                            q_key = k
                            break
                except:
                    pass
            skin['quality_key'] = q_key

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=0.6, user-scalable=yes">
    <title>Honor of Kings Skin Revenue Forecast</title>
    <style>
        :root { --header-bg: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f0f2f5; display: flex; flex-direction: column; align-items: center; padding: 20px; gap: 30px; }
        .chart-card { background: white; width: 100%; max-width: 950px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); padding-bottom: 20px; }
        .chart-header { background: var(--header-bg); padding: 15px 20px; color: white; display: flex; align-items: center; justify-content: center; gap: 20px; }
        .header-content { text-align: center; flex: 1; }
        .header-content h1 { font-size: 24px; font-weight: 800; margin: 0; }
        .info-container { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 5px; }
        .info-btn { background: white; color: black; border: none; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold; cursor: pointer; transition: opacity 0.2s; }
        .info-btn:hover { opacity: 0.8; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5); backdrop-filter: blur(2px); }
        .modal-content { background-color: #fefefe; margin: 15% auto; padding: 20px; border-radius: 12px; width: 80%; max-width: 500px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); animation: fadeIn 0.3s; }
        @keyframes fadeIn { from {opacity: 0; transform: translateY(-20px);} to {opacity: 1; transform: translateY(0);} }
        .close-btn { color: #aaa; float: right; font-size: 24px; font-weight: bold; cursor: pointer; line-height: 20px; }
        .close-btn:hover { color: black; }
        .modal-list { text-align: left; margin-top: 15px; padding-left: 20px; font-size: 14px; line-height: 1.6; color: #333; }
        .header-gifs-container { display: flex; gap: 10px; }
        .header-gif { width: 55px; height: 55px; border-radius: 8px; object-fit: cover; border: 2px solid rgba(255,255,255,0.4); }
        .table-container { width: 100%; overflow-x: auto; }
        table { width: 98%; margin: 0 auto; border-collapse: separate; border-spacing: 0 8px; font-size: 14px; min-width: 800px; }
        th { text-align: center; padding: 8px 2px; font-weight: 800; border-bottom: 3px solid #6366f1; white-space: nowrap; }
        td { padding: 12px 2px; vertical-align: middle; text-align: center; background: transparent; border: none; }
        .rounded-left { border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
        .rounded-right { border-top-right-radius: 12px; border-bottom-right-radius: 12px; }
        .desc-col { width: 100px; padding: 2px !important; }
        .desc-img { max-width: 100%; height: auto; max-height: 50px; object-fit: contain; display: block; margin: 0 auto; border-radius: 4px; mix-blend-mode: screen; filter: contrast(1.5) saturate(4.0); }
        .qual-header { display: inline-flex; align-items: center; justify-content: center; gap: 6px; position: relative; }
        .multi-select-box { font-size: 11px; border-radius: 4px; border: 1px solid #ddd; padding: 4px 8px; cursor: pointer; background: white; min-width: 85px; }
        .dropdown-menu { display: none; position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; border-radius: 6px; padding: 8px; min-width: 130px; text-align: left; }
        .dropdown-menu.show { display: block; }
        .col-sort { cursor: pointer; position: relative; } .col-sort::after { content: ' ⇅'; color: #ccc; margin-left: 5px; font-size: 10px; }
        th.sort-asc .col-sort::after, th.sort-asc.col-sort::after { content: ' ▲'; color: #6366f1; }
        th.sort-desc .col-sort::after, th.sort-desc.col-sort::after { content: ' ▼'; color: #6366f1; }

        .quality-icon { height: 28px; width: auto; display: inline-block; vertical-align: middle; transition: transform 0.2s; object-fit: contain; }
        .rare-wushuang-big { height: 60px !important; width: auto !important; margin: -15px 0; }
        .wushuang-big { height: 45px !important; margin: -8px 0; }
        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; object-fit: cover; }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 5px; min-width: 180px; }
        .name-container { display: flex; flex-direction: column; gap: 2px; width: 86px; align-items: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; white-space: nowrap; transform-origin: center; display: inline-block; }
        .badge { display: block; width: 100%; text-align: center; padding: 1px 0; font-size: 9px; font-weight: 900; border-radius: 3px; text-transform: uppercase; }
        .badge-new { background: #ffd700; color: #000; } .badge-return { background: #1d4ed8; color: #fff; } .badge-preset { background: #06b6d4; color: #fff; } .badge-out { background: #4b5563; color: #fff; }

        .rank-box { 
            display: inline-flex; align-items: center; justify-content: center;
            width: 28px; height: 28px; background: #1d4ed8; color: #fff; 
            font-size: 15px; font-weight: 900; border-radius: 6px; line-height: 1;
        }
        .box-style { display: inline-block; width: 75px; padding: 4px 0; font-weight: 700; border-radius: 6px; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .growth-down { color: #991b1b !important; } .growth-up-mid { color: #16a34a !important; } .growth-up-high { color: #ea580c !important; } .growth-special { color: #a855f7 !important; font-weight: 900 !important; }
    </style>
</head>
<body>
    <div class="chart-card">
        <div class="chart-header">
            <div class="header-gifs-container">{% for g in header_gifs[:2] %}<img src="./show/{{ g }}" class="header-gif">{% endfor %}</div>
            <div class="header-content">
                <h1>Honor of Kings Skin Revenue Forecast</h1>
                <div class="info-container"><p>Update: {{ update_time }}</p><button class="info-btn" onclick="openModal()">说明</button></div>
            </div>
            <div class="header-gifs-container">{% for g in header_gifs[2:4] %}<img src="./show/{{ g }}" class="header-gif">{% endfor %}</div>
        </div>
        <div class="table-container">
            <table id="skinTable">
                <thead>
                    <tr>
                        <th class="col-sort" onclick="sortTable(0, 'int')">No</th>
                        <th><div class="qual-header"><div id="multiSelectBtn" class="multi-select-box" onclick="toggleMenu(event)">全部品质</div>
                            <div id="dropdownMenu" class="dropdown-menu">
                                <label class="dropdown-item"><input type="checkbox" id="selectAll" value="all" checked onchange="handleSelectAll(this)"> 全选</label><hr>
                                {% for q in quality_config.values()|map(attribute='name')|unique %}
                                <label class="dropdown-item"><input type="checkbox" class="q-check" value="{{ q }}" onchange="handleSingleSelect(this)"> {{ q }}</label>
                                {% endfor %}
                            </div><span class="col-sort" onclick="sortTable(1, 'float')"></span></div></th>
                        <th style="text-align:left; padding-left:20px;">Skin Name</th><th></th>
                        <th class="col-sort" onclick="sortTable(4, 'float')">Rank Pts</th>
                        <th class="col-sort" onclick="sortTable(5, 'float')">Real Pts</th>
                        <th class="col-sort" onclick="sortTable(6, 'float')">Growth</th>
                        <th class="col-sort" onclick="sortTable(7, 'float')">List P</th>
                        <th class="col-sort" onclick="sortTable(8, 'float')">Real P</th>
                    </tr>
                </thead>
                <tbody>
                    {% for skin in total_skins %}
                    {% set q_str = skin.quality_key %}
                    {% set q_cfg = quality_config.get(q_str, {}) %}
                    {% set parent_id = q_cfg.parent|string if q_cfg.parent else none %}
                    {% set display_img_id = parent_id if parent_id else q_str %}
                    {% set root_cfg = quality_config.get(display_img_id, q_cfg) %}
                    {% set scale_val = q_cfg.get('scale', 1.0) %}
                    {% set bg_c = root_cfg.get('bg_color', '#ffffff') %}
                    {% set q_cls = 'rare-wushuang-big' if root_cfg.name == '珍品无双' else ('wushuang-big' if root_cfg.name == '无双' else '') %}
                    <tr data-quality="{{ q_cfg.name }}">
                        <td>{% if not skin.is_preset and not skin.is_discontinued %}<span class="rank-box">{{ loop.index }}</span>{% else %}-{% endif %}</td>
                        <td class="quality-col" data-val="{{ skin.quality }}">
                            <img src="./images/{{ q_str }}.gif" data-q="{{ q_str }}" data-p="{{ parent_id }}" class="quality-icon {{ q_cls }}" style="transform: scale({{ scale_val }});" onerror="loadFallbackImg(this)">
                        </td>
                        <td class="rounded-left" style="background-color: {{ bg_c }};"><div class="song-col">
                            <img src="./{{ skin.local_img or 'placeholder.jpg' }}" class="album-art">
                            <div class="name-container"><span class="song-title">{{ skin.name }}</span>
                                {% if skin.is_discontinued %}<span class="badge badge-out">Out of Print</span>{% elif skin.is_preset %}<span class="badge badge-preset">Coming Soon</span>{% elif skin.is_new %}<span class="badge badge-new">New Arrival</span>{% elif skin.is_rerun %}<span class="badge badge-return">Limit Return</span>{% endif %}
                            </div>
                        </div></td>
                        <td class="desc-col" style="background-color: {{ bg_c }};">{% if skin.desc_img %}<img src="./skin_descs/{{ skin.desc_img }}" class="desc-img">{% endif %}</td>
                        <td data-val="{{ skin.score if skin.score is not none else -999 }}" style="background-color: {{ bg_c }};"><div class="box-style">{% if skin.is_discontinued %}{{ '--' }}{% else %}{{ skin.score or '--' }}{% endif %}</div></td>
                        <td style="background-color: {{ bg_c }}; color:#6366f1; font-weight:bold;">{{ skin.real_score or '--' }}</td>
                        <td style="background-color: {{ bg_c }};">{% if skin.growth %}{% set g_cls = 'growth-special' if skin.growth == 1.9 else ('growth-down' if skin.growth < 0 else ('growth-up-high' if skin.growth >= 10 else ('growth-up-mid' if skin.growth >= 5 else ''))) %}<div class="box-style {{ g_cls }}">{{ skin.growth }}%{% if skin.growth == 1.9 %}!{% endif %}</div>{% else %}--{% endif %}</td>
                        <td style="background-color: {{ bg_c }};">¥{{ skin.list_price }}</td>
                        <td class="rounded-right" style="background-color: {{ bg_c }};"><div class="box-style">{% if skin.real_price > 0 %}¥{{ skin.real_price }}{% else %}--{% endif %}</div></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <div id="infoModal" class="modal"><div class="modal-content"><span class="close-btn" onclick="closeModal()">&times;</span><h2 style="text-align:center;">说明</h2><hr><ul class="modal-list">{% for item in instructions %}<li>{{ item }}</li>{% endfor %}</ul></div></div>
    <script>
    function openModal() { document.getElementById('infoModal').style.display = 'block'; }
    function closeModal() { document.getElementById('infoModal').style.display = 'none'; }
    window.onclick = function(e) { if (e.target == document.getElementById('infoModal')) closeModal(); }
    function toggleMenu(e) { e.stopPropagation(); document.getElementById('dropdownMenu').classList.toggle('show'); }
    document.addEventListener('click', () => document.getElementById('dropdownMenu').classList.remove('show'));
    document.getElementById('dropdownMenu').addEventListener('click', (e) => e.stopPropagation());
    window.onload = () => { sortTable(4, 'float'); adjustNameFontSize(); };
    function adjustNameFontSize() {
        const containers = document.querySelectorAll('.name-container'); const maxWidth = 86; 
        containers.forEach(container => {
            const title = container.querySelector('.song-title');
            if (title && title.scrollWidth > maxWidth) title.style.transform = `scale(${maxWidth / title.scrollWidth})`;
        });
    }
    function loadFallbackImg(img) {
        const q = img.getAttribute('data-q');
        const p = img.getAttribute('data-p');
        const src = img.src;
        if (src.indexOf(q + '.gif') !== -1) { img.src = './images/' + q + '.jpg'; }
        else if (src.indexOf(q + '.jpg') !== -1 && p && p !== 'None') { img.src = './images/' + p + '.gif'; }
        else if (p && src.indexOf(p + '.gif') !== -1) { img.src = './images/' + p + '.jpg'; }
    }
    function handleSelectAll(cb) { if(cb.checked) document.querySelectorAll('.q-check').forEach(c=>c.checked=false); updateFilter(); }
    function handleSingleSelect(cb) { if(cb.checked) document.getElementById('selectAll').checked=false; updateFilter(); }
    function updateFilter() {
        const main = document.getElementById('selectAll');
        const checked = Array.from(document.querySelectorAll('.q-check')).filter(c=>c.checked).map(c=>c.value);
        document.getElementById('multiSelectBtn').innerText = (main.checked || checked.length===0) ? "全部品质" : (checked.length===1 ? checked[0] : "筛选中");
        document.querySelectorAll('#skinTable tbody tr').forEach(r => {
            r.style.display = (main.checked || checked.length===0 || checked.includes(r.getAttribute('data-quality'))) ? "" : "none";
        });
    }
    function sortTable(n, type) {
        var table = document.getElementById("skinTable"), rows = Array.from(table.rows).slice(1), headers = table.getElementsByTagName("TH"), dir = "desc";
        if (headers[n].classList.contains("sort-desc")) dir = "asc";
        Array.from(headers).forEach(h => h.classList.remove("sort-asc", "sort-desc"));
        headers[n].classList.add(dir === "asc" ? "sort-asc" : "sort-desc");
        rows.sort((a, b) => {
            var x = parseFloat(a.cells[n].getAttribute("data-val") || a.cells[n].innerText.replace(/[¥%!]/g, ''));
            var y = parseFloat(b.cells[n].getAttribute("data-val") || b.cells[n].innerText.replace(/[¥%!]/g, ''));
            if (isNaN(x)) x = -9999999; if (isNaN(y)) y = -9999999;
            return dir === "asc" ? x - y : y - x;
        });
        rows.forEach(r => table.tBodies[0].appendChild(r));
    }
    </script>
</body>
</html>
        """
        t = Template(html_template)
        html_content = t.render(total_skins=display_skins, quality_config=self.quality_config,
                                header_gifs=header_gifs, instructions=self.instructions,
                                update_time=datetime.now().strftime("%Y-%m-%d %H:%M"))
        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            return True, "📄 HTML 生成成功"
        except Exception as e:
            return False, f"HTML 生成失败: {e}"


# ================= 🚀 Streamlit 界面逻辑 =================

st.set_page_config(page_title="王者皮肤榜单管理", page_icon="👑", layout="wide")

# 初始化系统实例
if 'app' not in st.session_state:
    st.session_state.app = SkinSystem()

app = st.session_state.app

# ----------------- 顶部导航 -----------------
# 移除主标题 st.title("👑 榜单管理后台") 以节省空间
tab_list = ["📊 榜单概览", "➕ 添加皮肤", "🕒 预设上线", "✏️ 数据编辑", "💎 品质管理", "🚀 发布与工具"]
t1, t2, t3, t4, t5, t6 = st.tabs(tab_list)

# ----------------- Tab 1: 榜单概览 -----------------
with t1:
    # 顶部控制栏
    col_ctrl1, col_ctrl2 = st.columns([0.2, 0.8])
    with col_ctrl1:
        # 旋转按钮逻辑：默认为总榜 (False)，开启后看新品榜 (True)
        show_active = st.toggle("只看新品活跃榜", value=False)

    with col_ctrl2:
        if show_active:
            st.subheader("🔥 新品活跃榜 (Top 10+)")
        else:
            st.subheader("📚 完整库存 (总榜)")

    st.divider()

    if show_active:
        data_list = app.get_active_leaderboard()
        if not data_list:
            st.info("暂无上榜数据")
            data_list = []
    else:
        data_list = app.get_total_skins()

    if data_list:
        df = pd.DataFrame(data_list)
        # 序号从1开始
        df.index = df.index + 1


        # 1. 预处理数据：增加“标签”列和“品质”名
        def get_tag(row):
            if row.get('is_discontinued'): return "绝版"
            if row.get('is_preset'): return "预设"
            if row.get('is_rerun'): return "返场"
            if row.get('is_new'): return "新品"
            return ""  # 移除“普通”，若无标签则留空


        df['tag'] = df.apply(get_tag, axis=1)
        # 修复品质名映射：先转int再转str，避免 5000.0 匹配不到 '5000'
        df['quality_key'] = df['quality'].apply(lambda x: str(int(x)) if pd.notnull(x) else "")
        df['quality_name'] = df['quality_key'].map(lambda x: app.quality_config.get(x, {}).get('name', "未知"))

        # 中文列名映射配置
        column_config = {
            "name": st.column_config.TextColumn("皮肤名称", width="medium"),  # 名字宽度改为medium
            "quality_name": st.column_config.TextColumn("品质", width="small"),
            "quality": st.column_config.NumberColumn("品质代码", format="%d", width="small"),  # 强制整数，并在下面修正配置
            "tag": st.column_config.TextColumn("标签", width="small"),
            "growth": st.column_config.NumberColumn("涨幅%", format="%.2f", width="small"),
            "score": st.column_config.NumberColumn("排位分", format="%.1f", width="small"),
            "real_score": st.column_config.NumberColumn("实际分", format="%.1f", width="small"),
            "list_price": st.column_config.NumberColumn("定价", format="¥%.1f", width="small"),
            "real_price": st.column_config.NumberColumn("实际价格", format="¥%.1f", width="small"),
            "local_img": st.column_config.ImageColumn("预览", width="small")
        }

        # 展示列顺序：皮肤名称 -> 品质 -> 品质代码 -> 标签 -> 涨幅 -> 排位分 -> 实际分 -> 定价 -> 实际价格
        display_cols = ['name', 'quality_name', 'quality', 'tag', 'growth', 'score', 'real_score', 'list_price',
                        'real_price']

        # 尝试使用 Pandas Styler 居中
        styled_df = df[display_cols].style.set_properties(**{'text-align': 'center'})

        # 使用全宽展示，防止横向滚动
        st.dataframe(
            styled_df,  # 使用 styled_df
            column_config=column_config,
            use_container_width=True,  # 占满全宽
            height=600,
            hide_index=False  # 恢复左侧序号列
        )

# ----------------- Tab 2: 添加皮肤 -----------------
with t2:
    # 移除标题 header

    # ------------------ 品质选择区域 ------------------
    # 模式选择
    q_mode = st.radio("品质来源", ["默认品质", "新建品质"], horizontal=True, label_visibility="collapsed")

    final_q_code = None  # 最终选定/新建的品质代码
    final_list_price = 0.0  # 最终定价

    # 准备数据：分出 父级(Root) 和 子级(Children)
    all_roots = {k: v for k, v in app.quality_config.items() if not v.get('parent')}
    all_children = {k: v for k, v in app.quality_config.items() if v.get('parent')}

    if q_mode == "默认品质":
        # 场景 A: 选择已有
        col_q1, col_q2 = st.columns(2)

        # 1. 选择父品质
        root_opts = {k: f"{v['name']} ({k})" for k, v in all_roots.items()}
        sel_root = col_q1.selectbox("选择父品质", options=list(root_opts.keys()), format_func=lambda x: root_opts[x])

        # 2. 查找是否有子品质
        my_children = {k: v for k, v in all_children.items() if str(v['parent']) == str(sel_root)}

        if my_children:
            # 有子品质，允许进一步选择
            child_opts = {sel_root: f"{all_roots[sel_root]['name']} (父级本身)"}
            for k, v in my_children.items():
                child_opts[k] = f"{v['name']} ({k})"

            sel_child = col_q2.selectbox("选择具体品质", options=list(child_opts.keys()),
                                         format_func=lambda x: child_opts[x])
            final_q_code = sel_child
        else:
            # 无子品质，直接用父级
            col_q2.info("该品质无子分类")
            final_q_code = sel_root

        final_list_price = app._get_list_price_by_quality(final_q_code)

    else:
        # 场景 B: 新建品质
        new_sub_mode = st.radio("新建类型", ["新建子品质 (归属已有系列)", "全新独立品质"], horizontal=True)

        if new_sub_mode == "新建子品质 (归属已有系列)":
            # B1: 新建子品质
            c_new1, c_new2 = st.columns(2)
            root_opts = {k: f"{v['name']} ({k})" for k, v in all_roots.items()}
            sel_root_for_new = c_new1.selectbox("选择归属父品质", options=list(root_opts.keys()),
                                                format_func=lambda x: root_opts[x])

            # 展示父级和兄弟级信息
            with c_new2:
                st.caption(f"当前父级: {all_roots[sel_root_for_new]['name']} (代码 {sel_root_for_new})")
                siblings = [f"{v['name']}({k})" for k, v in all_children.items() if
                            str(v['parent']) == str(sel_root_for_new)]
                if siblings:
                    st.caption(f"现有子品质: {', '.join(siblings)}")
                else:
                    st.caption("暂无子品质")

            # 输入新信息
            c_in1, c_in2, c_in3 = st.columns(3)
            new_q_name = c_in1.text_input("子品质名称")
            new_q_code = c_in2.text_input("子品质代号 (数字)")
            new_q_price = c_in3.number_input("定价", value=all_roots[sel_root_for_new]['price'])  # 默认继承父级

            if new_q_name and new_q_code:
                # 暂存信息，提交时写入
                final_q_code = new_q_code  # 标记为新代码
                # 构造临时数据用于展示
                st.info(f"将创建: {new_q_name} (隶属 {all_roots[sel_root_for_new]['name']})")
                # 实际上要在提交时再保存到 config

        else:
            # B2: 全新独立品质
            st.caption("现有顶级品质一览:")
            st.dataframe(pd.DataFrame([{"代码": k, "名称": v['name']} for k, v in all_roots.items()]).T)

            c_in1, c_in2, c_in3 = st.columns(3)
            new_q_name = c_in1.text_input("全新名称")
            new_q_code = c_in2.text_input("全新代号")
            new_q_price = c_in3.number_input("定价", min_value=0.0)

            if new_q_name and new_q_code:
                final_q_code = new_q_code

    st.divider()  # ------------------ 皮肤信息区域 ------------------

    # 皮肤名称放在最显眼位置
    name = st.text_input("皮肤名称", placeholder="请输入皮肤名字...")

    # 定价参考
    if q_mode == "默认品质":
        st.caption(f"当前品质标准定价: ¥{final_list_price}")

    # 核心数据行：实价 | 涨幅 | 标签 | 上榜
    c4, c5, c6, c7 = st.columns([1, 1, 1.5, 1])

    real_price = c4.number_input("实际价格", min_value=0.0, step=1.0)

    # 涨幅输入优化
    growth_input = c5.number_input("涨幅 (%)", value=0.0, step=0.1, help="输入 1 代表 1%")
    growth = growth_input / 100.0

    tag_option = c6.radio("标签", ["新品", "返场", "预设", "绝版"], horizontal=True)

    # 动态逻辑
    can_be_on_board = tag_option not in ["预设", "绝版"]
    on_board = c7.checkbox("登上新品榜", value=False, disabled=not can_be_on_board)
    if not can_be_on_board:
        c7.caption("🚫 预设/绝版不可上榜")

    st.divider()  # ------------------ 底部提交区域 ------------------

    # 左右分栏布局（左侧操作，右侧榜单）
    col_main_left, col_main_right = st.columns([1, 1.5])

    with col_main_left:
        # 仅在上榜时显示分数输入
        rank_score = None
        if on_board:
            st.info("排位分设置")
            score_mode = st.radio("分数来源", ["自定义输入", "排位计算"], horizontal=True)

            if score_mode == "自定义输入":
                rank_score = st.number_input("输入排位分 (Rank Pts)", value=0.0, step=0.1)
            else:
                target_rank = st.number_input("目标排名 (1=第一名)", min_value=1, value=1)
                # 实时计算预览
                active_list = app.get_active_leaderboard()
                preview_score = round(app.calculate_insertion_score(target_rank, active_list, real_price, growth), 1)
                st.metric("计算结果预览", f"{preview_score} Pts")
                rank_score = preview_score
        else:
            st.caption("未勾选上榜，无需设置分数")

        st.markdown("###")  # 占位
        submitted = st.button("提交保存", type="primary", use_container_width=True)

    with col_main_right:
        st.subheader("📊 当前新品榜参考 (前10名)")
        active_list_ref = app.get_active_leaderboard()
        if active_list_ref:
            ref_data = []
            for idx, item in enumerate(active_list_ref):
                ref_data.append({
                    "排名": idx + 1,
                    "皮肤": item['name'],
                    "分数": item.get('score', '--'),
                    "实价": item.get('real_price', '--')
                })
            st.dataframe(pd.DataFrame(ref_data), height=350, use_container_width=True, hide_index=True)
        else:
            st.info("暂无数据")

    # 提交逻辑处理
    if submitted:
        if not name:
            st.error("请输入皮肤名称")
        elif not final_q_code:
            st.error("品质选择无效")
        else:
            # 1. 如果是新建品质，先保存配置
            if q_mode == "新建品质":
                if final_q_code in app.quality_config:
                    st.warning("⚠️ 该品质代号已存在，将使用现有配置")
                else:
                    # 构造新配置
                    if new_sub_mode == "新建子品质 (归属已有系列)":
                        new_cfg = {
                            "price": new_q_price,
                            "name": new_q_name,
                            "parent": sel_root_for_new,  # 父级代码
                            "scale": 1.0,
                            "bg_color": "#ffffff"  # 默认白
                        }
                    else:
                        new_cfg = {
                            "price": new_q_price,
                            "name": new_q_name,
                            "parent": None,  # 顶级
                            "scale": 1.0,
                            "bg_color": "#ffffff"
                        }
                    app.quality_config[final_q_code] = new_cfg
                    app.save_data()  # 保存配置
                    st.success(f"已创建新品质: {new_q_name}")

            # 2. 标签转换逻辑
            is_new = (tag_option == "新品")
            is_rerun = (tag_option == "返场")
            is_preset = (tag_option == "预设")
            is_discontinued = (tag_option == "绝版")

            final_on_board = False if not can_be_on_board else on_board
            final_score = rank_score if final_on_board else None

            # 获取最终定价 (如果是新建的，前面没算)
            if q_mode == "新建品质":
                final_list_price = new_q_price
            else:
                final_list_price = app._get_list_price_by_quality(
                    float(final_q_code) if '.' in str(final_q_code) else int(final_q_code))

            # 3. 创建皮肤
            new_skin = {
                "quality": float(final_q_code) if '.' in str(final_q_code) else int(final_q_code),
                "name": name,
                "is_new": is_new, "is_rerun": is_rerun,
                "is_preset": is_preset, "is_discontinued": is_discontinued,
                "on_leaderboard": final_on_board,
                "score": final_score,
                "real_score": app._calculate_real_score(final_score, final_list_price, real_price),
                "growth": growth,
                "list_price": final_list_price,
                "real_price": real_price,
                "local_img": None
            }

            app.all_skins.append(new_skin)
            app.auto_prune_leaderboard()
            app.save_data()
            st.success(f"✅ 皮肤 [{name}] 已添加！")
            time.sleep(1)
            st.rerun()

# ----------------- Tab 3: 预设上线 -----------------
with t3:
    st.header("🕒 预设皮肤上线管理")

    presets = [s for s in app.all_skins if s.get('is_preset')]

    if not presets:
        st.info("当前没有预设皮肤。")
    else:
        # 选择要上线的皮肤
        skin_names = [s['name'] for s in presets]
        selected_name = st.selectbox("选择预设皮肤", skin_names)

        target_skin = next((s for s in presets if s['name'] == selected_name), None)

        if target_skin:
            st.divider()

            # 布局调整：左操作区 + 右榜单区
            col_preset_left, col_preset_right = st.columns([1, 1.2])

            with col_preset_left:
                c_p1, c_p2 = st.columns(2)
                new_price = c_p1.number_input("最终实价", value=float(target_skin.get('real_price', 0)))
                new_growth_input = c_p2.number_input("涨幅 (%)", value=float(target_skin.get('growth', 0)) * 100,
                                                     step=0.1)
                new_growth = new_growth_input / 100.0

                calc_method = st.radio("分数计算方式", ["根据排名自动计算", "手动输入分数", "不上榜"])

                final_score = None
                manual_score = 0.0
                target_rank = 1

                if calc_method == "根据排名自动计算":
                    target_rank = st.number_input("目标排名", min_value=1, value=1)
                    # 实时预览分数
                    active = app.get_active_leaderboard()
                    preview_pts = round(app.calculate_insertion_score(target_rank, active, new_price, new_growth), 1)
                    st.metric("预计排位分", f"{preview_pts} Pts")

                elif calc_method == "手动输入分数":
                    manual_score = st.number_input("输入 Rank Pts", value=0.0)

                st.markdown("###")
                if st.button("🚀 确认上线", type="primary", use_container_width=True):
                    # 更新基础数据
                    target_skin['is_preset'] = False
                    target_skin['is_new'] = True
                    target_skin['real_price'] = new_price
                    target_skin['growth'] = new_growth

                    if calc_method == "不上榜":
                        target_skin['on_leaderboard'] = False
                        target_skin['score'] = None
                    else:
                        target_skin['on_leaderboard'] = True
                        if calc_method == "手动输入分数":
                            target_skin['score'] = manual_score
                        else:
                            active = app.get_active_leaderboard()
                            target_skin['score'] = round(
                                app.calculate_insertion_score(target_rank, active, new_price, new_growth), 1)

                    # 计算真分
                    target_skin['real_score'] = app._calculate_real_score(target_skin['score'],
                                                                          target_skin['list_price'], new_price)

                    app.auto_prune_leaderboard()
                    app.save_data()
                    st.balloons()
                    st.success(f"✅ [{selected_name}] 已成功上线！")
                    time.sleep(1)
                    st.rerun()

            with col_preset_right:
                st.subheader("📊 当前新品榜参考")
                active_list_ref = app.get_active_leaderboard()
                if active_list_ref:
                    ref_data = []
                    for idx, item in enumerate(active_list_ref):
                        ref_data.append({
                            "排名": idx + 1,
                            "皮肤": item['name'],
                            "分数": item.get('score', '--'),
                            "实价": item.get('real_price', '--')
                        })
                    st.dataframe(pd.DataFrame(ref_data), height=400, use_container_width=True, hide_index=True)
                else:
                    st.info("暂无数据")

# ----------------- Tab 4: 数据编辑 -----------------
with t4:
    st.header("✏️ 全局数据编辑器")
    st.info("💡 提示：在下方表格中直接修改数据，改完后按 Enter 确认，数据会自动保存。")

    # 准备用于编辑的 DataFrame
    df = pd.DataFrame(app.all_skins)

    # 配置列的编辑类型 (全中文)
    column_config = {
        "name": st.column_config.TextColumn("皮肤名称", width="medium"),
        "quality": st.column_config.NumberColumn("品质代码", format="%d"),  # 修复为NumberColumn
        "score": st.column_config.NumberColumn("排位分", format="%.1f"),
        "real_price": st.column_config.NumberColumn("实价", format="¥%.1f"),
        "growth": st.column_config.NumberColumn("涨幅%", format="%.2f"),
        "list_price": st.column_config.NumberColumn("原价", format="¥%.1f"),
        "real_score": st.column_config.NumberColumn("真分", format="%.1f"),
        "is_new": st.column_config.CheckboxColumn("新品?"),
        "is_rerun": st.column_config.CheckboxColumn("返场?"),
        "is_preset": st.column_config.CheckboxColumn("预设?"),
        "is_discontinued": st.column_config.CheckboxColumn("绝版?"),
        "on_leaderboard": st.column_config.CheckboxColumn("在榜?"),
        "local_img": st.column_config.TextColumn("本地图片路径")
    }

    # 显示可编辑表格
    edited_df = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        num_rows="dynamic",
        key="data_editor",
        height=800
    )

    # 保存逻辑
    if st.button("💾 保存所有修改"):
        # 将 DataFrame 转回 List[Dict]
        updated_data = edited_df.to_dict(orient='records')

        # 重新计算关联数据 (如 list_price, real_score)
        app.all_skins = updated_data
        app._migrate_data_structure()  # 这个方法包含重新计算和保存
        st.success("✅ 数据已保存并重新计算！")

# ----------------- Tab 5: 品质管理 -----------------
with t5:
    st.header("💎 品质配置管理")

    q_df = pd.DataFrame.from_dict(app.quality_config, orient='index')
    q_df.index.name = 'code'
    q_df = q_df.reset_index()

    # 中文列名
    q_column_config = {
        "code": "品质代码",
        "name": "品质名称",
        "price": st.column_config.NumberColumn("定价", format="¥%.1f"),
        "parent": "父级代码",
        "scale": "缩放比例",
        "bg_color": st.column_config.TextColumn("背景色")
    }

    st.dataframe(q_df, column_config=q_column_config, use_container_width=True)

    with st.expander("➕ 新增/修改 品质"):
        with st.form("quality_form"):
            c1, c2, c3 = st.columns(3)
            q_code = c1.text_input("代号 (如 0.81)")
            q_name = c2.text_input("名称")
            q_price = c3.number_input("定价", min_value=0.0)

            c4, c5 = st.columns(2)
            q_color = c4.color_picker("背景颜色", "#ffffff")
            q_parent = c5.text_input("父级代号 (可选)")

            if st.form_submit_button("保存配置"):
                app.quality_config[q_code] = {
                    "price": q_price,
                    "name": q_name,
                    "parent": q_parent if q_parent else None,
                    "scale": 1.0,
                    "bg_color": q_color
                }
                app.save_data()
                st.success("✅ 品质配置已更新")
                st.rerun()

# ----------------- Tab 6: 发布与工具 -----------------
with t6:
    st.header("🚀 部署与工具箱")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📄 页面生成")
        if st.button("生成 index.html"):
            success, msg = app.generate_html()
            if success:
                st.success(msg)
                with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "r", encoding="utf-8") as f:
                    st.download_button("下载 HTML 文件", f, "index.html", "text/html")
            else:
                st.error(msg)

    with col2:
        st.subheader("🕷️ 头像抓取")
        if st.button("开始爬取缺失头像"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            missing_skins = [s for s in app.all_skins if not s.get('local_img')]
            total = len(missing_skins)

            if total == 0:
                st.info("所有皮肤都有头像了！")
            else:
                for i, skin in enumerate(missing_skins):
                    status_text.text(f"正在处理: {skin['name']}...")
                    success, log = app.crawler.fetch_single_image(skin)
                    if success:
                        print(log)  # 控制台留底
                    progress_bar.progress((i + 1) / total)

                app.save_data()
                st.success("✅ 抓取完成！")

    with col3:
        st.subheader("🌐 GitHub 发布")

        # 代理设置小工具
        st.markdown("**Git 代理设置 (解决连接失败)**")
        proxy_port = st.text_input("代理端口 (如 7890)", "7890")

        c_p1, c_p2 = st.columns(2)
        if c_p1.button("开启 Git 代理"):
            os.system(f"git config --global http.proxy http://127.0.0.1:{proxy_port}")
            os.system(f"git config --global https.proxy http://127.0.0.1:{proxy_port}")
            st.toast(f"已设置代理端口 {proxy_port}")

        if c_p2.button("关闭 Git 代理"):
            os.system("git config --global --unset http.proxy")
            os.system("git config --global --unset https.proxy")
            st.toast("已取消 Git 代理")

        st.divider()
        if st.button("🚀 Push 到 GitHub", type="primary"):
            os.chdir(LOCAL_REPO_PATH)

            # 🔥 核心修复：推送前强制自动刷新 HTML
            # 这步操作会将你内存里修复好的价格 (178.8等) 真正写入到 index.html 文件中
            with st.spinner("正在生成最新页面数据..."):
                gen_success, gen_msg = app.generate_html()
                if not gen_success:
                    st.error(f"页面生成失败，终止发布: {gen_msg}")
                    st.stop()

            try:
                # 容错处理：如果 commit 没有东西可提交，会返回 exit status 1，但这不代表 push 失败
                # 所以我们用 try-except 包裹 commit，允许它“失败”
                try:
                    subprocess.run([GIT_EXECUTABLE_PATH, "add", "."], check=True)
                    subprocess.run([GIT_EXECUTABLE_PATH, "commit", "-m", "update via streamlit"], check=True)
                except subprocess.CalledProcessError:
                    pass  # 忽略 commit 错误 (比如没有文件变化)

                # 执行 Push
                with st.spinner("正在推送到 GitHub..."):
                    result = subprocess.run([GIT_EXECUTABLE_PATH, "push"], capture_output=True, text=True)

                    if result.returncode == 0:
                        st.success(f"✅ 发布成功！")
                        st.markdown(f"[点击访问页面](https://{GITHUB_USERNAME}.github.io/hok-rank/)")
                    else:
                        st.error("❌ 发布失败")
                        st.code(result.stderr)
            except Exception as e:
                st.error(f"执行出错: {e}")