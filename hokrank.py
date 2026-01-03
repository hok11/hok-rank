import math
import json
import os
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

# 新品榜计算窗口 Top 10
LEADERBOARD_CAPACITY = 10


# ===========================================

class SkinCrawler:
    def __init__(self, data_path):
        self.save_dir = os.path.join(data_path, "skin_avatars")
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/plain, */*; q=0.01', 'Referer': 'https://image.baidu.com/search/index',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def fetch_images(self, skin_list):
        print("\n🕷️ 正在启动百度图片搜索...")
        count = 0
        for skin in skin_list:
            if skin.get('local_img') and os.path.exists(os.path.join(LOCAL_REPO_PATH, skin['local_img'])): continue
            parts = skin['name'].split('-')
            keyword = f"{parts[1]} {parts[0]}" if len(parts) >= 2 else skin['name']
            url = "https://image.baidu.com/search/acjson"
            params = {
                "tn": "resultjson_com", "logid": "8388656667592781395", "ipn": "rj", "ct": "201326592", "is": "",
                "fp": "result",
                "queryWord": keyword, "cl": "2", "lm": "-1", "ie": "utf-8", "oe": "utf-8", "adpicid": "", "st": "-1",
                "z": "",
                "ic": "", "hd": "", "latest": "", "copyright": "", "word": keyword, "s": "", "se": "", "tab": "",
                "width": "",
                "height": "", "face": "0", "istype": "2", "qc": "", "nc": "1", "fr": "", "expermode": "", "force": "",
                "pn": "0", "rn": "1", "gsm": "1e",
            }
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=5)
                try:
                    data = resp.json()
                except:
                    try:
                        data = json.loads(resp.text.replace(r"\'", r"'"))
                    except:
                        continue
                if 'data' in data and len(data['data']) > 0 and 'thumbURL' in data['data'][0]:
                    img_url = data['data'][0]['thumbURL']
                    if not img_url:
                        if 'replaceUrl' in data['data'][0] and len(data['data'][0]['replaceUrl']) > 0:
                            img_url = data['data'][0]['replaceUrl'][0]['ObjURL']
                        else:
                            continue
                    print(f"   🔍 搜索 [{keyword}] -> 成功!")
                    img_resp = requests.get(img_url, headers=self.headers, timeout=10)
                    safe_name = skin['name'].replace("/", "_").replace("\\", "_").replace(" ", "")
                    file_name = f"{safe_name}.jpg"
                    file_path = os.path.join(self.save_dir, file_name)
                    with open(file_path, 'wb') as f:
                        f.write(img_resp.content)
                    skin['local_img'] = f"skin_avatars/{file_name}"
                    count += 1
                    print(f"   ✅ 已下载: {file_name}")
                    time.sleep(random.uniform(0.5, 1.5))
            except Exception:
                pass
        return count


class SkinSystem:
    def __init__(self):
        self.all_skins = []
        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
        self.crawler = SkinCrawler(LOCAL_REPO_PATH)
        self.load_data()
        self._migrate_data_structure()

    def _get_list_price_by_quality(self, q_code):
        # 3.5 (传限): 178.8 | 4 (传说): 168.8 | 6 (勇者): 48.8 | 0.5-1 (无双): 400
        mapping = {0: 800.0, 1: 400.0, 2: 600.0, 3: 200.0, 3.5: 178.8, 4: 168.8, 5: 88.8, 6: 48.8}
        if 0.5 <= q_code < 1: return 400.0
        return mapping.get(q_code, 0.0)

    def _calculate_real_score(self, rank_score, list_price, real_price):
        # 🔥 修正：如果点数被显式设为 None，真实点数也为 None
        if rank_score is None: return None
        if real_price <= 0 or list_price <= 0: return None
        return round(rank_score * (real_price / list_price), 1)

    def _migrate_data_structure(self):
        if not self.all_skins: return
        for skin in self.all_skins:
            skin['list_price'] = self._get_list_price_by_quality(skin['quality'])
            if 'real_price' not in skin: skin['real_price'] = skin.get('price', 0.0)

            # 🔥 允许 score 字段为 None
            skin['real_score'] = self._calculate_real_score(skin.get('score'), skin['list_price'], skin['real_price'])
            if 'price' in skin: del skin['price']

            if 'on_leaderboard' not in skin:
                skin['on_leaderboard'] = True if (skin.get('is_new') or skin.get('is_rerun')) else False
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
                    self.all_skins = loaded.get('total', []) + loaded.get('new', [])
                seen = set();
                unique = []
                for s in self.all_skins:
                    if s['name'] not in seen: unique.append(s); seen.add(s['name'])
                self.all_skins = unique
                print(f"✅ 数据加载完毕 (总库存: {len(self.all_skins)})")
            except:
                self.all_skins = []
        else:
            self.save_data()

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                # 🔥 排序逻辑：None 值 (Null) 默认排在数字后面
                self.all_skins.sort(key=lambda x: (x.get('score') is None, -(x.get('score') or 0)))
                json.dump(self.all_skins, f, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            print(f"❌ 错误：找不到路径 {LOCAL_REPO_PATH}")

    # ================= 数据逻辑 =================
    def get_total_skins(self):
        data = self.all_skins[:]
        data.sort(key=lambda x: (x.get('score') is None, -(x.get('score') or 0)))
        return data

    def get_active_leaderboard(self):
        active = [s for s in self.all_skins if s.get('on_leaderboard', False)]
        active.sort(key=lambda x: (x.get('score') is None, -(x.get('score') or 0)))
        return active[:LEADERBOARD_CAPACITY]

    # ================= 打印逻辑 =================
    def print_console_table(self, data_list=None, title="榜单"):
        if data_list is None:
            data_list = self.get_total_skins()

        print(f"\n====== 🏆 {title} (Items: {len(data_list)}) ======")
        print(
            f"{'No.':<4} {'St':<6} {'Q':<4} {'名字':<12} {'RankPts':<8} {'RealPts':<8} {'Growth':<8} {'ListP':<8} {'RealP'}")
        print("-" * 94)
        for i, skin in enumerate(data_list):
            # 🔥 控制台显式显示 Null
            s_val = skin.get('score')
            score_str = "Null" if s_val is None else str(s_val)
            real_pts_str = "Null" if skin.get('real_score') is None else str(skin['real_score'])

            list_p_str = f"¥{skin.get('list_price', 0)}"
            real_p_str = f"¥{skin.get('real_price', 0)}" if skin.get('real_price', 0) > 0 else "--"
            g_val = skin.get('growth', 0)
            growth_str = f"+{g_val}%" if g_val > 0 else (f"{g_val}%" if g_val < 0 else "--")

            status_str = "[🔥在榜]" if skin.get('on_leaderboard') else "[❌退榜]"
            q_val = skin['quality']
            q_str = str(q_val) if isinstance(q_val, float) else str(q_val)

            print(
                f"{i + 1:<4} {status_str:<6} {q_str:<4} {skin['name']:<12} {score_str:<8} {real_pts_str:<8} {growth_str:<8} {list_p_str:<8} {real_p_str}")
        print("=" * 94 + "\n")

    def view_rank_ui(self):
        print("\n1. 查看新品榜 (Top 10)")
        print("2. 查看历史总榜 (All)")
        c = input("选: ")
        if c == '1':
            self.print_console_table(self.get_active_leaderboard(), "新品榜")
        else:
            self.print_console_table(self.get_total_skins(), "历史总榜")

    def calculate_insertion_score(self, rank_input, active_list, real_price, growth):
        if rank_input == 1:
            old_top1_score = active_list[0]['score'] if active_list and active_list[0]['score'] else 0
            return max(old_top1_score / 0.6, (282 / math.sqrt(1.25)) - 82, real_price * growth * 15)

        prev_idx = rank_input - 2
        prev_score = 200 if prev_idx < 0 else (active_list[prev_idx]['score'] or 0)
        next_idx = rank_input - 1

        if next_idx < len(active_list) and active_list[next_idx]['score'] is not None:
            next_score = active_list[next_idx]['score']
            return math.sqrt(prev_score * next_score)
        else:
            print(f"   ⚠️ 触发断层补位算法 (上一名分数: {prev_score})")
            t = int(rank_input)
            while True:
                val = self._get_base_score(t)
                if val < prev_score:
                    print(f"   ✅ 补位成功：使用 Rank {t} 的理论分, 分数={round(val, 1)}")
                    return val
                t += 1
                if t > 1000: return 1.0

    def _auto_prune_leaderboard(self):
        """🔥 自动挤出机制：确保榜单只有 10 人"""
        active = [s for s in self.all_skins if s.get('on_leaderboard', False)]
        active.sort(key=lambda x: (x.get('score') is None, -(x.get('score') or 0)))

        if len(active) > LEADERBOARD_CAPACITY:
            # 找到第11名及以后的皮肤
            to_remove = active[LEADERBOARD_CAPACITY:]
            for skin in to_remove:
                skin['on_leaderboard'] = False
                print(f"   📉 榜单超员，[{skin['name']}] 已自动退榜")

    def add_skin_ui(self):
        active_list = self.get_active_leaderboard()
        print(f"\n>>> 添加新皮肤 (计算参考: 真实在榜 Top {len(active_list)})")
        self.print_console_table(active_list, "当前新品榜")

        try:
            print("格式: 品质代码(0.5-1/3.5/4/6...) 名字 [非0=复刻]")
            raw = input("输入: ").split()
            if len(raw) < 2: return

            try:
                q_code = float(raw[0])
                if q_code.is_integer(): q_code = int(q_code)
            except:
                print("❌ 品质代码必须是数字");
                return

            name = raw[1]
            is_rerun = (len(raw) >= 3 and raw[2] != '0')
            is_new = not is_rerun
            list_p = self._get_list_price_by_quality(q_code)  # 自动锁定原价

            enter_board_input = input("是否计入新品榜? (y/n, 默认y): ").strip().lower()
            is_on_board = (enter_board_input != 'n')

            rank_score = None
            real_p = 0.0
            growth = 0.0

            if is_on_board:
                print(f"--- 进入新品榜自动计算 ---")
                rank = int(input(f"插入到新品榜第几名? (1-{len(active_list) + 1}): "))
                real_p = float(input("实际价格: "))
                growth = float(input("涨幅: "))
                rank_score = round(self.calculate_insertion_score(rank, active_list, real_p, growth), 1)
            else:
                # 🔥 修正：不上榜皮肤支持输入 Null 设为空
                print(f"--- 🚫 不进榜 (自定义模式) ---")
                score_in = input("请输入排位点数 (直接回车或输入null代表不计分): ").strip().lower()
                if score_in and score_in != 'null':
                    rank_score = float(score_in)

                real_p = float(input("实际价格: ") or 0.0)
                growth = float(input("涨幅: ") or 0.0)

            real_score = self._calculate_real_score(rank_score, list_p, real_p)

            self.all_skins.append({
                "quality": q_code, "name": name,
                "is_rerun": is_rerun, "is_new": is_new,
                "on_leaderboard": is_on_board,
                "score": rank_score,
                "real_score": real_score,
                "growth": growth,
                "list_price": list_p,
                "real_price": real_p,
                "local_img": None
            })

            self._auto_prune_leaderboard()  # 🔥 触发挤出逻辑
            self.save_data()
            self.generate_html()
            status_msg = "[🔥在榜]" if is_on_board else "[🚫不进榜]"
            print(f"✅ 添加成功 {status_msg} - 分数: {rank_score}")

        except ValueError:
            print("❌ 输入错误")

    def retire_skin_ui(self):
        print("\n>>> 手动退榜 (售卖期结束)")
        active_list = self.get_active_leaderboard()
        self.print_console_table(active_list, "当前在榜名单")
        try:
            idx = int(input("输入要下榜的序号 (No.): ")) - 1
            if 0 <= idx < len(active_list):
                target_skin = active_list[idx]
                if input(f"确认将 [{target_skin['name']}] 移出新品榜? (y/n): ").lower() == 'y':
                    target_skin['on_leaderboard'] = False
                    self.save_data();
                    self.generate_html();
                    print(f"✅ [{target_skin['name']}] 已退榜")
            else:
                print("❌ 序号无效")
        except ValueError:
            print("❌ 输入错误")

    def modify_data_ui(self):
        print("\n1. 修改数据")
        print("2. 删除数据")
        c = input("选: ")
        self.print_console_table(self.get_total_skins(), "历史总榜")
        target_list = self.get_total_skins()
        try:
            idx = int(input("输入总榜序号: ")) - 1
            if 0 <= idx < len(target_list):
                if c == '2':
                    del self.all_skins[idx];
                    self.save_data();
                    self.generate_html();
                    print("🗑️ 已删除");
                    return

                item = target_list[idx]
                while True:
                    # 🔥 显式 Null
                    cur_s = "Null" if item['score'] is None else item['score']
                    print(f"\n当前: {item['name']} | 状态: {'[🔥在榜]' if item.get('on_leaderboard') else '[❌退榜]'}")
                    print(f"1. 排位点数: {cur_s}")
                    print(f"2. 涨幅 (%): {item['growth']}")
                    print(f"3. 实际价格: {item.get('real_price', 0)}")
                    print(f"4. 列表定价: {item.get('list_price', 0)}")
                    print(f"5. 品质代码: {item['quality']}")

                    raw = input("输入 [序号] [数值] (输null设为空, 直接回车退出): ").strip().lower()
                    if not raw: break
                    parts = raw.split()

                    if len(parts) < 2: continue

                    try:
                        opt, val_raw = parts[0], parts[1]
                        if opt == '1':
                            item['score'] = float(val_raw) if val_raw != 'null' else None
                        elif opt == '2':
                            item['growth'] = float(val_raw)
                        elif opt == '3':
                            item['real_price'] = float(val_raw)
                        elif opt == '4':
                            item['list_price'] = float(val_raw)
                        elif opt == '5':
                            item['quality'] = float(val_raw)

                        item['real_score'] = self._calculate_real_score(item['score'], item['list_price'],
                                                                        item['real_price'])
                        print("✅ 已暂存")
                    except:
                        pass
                self.save_data();
                self.generate_html();
                print("💾 保存成功")
        except:
            pass

    def manage_status_ui(self):
        self.print_console_table()
        try:
            idx = int(input("输入序号修改标签: ")) - 1
            if 0 <= idx < len(self.get_total_skins()):  # 修复范围
                target = self.get_total_skins()[idx]
                op = input("设为: 1-复刻  2-新增: ")
                if op == '1':
                    target['is_rerun'] = True;
                    target['is_new'] = False;
                    print("✅ [复刻]")
                elif op == '2':
                    target['is_rerun'] = False;
                    target['is_new'] = True;
                    print("✅ [新增]")
                self.save_data();
                self.generate_html()
        except:
            pass

    def run_crawler_ui(self):
        count = self.crawler.fetch_images(self.all_skins)
        if count > 0:
            self.save_data();
            self.generate_html();
            print(f"\n🎉 更新了 {count} 张图片！")
        else:
            print("\n⚠️ 无新图片更新")

    def generate_html(self):
        quality_map = {0: "珍品无双", 1: "无双", 2: "荣耀典藏", 3: "珍品传说", 3.5: "传说限定", 4: "传说", 5: "史诗",
                       6: "勇者"}
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=0.6, minimum-scale=0.1, maximum-scale=3.0, user-scalable=yes">
    <title>Honor of Kings Skin Prediction</title>
    <style>
        :root { --header-bg: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f0f2f5; display: flex; flex-direction: column; align-items: center; padding: 20px; gap: 30px; }

        @media screen and (max-width: 600px) {
            .chart-card { zoom: 0.7; }
            body { padding: 5px; align-items: center; }
        }

        .chart-card { background: white; width: 100%; max-width: 950px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); padding-bottom: 20px; }
        .chart-header { background: var(--header-bg); padding: 25px 20px; text-align: center; color: white; margin-bottom: 10px; }
        .chart-header h1 { font-size: 24px; font-weight: 800; margin-bottom: 8px; }
        .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
        table { width: 98%; margin: 0 auto; border-collapse: separate; border-spacing: 0 8px; font-size: 14px; min-width: 750px; }
        th { text-align: center; padding: 12px 2px; font-weight: 700; color: #111; border-bottom: 1px solid #eee; font-size: 12px; white-space: nowrap; }

        .qual-header { display: inline-flex; align-items: center; justify-content: center; gap: 6px; position: relative; }
        .multi-select-box { 
            font-size: 11px; border-radius: 4px; border: 1px solid #ddd; padding: 4px 8px; 
            color: #333; font-weight: bold; cursor: pointer; background: white; min-width: 85px; text-align: center;
        }
        .dropdown-menu {
            display: none; position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; border-radius: 6px; padding: 8px; min-width: 130px; text-align: left;
        }
        .dropdown-menu.show { display: block; }
        .dropdown-item { display: flex; align-items: center; gap: 8px; padding: 6px 4px; cursor: pointer; font-size: 12px; color: #444; }
        .dropdown-item:hover { background: #f5f5f5; }

        .col-sort { cursor: pointer; position: relative; }
        .col-sort::after { content: ' ⇅'; font-size: 10px; color: #ccc; margin-left: 5px; }
        .col-sort.sort-asc::after { content: ' ▲'; color: #6366f1; }
        .col-sort.sort-desc::after { content: ' ▼'; color: #6366f1; }

        td { padding: 12px 2px; vertical-align: middle; text-align: center; background-color: transparent; border: none; white-space: nowrap; }
        .rounded-left { border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
        .rounded-right { border-top-right-radius: 12px; border-bottom-right-radius: 12px; }

        .quality-col { min-width: 60px; text-align: center; }
        .quality-icon { 
            height: 28px; width: auto; display: inline-block; 
            vertical-align: middle; transition: transform 0.2s; 
            object-fit: contain;
        }
        .quality-icon.wushuang-big { transform: scale(1.45); }
        .quality-icon.legend-big { transform: scale(1.1); }
        .quality-icon.brave-small { transform: scale(0.8); }

        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; object-fit: cover; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 5px; min-width: 180px; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; }
        .box-style { display: inline-block; width: 100%; padding: 6px 0; font-weight: 700; font-size: 12px; border-radius: 6px; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }

        /* 🔥 Null 样式 */
        .pts-null { color: #f43f5e; font-weight: 800; font-style: italic; }
        /* 🔥 1.9% 特殊紫色样式 */
        .growth-special { color: #a855f7 !important; font-weight: 900 !important; }
    </style>
</head>
<body>
    <div class="chart-card">
        <div class="chart-header"><h1>Honor of Kings Skin Prediction</h1><p>Update: {{ update_time }}</p></div>
        <div class="table-container">
            <table id="skinTable">
                <thead>
                    <tr>
                        <th class="col-sort" onclick="sortTable(0, 'int')">No</th>
                        <th>
                            <div class="qual-header">
                                <div id="multiSelectBtn" class="multi-select-box" onclick="toggleMenu(event)">全部品质</div>
                                <div id="dropdownMenu" class="dropdown-menu">
                                    <label class="dropdown-item"><input type="checkbox" id="selectAll" value="all" checked onchange="handleSelectAll(this)"> <strong>全部品质</strong></label>
                                    <hr style="margin: 4px 0; border: 0; border-top: 1px solid #eee;">
                                    {% for qname in ["珍品无双", "无双", "荣耀典藏", "珍品传说", "传说限定", "传说", "史诗", "勇者"] %}
                                    <label class="dropdown-item"><input type="checkbox" class="q-check" value="{{ qname }}" onchange="handleSingleSelect(this)"> {{ qname }}</label>
                                    {% endfor %}
                                </div>
                                <span class="col-sort" style="padding-left:10px" onclick="sortTable(1, 'float')"></span>
                            </div>
                        </th>
                        <th style="cursor:default; text-align:left; padding-left:20px;">Skin Name</th>
                        <th class="col-sort" onclick="sortTable(3, 'float')">Rank Pts</th>
                        <th class="col-sort" onclick="sortTable(4, 'float')">Real Pts</th>
                        <th class="col-sort" onclick="sortTable(5, 'float')">Growth</th>
                        <th class="col-sort" onclick="sortTable(6, 'float')">List P</th>
                        <th class="col-sort" onclick="sortTable(7, 'float')">Real P</th>
                    </tr>
                </thead>
                <tbody>
                    {% for skin in total_skins %}
                    {% set rb = '#ffffff' %}
                    {% if skin.quality == 3.5 %}{% set rb = '#e0f2fe' %}{% elif skin.quality == 3 %}{% set rb = '#dcfce7' %}{% elif skin.quality == 2 %}{% set rb = '#bfdbfe' %}{% elif skin.quality == 1 or (skin.quality >= 0.5 and skin.quality < 1) %}{% set rb = '#f3e8ff' %}{% elif skin.quality == 0 %}{% set rb = '#fef9c3' %}{% endif %}

                    {% set q_display_name = quality_map[skin.quality] or ("无双" if 0.5 <= skin.quality < 1 else "") %}

                    <tr data-quality="{{ q_display_name }}">
                        <td>{{ loop.index }}</td>
                        <td class="quality-col" data-val="{{ skin.quality }}">
                            {% set q_cls = '' %}
                            {% if skin.quality <= 1 %}{% set q_cls = 'wushuang-big' %}
                            {% elif skin.quality == 4 %}{% set q_cls = 'legend-big' %}
                            {% elif skin.quality == 6 %}{% set q_cls = 'brave-small' %}{% endif %}
                            <img src="./images/{{ skin.quality }}.gif" class="quality-icon {{ q_cls }}" 
                                 onerror="loadFallbackImg(this, '{{ skin.quality }}')">
                        </td>
                        <td class="rounded-left" style="background-color: {{ rb }};"><div class="song-col">
                            {% if skin.local_img %}<img src="./{{ skin.local_img }}" class="album-art">{% else %}<img src="https://via.placeholder.com/48?text={{ skin.name[0] }}" class="album-art">{% endif %}
                            <div class="song-info"><span class="song-title" style="font-weight:700">{{ skin.name }}</span></div>
                        </div></td>
                        <td data-val="{{ skin.score if skin.score is not none else -999999 }}" style="background-color: {{ rb }};">
                            {% if skin.score is not none %}<span>{{ skin.score }}</span>{% else %}<span class="pts-null">Null</span>{% endif %}
                        </td>
                        <td data-val="{{ skin.real_score if skin.real_score is not none else -999999 }}" style="background-color: {{ rb }}; color:#6366f1;">
                            {% if skin.real_score is not none %}<span>{{ skin.real_score }}</span>{% elif skin.score is none %}<span class="pts-null">Null</span>{% else %}<span>--</span>{% endif %}
                        </td>
                        <td data-val="{{ skin.growth }}" style="background-color: {{ rb }};">
                            <div class="box-style {{ 'growth-special' if skin.growth == 1.9 else '' }}">
                                {{ skin.growth }}%{% if skin.growth == 1.9 %}!{% endif %}
                            </div>
                        </td>
                        <td data-val="{{ skin.list_price }}" style="background-color: {{ rb }};">¥{{ skin.list_price }}</td>
                        <td class="rounded-right" data-val="{{ skin.real_price }}" style="background-color: {{ rb }};">{% if skin.real_price > 0 %}¥{{ skin.real_price }}{% else %}--{% endif %}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <script>
    function toggleMenu(e) { e.stopPropagation(); document.getElementById('dropdownMenu').classList.toggle('show'); }
    document.addEventListener('click', () => document.getElementById('dropdownMenu').classList.remove('show'));
    document.getElementById('dropdownMenu').addEventListener('click', (e) => e.stopPropagation());

    function loadFallbackImg(img, q) {
        if (img.src.indexOf('.gif') !== -1) {
            img.src = './images/' + q + '.jpg';
        } else if (img.src.indexOf('.jpg') !== -1 && img.src.indexOf('1.jpg') === -1) {
            let qv = parseFloat(q);
            if (qv >= 0.5 && qv <= 1) img.src = './images/1.jpg';
        }
    }

    function handleSelectAll(mainCb) { if (mainCb.checked) document.querySelectorAll('.q-check').forEach(cb => cb.checked = false); updateFilter(); }
    function handleSingleSelect(singleCb) { if (singleCb.checked) document.getElementById('selectAll').checked = false; updateFilter(); }
    function updateFilter() {
        const main = document.getElementById('selectAll');
        const checkedOnes = Array.from(document.querySelectorAll('.q-check')).filter(i => i.checked).map(i => i.value);
        const btn = document.getElementById('multiSelectBtn');
        if (main.checked || checkedOnes.length === 0) {
            main.checked = true; btn.innerText = "全部品质";
            document.querySelectorAll('#skinTable tbody tr').forEach(r => r.style.display = "");
        } else {
            btn.innerText = checkedOnes.length === 1 ? checkedOnes[0] : "筛选中";
            document.querySelectorAll('#skinTable tbody tr').forEach(r => {
                r.style.display = checkedOnes.includes(r.getAttribute('data-quality')) ? "" : "none";
            });
        }
    }
    function sortTable(n, type) {
        var table = document.getElementById("skinTable"), rows = Array.from(table.rows).slice(1), headers = table.getElementsByTagName("TH"), dir = "desc";
        if (headers[n].classList.contains("sort-desc")) dir = "asc";
        rows.sort((a, b) => {
            var x = parseFloat(a.cells[n].getAttribute("data-val") || a.cells[n].innerText.replace(/[¥%!]/g, ''));
            var y = parseFloat(b.cells[n].getAttribute("data-val") || b.cells[n].innerText.replace(/[¥%!]/g, ''));
            if (isNaN(x)) x = -9999999; if (isNaN(y)) y = -9999999;
            return dir === "asc" ? x - y : y - x;
        });
        rows.forEach(r => table.tBodies[0].appendChild(r));
        Array.from(headers).forEach(h => h.classList.remove("sort-asc", "sort-desc"));
        headers[n].classList.add(dir === "asc" ? "sort-asc" : "sort-desc");
    }
    window.onload = () => sortTable(3, 'float');
    </script>
</body>
</html>
        """
        t = Template(html_template)
        html_content = t.render(total_skins=self.get_total_skins(), quality_map=quality_map,
                                update_time=datetime.now().strftime("%Y-%m-%d %H:%M"))
        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            print("📄 HTML 刷新完成")
        except:
            print("❌ 路径错误")

    def deploy_to_github(self):
        print("\n🚀 正在连接 GitHub...");
        os.chdir(LOCAL_REPO_PATH)
        try:
            subprocess.run([GIT_EXECUTABLE_PATH, "add", "."], check=True)
            subprocess.run([GIT_EXECUTABLE_PATH, "commit", "-m", f"Update {datetime.now().strftime('%H:%M')}"],
                           check=True)
            subprocess.run([GIT_EXECUTABLE_PATH, "push"], check=True)
            print(f"\n✅ 发布成功！🌐 访问: https://hok11.github.io/hok-rank/")
        except Exception as e:
            print(f"\n❌ 发布失败: {e}")


if __name__ == "__main__":
    app = SkinSystem()
    while True:
        print("\n" + "=" * 55)
        print("👑 王者荣耀榜单 V19.74 (1.9%彩蛋全量版)")
        print(f"📊 当前库存 {len(app.all_skins)}")
        print("-" * 55)
        print("1. 添加皮肤 | 2. 修改数据 | 3. 修改标签 | 4. >>> 发布到互联网 <<<")
        print("5. 强制刷新HTML | 6. 查看榜单 | 7. 🕷️ 自动抓取百度头像 | 8. 📉 手动退榜 | 0. 退出")
        print("=" * 55)
        cmd = input("指令: ").strip()

        if cmd == '1':
            app.add_skin_ui()
        elif cmd == '2':
            app.modify_data_ui()
        elif cmd == '3':
            app.manage_status_ui()
        elif cmd == '4':
            app.deploy_to_github()
        elif cmd == '5':
            app.generate_html()
        elif cmd == '6':
            app.view_rank_ui()
        elif cmd == '7':
            app.run_crawler_ui()
        elif cmd == '8':
            app.retire_skin_ui()
        elif cmd == '0':
            break