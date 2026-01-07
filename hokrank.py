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
                    safe_name = skin['name'].replace("/", "_").replace("\\", "_").replace(" ", "")
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
        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
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

            cur_score = skin.get('score')
            skin['real_score'] = self._calculate_real_score(cur_score, skin['list_price'], skin['real_price'])

            if 'price' in skin: del skin['price']
            if 'on_leaderboard' not in skin:
                skin['on_leaderboard'] = True if (
                            skin.get('is_new') or skin.get('is_rerun') or skin.get('is_preset')) else False
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
                print(f"✅ 数据加载完毕 (库存库容: {len(self.all_skins)})")
            except Exception as e:
                print(f"❌ 加载失败: {e}");
                self.all_skins = []
        else:
            self.save_data()

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                self.all_skins.sort(
                    key=lambda x: (0 if x.get('is_preset') else 1, x.get('score') is None, -(x.get('score') or 0)))
                json.dump(self.all_skins, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 存档失败: {e}")

    def get_total_skins(self):
        data = self.all_skins[:]
        data.sort(key=lambda x: (x.get('is_preset', False), x.get('score') is None, -(x.get('score') or 0)))
        return data

    def get_active_leaderboard(self):
        active = [s for s in self.all_skins if s.get('on_leaderboard', False)]
        active.sort(key=lambda x: (x.get('is_preset', False), x.get('score') is None, -(x.get('score') or 0)))
        return active[:LEADERBOARD_CAPACITY + 5]

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
        valid_list = [s for s in active_list if not s.get('is_preset') and s.get('score') is not None]
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
        active = [s for s in self.all_skins if s.get('on_leaderboard', False) and not s.get('is_preset')]
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
            # 🔥 修复变量名问题：is_rr
            is_rr = (len(raw) >= 3 and raw[2] != '0')
            list_p = self._get_list_price_by_quality(q_code)

            mode = input("模式: 1.立即上榜  2.不进榜  3.预设(Coming Soon): ").strip()

            is_on = False;
            is_preset = False
            rank_score = None;
            real_p = 0.0;
            growth = 0.0

            if mode == '3':
                is_preset = True;
                is_on = True
                rp_in = input("预估实价 (回车0): ").strip()
                real_p = float(rp_in) if rp_in else 0.0
                print("🕒 已设为预设皮肤，已进入自动抓取队列。")
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
                "on_leaderboard": is_on, "is_preset": is_preset,
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

                rank = int(input("插入排名: "))
                def_rp = target.get('real_price', 0)
                rp_in = input(f"实际价格 (默认{def_rp}): ").strip()
                rp = float(rp_in) if rp_in else def_rp
                gt = float(input("涨幅: "))

                rank_score = round(self.calculate_insertion_score(rank, active_list, rp, gt), 1)

                target['is_preset'] = False
                target['score'] = rank_score;
                target['real_price'] = rp;
                target['growth'] = gt
                target['real_score'] = self._calculate_real_score(rank_score, target['list_price'], rp)

                self._auto_prune_leaderboard();
                self.save_data();
                self.generate_html()
                print(f"✅ [{target['name']}] 已成功上线！")
        except ValueError:
            pass

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
        parts = raw.split()
        target_list = self.get_total_skins()

        try:
            if len(parts) >= 3:
                idx = int(parts[0]) - 1
                opt = parts[1]
                val = parts[2]
                if 0 <= idx < len(target_list):
                    item = target_list[idx]
                    if self._apply_modification(item, opt, val):
                        self.save_data();
                        self.generate_html()
                        print(f"✅ 快捷修改成功: {item['name']}")
                    else:
                        print("❌ 数值格式错误")

            elif len(parts) == 1:
                idx = int(parts[0]) - 1
                if 0 <= idx < len(target_list):
                    if raw == 'delete': del self.all_skins[idx]; self.save_data(); print("🗑️ 已删除"); return
                    item = target_list[idx]
                    while True:
                        cur_s = "--" if item['score'] is None else item['score']
                        print(
                            f"\n修改: {item['name']} | 1.分:{cur_s} | 2.涨幅:{item['growth']} | 3.实价:{item['real_price']} | 0.保存")
                        sub_raw = input("序号 数值: ").strip().lower()
                        if not sub_raw or sub_raw == '0': break
                        sub_parts = sub_raw.split()
                        if len(sub_parts) < 2: continue
                        if self._apply_modification(item, sub_parts[0], sub_parts[1]):
                            print("   ✅ 已暂存")
                        else:
                            print("   ❌ 格式错误")
                    self.save_data();
                    self.generate_html();
                    print("💾 全部更改已保存")
        except:
            pass

    def manage_status_ui(self):
        self.print_console_table()
        try:
            idx = int(input("序号: ")) - 1;
            target = self.get_total_skins()[idx]
            op = input("1-复刻 2-新增: ")
            if op == '1':
                target['is_rerun'] = True; target['is_new'] = False
            elif op == '2':
                target['is_rerun'] = False; target['is_new'] = True
            self.save_data();
            self.generate_html();
            print("✅ 更新成功")
        except:
            pass

    def run_crawler_ui(self):
        print("\n🕷️ 启动自动抓取程序...")
        count = self.crawler.fetch_images(self.all_skins)
        if count > 0:
            self.save_data(); self.generate_html(); print(f"\n🎉 同步了 {count} 张新图片！")
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

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=0.6, minimum-scale=0.1, maximum-scale=3.0, user-scalable=yes">
    <title>Honor of Kings Skin Revenue Forecast</title>
    <style>
        :root { --header-bg: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f0f2f5; display: flex; flex-direction: column; align-items: center; padding: 20px; gap: 30px; }
        @media screen and (max-width: 600px) { .chart-card { zoom: 0.7; } body { padding: 5px; align-items: center; } }
        .chart-card { background: white; width: 100%; max-width: 950px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); padding-bottom: 20px; }

        .chart-header { 
            background: var(--header-bg); padding: 15px 20px; color: white; margin-bottom: 2px; 
            display: flex; align-items: center; justify-content: center; gap: 20px;
        }
        .header-content { text-align: center; flex: 1; }
        .header-content h1 { font-size: 24px; font-weight: 800; margin: 0; line-height: 1.2; }
        .header-content p { margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }

        .header-gifs-container { display: flex; gap: 10px; align-items: center; }
        .header-gif { 
            width: 55px; height: 55px; border-radius: 8px; object-fit: cover; 
            border: 2px solid rgba(255,255,255,0.4); 
            background: rgba(255,255,255,0.1);
        }
        @media screen and (max-width: 600px) { 
            .chart-header { flex-direction: column; gap: 10px; padding: 15px; }
            .header-gif { width: 40px; height: 40px; }
        }

        .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
        table { width: 98%; margin: 0 auto; border-collapse: separate; border-spacing: 0 8px; font-size: 14px; min-width: 750px; }

        th { 
            text-align: center; 
            padding: 8px 2px; 
            font-weight: 800; 
            color: #333; 
            background-color: transparent; 
            border-bottom: 3px solid #6366f1; 
            font-size: 13px;
            white-space: nowrap; 
        }

        td:first-child {
            padding: 0 !important;
            height: 1px;
        }

        .qual-header { display: inline-flex; align-items: center; justify-content: center; gap: 6px; position: relative; }
        .multi-select-box { font-size: 11px; border-radius: 4px; border: 1px solid #ddd; padding: 4px 8px; color: #333; font-weight: bold; cursor: pointer; background: white; min-width: 85px; text-align: center; }
        .dropdown-menu { display: none; position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; border-radius: 6px; padding: 8px; min-width: 130px; text-align: left; }
        .dropdown-menu.show { display: block; }
        .dropdown-item { display: flex; align-items: center; gap: 8px; padding: 6px 4px; cursor: pointer; font-size: 12px; color: #444; }
        .col-sort { cursor: pointer; position: relative; }
        .col-sort::after { content: ' ⇅'; font-size: 10px; color: #ccc; margin-left: 5px; }
        .col-sort.sort-asc::after { content: ' ▲'; color: #6366f1; }
        .col-sort.sort-desc::after { content: ' ▼'; color: #6366f1; }
        td { padding: 12px 2px; vertical-align: middle; text-align: center; background-color: transparent; border: none; white-space: nowrap; }
        .rounded-left { border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
        .rounded-right { border-top-right-radius: 12px; border-bottom-right-radius: 12px; }
        .quality-icon { height: 28px; width: auto; display: inline-block; vertical-align: middle; transition: transform 0.2s; object-fit: contain; }

        /* 🔥 V21.7 修正：品质图标缩放矩阵 */
        .quality-icon.wushuang-big { transform: scale(1.5); }
        .quality-icon.legend-big { transform: scale(1.2); }
        .quality-icon.epic-medium { transform: scale(1.1); } 
        /* 🔥 V21.7 新增：荣耀典藏放大 1.4 */
        .quality-icon.glory-big { transform: scale(1.4); }
        .quality-icon.brave-small { transform: scale(0.9); }

        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; object-fit: cover; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 5px; min-width: 180px; position: relative; }

        .name-container { display: flex; flex-direction: column; gap: 2px; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; }

        /* 🔥 V20.7 样式继承：蓝底白字 */
        .rank-box { 
            display: inline-block; 
            min-width: 20px;       
            padding: 0px 5px;      
            border: none;          
            background: #1d4ed8;   
            color: #ffffff;        
            font-size: 20px;       
            font-weight: 900; 
            text-align: center;    
            line-height: 24px;     
            border-radius: 4px;    
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .badge { 
            display: inline-block; width: fit-content; padding: 1px 5px; font-size: 9px; 
            font-weight: 900; border-radius: 3px; text-transform: uppercase;
        }
        .badge-new { background: #ffd700; color: #000; }
        .badge-return { background: #1d4ed8; color: #fff; }
        .badge-preset { background: #06b6d4; color: #fff; }

        .box-style { 
            display: inline-block; width: 75px; padding: 4px 0; 
            font-weight: 700; font-size: 12px; border-radius: 6px; 
            background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin: 0 auto;
        }

        .pts-null { color: inherit; font-style: italic; opacity: 0.6; }
        .growth-down { color: #991b1b !important; }
        .growth-up-mid { color: #16a34a !important; }
        .growth-up-high { color: #ea580c !important; }
        .growth-special { color: #a855f7 !important; font-weight: 900 !important; }
    </style>
</head>
<body>
    <div class="chart-card">
        <div class="chart-header">
            <div class="header-gifs-container">
                {% if header_gifs|length >= 1 %}<img src="./show/{{ header_gifs[0] }}" class="header-gif">{% endif %}
                {% if header_gifs|length >= 2 %}<img src="./show/{{ header_gifs[1] }}" class="header-gif">{% endif %}
            </div>
            <div class="header-content">
                <h1>Honor of Kings Skin Revenue Forecast</h1>
                <p>Update: {{ update_time }}</p>
            </div>
            <div class="header-gifs-container">
                {% if header_gifs|length >= 3 %}<img src="./show/{{ header_gifs[2] }}" class="header-gif">{% endif %}
                {% if header_gifs|length >= 4 %}<img src="./show/{{ header_gifs[3] }}" class="header-gif">{% endif %}
            </div>
        </div>

        <div class="table-container">
            <table id="skinTable">
                <thead>
                    <tr>
                        <th class="col-sort" onclick="sortTable(0, 'int')">No</th>
                        <th><div class="qual-header">
                            <div id="multiSelectBtn" class="multi-select-box" style="border:1px solid #ddd; padding:4px 8px; cursor:pointer;" onclick="toggleMenu(event)">全部品质</div>
                            <div id="dropdownMenu" class="dropdown-menu">
                                <label class="dropdown-item"><input type="checkbox" id="selectAll" value="all" checked onchange="handleSelectAll(this)"> <strong>全部品质</strong></label>
                                <hr style="margin:4px 0">
                                {% for qname in ["珍品无双", "无双", "荣耀典藏", "珍品传说", "传说限定", "传说", "史诗", "勇者"] %}
                                <label class="dropdown-item"><input type="checkbox" class="q-check" value="{{ qname }}" onchange="handleSingleSelect(this)"> {{ qname }}</label>
                                {% endfor %}
                            </div>
                            <span class="col-sort" style="padding-left:10px" onclick="sortTable(1, 'float')"></span>
                        </div></th>
                        <th style="text-align:left; padding-left:20px; padding-right:120px;">Skin Name</th>
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
                    {% set q_name = quality_map[skin.quality] or ("无双" if 0.5 <= skin.quality < 1 else "") %}
                    <tr data-quality="{{ q_name }}">
                        <td>
                            {% if not skin.is_preset %}
                            <span class="rank-box">{{ loop.index }}</span>
                            {% else %}
                            <span style="font-weight:bold; color:#999;">-</span>
                            {% endif %}
                        </td>
                        <td class="quality-col" data-val="{{ skin.quality }}">
                            {% set q_cls = '' %}
                            {% if skin.quality <= 1 %}{% set q_cls = 'wushuang-big' %}
                            {# 🔥 V21.7: 绑定荣耀典藏(2)专属样式 #}
                            {% elif skin.quality == 2 %}{% set q_cls = 'glory-big' %} 
                            {% elif skin.quality == 4 %}{% set q_cls = 'legend-big' %}
                            {% elif skin.quality == 5 or skin.quality == 3.5 %}{% set q_cls = 'epic-medium' %}
                            {% elif skin.quality == 6 %}{% set q_cls = 'brave-small' %}{% endif %}
                            <img src="./images/{{ skin.quality }}.gif" class="quality-icon {{ q_cls }}" onerror="loadFallbackImg(this, '{{ skin.quality }}')">
                        </td>
                        <td class="rounded-left" style="background-color: {{ rb }}; padding-right:120px;"><div class="song-col">
                            {% if skin.local_img %}<img src="./{{ skin.local_img }}" class="album-art">{% else %}<img src="https://via.placeholder.com/48?text={{ skin.name[0] }}" class="album-art">{% endif %}
                            <div class="name-container">
                                <span class="song-title">{{ skin.name }}</span>
                                {# 🔥 V21.6: 预设角标优先级置顶 #}
                                {% if skin.is_preset %}<span class="badge badge-preset">Coming Soon</span>
                                {% elif skin.is_new %}<span class="badge badge-new">New Arrival</span>
                                {% elif skin.is_rerun %}<span class="badge badge-return">Limit Return</span>{% endif %}
                            </div>
                        </div></td>
                        <td data-val="{{ skin.score if skin.score is not none else -9999999 }}" style="background-color: {{ rb }};">
                            <div class="box-style">
                                {{ skin.score if skin.score is not none else '--' }}
                            </div>
                        </td>
                        <td data-val="{{ skin.real_score if skin.real_score is not none else -9999999 }}" style="background-color: {{ rb }}; color:#6366f1; font-weight:bold;">
                            {{ skin.real_score if skin.real_score is not none else '--' }}
                        </td>
                        <td data-val="{{ skin.growth }}" style="background-color: {{ rb }};">
                            {% if skin.growth == 0 or skin.growth is none %}<div class="box-style">--</div>
                            {% else %}
                                {% set g_cls = '' %}
                                {% if skin.growth == 1.9 %}{% set g_cls = 'growth-special' %}
                                {% elif skin.growth < 0 %}{% set g_cls = 'growth-down' %}
                                {% elif skin.growth >= 10 %}{% set g_cls = 'growth-up-high' %}
                                {% elif skin.growth >= 5 %}{% set g_cls = 'growth-up-mid' %}{% endif %}
                                <div class="box-style {{ g_cls }}">{{ skin.growth }}%{% if skin.growth == 1.9 %}!{% endif %}</div>
                            {% endif %}
                        </td>
                        <td data-val="{{ skin.list_price }}" style="background-color: {{ rb }};">¥{{ skin.list_price }}</td>
                        <td class="rounded-right" data-val="{{ skin.real_price }}" style="background-color: {{ rb }};">
                            <div class="box-style">
                                {% if skin.real_price > 0 %}¥{{ skin.real_price }}{% else %}--{% endif %}
                            </div>
                        </td>
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

    window.onload = () => {
        sortTable(3, 'float');
        const gifs = document.querySelectorAll('.header-gif');
        if (gifs.length > 0) {
            gifs.forEach(g => {
                let s = g.src; g.src = ''; g.src = s; 
            });
        }
    };

    function loadFallbackImg(img, q) {
        if (img.src.indexOf('.gif') !== -1) { img.src = './images/' + q + '.jpg'; }
        else if (img.src.indexOf('.jpg') !== -1 && img.src.indexOf('1.jpg') === -1) {
            let v = parseFloat(q); if (v >= 0.5 && v <= 1) img.src = './images/1.jpg';
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
    </script>
</body>
</html>
"""
        t = Template(html_template)
        html_content = t.render(total_skins=self.get_total_skins(), quality_map=quality_map,
                                header_gifs=header_gifs,
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
        print("\n" + "=" * 55)
        print("👑 王者荣耀榜单 V21.7 (完整终极版)")
        print(f"📊 当前库存 {len(app.all_skins)}")
        print("-" * 55)
        print("1. 添加皮肤 | 2. 修改数据 | 3. 修改标签 | 4. >>> 发布互联网 <<<")
        print("5. 强制刷新HTML | 6. 查看榜单 | 7. 🕷️ 抓取头像 | 8. 📉 退榜")
        print("9. 🚀 预设上线 | 0. 退出")
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
        elif cmd == '0':
            break