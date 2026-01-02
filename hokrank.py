import math
import json
import os
import subprocess
from datetime import datetime
from jinja2 import Template

# ================= ⚠️ 配置区域 (请确认路径) =================

# 1. 设置你的 hok-rank 文件夹路径
LOCAL_REPO_PATH = r"D:\python-learn\hok-rank"

# 2. 设置你的 Git.exe 路径
GIT_EXECUTABLE_PATH = r"D:\Git\bin\git.exe"


# ===========================================================

class SkinSystem:
    def __init__(self):
        self.quality_map = {
            0: "【珍品无双】", 1: "【无双】", 2: "【荣耀典藏】",
            3: "【珍品传说】", 4: "【传说】", 5: "【史诗】", 6: "【勇者】"
        }
        self.active_leaderboard = []
        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
        self.load_data()

    def _get_base_score(self, x):
        if x <= 0: return 200
        val = (288 / math.sqrt(x)) - 88
        return max(val, 0)

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.active_leaderboard = json.load(f)
                print(f"✅ 已加载历史数据 (共{len(self.active_leaderboard)}条)")
                return
            except:
                print("⚠️ 数据读取失败，初始化默认数据")

        # 默认初始化
        self.active_leaderboard = []
        self.save_data()

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_leaderboard, f, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            print(f"❌ 错误：找不到路径 {LOCAL_REPO_PATH}")

    def generate_html(self):
        """生成 V14.0 美化版网页"""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honor of Kings Prediction</title>
    <style>
        :root { --header-bg: linear-gradient(90deg, #d68bfb 0%, #faa6d9 100%); --percent-green: #bbf7d0; --row-green: #bbf7d0; --row-purple: #f3e8ff; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f0f2f5; display: flex; justify-content: center; padding: 20px; }
        .chart-card { background: white; width: 100%; max-width: 800px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }

        /* 头部样式优化 */
        .chart-header { background: var(--header-bg); padding: 30px 20px; text-align: center; color: #111; }
        .chart-header h1 { font-size: 26px; font-weight: 800; margin-bottom: 8px; color: #000; letter-spacing: -0.5px; }
        .chart-header p { font-size: 13px; font-weight: 600; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }

        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { text-align: center; padding: 12px 8px; font-weight: 700; color: #111; border-bottom: 1px solid #eee; font-size: 13px; text-transform: uppercase; }
        td { padding: 10px 8px; vertical-align: middle; text-align: center; }

        .rank-col { font-weight: 800; font-size: 18px; width: 50px; }
        .quality-col { font-size: 12px; width: 80px; font-weight: bold; color: #555; }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 15px; }
        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; background-color: #eee; object-fit: cover; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .song-info { display: flex; flex-direction: column; justify-content: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; margin-bottom: 3px; }
        .artist-name { font-size: 12px; color: #666; font-weight: 500; }

        .points-col { text-align: right; font-weight: 800; padding-right: 25px; width: 80px; font-size: 16px; }

        /* 统一的框框样式 */
        .box-style { display: inline-block; width: 100%; padding: 6px 0; font-weight: 600; font-size: 12px; border-radius: 6px; }
        .bg-up { background-color: var(--percent-green); color: #064e3b; }
        .bg-none { background-color: #f3f4f6; color: #888; }
        .bg-price { background-color: #f3f4f6; color: #333; font-weight: 700; }

        /* 前三名高亮 */
        tr:nth-child(1) td, tr:nth-child(2) td, tr:nth-child(3) td { background-color: var(--row-green); }
        tr.rerun-row td { background-color: var(--row-purple); }

        .footer { background: #8b5cf6; color: white; text-align: center; padding: 12px; font-weight: 700; font-size: 13px; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <div class="chart-card">
        <div class="chart-header">
            <h1>Honor of Kings Skin Revenue Prediction</h1>
            <p>Last Updated: {{ update_time }}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Qual</th>
                    <th style="text-align:left; padding-left:25px;">Skin Name</th>
                    <th>Points</th>
                    <th>Growth</th> <th>Price</th>
                </tr>
            </thead>
            <tbody>
                {% for skin in skins %}
                <tr class="{{ 'rerun-row' if skin.is_rerun else '' }}">
                    <td class="rank-col">{{ loop.index }}</td>
                    <td class="quality-col">{{ skin.quality_str }}</td>
                    <td>
                        <div class="song-col">
                            <img src="https://via.placeholder.com/48/{{ 'E9D5FF' if skin.is_rerun else 'DCFCE7' }}/555555?text={{ skin.name[0] }}" class="album-art">
                            <div class="song-info">
                                <span class="song-title">{{ skin.name }}</span>
                                <span class="artist-name">{{ '★ 限定复刻' if skin.is_rerun else 'New Arrival' }}</span>
                            </div>
                        </div>
                    </td>
                    <td class="points-col">{{ skin.score }}</td>
                    <td style="width: 80px;">
                        {% if skin.growth > 0 %}
                        <div class="box-style bg-up">+{{ skin.growth }}%</div>
                        {% else %}
                        <div class="box-style bg-none">--</div>
                        {% endif %}
                    </td>
                    <td style="width: 80px; padding-right:10px;">
                        <div class="box-style {{ 'bg-price' if skin.price > 0 else 'bg-none' }}">
                             {% if skin.price > 0 %}¥{{ skin.price }}{% else %}--{% endif %}
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="footer">Top 10 Available via PyCharm System</div>
    </div>
</body>
</html>
        """

        render_list = []
        for skin in self.active_leaderboard:
            item = skin.copy()
            item['quality_str'] = self.quality_map.get(item['quality'], "")
            render_list.append(item)

        t = Template(html_template)
        html_content = t.render(skins=render_list, update_time=datetime.now().strftime("%Y-%m-%d"))

        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            print("📄 网页文件已更新 (V14.0 美化版)")
        except FileNotFoundError:
            pass

    def deploy_to_github(self):
        """一键发布"""
        print("\n🚀 正在连接 GitHub...")
        try:
            os.chdir(LOCAL_REPO_PATH)
            git_cmd = GIT_EXECUTABLE_PATH

            subprocess.run([git_cmd, "add", "."], check=True)
            subprocess.run([git_cmd, "commit", "-m", f"Update {datetime.now().strftime('%H:%M')}"], check=True)
            subprocess.run([git_cmd, "push"], check=True)

            print("\n✅ 发布成功！")
            try:
                username = LOCAL_REPO_PATH.split(os.sep)[-2]
                print(f"🌐 访问: https://{username}.github.io/hok-rank/")
            except:
                print("🌐 请访问你的 GitHub Pages 网址")
        except Exception as e:
            print(f"\n❌ 发布失败 (如果是因为没修改数据，请先修改任意数据再发布)")

    # --- 交互逻辑 ---
    def add_skin_ui(self):
        print("\n>>> 添加新皮肤")
        try:
            raw = input("输入 [品质代码 名字]: ").split()
            if len(raw) < 2: return
            q_code = int(raw[0])
            name = raw[1]
            is_rerun = input("是复刻吗? (y/n): ").lower() == 'y'

            # 简单的初始分计算
            rank = len(self.active_leaderboard) + 1
            score = self._get_base_score(rank)

            new_skin = {"quality": q_code, "name": name, "is_rerun": is_rerun, "score": round(score, 1), "growth": 0.0,
                        "price": 0.0}
            self.active_leaderboard.append(new_skin)

            self.save_data()
            self.generate_html()
            print("✅ 添加成功")
        except:
            print("输入有误")

    def remove_skin_ui(self):
        try:
            idx = int(input("输入要删除的排名序号: ")) - 1
            if 0 <= idx < len(self.active_leaderboard):
                print(f"已删除: {self.active_leaderboard[idx]['name']}")
                self.active_leaderboard.pop(idx)
                self.save_data()
                self.generate_html()
        except:
            pass

    def modify_data_ui(self):
        """全面升级的修改功能"""
        try:
            idx = int(input("请输入要修改的 [排名序号]: ")) - 1
            if 0 <= idx < len(self.active_leaderboard):
                item = self.active_leaderboard[idx]
                print(f"\n当前选中: {item['name']}")
                print(f"当前数据: 点数={item['score']}, 涨幅={item['growth']}%, 价格={item['price']}")
                print("(提示: 不想改的项直接按回车跳过)")

                # 修改点数
                s_in = input(f"新点数 (原{item['score']}): ")
                if s_in.strip(): item['score'] = float(s_in)

                # 修改涨幅
                g_in = input(f"新涨幅 (原{item['growth']}): ")
                if g_in.strip(): item['growth'] = float(g_in)

                # 修改价格
                p_in = input(f"新价格 (原{item['price']}): ")
                if p_in.strip(): item['price'] = float(p_in)

                self.save_data()
                self.generate_html()
                print("✅ 修改保存成功！")
        except ValueError:
            print("❌ 输入格式错误，请输入数字")


# ================= 运行入口 =================
if __name__ == "__main__":
    app = SkinSystem()

    while True:
        print("\n" + "=" * 40)
        print("👑 王者荣耀榜单 V14.0 (增强版)")
        print("1. 添加皮肤")
        print("2. 删除皮肤")
        print("3. 修改数据 (点数/涨幅/价格)")
        print("4. >>> 发布到互联网 <<<")
        print("0. 退出")
        print("=" * 40)

        cmd = input("指令: ").strip()

        if cmd == '1':
            app.add_skin_ui()
        elif cmd == '2':
            app.remove_skin_ui()
        elif cmd == '3':
            app.modify_data_ui()  # 这里的函数换了
        elif cmd == '4':
            app.deploy_to_github()
        elif cmd == '0':
            break