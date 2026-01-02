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
        mapping = {0: 800.0, 1: 400.0, 2: 600.0, 3: 200.0, 6: 178.8, 5: 88.8, 4: 48.8}
        return mapping.get(q_code, 0.0)

    def _calculate_real_score(self, rank_score, list_price, real_price):
        if real_price <= 0 or list_price <= 0: return None
        return round(rank_score * (real_price / list_price), 1)

    def _migrate_data_structure(self):
        if not self.all_skins: return
        for skin in self.all_skins:
            if 'real_price' not in skin: skin['real_price'] = skin.get('price', 0.0)
            if 'list_price' not in skin: skin['list_price'] = self._get_list_price_by_quality(skin['quality'])
            skin['real_score'] = self._calculate_real_score(skin['score'], skin['list_price'], skin['real_price'])
            if 'price' in skin: del skin['price']
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
                self.all_skins.sort(key=lambda x: x['score'], reverse=True)
                json.dump(self.all_skins, f, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            print(f"❌ 错误：找不到路径 {LOCAL_REPO_PATH}")

    def get_total_skins(self):
        data = self.all_skins[:]
        data.sort(key=lambda x: x['score'], reverse=True)
        return data

    def print_console_table(self):
        """控制台打印 - 已加回涨幅显示"""
        data = self.get_total_skins()
        print(f"\n====== 🏆 历史总榜 (Total History) ======")
        # 增加了 Growth 列
        print(f"{'No.':<4} {'Q':<2} {'名字':<12} {'RankPts':<8} {'RealPts':<8} {'Growth':<8} {'ListP':<8} {'RealP'}")
        print("-" * 85)
        for i, skin in enumerate(data):
            real_pts_str = str(skin.get('real_score')) if skin.get('real_score') else "--"
            list_p_str = f"¥{skin.get('list_price', 0)}"
            real_p_str = f"¥{skin.get('real_price', 0)}" if skin.get('real_price', 0) > 0 else "--"

            # 涨幅显示逻辑
            g_val = skin.get('growth', 0)
            growth_str = f"+{g_val}%" if g_val > 0 else "--"

            print(
                f"{i + 1:<4} {skin['quality']:<2} {skin['name']:<12} {skin['score']:<8} {real_pts_str:<8} {growth_str:<8} {list_p_str:<8} {real_p_str}")
        print("=" * 85 + "\n")

    def calculate_insertion_score(self, rank_input, active_list, real_price, growth):
        if rank_input == 1:
            old_top1_score = active_list[0]['score'] if active_list else 0
            return max(old_top1_score / 0.6, (282 / math.sqrt(1.25)) - 82, real_price * growth * 15)
        prev_idx = rank_input - 2
        prev_score = 200 if prev_idx < 0 else active_list[prev_idx]['score']
        if rank_input - 1 >= len(active_list):
            next_score = max(self._get_base_score(rank_input + 1), 1)
        else:
            next_score = active_list[rank_input - 1]['score']
        return math.sqrt(prev_score * next_score)

    def add_skin_ui(self):
        print("\n>>> 添加新皮肤")
        self.print_console_table()
        active_list = self.get_total_skins()
        try:
            print("格式: 品质代码 名字 [非0=复刻]")
            raw = input("输入: ").split()
            if len(raw) < 2: return
            q_code = int(raw[0]);
            name = raw[1]
            is_rerun = (len(raw) >= 3 and raw[2] != '0')
            is_new = not is_rerun
            rank = int(input(f"排名 (1-{len(active_list) + 1}): "))
            if rank < 1: rank = 1
            if rank > len(active_list) + 1: rank = len(active_list) + 1

            list_p = self._get_list_price_by_quality(q_code)
            list_p_input = input(f"定价 (默认 {list_p}, 回车确认): ")
            if list_p_input.strip(): list_p = float(list_p_input)

            real_p = 0.0;
            growth = 0.0
            if rank == 1:
                rp_in = input("实际价格 (Real Price): ")
                real_p = float(rp_in) if rp_in else 0.0
                growth = float(input("涨幅 (Growth %): "))
            else:
                extra = input("选填 [涨幅 实际价格]: ").split()
                if len(extra) >= 1: growth = float(extra[0])
                if len(extra) >= 2: real_p = float(extra[1])

            rank_score = round(self.calculate_insertion_score(rank, active_list, real_p, growth), 1)
            real_score = self._calculate_real_score(rank_score, list_p, real_p)

            self.all_skins.append({
                "quality": q_code, "name": name,
                "is_rerun": is_rerun, "is_new": is_new,
                "score": rank_score,
                "real_score": real_score,
                "growth": growth,
                "list_price": list_p,
                "real_price": real_p,
                "local_img": None
            })
            self.save_data();
            self.generate_html()
            print(f"✅ 添加成功")
        except ValueError:
            print("❌ 输入错误")

    def modify_data_ui(self):
        print("\n1. 修改数据 (快捷模式)")
        print("2. 删除数据")
        c = input("选: ")
        self.print_console_table()
        target_list = self.get_total_skins()
        try:
            idx = int(input("输入序号: ")) - 1
            if 0 <= idx < len(target_list):
                if c == '2':
                    del self.all_skins[idx]
                    self.save_data();
                    self.generate_html()
                    print("🗑️ 已删除")
                    return

                item = target_list[idx]
                while True:
                    print(f"\n当前: {item['name']}")
                    print(f"1. 排位点数: {item['score']}")
                    print(f"2. 涨幅: {item['growth']}%")
                    print(f"3. 实际价格: {item.get('real_price', 0)}")
                    print(f"4. 定价: {item.get('list_price', 0)}")
                    print(f"5. 品质: {item['quality']}")

                    raw = input("输入 [序号] [数值] (直接回车退出): ").strip()
                    if not raw: break
                    parts = raw.split()
                    if len(parts) < 2: print("❌ 格式错误"); continue

                    try:
                        opt, val = parts[0], float(parts[1])
                        if opt == '1':
                            item['score'] = val
                        elif opt == '2':
                            item['growth'] = val
                        elif opt == '3':
                            item['real_price'] = val
                        elif opt == '4':
                            item['list_price'] = val
                        elif opt == '5':
                            item['quality'] = int(val)
                        else:
                            print("❌ 无效序号"); continue

                        if opt in ['1', '3', '4']:
                            item['real_score'] = self._calculate_real_score(item['score'], item['list_price'],
                                                                            item['real_price'])
                        print("✅ 已暂存")
                    except ValueError:
                        print("❌ 数值错误")

                self.save_data();
                self.generate_html()
                print("💾 保存成功并刷新网页")
        except:
            pass

    def manage_status_ui(self):
        self.print_console_table()
        active_view = self.get_total_skins()
        try:
            idx = int(input("输入序号修改标签: ")) - 1
            if 0 <= idx < len(active_view):
                target = active_view[idx]
                op = input("设为: 1-复刻  2-新增  3-历史: ")
                if op == '1':
                    target['is_rerun'] = True; target['is_new'] = False
                elif op == '2':
                    target['is_rerun'] = False; target['is_new'] = True
                elif op == '3':
                    target['is_rerun'] = False; target['is_new'] = False
                self.save_data();
                self.generate_html()
                print(f"✅ 标签已更新")
        except:
            pass

    def run_crawler_ui(self):
        count = self.crawler.fetch_images(self.all_skins)
        if count > 0:
            self.save_data();
            self.generate_html()
            print(f"\n🎉 更新了 {count} 张图片！")
        else:
            print("\n⚠️ 无新图片更新")

    def generate_html(self):
        """生成网页 V19.19"""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honor of Kings Skin Revenue Prediction</title>
    <style>
        :root {
            --header-bg: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);
            --percent-green: #bbf7d0;
            --row-green: #bbf7d0;
            --row-blue: #bfdbfe;
            --row-purple: #e9d5ff;
            --row-gold: #fde68a;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f0f2f5; display: flex; flex-direction: column; align-items: center; padding: 20px; gap: 30px; }
        .chart-card { background: white; width: 100%; max-width: 950px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .chart-header { background: var(--header-bg); padding: 25px 20px; text-align: center; color: white; }
        .chart-header h1 { font-size: 24px; font-weight: 800; margin-bottom: 8px; color: white; letter-spacing: -0.5px; }
        .chart-header p { font-size: 13px; font-weight: 600; opacity: 0.9; text-transform: uppercase; color: rgba(255,255,255,0.9); }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { text-align: center; padding: 12px 6px; font-weight: 700; color: #111; border-bottom: 1px solid #eee; font-size: 12px; text-transform: uppercase; }
        td { padding: 10px 6px; vertical-align: middle; text-align: center; }
        .rank-col { font-weight: 800; font-size: 18px; width: 40px; }
        .quality-col { width: 80px; text-align: center; }
        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; background-color: transparent; object-fit: cover; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .quality-icon { height: 28px; width: auto; display: inline-block; mix-blend-mode: multiply; filter: contrast(1.1); transition: transform 0.2s; }
        .quality-icon.wushuang-big { transform: scale(1.4); }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 10px; min-width: 200px; }
        .song-info { display: flex; flex-direction: column; justify-content: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; margin-bottom: 3px; }
        .artist-name { font-size: 12px; color: #666; font-weight: 500; }
        .data-col { font-weight: 700; font-size: 15px; width: 80px; }
        .real-pts { color: #6366f1; } 
        .missing-data { color: #ccc; font-weight: 400; }
        .box-style { display: inline-block; width: 100%; padding: 6px 0; font-weight: 600; font-size: 12px; border-radius: 6px; }
        .bg-up { background-color: var(--percent-green); color: #064e3b; }
        .bg-none { background-color: #f3f4f6; color: #888; }
        .bg-price { background-color: #f3f4f6; color: #333; font-weight: 700; }
        tr.q-normal td { background-color: #ffffff; }
        tr.q-green td { background-color: var(--row-green); }
        tr.q-blue td { background-color: var(--row-blue); }
        tr.q-purple td { background-color: var(--row-purple); }
        tr.q-gold td { background-color: var(--row-gold); }
        tr:not(.q-normal) .bg-up, tr:not(.q-normal) .bg-price { background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
</head>
<body>
    <div class="chart-card">
        <div class="chart-header">
            <h1>Honor of Kings Skin Revenue Prediction</h1>
            <p>Last updated: {{ update_time }}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Rank</th><th>Qual</th><th style="text-align:left; padding-left:20px;">Skin Name</th>
                    <th>Rank Pts</th><th>Real Pts</th><th>Growth</th><th>List Price</th><th>Real Price</th>
                </tr>
            </thead>
            <tbody>
                {% for skin in total_skins %}
                {% set q_class = 'q-normal' %}
                {% if skin.quality == 3 %}{% set q_class = 'q-green' %}
                {% elif skin.quality == 2 %}{% set q_class = 'q-blue' %}
                {% elif skin.quality == 1 %}{% set q_class = 'q-purple' %}
                {% elif skin.quality == 0 %}{% set q_class = 'q-gold' %}
                {% endif %}
                <tr class="{{ q_class }}">
                    <td class="rank-col">{{ loop.index }}</td>
                    <td class="quality-col">
                        <img src="./images/{{ skin.quality }}.jpg" class="quality-icon {{ 'wushuang-big' if skin.quality <= 1 else '' }}">
                    </td>
                    <td>
                        <div class="song-col">
                            {% set placeholder_bg = 'f3f4f6' %}
                            {% if skin.quality == 3 %}{% set placeholder_bg = 'bbf7d0' %}
                            {% elif skin.quality == 2 %}{% set placeholder_bg = 'bfdbfe' %}
                            {% elif skin.quality == 1 %}{% set placeholder_bg = 'e9d5ff' %}
                            {% elif skin.quality == 0 %}{% set placeholder_bg = 'fde68a' %}
                            {% endif %}
                            {% if skin.local_img %}
                                <img src="./{{ skin.local_img }}" class="album-art">
                            {% else %}
                                <img src="https://via.placeholder.com/48/{{ placeholder_bg }}/555555?text={{ skin.name[0] }}" class="album-art">
                            {% endif %}
                            <div class="song-info">
                                <span class="song-title">{{ skin.name }}</span>
                                <span class="artist-name">
                                    {% if skin.is_rerun %}★ Limited Rerun{% elif skin.is_new %}New Arrival{% else %}History{% endif %}
                                </span>
                            </div>
                        </div>
                    </td>
                    <td class="data-col">{{ skin.score }}</td>
                    <td class="data-col real-pts">{% if skin.real_score %}{{ skin.real_score }}{% else %}<span class="missing-data">--</span>{% endif %}</td>
                    <td style="width: 80px;">{% if skin.growth > 0 %}<div class="box-style bg-up">+{{ skin.growth }}%</div>{% else %}<div class="box-style bg-none">--</div>{% endif %}</td>
                    <td style="width: 80px; padding-right:5px;"><div class="box-style bg-none">¥{{ skin.list_price }}</div></td>
                    <td style="width: 80px; padding-right:10px;"><div class="box-style {{ 'bg-price' if skin.real_price > 0 else 'bg-none' }}">{% if skin.real_price > 0 %}¥{{ skin.real_price }}{% else %}--{% endif %}</div></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        t = Template(html_template)
        html_content = t.render(total_skins=self.get_total_skins(),
                                update_time=datetime.now().strftime("%Y-%m-%d %H:%M"))
        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            print("📄 网页文件已更新")
        except:
            print("❌ 错误：找不到 index.html 路径")

    def deploy_to_github(self):
        print("\n🚀 正在连接 GitHub...")
        try:
            os.chdir(LOCAL_REPO_PATH)
            subprocess.run([GIT_EXECUTABLE_PATH, "add", "."], check=True)
            subprocess.run([GIT_EXECUTABLE_PATH, "commit", "-m", f"Update {datetime.now().strftime('%H:%M')}"],
                           check=True)
            subprocess.run([GIT_EXECUTABLE_PATH, "push"], check=True)
            print("\n✅ 发布成功！")
            print(f"🌐 访问: https://{GITHUB_USERNAME}.github.io/hok-rank/")
        except Exception as e:
            print(f"\n❌ 发布失败: {e}")


if __name__ == "__main__":
    app = SkinSystem()
    while True:
        print("\n" + "=" * 55)
        print("👑 王者荣耀榜单 V19.19 (修复控制台涨幅显示)")
        print(f"📊 当前库存 {len(app.all_skins)}")
        print("-" * 55)
        print("1. 添加皮肤")
        print("2. 修改数据 (快捷指令)")
        print("3. 修改标签")
        print("4. >>> 发布到互联网 <<<")
        print("5. 强制刷新HTML")
        print("6. 查看榜单")
        print("7. 🕷️ 自动抓取百度头像")
        print("0. 退出")
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
            app.print_console_table()
        elif cmd == '7':
            app.run_crawler_ui()
        elif cmd == '0':
            break