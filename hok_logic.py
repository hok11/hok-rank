import json
import os
import math
import subprocess
import requests
import time
import random
from datetime import datetime
from jinja2 import Template
import hok_templates  # 引用模板

# ================= 配置区域 =================
LOCAL_REPO_PATH = r"D:\python-learn\hok-rank"
GIT_EXECUTABLE_PATH = r"D:\Git\bin\git.exe"
GITHUB_USERNAME = "hok11"
LEADERBOARD_CAPACITY = 10


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
        # 保持原有爬虫逻辑
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
            "1": {"price": 48.8, "parent": None, "name": "勇者", "scale": 0.9, "bg_color": "#ffffff"},
            "20": {"price": 48.8, "parent": "1", "name": "勇者", "scale": 1.1, "bg_color": "#ffffff"},
            "50": {"price": 18.8, "parent": None, "name": "战令限定", "scale": 1.0, "bg_color": "#ffffff"},
            "50.1": {"price": 18.8, "parent": "50", "name": "战令限定", "scale": 1.0, "bg_color": "#ffffff"},
            "100": {"price": 71.0, "parent": None, "name": "史诗", "scale": 1.1, "bg_color": "#ffffff"},
            "250": {"price": 135.0, "parent": None, "name": "传说", "scale": 1.2, "bg_color": "#ffffff"},
            "500": {"price": 143.0, "parent": None, "name": "传说限定", "scale": 1.1, "bg_color": "#e0f2fe"},
            "900": {"price": 143.0, "parent": "500", "name": "马年限定", "scale": 1.0, "bg_color": "#ffffff"},
            "1000": {"price": 200.0, "parent": None, "name": "珍品传说", "scale": 1.0, "bg_color": "#bfdbfe"},
            "2500": {"price": 600.0, "parent": None, "name": "荣耀典藏", "scale": 1.4, "bg_color": "#fff7cd"},
            "5000": {"price": 400.0, "parent": None, "name": "无双", "scale": 1.0, "bg_color": "#f3e8ff"},
            "7500": {"price": 400.0, "parent": "5000", "name": "无双", "scale": 1.0, "bg_color": "#f3e8ff"},
            "10000": {"price": 800.0, "parent": None, "name": "珍品无双", "scale": 1.1, "bg_color": "#ffdcdc"},
        }

        self.quality_config = self.default_quality_config.copy()

        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
        self.desc_dir = os.path.join(LOCAL_REPO_PATH, "skin_descs")
        self.avatar_dir = os.path.join(LOCAL_REPO_PATH, "skin_avatars")

        if not os.path.exists(self.desc_dir): os.makedirs(self.desc_dir)
        if not os.path.exists(self.avatar_dir): os.makedirs(self.avatar_dir)

        self.crawler = SkinCrawler(LOCAL_REPO_PATH)
        self.load_data()

        # 强制合并配置 (代码优先)
        for k, v in self.default_quality_config.items():
            if k in self.quality_config:
                self.quality_config[k]['price'] = v['price']
                self.quality_config[k]['name'] = v['name']
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

                # 去重
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
            print(f"存档失败: {e}")

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