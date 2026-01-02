import math
import json
import os
import subprocess
from datetime import datetime
from jinja2 import Template

# ================= ⚠️ 配置区域 =================
# 请确保这些路径和你电脑上的一致
LOCAL_REPO_PATH = r"D:\python-learn\hok-rank"
GIT_EXECUTABLE_PATH = r"D:\Git\bin\git.exe"
GITHUB_USERNAME = "hok11"


# ===========================================

class SkinSystem:
    def __init__(self):
        # 核心：单源存储。is_new=True 代表在新品榜，False 代表仅在总榜
        self.all_skins = []
        self.data_file = os.path.join(LOCAL_REPO_PATH, "data.json")
        self.load_data()
        # 🔥 新增：启动时立即用新算法重算所有现有数据
        self.recalculate_all_scores()

    def _get_base_score(self, x):
        """(新版算法) 理论曲线公式: y = 282/sqrt(x) - 82"""
        if x <= 0: return 200
        # 修改点：282 / 82
        val = (282 / math.sqrt(x)) - 82
        return max(val, 0)

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)

                if isinstance(loaded, list):
                    self.all_skins = loaded
                    for s in self.all_skins:
                        if 'is_new' not in s: s['is_new'] = True
                elif isinstance(loaded, dict):
                    # 兼容合并
                    self.all_skins = []
                    seen = set()
                    for s in loaded.get('new', []):
                        s['is_new'] = True
                        self.all_skins.append(s)
                        seen.add(s['name'])
                    for s in loaded.get('total', []):
                        if s['name'] not in seen:
                            s['is_new'] = False
                            self.all_skins.append(s)
                            seen.add(s['name'])

                print(f"✅ 数据加载完毕 (总库存: {len(self.all_skins)})")
            except:
                self.all_skins = []
        else:
            self.save_data()

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                # 存盘按分数排序
                self.all_skins.sort(key=lambda x: x['score'], reverse=True)
                json.dump(self.all_skins, f, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            print(f"❌ 错误：找不到路径 {LOCAL_REPO_PATH}")

    # 🔥 新增：全量数据重算函数
    def recalculate_all_scores(self):
        if not self.all_skins: return
        print("\n🔄 正在使用新算法 (282/82) 重新计算所有库存分数...")
        # 确保先按现有分数排序，确定排名
        self.all_skins.sort(key=lambda x: x['score'], reverse=True)

        for i, skin in enumerate(self.all_skins):
            rank = i + 1
            # 直接使用基础公式计算理论分
            new_score = self._get_base_score(rank)
            # 更新分数 (保留1位小数)
            old_score = skin['score']
            skin['score'] = round(new_score, 1)
            print(f"   - Rank {rank} [{skin['name']}]: {old_score} -> {skin['score']}")

        # 立即保存更新后的数据
        self.save_data()
        # 顺便刷新一下HTML
        self.generate_html()
        print("✅ 所有数据已更新完毕并保存！\n")

    # --- 视图逻辑 ---
    def get_active_skins(self):
        """新品榜：只包含 is_new=True 的皮肤"""
        data = [s for s in self.all_skins if s.get('is_new', True)]
        data.sort(key=lambda x: x['score'], reverse=True)
        return data

    def get_total_skins(self):
        """总榜：包含所有皮肤"""
        data = self.all_skins[:]
        data.sort(key=lambda x: x['score'], reverse=True)
        return data

    # --- 控制台打印 ---
    def print_console_table(self, view_type="new"):
        if view_type == "new":
            data = self.get_active_skins()
            title = f"🔥 新品榜 (Active Top 10)"
        else:
            data = self.get_total_skins()
            title = f"🏆 历史总榜 (Total History)"

        print(f"\n====== {title} ======")
        print(f"{'No.':<4} {'状态':<6} {'名字':<12} {'点数':<8} {'涨幅':<8} {'价格'}")
        print("-" * 60)

        for i, skin in enumerate(data):
            status = " [在榜]" if skin.get('is_new') else " [退榜]"
            growth_str = f"+{skin['growth']}%" if skin['growth'] > 0 else "--"
            price_str = f"¥{skin['price']}" if skin['price'] > 0 else "--"
            print(f"{i + 1:<4} {status:<6} {skin['name']:<12} {skin['score']:<8} {growth_str:<8} {price_str}")
        print("=" * 60 + "\n")

    # --- 核心算法 ---
    def calculate_insertion_score(self, rank_input, active_list, price=0, growth=0):
        # 1. 榜首算法
        if rank_input == 1:
            old_top1_score = active_list[0]['score'] if active_list else 0
            algo_1 = old_top1_score / 0.6
            # 修改点：同步更新这里的比较参数 282 / 82
            algo_2 = (282 / math.sqrt(1.25)) - 82
            algo_3 = price * growth * 15

            final_score = max(algo_1, algo_2, algo_3)
            print(f"   [算法] 榜首MAX: A({algo_1:.1f}), B({algo_2:.1f}), C({algo_3:.1f}) -> {final_score:.1f}")
            return final_score

        # 2. 插值算法
        prev_idx = rank_input - 2
        next_idx = rank_input - 1

        # 上一名分数
        if prev_idx < 0:
            prev_score = 200
        else:
            prev_score = active_list[prev_idx]['score']

        # 下一名分数
        if next_idx >= len(active_list):
            # 队尾：取 [上一名] 和 [理论公式下一名] 的几何平均
            theoretical_next = self._get_base_score(rank_input + 1)
            if theoretical_next < 0: theoretical_next = 1
            next_score = theoretical_next
        else:
            # 中间：取 [上一名] 和 [被插队的那个] 的几何平均
            next_score = active_list[next_idx]['score']

        final_score = math.sqrt(prev_score * next_score)
        print(f"   [算法] 插值计算: sqrt({prev_score:.1f} * {next_score:.1f}) = {final_score:.1f}")
        return final_score

    # --- 交互功能 ---
    def add_skin_ui(self):
        print("\n>>> 添加新皮肤")
        self.print_console_table("new")
        active_list = self.get_active_skins()

        try:
            print("格式: 品质代码 名字 [非0数字代表复刻] (提示: 无双品质代码通常为1)")
            raw = input("输入: ").split()
            if len(raw) < 2: return

            q_code = int(raw[0])
            name = raw[1]
            is_rerun = False
            if len(raw) >= 3 and raw[2] != '0': is_rerun = True

            # 询问排名
            rank_str = input(f"插入排名位置 (1-{len(active_list) + 1}): ").strip()
            if not rank_str.isdigit(): return
            rank = int(rank_str)
            if rank < 1: rank = 1
            if rank > len(active_list) + 1: rank = len(active_list) + 1

            price = 0.0
            growth = 0.0

            # 第一名强校验
            if rank == 1:
                print(">>> 🔥 榜首数据录入")
                try:
                    price = float(input("售价 (RMB): "))
                    growth = float(input("次日涨幅 (%): "))
                except:
                    price = 0;
                    growth = 0
            else:
                extra = input("选填 [涨幅 售价] (回车跳过): ").split()
                if len(extra) >= 1: growth = float(extra[0])
                if len(extra) >= 2: price = float(extra[1])

            # 计算分数
            new_score = self.calculate_insertion_score(rank, active_list, price, growth)

            # 创建对象
            new_skin = {
                "quality": q_code, "name": name, "is_rerun": is_rerun,
                "score": round(new_score, 1),
                "growth": growth, "price": price,
                "is_new": True
            }
            self.all_skins.append(new_skin)

            # 自动挤出逻辑
            current_active = self.get_active_skins()
            if len(current_active) > 10:
                last_skin = current_active[-1]
                last_skin['is_new'] = False
                print(f"\n📉 榜单已满，[{last_skin['name']}] 自动退榜 (保留在总榜)")

            self.save_data()
            self.generate_html()
            print(f"✅ 添加成功！点数: {new_score:.1f}")

        except ValueError:
            print("❌ 输入错误")

    def manage_status_ui(self):
        """手动退榜"""
        self.print_console_table("new")
        active_view = self.get_active_skins()

        try:
            idx = int(input("输入要【手动退榜】的序号: ")) - 1
            if 0 <= idx < len(active_view):
                target = active_view[idx]
                target['is_new'] = False
                self.save_data()
                self.generate_html()
                print(f"✅ {target['name']} 已退榜 (保留在总榜)")
            else:
                print("❌ 序号无效")
        except:
            pass

    def modify_data_ui(self):
        print("\n1. 修改 Active 榜")
        print("2. 修改 Total 榜")
        choice = input("选: ")
        view_type = "new" if choice == "1" else "total"
        self.print_console_table(view_type)
        target_list = self.get_active_skins() if choice == '1' else self.get_total_skins()

        try:
            idx = int(input("输入序号修改: ")) - 1
            if 0 <= idx < len(target_list):
                item = target_list[idx]
                print(f"当前: {item['name']} 分数:{item['score']}")

                s = input("新分数: ")
                if s: item['score'] = float(s)
                g = input(f"新涨幅 (原{item['growth']}): ")
                if g: item['growth'] = float(g)
                p = input(f"新价格 (原{item['price']}): ")
                if p: item['price'] = float(p)

                self.save_data()
                self.generate_html()
                print("✅ 修改成功")
        except:
            pass

    def generate_html(self):
        """生成网页：修复品质栏染色 + 无双图标放大 + UI修复"""
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

        /* 默认图标样式 */
        .quality-icon { height: 28px; width: auto; display: inline-block; mix-blend-mode: multiply; filter: contrast(1.1); transition: transform 0.2s; }

        /* 🔥 修复2：无双大图标样式 (假设无双代码为1) */
        .quality-icon.wushuang-big {
            transform: scale(1.4); /* 放大1.4倍，可自行调整 */
        }

        .song-col { display: flex; align-items: center; text-align: left; padding-left: 15px; }
        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; background-color: #eee; object-fit: cover; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .song-info { display: flex; flex-direction: column; justify-content: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; margin-bottom: 3px; }
        .artist-name { font-size: 12px; color: #666; font-weight: 500; }

        .points-col { text-align: right; font-weight: 800; padding-right: 25px; width: 80px; font-size: 16px; }

        .box-style { display: inline-block; width: 100%; padding: 6px 0; font-weight: 600; font-size: 12px; border-radius: 6px; }
        .bg-up { background-color: var(--percent-green); color: #064e3b; }
        .bg-none { background-color: #f3f4f6; color: #888; }
        .bg-price { background-color: #f3f4f6; color: #333; font-weight: 700; }

        /* 行背景色设置 */
        tbody tr:nth-child(-n+3) td { background-color: var(--row-green); }
        tr.rerun-row td { background-color: var(--row-purple); !important; }

        /* 🔥 修复1：强制前三行的“品质栏”背景为透明/白色，解决染色问题 */
        tbody tr:nth-child(-n+3) .quality-col,
        tr.rerun-row:nth-child(-n+3) .quality-col {
            background-color: #fff !important; /* 或者使用 transparent */
        }

        /* 修复卡片样式：前三行数据中的框强制白色背景 */
        tbody tr:nth-child(-n+3) .bg-up,
        tbody tr:nth-child(-n+3) .bg-price {
            background-color: #ffffff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
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
                            <img src="https://via.placeholder.com/48/{{ 'E9D5FF' if skin.is_rerun else 'DCFCE7' }}/555555?text={{ skin.name[0] }}" class="album-art">
                            <div class="song-info"><span class="song-title">{{ skin.name }}</span><span class="artist-name">{{ 'Active' if skin.is_new else 'Retired' }}</span></div>
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
        html_content = t.render(
            total_skins=self.get_total_skins(),
            update_time=datetime.now().strftime("%Y-%m-%d %H:%M")
        )

        try:
            with open(os.path.join(LOCAL_REPO_PATH, "index.html"), "w", encoding='utf-8') as f:
                f.write(html_content)
            print("📄 网页文件已更新 (修复染色 + 无双放大)")
        except FileNotFoundError:
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
    # 程序启动时会自动加载数据并重算分数
    app = SkinSystem()
    while True:
        print("\n" + "=" * 45)
        print("👑 王者荣耀榜单 V19.2 (自动重算+UI修复)")
        print(f"📊 当前库存 {len(app.all_skins)}")
        print("-" * 45)
        print("1. 添加皮肤 (自动插值)")
        print("2. 修改数据")
        print("3. 手动退榜")
        print("4. >>> 发布到互联网 <<<")
        print("5. 强制刷新HTML (不改数据)")
        print("6. 查看榜单")
        print("0. 退出")
        print("=" * 45)
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
            app.print_console_table("total")
        elif cmd == '0':
            break