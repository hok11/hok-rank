import math
import json
import os
import subprocess
from datetime import datetime
from jinja2 import Template

# ================= ⚠️ 配置区域 (请修改这两行) =================

# 1. 设置你的 hok-rank 文件夹路径 (刚才克隆下来的那个文件夹)
# 注意：路径前面加个 r，防止报错
LOCAL_REPO_PATH = r"D:\python-learn\hok-rank"

# 2. 设置你的 Git.exe 路径 (就是你刚才找到的那个)
# 如果不设置这个，发布时可能会报错“找不到文件”
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

        # 自动加载数据
        self.load_data()

    def _get_base_score(self, x):
        if x <= 0: return 200
        val = (288 / math.sqrt(x)) - 88
        return max(val, 0)

    def load_data(self):
        """读取本地存储的数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.active_leaderboard = json.load(f)
                print(f"✅ 已加载历史数据 (共{len(self.active_leaderboard)}条)")
                return
            except:
                print("⚠️ 数据文件为空或损坏，使用默认初始化")

        # 初始化默认数据 (如果没有旧数据)
        init_data = [
            (1, "孙悟空-无相", False), (1, "甄姬-雪境奇遇", True),
            (1, "瑶-真我赫兹", True), (4, "曹操-万灵伏威", False),
            (5, "安琪拉-糖果风暴", False), (6, "孙权-径山谋武", False),
            (6, "蚩姹-极光幻客", False), (4, "小乔-山海·琳琅生", True),
            (5, "妲己-热情桑巴", True), (4, "曜-山海·苍雷引", True)
        ]
        self.active_leaderboard = []
        for i, (q_code, name, is_rerun) in enumerate(init_data):
            score = self._get_base_score(i + 1)
            self.active_leaderboard.append({
                "quality": q_code, "name": name, "is_rerun": is_rerun,
                "score": round(score, 1), "growth": 0.0, "price": 0.0
            })
        self.save_data()
        self.generate_html()

    def save_data(self):
        """保存数据到JSON"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_leaderboard, f, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            print(f"❌ 错误：找不到路径 {LOCAL_REPO_PATH}")
            print("请检查代码顶部的 LOCAL_REPO_PATH 是否配置正确！")

    def generate_html(self):
        """生成漂亮的静态HTML文件"""
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>王者荣耀皮肤销量点数榜</title>
    <style>
        :root { --header-bg: linear-gradient(90deg, #d68bfb 0%, #faa6d9 100%); --percent-green: #bbf7d0; --row-green: #bbf7d0; --row-purple: #f3e8ff; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #f0f2f5; display: flex; justify-content: center; padding: 20px; }
        .chart-card { background: white; width: 100%; max-width: 800px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .chart-header { background: var(--header-bg); padding: 25px; text-align: center; color: #111; }
        .chart-header h1 { font-size: 24px; font-weight: 800; margin-bottom: 5px; }
        .chart-header p { font-size: 14px; font-weight: 500; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { text-align: center; padding: 10px; font-weight: 700; color: #111; border-bottom: 1px solid #eee; }
        td { padding: 8px; vertical-align: middle; text-align: center; }
        .rank-col { font-weight: 800; font-size: 16px; width: 50px; }
        .quality-col { font-size: 12px; width: 80px; font-weight: bold; color: #555; }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 20px; }
        .album-art { width: 45px; height: 45px; border-radius: 4px; margin-right: 12px; background-color: #ddd; object-fit: cover; }
        .song-info { display: flex; flex-direction: column; justify-content: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #111; margin-bottom: 2px; }
        .artist-name { font-size: 12px; color: #666; }
        .points-col { text-align: right; font-weight: 800; padding-right: 20px; width: 80px; }
        .percent-box { display: inline-block; width: 100%; padding: 8px 0; font-weight: 500; font-size: 12px; border-radius: 4px; }
        .bg-up { background-color: var(--percent-green); }
        .bg-none { background-color: #f3f4f6; color: #999; }

        /* 还原图片风格 */
        tr:nth-child(1) td, tr:nth-child(2) td, tr:nth-child(3) td { background-color: var(--row-green); }
        tr.rerun-row td { background-color: var(--row-purple); }

        .footer { background: #8b5cf6; color: white; text-align: center; padding: 10px; font-weight: 700; font-size: 14px; }
    </style>
</head>
<body>
    <div class="chart-card">
        <div class="chart-header">
            <h1>Early Hot 100 Predictions</h1>
            <p>王者荣耀皮肤销量点数榜 (Update: {{ update_time }})</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Qual</th>
                    <th style="text-align:left; padding-left:30px;">Skin Name</th>
                    <th>Points</th>
                    <th>%</th>
                    <th>Price</th>
                </tr>
            </thead>
            <tbody>
                {% for skin in skins %}
                <tr class="{{ 'rerun-row' if skin.is_rerun else '' }}">
                    <td class="rank-col">{{ loop.index }}</td>
                    <td class="quality-col">{{ skin.quality_str }}</td>
                    <td>
                        <div class="song-col">
                            <img src="https://via.placeholder.com/45/{{ '9333ea' if skin.is_rerun else '16a34a' }}/FFFFFF?text={{ skin.name[0] }}" class="album-art">
                            <div class="song-info">
                                <span class="song-title">{{ skin.name }}</span>
                                <span class="artist-name">{{ '★ 限定复刻' if skin.is_rerun else 'New Arrival' }}</span>
                            </div>
                        </div>
                    </td>
                    <td class="points-col">{{ skin.score }}</td>
                    <td>
                        {% if skin.growth > 0 %}
                        <div class="percent-box bg-up">+{{ skin.growth }}%</div>
                        {% else %}
                        <div class="percent-box bg-none">--</div>
                        {% endif %}
                    </td>
                    <td style="font-weight:bold; color:#555;">
                        {% if skin.price > 0 %}¥{{ skin.price }}{% else %}--{% endif %}
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

        # 写入 index.html 到仓库目录
        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            print("📄 网页文件已自动更新")
        except FileNotFoundError:
            pass

    def deploy_to_github(self):
        """一键发布到 GitHub (使用指定的 git.exe)"""
        print("\n🚀 正在连接 GitHub，请稍候...")
        try:
            # 切换到仓库目录
            os.chdir(LOCAL_REPO_PATH)

            # 使用用户指定的 git 路径
            git_cmd = GIT_EXECUTABLE_PATH

            # 执行 Git 命令
            subprocess.run([git_cmd, "add", "."], check=True)
            subprocess.run([git_cmd, "commit", "-m", f"Update {datetime.now().strftime('%H:%M')}"], check=True)
            subprocess.run([git_cmd, "push"], check=True)

            print("\n✅ 发布成功！")
            # 尝试从路径中解析用户名
            try:
                username = LOCAL_REPO_PATH.split(os.sep)[-2]  # 简单猜测
                if "github" not in username and "Users" not in username:
                    print(f"🌐 你的网站地址: https://{username}.github.io/hok-rank/")
                else:
                    print(f"🌐 你的网站地址: https://[你的GitHub用户名].github.io/hok-rank/")
            except:
                print(f"🌐 你的网站地址: https://[你的GitHub用户名].github.io/hok-rank/")

            print("(注意：GitHub 更新可能有 1-2 分钟延迟，请稍后刷新网页)")
        except Exception as e:
            print(f"\n❌ 发布失败: {e}")
            print("请检查：")
            print("1. LOCAL_REPO_PATH 和 GIT_EXECUTABLE_PATH 是否都填对了？")
            print("2. 第一次运行可能需要你在弹出的窗口里登录 GitHub 账号。")

    # --- 界面交互逻辑 ---
    def add_skin_ui(self):
        print("\n>>> 请输入皮肤信息 (格式: 品质代码 名字 [任意数字代表复刻])")
        try:
            raw = input("输入: ").strip().split()
            if len(raw) < 2: return
            q_code = int(raw[0])
            name = raw[1]
            is_rerun = True if len(raw) >= 3 else False

            rank = int(input(f"插入排名位置 (1-{len(self.active_leaderboard) + 1}): "))
            if rank < 1: rank = 1
            if rank > len(self.active_leaderboard) + 1: rank = len(self.active_leaderboard) + 1

            price, growth, new_score = 0.0, 0.0, 0.0

            if rank == 1:
                p_in = input("售价 (RMB): ")
                g_in = input("次日涨幅 (%): ")
                try:
                    price, growth = float(p_in), float(g_in)
                except:
                    pass

                algo_1 = self.active_leaderboard[0]['score'] / 0.6 if self.active_leaderboard else 0
                algo_2 = 169.6
                algo_3 = price * growth * 15
                new_score = max(algo_1, algo_2, algo_3)
            else:
                extra = input("输入 [涨幅 售价] (可选): ").split()
                if len(extra) >= 1: growth = float(extra[0])
                if len(extra) >= 2: price = float(extra[1])

                prev_idx, next_idx = rank - 2, rank - 1
                if prev_idx < 0:
                    new_score = 200
                elif next_idx >= len(self.active_leaderboard):
                    new_score = math.sqrt(self.active_leaderboard[prev_idx]['score'] * self._get_base_score(rank + 1))
                else:
                    new_score = math.sqrt(
                        self.active_leaderboard[prev_idx]['score'] * self.active_leaderboard[next_idx]['score'])

            new_skin = {"quality": q_code, "name": name, "is_rerun": is_rerun, "score": new_score, "growth": growth,
                        "price": price}
            self.active_leaderboard.insert(rank - 1, new_skin)
            if len(self.active_leaderboard) > 10: self.active_leaderboard.pop()

            self.save_data()
            self.generate_html()
            print("✅ 录入成功")

        except Exception as e:
            print(f"❌ 错误: {e}")

    def remove_skin_ui(self):
        val = input("请输入要退榜的 [排名序号]: ").strip()
        if val.isdigit():
            idx = int(val) - 1
            if 0 <= idx < len(self.active_leaderboard):
                self.active_leaderboard.pop(idx)
                self.save_data()
                self.generate_html()
                print("✅ 退榜成功")

    def modify_score_ui(self):
        try:
            idx = int(input("请输入新品榜序号: ")) - 1
            if 0 <= idx < len(self.active_leaderboard):
                self.active_leaderboard[idx]['score'] = float(input("新点数: "))
                self.save_data()
                self.generate_html()
                print("✅ 修改成功")
        except:
            print("输入错误")


# ================= 运行入口 =================
if __name__ == "__main__":
    app = SkinSystem()

    while True:
        print("\n" + "=" * 40)
        print("👑 王者荣耀榜单管理员系统 (V13.0)")
        print("1. 新品上榜")
        print("2. 皮肤退榜")
        print("3. 修改点数")
        print("4. >>> 发布到互联网 <<<")
        print("0. 退出")
        print("=" * 40)

        cmd = input("指令: ").strip()

        if cmd == '1':
            app.add_skin_ui()
        elif cmd == '2':
            app.remove_skin_ui()
        elif cmd == '3':
            app.modify_score_ui()
        elif cmd == '4':
            app.deploy_to_github()
        elif cmd == '0':
            break