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
        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")

        # 🔥 V23.0 新增：初始化描述图文件夹
        self.desc_dir = os.path.join(LOCAL_REPO_PATH, "skin_descs")
        if not os.path.exists(self.desc_dir):
            os.makedirs(self.desc_dir)

        self.crawler = SkinCrawler(LOCAL_REPO_PATH)
        self.load_data()
        self._migrate_data_structure()

    def _get_list_price_by_quality(self, q_code):
        mapping = {0: 800.0, 1: 400.0, 2: 600.0, 3: 200.0, 3.5: 178.8, 4: 168.8, 5: 88.8, 6: 48.8}
        if 0.5 <= q_code < 1: return 400.0
        return mapping.get(q_code, 0.0)

    def _calculate_real_score(self, rank_score, list_price, real_price):
        if rank_score is None: return None
        if real_price <= 0 or list_price <= 0: return None
        return round(rank_score * (real_price / list_price), 1)

    def _migrate_data_structure(self):
        if not self.all_skins: return
        print("🛠️ 正在执行核心数据迁移与完整性校准...")
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

                # 兼容旧数据结构，读取列表或字典
                if isinstance(loaded, list):
                    self.all_skins = loaded
                elif isinstance(loaded, dict):
                    self.all_skins = loaded.get('skins', loaded.get('total', []))
                    if 'instructions' in loaded:
                        self.instructions = loaded['instructions']

                seen = set();
                unique = []
                for s in self.all_skins:
                    if s['name'] not in seen: unique.append(s); seen.add(s['name'])
                self.all_skins = unique
                print(f"✅ 数据加载完毕 (库存: {len(self.all_skins)} | 说明条目: {len(self.instructions)})")
            except Exception as e:
                print(f"❌ 加载失败: {e}");
                self.all_skins = []
        else:
            self.save_data()

    def _get_sort_key(self, skin):
        """
        🔥 核心排序逻辑
        1. 绝版 (10) > 预设 (1) > 在榜 (0)
        2. 如果是 绝版/预设：按品质数值升序（0是最高品质，6是最低）
        3. 如果是 在榜：按分数降序
        """
        group_weight = 10 if skin.get('is_discontinued') else (1 if skin.get('is_preset') else 0)
        if group_weight == 0:
            return (group_weight, skin.get('score') is None, -(skin.get('score') or 0))
        else:
            return (group_weight, skin.get('quality', 99))

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                self.all_skins.sort(key=self._get_sort_key)
                data_to_save = {"skins": self.all_skins, "instructions": self.instructions}
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
                status_str = "[🕒预设]"
                score_str = "Wait"
                real_pts_str = "--"
                growth_str = "--"
            elif skin.get('is_discontinued'):
                status_str = "[💀绝版]"
                score_str = "End"
                real_pts_str = "--"
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
                val = self._get_base_score(t)
                if val < p_score: return val
                t += 1

    def _auto_prune_leaderboard(self):
        active = [s for s in self.all_skins if
                  s.get('on_leaderboard', False) and not s.get('is_preset') and not s.get('is_discontinued')]
        active.sort(key=lambda x: (x.get('score') is None, -(x.get('score') or 0)))
        if len(active) > LEADERBOARD_CAPACITY:
            for skin in active[LEADERBOARD_CAPACITY:]: skin['on_leaderboard'] = False

    def add_skin_ui(self):
        active_list = self.get_active_leaderboard()
        print(f"\n>>> 添加新皮肤")
        try:
            raw = input("品质 名字 [返场输入1, 新增输入0]: ").split()
            if len(raw) < 2: return
            q_code = float(raw[0]);
            name = raw[1]
            is_rr = (len(raw) >= 3 and raw[2] != '0')
            list_p = self._get_list_price_by_quality(q_code)

            mode = input("模式: 1.上榜 2.不上榜 3.预设(Coming) 4.绝版(Out): ").strip()

            is_on = False;
            is_preset = False;
            is_discontinued = False
            rank_score = None;
            real_p = 0.0;
            growth = 0.0

            if mode == '3':
                is_preset = True;
                is_on = True
                rp_in = input("预估实价 (回车0): ").strip()
                real_p = float(rp_in) if rp_in else 0.0
            elif mode == '4':
                is_discontinued = True;
                is_on = True
                print("💀 已设为绝版皮肤。")
            elif mode == '1':
                is_on = True
                rank = int(input("插入排名: "));
                rp = float(input("实价: "));
                gt = float(input("涨幅: "))
                rank_score = round(self.calculate_insertion_score(rank, active_list, rp, gt), 1)
                real_p = rp;
                growth = gt
            else:  # mode 2
                score_in = input("排位分 (回车跳过): ").strip()
                if score_in: rank_score = float(score_in)
                real_p = float(input("实际价格: ") or 0.0);
                growth = float(input("涨幅: ") or 0.0)

            self.all_skins.append({
                "quality": q_code if not q_code.is_integer() else int(q_code),
                "name": name, "is_rerun": is_rr, "is_new": not is_rr,
                "on_leaderboard": is_on, "is_preset": is_preset, "is_discontinued": is_discontinued,
                "score": rank_score, "real_score": self._calculate_real_score(rank_score, list_p, real_p),
                "growth": growth, "list_price": list_p, "real_price": real_p, "local_img": None
            })
            self._auto_prune_leaderboard();
            self.save_data();
            self.generate_html();
            print(f"✅ 完成")
        except Exception as e:
            print(f"❌ 错误: {e}")

    def manage_preset_ui(self):
        presets = [s for s in self.all_skins if s.get('is_preset')]
        if not presets: print("\n⚠️ 当前没有预设皮肤。"); return
        print(f"\n====== 🚀 预设上线管理 (待机中: {len(presets)}) ======")
        for i, s in enumerate(presets): print(f"{i + 1}. {s['name']} (Q:{s['quality']} | 预估¥{s['real_price']})")
        print("0. 退出")
        try:
            sel = int(input("选择要上线的皮肤序号: ")) - 1
            if 0 <= sel < len(presets):
                target = presets[sel]
                print(f"\n🎉 正在上线: [{target['name']}]")
                active_list = self.get_active_leaderboard()
                rank = int(input("插入排名: "));
                rp_in = input(f"实际价格 (默认{target.get('real_price', 0)}): ").strip()
                rp = float(rp_in) if rp_in else target.get('real_price', 0)
                gt = float(input("涨幅: "))
                rank_score = round(self.calculate_insertion_score(rank, active_list, rp, gt), 1)

                target['is_preset'] = False
                target['score'] = rank_score;
                target['real_price'] = rp;
                target['growth'] = gt
                target['real_score'] = self._calculate_real_score(rank_score, target['list_price'], rp)
                self._auto_prune_leaderboard();
                self.save_data();
                self.generate_html();
                print(f"✅ 上线成功！")
        except ValueError:
            pass

    def manage_instructions_ui(self):
        """🔥 新增：说明书管理界面"""
        while True:
            print(f"\n====== 📝 管理页面说明 (当前: {len(self.instructions)}条) ======")
            for i, text in enumerate(self.instructions):
                print(f"{i + 1}. {text}")
            print("-" * 30)
            print("1. 添加说明 | 2. 删除说明 | 3. 修改说明 | 0. 返回")
            c = input("指令: ").strip()

            if c == '1':
                new_text = input("输入新说明内容: ").strip()
                if new_text:
                    self.instructions.append(new_text)
                    self.save_data();
                    self.generate_html()
            elif c == '2':
                try:
                    idx = int(input("删除序号: ")) - 1
                    if 0 <= idx < len(self.instructions):
                        print(f"🗑️ 已删除: {self.instructions.pop(idx)}")
                        self.save_data();
                        self.generate_html()
                except:
                    pass
            elif c == '3':
                try:
                    idx = int(input("修改序号: ")) - 1
                    if 0 <= idx < len(self.instructions):
                        print(f"原内容: {self.instructions[idx]}")
                        new_text = input("新内容: ").strip()
                        if new_text:
                            self.instructions[idx] = new_text
                            self.save_data();
                            self.generate_html()
                except:
                    pass
            elif c == '0':
                break

    def retire_skin_ui(self):
        print("\n>>> 手动下榜...");
        active_list = self.get_active_leaderboard();
        self.print_console_table(active_list)
        try:
            idx = int(input("输入序号下榜: ")) - 1
            if 0 <= idx < len(active_list):
                active_list[idx]['on_leaderboard'] = False;
                self.save_data();
                self.generate_html();
                print("✅ 已下榜")
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
                new_q = float(val_raw)
                item['quality'] = new_q if not new_q.is_integer() else int(new_q)
                item['list_price'] = self._get_list_price_by_quality(item['quality'])
            item['real_score'] = self._calculate_real_score(item['score'], item['list_price'],
                                                            item.get('real_price', 0))
            return True
        except:
            return False

    def modify_data_ui(self):
        self.print_console_table(self.get_total_skins())
        print("💡 快捷指令: [序号] [属性ID] [新值] (例如: 1 1 200)")
        print("   属性ID: 1=分数, 2=涨幅, 3=实价")
        raw = input("输入指令: ").strip().lower()
        if not raw: return
        parts = raw.split();
        target_list = self.get_total_skins()
        try:
            if len(parts) >= 3:
                idx = int(parts[0]) - 1
                if 0 <= idx < len(target_list):
                    if self._apply_modification(target_list[idx], parts[1], parts[2]):
                        self.save_data();
                        self.generate_html();
                        print(f"✅ 快捷修改成功")
            elif len(parts) == 1:
                idx = int(parts[0]) - 1
                if 0 <= idx < len(target_list):
                    if raw == 'delete': del self.all_skins[idx]; self.save_data(); print("🗑️ 已删除"); return
                    item = target_list[idx]
                    while True:
                        print(
                            f"\n修改: {item['name']} | 1.分:{item.get('score')} | 2.涨幅:{item.get('growth')} | 3.实价:{item.get('real_price')} | 0.保存")
                        sub = input("序号 数值: ").strip()
                        if not sub or sub == '0': break
                        sp = sub.split()
                        if len(sp) >= 2: self._apply_modification(item, sp[0], sp[1])
                    self.save_data();
                    self.generate_html();
                    print("💾 保存成功")
        except:
            pass

    def manage_status_ui(self):
        self.print_console_table()
        try:
            idx = int(input("输入序号修改状态: ")) - 1
            if 0 <= idx < len(self.get_total_skins()):
                target = self.get_total_skins()[idx]
                print(f"当前: {target['name']}")
                print("1. 设为新增 (New Arrival)")
                print("2. 设为返场 (Limit Return)")
                print("3. 设为预设 (Coming Soon)")
                print("4. 设为绝版 (Out of Print)")
                op = input("选择状态: ").strip()

                target['is_new'] = False;
                target['is_rerun'] = False;
                target['is_preset'] = False;
                target['is_discontinued'] = False
                if op == '1':
                    target['is_new'] = True
                elif op == '2':
                    target['is_rerun'] = True
                elif op == '3':
                    target['is_preset'] = True
                elif op == '4':
                    target['is_discontinued'] = True
                target['on_leaderboard'] = True

                self.save_data();
                self.generate_html();
                print("✅ 状态更新成功")
        except:
            pass

    def run_crawler_ui(self):
        print("\n🕷️ 启动自动抓取程序...")
        count = self.crawler.fetch_images(self.all_skins)
        if count > 0:
            self.save_data();
            self.generate_html();
            print(f"\n🎉 同步了 {count} 张新图片！")
        else:
            print("\n⚠️ 暂无新图片需要抓取")

    def get_header_gifs(self):
        show_dir = os.path.join(LOCAL_REPO_PATH, "show")
        if not os.path.exists(show_dir): return []
        gifs = [f for f in os.listdir(show_dir) if f.lower().endswith('.gif')]
        gifs.sort()
        return gifs

    def generate_html(self):
        quality_map = {0: "珍品无双", 1: "无双", 2: "荣耀典藏", 3: "珍品传说", 3.5: "传说限定", 4: "传说", 5: "史诗",
                       6: "勇者"}
        header_gifs = self.get_header_gifs()

        # 🔥 V23.0 逻辑：扫描 skin_descs 文件夹，构建皮肤描述图映射
        desc_files = {}
        if os.path.exists(self.desc_dir):
            for f in os.listdir(self.desc_dir):
                # 获取不带后缀的文件名
                name_part = os.path.splitext(f)[0]
                desc_files[name_part] = f

        # 为每个皮肤对象注入 desc_img 属性 (仅用于本次渲染)
        display_skins = self.get_total_skins()
        for skin in display_skins:
            skin['desc_img'] = desc_files.get(skin['name'])

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

        .chart-header { 
            background: var(--header-bg); padding: 15px 20px; color: white; margin-bottom: 2px; 
            display: flex; align-items: center; justify-content: center; gap: 20px;
        }
        .header-content { text-align: center; flex: 1; }
        .header-content h1 { font-size: 24px; font-weight: 800; margin: 0; }

        /* 🔥 新增：说明按钮和头部布局容器 */
        .info-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 5px;
        }

        .info-btn {
            background: white;
            color: black;
            border: none;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .info-btn:hover { opacity: 0.8; }

        /* 🔥 新增：模态框样式 */
        .modal {
            display: none; 
            position: fixed; 
            z-index: 1000; 
            left: 0;
            top: 0;
            width: 100%; 
            height: 100%; 
            overflow: auto; 
            background-color: rgba(0,0,0,0.5); 
            backdrop-filter: blur(2px);
        }

        .modal-content {
            background-color: #fefefe;
            margin: 15% auto; 
            padding: 20px;
            border-radius: 12px;
            width: 80%;
            max-width: 500px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn { from {opacity: 0; transform: translateY(-20px);} to {opacity: 1; transform: translateY(0);} }

        .close-btn {
            color: #aaa;
            float: right;
            font-size: 24px;
            font-weight: bold;
            cursor: pointer;
            line-height: 20px;
        }
        .close-btn:hover { color: black; }

        .modal-list {
            text-align: left;
            margin-top: 15px;
            padding-left: 20px;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }

        .header-gifs-container { display: flex; gap: 10px; }
        .header-gif { width: 55px; height: 55px; border-radius: 8px; object-fit: cover; border: 2px solid rgba(255,255,255,0.4); }

        .table-container { width: 100%; overflow-x: auto; }
        table { width: 98%; margin: 0 auto; border-collapse: separate; border-spacing: 0 8px; font-size: 14px; min-width: 800px; }
        th { text-align: center; padding: 8px 2px; font-weight: 800; border-bottom: 3px solid #6366f1; white-space: nowrap; }

        td { padding: 12px 2px; vertical-align: middle; text-align: center; background: transparent; border: none; }
        .rounded-left { border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
        .rounded-right { border-top-right-radius: 12px; border-bottom-right-radius: 12px; }

        /* 🔥 V23.0 新增样式：描述图列 */
        .desc-col {
            width: 100px; /* 固定列宽 */
            padding: 2px !important;
        }
        .desc-img {
            max-width: 100%;
            height: auto;
            max-height: 50px; /* 限制高度，自适应 */
            object-fit: contain;
            display: block;
            margin: 0 auto;
            border-radius: 4px;
        }

        .qual-header { display: inline-flex; align-items: center; justify-content: center; gap: 6px; position: relative; }
        .multi-select-box { font-size: 11px; border-radius: 4px; border: 1px solid #ddd; padding: 4px 8px; cursor: pointer; background: white; min-width: 85px; }
        .dropdown-menu { display: none; position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; border-radius: 6px; padding: 8px; min-width: 130px; text-align: left; }
        .dropdown-menu.show { display: block; }
        .col-sort { cursor: pointer; } .col-sort::after { content: ' ⇅'; color: #ccc; }

        /* 图标样式 & 物理放大 */
        .quality-icon { height: 28px; width: auto; display: inline-block; vertical-align: middle; transition: transform 0.2s; object-fit: contain; }
        .rare-wushuang-big { height: 60px !important; width: auto !important; margin: -15px 0; transform: scale(1.1); }
        .wushuang-big { height: 45px !important; margin: -8px 0; }
        .glory-big { transform: scale(1.4); } .legend-big { transform: scale(1.2); } .epic-medium { transform: scale(1.1); } .brave-small { transform: scale(0.9); }

        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; object-fit: cover; }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 5px; min-width: 180px; }
        .song-title { font-weight: 700; font-size: 14px; }
        .badge { display: inline-block; padding: 1px 5px; font-size: 9px; font-weight: 900; border-radius: 3px; }
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
                                {% for q in ["珍品无双", "无双", "荣耀典藏", "珍品传说", "传说限定", "传说", "史诗", "勇者"] %}
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
                    {% set rb = '#ffffff' %}
                    {% if skin.quality == 3.5 %}{% set rb = '#e0f2fe' %}{% elif skin.quality == 3 %}{% set rb = '#bfdbfe' %}{% elif skin.quality == 2 %}{% set rb = '#fff7cd' %}{% elif skin.quality == 1 or (skin.quality >= 0.5 and skin.quality < 1) %}{% set rb = '#f3e8ff' %}{% elif skin.quality == 0 %}{% set rb = '#ffdcdc' %}{% endif %}
                    {% set q_name = quality_map[skin.quality] or ("无双" if 0.5 <= skin.quality < 1 else "") %}

                    <tr data-quality="{{ q_name }}">
                        <td>{% if not skin.is_preset and not skin.is_discontinued %}<span class="rank-box">{{ loop.index }}</span>{% else %}-{% endif %}</td>
                        <td class="quality-col" data-val="{{ skin.quality }}">
                            {% set q_cls = '' %}
                            {% if skin.quality == 0 %}{% set q_cls = 'rare-wushuang-big' %}{% elif skin.quality >= 0.5 and skin.quality <= 1 %}{% set q_cls = 'wushuang-big' %}
                            {% elif skin.quality == 2 %}{% set q_cls = 'glory-big' %}{% elif skin.quality == 4 %}{% set q_cls = 'legend-big' %}
                            {% elif skin.quality == 5 or skin.quality == 3.5 %}{% set q_cls = 'epic-medium' %}{% elif skin.quality == 6 %}{% set q_cls = 'brave-small' %}{% endif %}
                            <img src="./images/{{ skin.quality }}.gif" class="quality-icon {{ q_cls }}" onerror="loadFallbackImg(this, '{{ skin.quality }}')">
                        </td>
                        <td class="rounded-left" style="background-color: {{ rb }};"><div class="song-col">
                            <img src="./{{ skin.local_img or 'placeholder.jpg' }}" class="album-art">
                            <div style="display:flex; flex-direction:column;">
                                <span class="song-title">{{ skin.name }}</span>
                                {% if skin.is_discontinued %}<span class="badge badge-out">Out of Print</span>{% elif skin.is_preset %}<span class="badge badge-preset">Coming Soon</span>{% elif skin.is_new %}<span class="badge badge-new">New Arrival</span>{% elif skin.is_rerun %}<span class="badge badge-return">Limit Return</span>{% endif %}
                            </div>
                        </div></td>

                        <td class="desc-col" style="background-color: {{ rb }};">
                            {% if skin.desc_img %}
                            <img src="./skin_descs/{{ skin.desc_img }}" class="desc-img">
                            {% endif %}
                        </td>

                        <td data-val="{{ skin.score if skin.score is not none else -999 }}" style="background-color: {{ rb }};"><div class="box-style">{% if skin.is_discontinued %}End{% else %}{{ skin.score or '--' }}{% endif %}</div></td>
                        <td style="background-color: {{ rb }}; color:#6366f1; font-weight:bold;">{{ skin.real_score or '--' }}</td>
                        <td style="background-color: {{ rb }};">
                            {% if skin.growth %}
                            {% set g_cls = '' %}
                            {% if skin.growth == 1.9 %}{% set g_cls = 'growth-special' %}{% elif skin.growth < 0 %}{% set g_cls = 'growth-down' %}
                            {% elif skin.growth >= 10 %}{% set g_cls = 'growth-up-high' %}{% elif skin.growth >= 5 %}{% set g_cls = 'growth-up-mid' %}{% endif %}
                            <div class="box-style {{ g_cls }}">{{ skin.growth }}%{% if skin.growth == 1.9 %}!{% endif %}</div>
                            {% else %}--{% endif %}
                        </td>
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
    window.onload = () => { sortTable(4, 'float'); };
    function loadFallbackImg(img, q) {
        if (img.src.indexOf('.gif') !== -1) img.src = './images/' + q + '.jpg';
        else if (img.src.indexOf('.jpg') !== -1 && img.src.indexOf('1.jpg') === -1) { let v = parseFloat(q); if (v >= 0.5 && v <= 1) img.src = './images/1.jpg'; }
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
    </script>
</body>
</html>
        """
        t = Template(html_template)
        html_content = t.render(total_skins=self.get_total_skins(), quality_map=quality_map,
                                header_gifs=header_gifs, instructions=self.instructions,
                                update_time=datetime.now().strftime("%Y-%m-%d %H:%M"))
        with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
            f.write(html_content)
        print("📄 HTML 刷新完成")

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
        print("\n" + "=" * 55)
        print("👑 王者荣耀榜单 V23.0 (完全体)")
        print(f"📊 当前库存 {len(app.all_skins)}")
        print("-" * 55)
        print("1. 添加皮肤 | 2. 修改数据 | 3. 修改标签 | 4. >>> 发布互联网 <<<")
        print("5. 强制刷新HTML | 6. 查看榜单 | 7. 🕷️ 抓取头像 | 8. 📉 退榜")
        print("9. 🚀 预设上线 | 10. 📝 管理说明 | 0. 退出")
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
        elif cmd == '9':
            app.manage_preset_ui()
        elif cmd == '10':  # 🔥 新增入口
            app.manage_instructions_ui()
        elif cmd == '0':
            break