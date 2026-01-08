import math
import json
import os
import subprocess
import requests
import time
import random
import shutil
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
            safe_name = skin['name'].replace("/", "_").replace("\\", "_").replace(" ", "")
            gif_filename = f"{safe_name}.gif"
            gif_path = os.path.join(self.save_dir, gif_filename)

            if os.path.exists(gif_path):
                current_path = f"skin_avatars/{gif_filename}"
                if skin.get('local_img') != current_path:
                    skin['local_img'] = current_path
                    print(f"   🎥 锁定本地动态头像: {gif_filename}")
                    count += 1
                continue

            if skin.get('local_img') and os.path.exists(os.path.join(LOCAL_REPO_PATH, skin['local_img'])):
                continue

            parts = skin['name'].split('-')
            keyword = f"{parts[1]} {parts[0]}" if len(parts) >= 2 else skin['name']
            url = "https://image.baidu.com/search/acjson"
            params = {
                "tn": "resultjson_com", "logid": "8388656667592781395", "ipn": "rj", "ct": "201326592", "is": "",
                "fp": "result", "queryWord": keyword, "cl": "2", "lm": "-1", "ie": "utf-8", "oe": "utf-8",
                "adpicid": "", "st": "-1", "z": "", "ic": "", "hd": "", "latest": "", "copyright": "",
                "word": keyword, "s": "", "se": "", "tab": "", "width": "", "height": "", "face": "0",
                "istype": "2", "qc": "", "nc": "1", "fr": "", "expermode": "", "force": "", "pn": "0", "rn": "1",
                "gsm": "1e",
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

                    file_name = f"{safe_name}.jpg"
                    file_path = os.path.join(self.save_dir, file_name)
                    with open(file_path, 'wb') as f:
                        f.write(img_resp.content)
                    skin['local_img'] = f"skin_avatars/{file_name}"
                    count += 1
                    print(f"   ✅ 已下载并同步: {file_name}")
                    time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                print(f"   ⚠️ 跳过 [{keyword}]: {e}")
        return count


class SkinSystem:
    def __init__(self):
        self.all_skins = []
        self.instructions = ["本榜单数据仅供参考", "数据更新时间以页面显示为准"]
        # V24.4: 默认品质配置 (包含 scale 字段)
        self.quality_config = {
            "0": {"price": 800.0, "parent": None, "name": "珍品无双", "scale": 1.4},
            "1": {"price": 400.0, "parent": None, "name": "无双", "scale": 1.2},
            "2": {"price": 600.0, "parent": None, "name": "荣耀典藏", "scale": 1.2},
            "3": {"price": 200.0, "parent": None, "name": "珍品传说", "scale": 1.0},
            "3.5": {"price": 178.8, "parent": None, "name": "传说限定", "scale": 1.0},
            "4": {"price": 168.8, "parent": None, "name": "传说", "scale": 1.0},
            "5": {"price": 88.8, "parent": None, "name": "史诗", "scale": 1.0},
            "6": {"price": 48.8, "parent": None, "name": "勇者", "scale": 0.9},
        }

        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
        self.desc_dir = os.path.join(LOCAL_REPO_PATH, "skin_descs")
        if not os.path.exists(self.desc_dir): os.makedirs(self.desc_dir)

        self.crawler = SkinCrawler(LOCAL_REPO_PATH)
        self.load_data()
        self._migrate_data_structure()

    def _get_list_price_by_quality(self, q_code):
        q_str = str(q_code)
        if q_str in self.quality_config:
            return self.quality_config[q_str]['price']
        for q, cfg in self.quality_config.items():
            if q == q_str and cfg.get('parent'):
                parent = str(cfg['parent'])
                if parent in self.quality_config:
                    return self.quality_config[parent]['price']
        return 0.0

    def _calculate_real_score(self, rank_score, list_price, real_price):
        if rank_score is None: return None
        if real_price <= 0 or list_price <= 0: return None
        return round(rank_score * (real_price / list_price), 1)

    def _migrate_data_structure(self):
        if not self.all_skins: return
        print("🛠️ 正在执行核心数据迁移与完整性校准...")

        # 确保所有配置都有 scale
        for k, v in self.quality_config.items():
            if 'scale' not in v: v['scale'] = 1.0

        for skin in self.all_skins:
            skin['list_price'] = self._get_list_price_by_quality(skin['quality'])
            if 'real_price' not in skin: skin['real_price'] = skin.get('price', 0.0)
            if 'is_preset' not in skin: skin['is_preset'] = False
            if 'is_discontinued' not in skin: skin['is_discontinued'] = False

            cur_score = skin.get('score')
            skin['real_score'] = self._calculate_real_score(cur_score, skin['list_price'], skin['real_price'])

            if 'price' in skin: del skin['price']
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

                seen = set();
                unique = []
                for s in self.all_skins:
                    if s['name'] not in seen: unique.append(s); seen.add(s['name'])
                self.all_skins = unique
                print(f"✅ 数据加载完毕 (库存: {len(self.all_skins)})")
            except Exception as e:
                print(f"❌ 加载失败: {e}");
                self.all_skins = []
        else:
            self.save_data()

    def _get_sort_key(self, skin):
        group_weight = 10 if skin.get('is_discontinued') else (1 if skin.get('is_preset') else 0)
        if group_weight == 0:
            return (group_weight, skin.get('score') is None, -(skin.get('score') or 0))
        else:
            return (group_weight, skin.get('quality', 99))

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                self.all_skins.sort(key=self._get_sort_key)
                data_to_save = {
                    "skins": self.all_skins,
                    "instructions": self.instructions,
                    "quality_config": self.quality_config
                }
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 存档失败: {e}")

    def get_total_skins(self):
        data = self.all_skins[:]
        data.sort(key=self._get_sort_key)
        return data

    def get_active_leaderboard(self):
        active = [s for s in self.all_skins if s.get('on_leaderboard', False)]
        active.sort(key=self._get_sort_key)
        return active[:LEADERBOARD_CAPACITY + 10]

    def print_console_table(self, data_list=None, title="榜单"):
        if data_list is None: data_list = self.get_total_skins()
        print(f"\n====== 🏆 {title} (Items: {len(data_list)}) ======")
        print(
            f"{'No.':<4} {'St':<6} {'Q':<4} {'名字':<12} {'RankPts':<8} {'RealPts':<8} {'Growth':<8} {'ListP':<8} {'RealP'}")
        print("-" * 105)
        for i, skin in enumerate(data_list):
            if skin.get('is_preset'):
                status_str = "[🕒预设]";
                score_str = "Wait";
                real_pts_str = "--";
                growth_str = "--"
            elif skin.get('is_discontinued'):
                status_str = "[💀绝版]";
                score_str = "--";
                real_pts_str = "--";
                growth_str = "--"
            else:
                s_val = skin.get('score')
                score_str = "--" if s_val is None else str(s_val)
                real_pts_str = "--" if skin.get('real_score') is None else str(skin['real_score'])
                growth_str = f"+{skin.get('growth', 0)}%" if (
                            skin.get('growth', 0) != 0 and skin.get('growth') is not None) else "--"
                status_str = "[🔥在榜]" if skin.get('on_leaderboard') else "[❌退榜]"

            list_p_str = f"¥{skin.get('list_price', 0)}"
            rp_str = f"¥{skin.get('real_price', 0)}" if skin.get('real_price', 0) > 0 else "--"

            print(
                f"{i + 1:<4} {status_str:<6} {skin['quality']:<4} {skin['name']:<12} {score_str:<8} {real_pts_str:<8} {growth_str:<8} {list_p_str:<8} {rp_str}")
        print("=" * 105 + "\n")

    def view_rank_ui(self):
        print("\n1. 查看新品榜 | 2. 查看总榜");
        c = input("选: ")
        if c == '1':
            self.print_console_table(self.get_active_leaderboard(), "新品榜")
        else:
            self.print_console_table(self.get_total_skins(), "总榜")

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
                val = self._get_base_score(t);
                if val < p_score: return val; t += 1

    def _auto_prune_leaderboard(self):
        active = [s for s in self.all_skins if
                  s.get('on_leaderboard', False) and not s.get('is_preset') and not s.get('is_discontinued')]
        active.sort(key=lambda x: (x.get('score') is None, -(x.get('score') or 0)))
        if len(active) > LEADERBOARD_CAPACITY:
            for skin in active[LEADERBOARD_CAPACITY:]: skin['on_leaderboard'] = False

    def manage_quality_ui(self):
        while True:
            print("\n====== 💎 品质管理系统 ======")
            print(f"{'代号':<8} {'定价':<10} {'倍数(Scale)':<12} {'父级':<8} {'名称'}")
            print("-" * 65)
            sorted_keys = sorted(self.quality_config.keys(), key=lambda k: float(k))
            for k in sorted_keys:
                v = self.quality_config[k]
                parent = str(v.get('parent')) if v.get('parent') else "--"
                scale_val = v.get('scale', 1.0)
                print(f"{k:<8} ¥{v['price']:<10} {scale_val:<12} {parent:<8} {v.get('name', '')}")
            print("-" * 65)
            print("1. 新增品质 | 2. 修改品质 (快捷:3000 1 400) | 3. 标签大小管理 | 0. 返回")
            c = input("指令: ").strip()

            if c == '1':
                code = input("输入新品质代号 (如 0.81): ").strip()
                if code in self.quality_config: print("❌ 已存在！"); continue
                type_c = input("类型: 1.全新独立品质 2.子品质(映射): ").strip()

                if type_c == '1':
                    name = input("输入描述名称: ").strip()
                    price = float(input("设定定价: "))
                    self.quality_config[code] = {"price": price, "parent": None, "name": name, "scale": 1.0}
                elif type_c == '2':
                    parent = input("输入父级代号 (如 1): ").strip()
                    if parent not in self.quality_config: print("❌ 父级不存在"); continue
                    price = self.quality_config[parent]['price']
                    name = self.quality_config[parent]['name']
                    self.quality_config[code] = {"price": price, "parent": parent, "name": name, "scale": 1.0}
                    print(f"🔗 已自动关联父级: {name} (¥{price})")
                self.save_data();
                print("✅ 添加成功")

            elif c == '2':
                raw = input("输入代号 或 快捷指令 (代号 模式 值): ").strip()
                parts = raw.split()
                target = parts[0]
                shortcut_mode = len(parts) >= 3

                if target not in self.quality_config: print("❌ 不存在"); continue

                if shortcut_mode:
                    if parts[1] == '1':  # 改价
                        try:
                            new_p = float(parts[2])
                            self.quality_config[target]['price'] = new_p
                            for k, v in self.quality_config.items():
                                if str(v.get('parent')) == target: v['price'] = new_p
                            self._migrate_data_structure();
                            print(f"✅ 快捷修改: 定价 -> ¥{new_p}")
                        except:
                            print("❌ 格式错误")
                    else:
                        print("⚠️ 快捷修改代号风险较高，请使用详细菜单操作。")
                else:
                    print(f"当前选中: {target} | 1.修改定价 | 2.修改代号(自动重命名文件/映射)")
                    sub_c = input("操作: ").strip()
                    if sub_c == '1':
                        try:
                            new_p = float(input("新定价: "))
                            self.quality_config[target]['price'] = new_p
                            for k, v in self.quality_config.items():
                                if str(v.get('parent')) == target: v['price'] = new_p
                            self._migrate_data_structure();
                            print("✅ 定价已更新")
                        except:
                            pass
                    elif sub_c == '2':
                        new_code = input("输入新代号 (如 100): ").strip()
                        if new_code in self.quality_config: print("❌ 新代号已存在"); continue
                        config_data = self.quality_config.pop(target)
                        self.quality_config[new_code] = config_data
                        for k, v in self.quality_config.items():
                            if str(v.get('parent')) == target: v['parent'] = new_code
                        count = 0
                        for skin in self.all_skins:
                            if str(skin['quality']) == target:
                                try:
                                    skin['quality'] = float(new_code) if '.' in new_code else int(new_code)
                                except:
                                    skin['quality'] = new_code
                                count += 1
                        img_dir = os.path.join(LOCAL_REPO_PATH, "images")
                        renamed_files = []
                        if os.path.exists(img_dir):
                            for ext in ['.gif', '.jpg', '.png']:
                                old_f = os.path.join(img_dir, f"{target}{ext}")
                                new_f = os.path.join(img_dir, f"{new_code}{ext}")
                                if os.path.exists(old_f):
                                    try:
                                        os.rename(old_f, new_f); renamed_files.append(f"{target}{ext}->{new_code}{ext}")
                                    except Exception as e:
                                        print(f"❌ 重命名失败 {old_f}: {e}")
                        self.save_data();
                        self.generate_html()
                        print(f"✅ 代号修改完成！受影响皮肤: {count} | 文件重命名: {renamed_files}")

            elif c == '3':
                print(">>> 标签大小管理")
                raw = input("输入: 代号 缩放倍数 (例如: 3000 1.5): ").strip()
                parts = raw.split()
                if len(parts) >= 2:
                    code = parts[0]
                    try:
                        scale = float(parts[1])
                        if code in self.quality_config:
                            self.quality_config[code]['scale'] = scale
                            self.save_data();
                            self.generate_html()
                            print(f"✅ 已设置 {code} 的缩放倍数为 {scale}x")
                        else:
                            print("❌ 代号不存在")
                    except:
                        print("❌ 倍数必须是数字")
                else:
                    print("❌ 格式错误")

            elif c == '0':
                break

    def add_skin_ui(self):
        active_list = self.get_active_leaderboard()
        print(f"\n>>> 添加新皮肤")
        try:
            raw = input("品质 名字 [返场输入1, 新增输入0]: ").split()
            if len(raw) < 2: return
            q_in = raw[0];
            q_code = float(q_in) if '.' in q_in else int(q_in)
            name = raw[1];
            is_rr = (len(raw) >= 3 and raw[2] != '0')
            list_p = self._get_list_price_by_quality(q_code)

            mode = input("模式: 1.上榜 2.不上榜 3.预设 4.绝版: ").strip()
            is_on = False;
            is_preset = False;
            is_discontinued = False;
            rank_score = None;
            real_p = 0.0;
            growth = 0.0
            if mode == '3':
                is_preset = True; is_on = True; real_p = float(input("预估实价: ") or 0)
            elif mode == '4':
                is_discontinued = True; is_on = True
            elif mode == '1':
                is_on = True;
                rank = int(input("排名: "));
                rp = float(input("实价: "));
                gt = float(input("涨幅: "))
                rank_score = round(self.calculate_insertion_score(rank, active_list, rp, gt), 1);
                real_p = rp;
                growth = gt
            else:
                s_in = input("分数: ");
                rank_score = float(s_in) if s_in else None
                real_p = float(input("实价: ") or 0);
                growth = float(input("涨幅: ") or 0)

            self.all_skins.append({
                "quality": q_code, "name": name, "is_rerun": is_rr, "is_new": not is_rr,
                "on_leaderboard": is_on, "is_preset": is_preset, "is_discontinued": is_discontinued,
                "score": rank_score, "real_score": self._calculate_real_score(rank_score, list_p, real_p),
                "growth": growth, "list_price": list_p, "real_price": real_p, "local_img": None
            })
            self._auto_prune_leaderboard();
            self.save_data();
            self.generate_html();
            print("✅ 完成")
        except Exception as e:
            print(f"❌ 错误: {e}")

    def manage_preset_ui(self):
        presets = [s for s in self.all_skins if s.get('is_preset')]
        if not presets: print("无预设"); return
        for i, s in enumerate(presets): print(f"{i + 1}. {s['name']}")
        try:
            sel = int(input("序号: ")) - 1
            if 0 <= sel < len(presets):
                t = presets[sel]
                active = self.get_active_leaderboard()
                rank = int(input("排名: "));
                rp = float(input(f"实价({t.get('real_price')}): ") or t.get('real_price', 0));
                gt = float(input("涨幅: "))
                t['is_preset'] = False;
                t['score'] = round(self.calculate_insertion_score(rank, active, rp, gt), 1)
                t['real_price'] = rp;
                t['growth'] = gt;
                t['real_score'] = self._calculate_real_score(t['score'], t['list_price'], rp)
                self._auto_prune_leaderboard();
                self.save_data();
                self.generate_html();
                print("✅ 上线")
        except:
            pass

    def manage_instructions_ui(self):
        while True:
            print(f"\n====== 📝 管理页面说明 (当前: {len(self.instructions)}条) ======")
            for i, t in enumerate(self.instructions): print(f"{i + 1}. {t}")
            print("-" * 50)
            print("1. 添加说明 | 2. 删除说明 | 3. 修改说明 | 0. 返回")
            c = input("指令: ").strip()
            if c == '1':
                self.instructions.append(input("内容: ")); self.save_data(); self.generate_html()
            elif c == '2':
                try:
                    self.instructions.pop(int(input("序号: ")) - 1); self.save_data(); self.generate_html()
                except:
                    pass
            elif c == '3':
                try:
                    self.instructions[int(input("序号: ")) - 1] = input(
                        "新内容: "); self.save_data(); self.generate_html()
                except:
                    pass
            elif c == '0':
                break

    def retire_skin_ui(self):
        print("\n>>> 手动下榜...");
        active = self.get_active_leaderboard();
        self.print_console_table(active)
        try:
            idx = int(input("序号: ")) - 1
            if 0 <= idx < len(active): active[idx][
                'on_leaderboard'] = False; self.save_data(); self.generate_html(); print("✅ 已下榜")
        except:
            pass

    def _apply_modification(self, item, opt, val_raw):
        try:
            if opt == '1':
                item['score'] = float(val_raw) if val_raw != 'null' else None
            elif opt == '2':
                item['growth'] = float(val_raw)
            elif opt == '3':
                item['real_price'] = float(val_raw)
            elif opt == '4':
                item['quality'] = float(val_raw) if '.' in val_raw else int(val_raw)
                item['list_price'] = self._get_list_price_by_quality(item['quality'])
            item['real_score'] = self._calculate_real_score(item['score'], item['list_price'],
                                                            item.get('real_price', 0))
            return True
        except:
            return False

    def modify_data_ui(self):
        self.print_console_table(self.get_total_skins())
        print("指令: [序号] [属性ID] [新值] (ID: 1=分, 2=涨, 3=价, 4=质)");
        raw = input("输入: ").strip().lower()
        if not raw: return
        parts = raw.split();
        target_list = self.get_total_skins()
        try:
            if len(parts) >= 3:
                idx = int(parts[0]) - 1
                if 0 <= idx < len(target_list) and self._apply_modification(target_list[idx], parts[1], parts[2]):
                    self.save_data();
                    self.generate_html();
                    print(f"✅ 修改成功")
            elif len(parts) == 1 and raw == 'delete':
                idx = int(input("删除序号: ")) - 1;
                del self.all_skins[idx];
                self.save_data();
                print("🗑️ 删除")
        except:
            pass

    def manage_status_ui(self):
        self.print_console_table();
        try:
            idx = int(input("序号: ")) - 1
            if 0 <= idx < len(self.get_total_skins()):
                t = self.get_total_skins()[idx]
                op = input("1.新 2.返 3.预 4.绝: ");
                t.update(
                    {'is_new': op == '1', 'is_rerun': op == '2', 'is_preset': op == '3', 'is_discontinued': op == '4',
                     'on_leaderboard': True})
                self.save_data();
                self.generate_html();
                print("✅ 更新")
        except:
            pass

    def run_crawler_ui(self):
        self.crawler.fetch_images(self.all_skins);
        self.save_data();
        self.generate_html()

    def get_header_gifs(self):
        show_dir = os.path.join(LOCAL_REPO_PATH, "show")
        if not os.path.exists(show_dir): return []
        gifs = [f for f in os.listdir(show_dir) if f.lower().endswith('.gif')]
        gifs.sort()
        return gifs

    def generate_html(self):
        header_gifs = self.get_header_gifs()
        desc_files = {}
        if os.path.exists(self.desc_dir):
            for f in os.listdir(self.desc_dir): desc_files[os.path.splitext(f)[0]] = f

        display_skins = self.get_total_skins()
        for skin in display_skins: skin['desc_img'] = desc_files.get(skin['name'])

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
        .wushuang-big { margin: -8px 0; }

        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; object-fit: cover; }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 5px; min-width: 180px; }
        .name-container { display: flex; flex-direction: column; gap: 2px; width: 86px; align-items: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; white-space: nowrap; transform-origin: center; display: inline-block; }
        .badge { display: block; width: 100%; text-align: center; padding: 1px 0; font-size: 9px; font-weight: 900; border-radius: 3px; text-transform: uppercase; }
        .badge-new { background: #ffd700; color: #000; } .badge-return { background: #1d4ed8; color: #fff; } .badge-preset { background: #06b6d4; color: #fff; } .badge-out { background: #4b5563; color: #fff; }
        .rank-box { display: inline-block; min-width: 20px; background: #1d4ed8; color: #fff; font-size: 20px; font-weight: 900; border-radius: 4px; }
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
                        <th style="text-align:left; padding-left:20px;">Skin Name</th>
                        <th></th>
                        <th class="col-sort" onclick="sortTable(4, 'float')">Rank Pts</th>
                        <th class="col-sort" onclick="sortTable(5, 'float')">Real Pts</th>
                        <th class="col-sort" onclick="sortTable(6, 'float')">Growth</th>
                        <th class="col-sort" onclick="sortTable(7, 'float')">List P</th>
                        <th class="col-sort" onclick="sortTable(8, 'float')">Real P</th>
                    </tr>
                </thead>
                <tbody>
                    {% for skin in total_skins %}
                    {% set q_str = skin.quality|string %}
                    {% set q_cfg = quality_config.get(q_str, {}) %}
                    {% set parent_id = q_cfg.parent|string if q_cfg.parent else 'None' %}
                    {% set display_img_id = parent_id if parent_id != 'None' else q_str %}

                    {# 🔥 V24.4: 读取缩放倍数 #}
                    {% set scale_val = q_cfg.get('scale', 1.0) %}

                    {% set rb = '#ffffff' %}
                    {% if display_img_id == '3.5' %}{% set rb = '#e0f2fe' %}{% elif display_img_id == '3' %}{% set rb = '#bfdbfe' %}{% elif display_img_id == '2' %}{% set rb = '#fff7cd' %}{% elif display_img_id == '1' %}{% set rb = '#f3e8ff' %}{% elif display_img_id == '0' %}{% set rb = '#ffdcdc' %}{% endif %}

                    <tr data-quality="{{ q_cfg.name }}">
                        <td>{% if not skin.is_preset and not skin.is_discontinued %}<span class="rank-box">{{ loop.index }}</span>{% else %}-{% endif %}</td>
                        <td class="quality-col" data-val="{{ skin.quality }}">
                            <img src="./images/{{ q_str }}.gif" 
                                 data-q="{{ q_str }}" data-p="{{ parent_id }}" 
                                 class="quality-icon"
                                 style="transform: scale({{ scale_val }});" 
                                 onerror="loadFallbackImg(this)">
                        </td>
                        <td class="rounded-left" style="background-color: {{ rb }};"><div class="song-col">
                            <img src="./{{ skin.local_img or 'placeholder.jpg' }}" class="album-art">
                            <div class="name-container">
                                <span class="song-title">{{ skin.name }}</span>
                                {% if skin.is_discontinued %}<span class="badge badge-out">Out of Print</span>{% elif skin.is_preset %}<span class="badge badge-preset">Coming Soon</span>{% elif skin.is_new %}<span class="badge badge-new">New Arrival</span>{% elif skin.is_rerun %}<span class="badge badge-return">Limit Return</span>{% endif %}
                            </div>
                        </div></td>
                        <td class="desc-col" style="background-color: {{ rb }};">{% if skin.desc_img %}<img src="./skin_descs/{{ skin.desc_img }}" class="desc-img">{% endif %}</td>
                        <td data-val="{{ skin.score if skin.score is not none else -999 }}" style="background-color: {{ rb }};"><div class="box-style">{% if skin.is_discontinued %}{{ '--' }}{% else %}{{ skin.score or '--' }}{% endif %}</div></td>
                        <td style="background-color: {{ rb }}; color:#6366f1; font-weight:bold;">{{ skin.real_score or '--' }}</td>
                        <td style="background-color: {{ rb }};">{% if skin.growth %}{% set g_cls = '' %}{% if skin.growth == 1.9 %}{% set g_cls = 'growth-special' %}{% elif skin.growth < 0 %}{% set g_cls = 'growth-down' %}{% elif skin.growth >= 10 %}{% set g_cls = 'growth-up-high' %}{% elif skin.growth >= 5 %}{% set g_cls = 'growth-up-mid' %}{% endif %}<div class="box-style {{ g_cls }}">{{ skin.growth }}%{% if skin.growth == 1.9 %}!{% endif %}</div>{% else %}--{% endif %}</td>
                        <td style="background-color: {{ rb }};">¥{{ skin.list_price }}</td>
                        <td class="rounded-right" style="background-color: {{ rb }};"><div class="box-style">{% if skin.real_price > 0 %}¥{{ skin.real_price }}{% else %}--{% endif %}</div></td>
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
        html_content = t.render(total_skins=self.get_total_skins(), quality_config=self.quality_config,
                                header_gifs=header_gifs, instructions=self.instructions,
                                update_time=datetime.now().strftime("%Y-%m-%d %H:%M"))
        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            print("📄 HTML 刷新完成")
        except Exception as e:
            print(f"❌ 路径错误: {e}")

    def deploy_to_github(self):
        print("\n🚀 正在同步至 GitHub...");
        os.chdir(LOCAL_REPO_PATH)
        try:
            subprocess.run([GIT_EXECUTABLE_PATH, "add", "."], check=True)
            subprocess.run([GIT_EXECUTABLE_PATH, "commit", "-m", "update"], check=True)
            subprocess.run([GIT_EXECUTABLE_PATH, "push"], check=True)
            print(f"\n✅ 发布成功！🌐 https://{GITHUB_USERNAME}.github.io/hok-rank/")
        except Exception as e:
            print(f"\n❌ 发布失败: {e}")


if __name__ == "__main__":
    app = SkinSystem()
    while True:
        # Header
        print("\n" + "="*60)
        print(f"👑 王者荣耀榜单 V24.4 (标签缩放+窄列版) | 📊 当前库存: {len(app.all_skins)}")
        print("-" * 60)

        # Row 1
        print("1. ➕ 添加皮肤   2. ✏️ 修改数据   3. 🏷️ 修改状态   4. 🚀 发布榜单   5. 🔄 刷新页面   6. 📊 查看榜单")
        # Row 2
        print("7. 🕷️ 抓取头像   8. 📉 手动退榜   9. ⏰ 预设上线   10.📝 说明管理   11.💎 品质管理   0. ❌ 退出程序")
        print("-" * 60)

        cmd = input("👉 请输入指令: ").strip()
        if cmd == '1': app.add_skin_ui()
        elif cmd == '2': app.modify_data_ui()
        elif cmd == '3': app.manage_status_ui()
        elif cmd == '4': app.deploy_to_github()
        elif cmd == '5': app.generate_html()
        elif cmd == '6': app.view_rank_ui()
        elif cmd == '7': app.run_crawler_ui()
        elif cmd == '8': app.retire_skin_ui()
        elif cmd == '9': app.manage_preset_ui()
        elif cmd == '10': app.manage_instructions_ui()
        elif cmd == '11': app.manage_quality_ui()
        elif cmd == '0': break