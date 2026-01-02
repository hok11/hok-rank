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
            'Accept': 'text/plain, */*; q=0.01',
            'Referer': 'https://image.baidu.com/search/index',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def fetch_images(self, skin_list):
        print("\n🕷️ 正在启动百度图片搜索 (纯净关键词版)...")
        count = 0

        for skin in skin_list:
            # 1. 检查本地文件 (你删了就会触发下载)
            if skin.get('local_img') and os.path.exists(os.path.join(LOCAL_REPO_PATH, skin['local_img'])):
                continue

            # 2. 🔥 核心修改：只保留 [皮肤名 英雄名]
            parts = skin['name'].split('-')
            if len(parts) >= 2:
                # 翻转：把独特的皮肤名放在前面，权重更高
                # 例如：曜-山海·苍雷引 -> "山海·苍雷引 曜"
                search_name = f"{parts[1]} {parts[0]}"
            else:
                search_name = skin['name']

            # ❌ 已移除 "王者荣耀" 和 "头像"
            keyword = search_name

            # 3. 百度图片 API
            url = "https://image.baidu.com/search/acjson"
            params = {
                "tn": "resultjson_com",
                "logid": "8388656667592781395",
                "ipn": "rj",
                "ct": "201326592",
                "is": "",
                "fp": "result",
                "queryWord": keyword,
                "cl": "2",
                "lm": "-1",
                "ie": "utf-8",
                "oe": "utf-8",
                "adpicid": "",
                "st": "-1",
                "z": "",
                "ic": "",
                "hd": "",
                "latest": "",
                "copyright": "",
                "word": keyword,
                "s": "",
                "se": "",
                "tab": "",
                "width": "",
                "height": "",
                "face": "0",
                "istype": "2",
                "qc": "",
                "nc": "1",
                "fr": "",
                "expermode": "",
                "force": "",
                "pn": "0",
                "rn": "1",
                "gsm": "1e",
            }

            try:
                # 4. 请求 API
                resp = requests.get(url, headers=self.headers, params=params, timeout=5)

                try:
                    data = resp.json()
                except:
                    try:
                        data = json.loads(resp.text.replace(r"\'", r"'"))
                    except:
                        print(f"   ⚠️ API 解析失败: {skin['name']}")
                        continue

                # 提取图片
                if 'data' in data and len(data['data']) > 0 and 'thumbURL' in data['data'][0]:
                    img_url = data['data'][0]['thumbURL']
                    if not img_url:
                        if 'replaceUrl' in data['data'][0] and len(data['data'][0]['replaceUrl']) > 0:
                            img_url = data['data'][0]['replaceUrl'][0]['ObjURL']
                        else:
                            print(f"   💨 API 返回空地址: {skin['name']}")
                            continue

                    print(f"   🔍 搜索 [{keyword}] -> 成功!")

                    # 5. 下载
                    img_resp = requests.get(img_url, headers=self.headers, timeout=10)

                    # 6. 保存
                    safe_name = skin['name'].replace("/", "_").replace("\\", "_").replace(" ", "")
                    file_name = f"{safe_name}.jpg"
                    file_path = os.path.join(self.save_dir, file_name)

                    with open(file_path, 'wb') as f:
                        f.write(img_resp.content)

                    skin['local_img'] = f"skin_avatars/{file_name}"
                    count += 1
                    print(f"   ✅ 已下载: {file_name}")

                    time.sleep(random.uniform(0.5, 1.5))
                else:
                    print(f"   💨 未搜索到图片: {skin['name']} (关键词: {keyword})")

            except Exception as e:
                print(f"   ❌ 错误 {skin['name']}: {e}")

        return count


class SkinSystem:
    def __init__(self):
        self.all_skins = []
        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
        self.crawler = SkinCrawler(LOCAL_REPO_PATH)
        self.load_data()
        self._fix_initial_status()

    def _fix_initial_status(self):
        if not self.all_skins: return
        rerun_indices = {1, 2, 7, 8, 9}
        for i, skin in enumerate(self.all_skins):
            if i >= 10: break
            if i in rerun_indices:
                skin['is_rerun'] = True; skin['is_new'] = False
            else:
                skin['is_rerun'] = False; skin['is_new'] = True
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

    # --- 视图逻辑 ---
    def get_total_skins(self):
        data = self.all_skins[:]
        data.sort(key=lambda x: x['score'], reverse=True)
        return data

    def print_console_table(self, view_type="total"):
        data = self.get_total_skins()
        print(f"\n====== 🏆 历史总榜 (Total History) ======")
        print(f"{'No.':<4} {'图片':<6} {'名字':<12} {'点数':<8} {'价格'}")
        print("-" * 60)
        for i, skin in enumerate(data):
            # 检查文件实际存在性
            has_img = skin.get('local_img') and os.path.exists(os.path.join(LOCAL_REPO_PATH, skin['local_img']))
            img_status = "🖼️ 有" if has_img else "❌ 无"
            price_str = f"¥{skin['price']}" if skin['price'] > 0 else "--"
            print(f"{i + 1:<4} {img_status:<6} {skin['name']:<12} {skin['score']:<8} {price_str}")
        print("=" * 60 + "\n")

    def calculate_insertion_score(self, rank_input, active_list, price=0, growth=0):
        if rank_input == 1:
            old_top1_score = active_list[0]['score'] if active_list else 0
            return max(old_top1_score / 0.6, (282 / math.sqrt(1.25)) - 82, price * growth * 15)
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
            p = 0.0;
            g = 0.0
            if rank == 1:
                p = float(input("售价: ")); g = float(input("涨幅: "))
            else:
                extra = input("选填 [涨幅 售价]: ").split()
                if len(extra) >= 1: g = float(extra[0])
                if len(extra) >= 2: p = float(extra[1])
            new_score = self.calculate_insertion_score(rank, active_list, p, g)
            self.all_skins.append({
                "quality": q_code, "name": name,
                "is_rerun": is_rerun, "is_new": is_new,
                "score": round(new_score, 1), "growth": g, "price": p,
                "local_img": None
            })
            self.save_data();
            self.generate_html()
            print(f"✅ 添加成功")
        except:
            print("❌ 错误")

    def run_crawler_ui(self):
        count = self.crawler.fetch_images(self.all_skins)
        if count > 0:
            self.save_data()
            self.generate_html()
            print(f"\n🎉 成功抓取并更新了 {count} 张新图片！")
        else:
            print("\n⚠️ 没有发现新图片，或已全部存在。")

    def generate_html(self):
        """生成网页 V19.12"""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honor of Kings Skin Revenue Prediction</title>
    <style>
        :root { --header-bg: linear-gradient(90deg, #6366f1 0%, #a855f7 100%); --percent-green: #bbf7d0; --row-green: #bbf7d0; --row-purple: #f3e8ff; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f0f2f5; display: flex; flex-direction: column; align-items: center; padding: 20px; gap: 30px; }
        .chart-card { background: white; width: 100%; max-width: 800px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .chart-header { background: var(--header-bg); padding: 25px 20px; text-align: center; color: white; }
        .chart-header h1 { font-size: 24px; font-weight: 800; margin-bottom: 8px; color: white; letter-spacing: -0.5px; }
        .chart-header p { font-size: 13px; font-weight: 600; opacity: 0.9; text-transform: uppercase; color: rgba(255,255,255,0.9); }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { text-align: center; padding: 12px 8px; font-weight: 700; color: #111; border-bottom: 1px solid #eee; font-size: 12px; text-transform: uppercase; }
        td { padding: 10px 8px; vertical-align: middle; text-align: center; }
        .rank-col { font-weight: 800; font-size: 18px; width: 50px; }
        .quality-col { width: 90px; text-align: center; }
        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; background-color: transparent; object-fit: cover; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .quality-icon { height: 28px; width: auto; display: inline-block; mix-blend-mode: multiply; filter: contrast(1.1); transition: transform 0.2s; }
        .quality-icon.wushuang-big { transform: scale(1.4); }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 15px; }
        .song-info { display: flex; flex-direction: column; justify-content: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; margin-bottom: 3px; }
        .artist-name { font-size: 12px; color: #666; font-weight: 500; }
        .points-col { text-align: right; font-weight: 800; padding-right: 25px; width: 80px; font-size: 16px; }
        .box-style { display: inline-block; width: 100%; padding: 6px 0; font-weight: 600; font-size: 12px; border-radius: 6px; }
        .bg-up { background-color: var(--percent-green); color: #064e3b; }
        .bg-none { background-color: #f3f4f6; color: #888; }
        .bg-price { background-color: #f3f4f6; color: #333; font-weight: 700; }
        tbody tr:nth-child(-n+3) td { background-color: var(--row-green); }
        tr.rerun-row td { background-color: var(--row-purple) !important; }
        tbody tr:nth-child(-n+3) .bg-up, tbody tr:nth-child(-n+3) .bg-price {
            background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
</head>
<body>
    <div class="chart-card">
        <div class="chart-header">
            <h1>Honor of Kings Skin Revenue Prediction</h1>
            <p>Last updated: {{ update_time }}</p>
        </div>
        <table>
            <thead><tr><th>Rank</th><th>Qual</th><th style="text-align:left; padding-left:25px;">Skin Name</th><th>Points</th><th>Growth</th><th>Price</th></tr></thead>
            <tbody>
                {% for skin in total_skins %}
                <tr class="{{ 'rerun-row' if skin.is_rerun else '' }}">
                    <td class="rank-col">{{ loop.index }}</td>
                    <td class="quality-col">
                        <img src="./images/{{ skin.quality }}.jpg" class="quality-icon {{ 'wushuang-big' if skin.quality == 1 else '' }}">
                    </td>
                    <td>
                        <div class="song-col">
                            {% set bg_color = 'f3e8ff' if skin.is_rerun else ('bbf7d0' if loop.index <= 3 else 'f3f4f6') %}
                            {% if skin.local_img %}
                                <img src="./{{ skin.local_img }}" class="album-art">
                            {% else %}
                                <img src="https://via.placeholder.com/48/{{ bg_color }}/555555?text={{ skin.name[0] }}" class="album-art">
                            {% endif %}
                            <div class="song-info">
                                <span class="song-title">{{ skin.name }}</span>
                                <span class="artist-name">
                                    {% if skin.is_rerun %}★ Limited Rerun{% elif skin.is_new %}New Arrival{% else %}History{% endif %}
                                </span>
                            </div>
                        </div>
                    </td>
                    <td class="points-col">{{ skin.score }}</td>
                    <td style="width: 80px;">{% if skin.growth > 0 %}<div class="box-style bg-up">+{{ skin.growth }}%</div>{% else %}<div class="box-style bg-none">--</div>{% endif %}</td>
                    <td style="width: 80px; padding-right:10px;"><div class="box-style {{ 'bg-price' if skin.price > 0 else 'bg-none' }}">{% if skin.price > 0 %}¥{{ skin.price }}{% else %}--{% endif %}</div></td>
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
        print("\n" + "=" * 45)
        print("👑 王者荣耀榜单 V19.12 (纯净搜索版)")
        print(f"📊 当前库存 {len(app.all_skins)}")
        print("-" * 45)
        print("1. 添加皮肤")
        print("2. 删除/修改数据")
        print("3. 手动修改状态")
        print("4. >>> 发布到互联网 <<<")
        print("5. 强制刷新HTML")
        print("6. 查看榜单")
        print("7. 🕷️ 自动抓取百度头像 (纯净版)")
        print("0. 退出")
        print("=" * 45)
        cmd = input("指令: ").strip()
        if cmd == '1':
            app.add_skin_ui()
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