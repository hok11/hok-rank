import json
import os
import math
import subprocess
import requests
import time
import random
import re
from datetime import datetime
from jinja2 import Template
import hok_templates

# ================= 配置区域 =================
LOCAL_REPO_PATH = r"D:\python-learn\hok-rank"
GIT_EXECUTABLE_PATH = r"D:\Git\bin\git.exe"
GITHUB_USERNAME = "hok11"
LEADERBOARD_CAPACITY = 20


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
        self.instructions = ["数据仅供参考", "金额单位为人民币/积分"]

        self.default_quality_config = {
            "1": {"price": 100.0, "parent": None, "name": "勇者", "scale": 0.9, "bg_color": "#ffffff"},
            "20": {"price": 100.0, "parent": "1", "name": "勇者", "scale": 1.1, "bg_color": "#ffffff"},
            "50": {"price": 100.0, "parent": None, "name": "战令限定", "scale": 1.0, "bg_color": "#ffffff"},
            "50.1": {"price": 100.0, "parent": "50", "name": "战令限定", "scale": 1.0, "bg_color": "#ffffff"},
            "100": {"price": 200.0, "parent": None, "name": "史诗", "scale": 1.1, "bg_color": "#ffffff"},
            "250": {"price": 400.0, "parent": None, "name": "传说", "scale": 1.2, "bg_color": "#ffffff"},
            "500": {"price": 400.0, "parent": None, "name": "传说限定", "scale": 1.1, "bg_color": "#e0f2fe"},
            "900": {"price": 400.0, "parent": "500", "name": "马年限定", "scale": 1.0, "bg_color": "#ffffff"},
            "1000": {"price": 600.0, "parent": None, "name": "珍品传说", "scale": 1.0, "bg_color": "#bfdbfe"},
            "2500": {"price": 1800.0, "parent": None, "name": "荣耀典藏", "scale": 1.4, "bg_color": "#fff7cd"},
            "5000": {"price": 1200.0, "parent": None, "name": "无双", "scale": 1.0, "bg_color": "#f3e8ff"},
            "7500": {"price": 1200.0, "parent": "5000", "name": "无双", "scale": 1.0, "bg_color": "#f3e8ff"},
            "10000": {"price": 2400.0, "parent": None, "name": "珍品无双", "scale": 1.1, "bg_color": "#ffdcdc"},
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
        return updates

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

    def parse_revenue_str(self, val):
        """解析单个数值字符串为浮点数 (支持中文/英文)"""
        if val is None: return 0.0
        s = str(val).upper().replace('¥', '').replace(',', '').strip()
        if not s: return 0.0

        multiplier = 1.0
        # 移除比较符号进行纯数值解析
        s = s.replace('>', '').replace('<', '').replace('~', '')

        if '亿' in s or 'B' in s:
            multiplier = 100000000.0
            s = s.replace('亿', '').replace('B', '')
        elif '万' in s or 'W' in s:
            multiplier = 10000.0
            s = s.replace('万', '').replace('W', '')
        elif 'M' in s:
            multiplier = 1000000.0
            s = s.replace('M', '')
        elif 'K' in s:
            multiplier = 1000.0
            s = s.replace('K', '')

        try:
            return float(s) * multiplier
        except:
            return 0.0

    def parse_revenue_for_sort(self, val_str):
        """
        🔥 智能排序算法：计算用于排序的权重值
        支持: "100~200" (取平均), ">100" (取100.0001), "<100" (取99.9999)
        """
        if not val_str: return -1.0
        s = str(val_str).strip()

        # 1. 范围型: A~B
        if '~' in s:
            parts = s.split('~')
            if len(parts) == 2:
                v1 = self.parse_revenue_str(parts[0])
                v2 = self.parse_revenue_str(parts[1])
                return (v1 + v2) / 2.0

        # 2. 大于型: >A
        if s.startswith('>') or s.startswith('》'):
            base = self.parse_revenue_str(s)
            return base + 0.0001  # 确保排在同数值前面

        # 3. 小于型: <A
        if s.startswith('<') or s.startswith('《'):
            base = self.parse_revenue_str(s)
            return base - 0.0001  # 确保排在同数值后面

        # 4. 普通数值
        return self.parse_revenue_str(s)

    def _migrate_data_structure(self):
        for skin in self.all_skins:
            skin['list_price'] = self._get_list_price_by_quality(skin['quality'])

            if 'sales_volume' not in skin: skin['sales_volume'] = "0"
            if 'revenue' not in skin: skin['revenue'] = "0"
            if 'real_price' not in skin: skin['real_price'] = str(skin.get('price', 0))
            if 'is_hidden' not in skin: skin['is_hidden'] = False
            if 'is_pool' not in skin: skin['is_pool'] = False  # 新增祈愿池标记

            skin['sales_volume'] = str(skin['sales_volume'])
            skin['revenue'] = str(skin['revenue'])
            skin['real_price'] = str(skin['real_price'])

            if isinstance(skin.get('real_price'), (int, float)):
                skin['real_price'] = str(skin['real_price'])

            if 'score' in skin: del skin['score']
            if 'real_score' in skin: del skin['real_score']

            if 'on_leaderboard' not in skin:
                skin['on_leaderboard'] = True
        self.save_data()

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
                seen = set();
                unique = []
                for s in self.all_skins:
                    if s['name'] not in seen: unique.append(s); seen.add(s['name'])
                self.all_skins = unique
            except:
                self.all_skins = []
        else:
            self.save_data()

    def _get_sort_key(self, skin):
        # 1. 隐藏的放最后
        # 2. 销售额 (revenue) 智能排序
        is_hidden = 1 if skin.get('is_hidden', False) else 0
        rev_val = self.parse_revenue_for_sort(skin.get('revenue', "0"))
        return (is_hidden, -rev_val)

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                # 排序保存
                self.all_skins.sort(key=self._get_sort_key)
                data_to_save = {
                    "skins": self.all_skins,
                    "instructions": self.instructions,
                    "quality_config": self.quality_config
                }
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"存档失败: {e}")

    def get_total_skins(self):
        data = self.all_skins[:]
        data.sort(key=self._get_sort_key)
        return data

    def get_active_leaderboard(self):
        active = [s for s in self.all_skins if not s.get('is_hidden', False) and s.get('on_leaderboard', True)]
        active.sort(key=self._get_sort_key)
        return active

    def auto_prune_leaderboard(self):
        self.all_skins.sort(key=self._get_sort_key)

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

        display_skins = self.get_total_skins()

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
                            q_key = k;
                            break
                except:
                    pass
            skin['quality_key'] = q_key

        t = Template(hok_templates.HTML_TEMPLATE)
        html_content = t.render(total_skins=display_skins, quality_config=self.quality_config,
                                header_gifs=header_gifs, instructions=self.instructions,
                                update_time=datetime.now().strftime("%Y-%m-%d %H:%M"))
        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            return True, "📄 HTML 生成成功"
        except Exception as e:
            return False, f"HTML 生成失败: {e}"