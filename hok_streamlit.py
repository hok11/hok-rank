import streamlit as st
import pandas as pd
import os
import subprocess
import time
import hok_logic  # 🔥 核心：导入逻辑层，使用它的计算能力

# ================= 🚀 Streamlit 界面逻辑 =================

st.set_page_config(page_title="王者皮肤榜单管理", page_icon="👑", layout="wide")

# 初始化系统实例 (单例模式，防止刷新重置)
if 'app' not in st.session_state:
    st.session_state.app = hok_logic.SkinSystem()

app = st.session_state.app

# ----------------- 顶部导航 -----------------
tab_list = ["📊 榜单概览", "➕ 添加皮肤", "🕒 预设上线", "✏️ 数据编辑", "💎 品质管理", "🚀 发布与工具"]
t1, t2, t3, t4, t5, t6 = st.tabs(tab_list)

# ----------------- Tab 1: 榜单概览 -----------------
with t1:
    col_ctrl1, col_ctrl2 = st.columns([0.2, 0.8])
    with col_ctrl1:
        # 旋转按钮逻辑
        show_active = st.toggle("只看新品活跃榜", value=False)

    with col_ctrl2:
        if show_active:
            st.subheader("🔥 新品活跃榜 (Top 10+)")
        else:
            st.subheader("📚 完整库存 (总榜)")

    st.divider()

    if show_active:
        data_list = app.get_active_leaderboard()
        if not data_list:
            st.info("暂无上榜数据")
            data_list = []
    else:
        data_list = app.get_total_skins()

    if data_list:
        df = pd.DataFrame(data_list)
        df.index = df.index + 1  # 序号从1开始


        # 标签转换逻辑
        def get_tag(row):
            if row.get('is_discontinued'): return "绝版"
            if row.get('is_preset'): return "预设"
            if row.get('is_rerun'): return "返场"
            if row.get('is_new'): return "新品"
            return ""


        df['tag'] = df.apply(get_tag, axis=1)
        # 品质名映射
        df['quality_key'] = df['quality'].apply(lambda x: str(int(x)) if pd.notnull(x) else "")
        df['quality_name'] = df['quality_key'].map(lambda x: app.quality_config.get(x, {}).get('name', "未知"))

        # 🔥 UI配置更新：ListP->万象积分(无符号), RealP->售价
        column_config = {
            "name": st.column_config.TextColumn("皮肤名称", width="medium"),
            "quality_name": st.column_config.TextColumn("品质", width="small"),
            "quality": st.column_config.NumberColumn("品质代码", format="%d", width="small"),
            "tag": st.column_config.TextColumn("标签", width="small"),
            "growth": st.column_config.NumberColumn("涨幅%", format="%.2f", width="small"),
            "score": st.column_config.NumberColumn("排位分", format="%.1f", width="small"),
            "real_score": st.column_config.NumberColumn("实际分", format="%.1f", width="small"),
            "list_price": st.column_config.NumberColumn("万象积分", format="%d", width="small"),  # 去掉 ¥
            "real_price": st.column_config.NumberColumn("售价", format="¥%.1f", width="small"),
            "local_img": st.column_config.ImageColumn("预览", width="small")
        }

        display_cols = ['name', 'quality_name', 'quality', 'tag', 'growth', 'score', 'real_score', 'list_price',
                        'real_price']
        # 样式优化
        styled_df = df[display_cols].style.set_properties(**{'text-align': 'center'})

        st.dataframe(
            styled_df,
            column_config=column_config,
            use_container_width=True,
            height=600,
            hide_index=False
        )

# ----------------- Tab 2: 添加皮肤 -----------------
with t2:
    # 模式选择：默认品质 vs 新建品质
    q_mode = st.radio("品质来源", ["默认品质", "新建品质"], horizontal=True, label_visibility="collapsed")

    final_q_code = None
    final_list_price = 0.0

    # 获取父子级数据
    all_roots = {k: v for k, v in app.quality_config.items() if not v.get('parent')}
    all_children = {k: v for k, v in app.quality_config.items() if v.get('parent')}

    # --- 品质选择逻辑 ---
    if q_mode == "默认品质":
        col_q1, col_q2 = st.columns(2)
        root_opts = {k: f"{v['name']} ({k})" for k, v in all_roots.items()}
        sel_root = col_q1.selectbox("选择父品质", options=list(root_opts.keys()), format_func=lambda x: root_opts[x])

        my_children = {k: v for k, v in all_children.items() if str(v['parent']) == str(sel_root)}

        if my_children:
            child_opts = {sel_root: f"{all_roots[sel_root]['name']} (父级本身)"}
            for k, v in my_children.items():
                child_opts[k] = f"{v['name']} ({k})"
            sel_child = col_q2.selectbox("选择具体品质", options=list(child_opts.keys()),
                                         format_func=lambda x: child_opts[x])
            final_q_code = sel_child
        else:
            col_q2.info("该品质无子分类")
            final_q_code = sel_root

        final_list_price = app._get_list_price_by_quality(final_q_code)

    else:  # 新建品质模式
        new_sub_mode = st.radio("新建类型", ["新建子品质 (归属已有系列)", "全新独立品质"], horizontal=True)
        if new_sub_mode == "新建子品质 (归属已有系列)":
            c_new1, c_new2 = st.columns(2)
            root_opts = {k: f"{v['name']} ({k})" for k, v in all_roots.items()}
            sel_root_for_new = c_new1.selectbox("选择归属父品质", options=list(root_opts.keys()),
                                                format_func=lambda x: root_opts[x])
            with c_new2:
                st.caption(f"当前父级: {all_roots[sel_root_for_new]['name']} (代码 {sel_root_for_new})")
                siblings = [f"{v['name']}({k})" for k, v in all_children.items() if
                            str(v['parent']) == str(sel_root_for_new)]
                if siblings:
                    st.caption(f"现有子品质: {', '.join(siblings)}")
                else:
                    st.caption("暂无子品质")
            c_in1, c_in2, c_in3 = st.columns(3)
            new_q_name = c_in1.text_input("子品质名称")
            new_q_code = c_in2.text_input("子品质代号 (数字)")
            new_q_price = c_in3.number_input("所需积分", value=all_roots[sel_root_for_new]['price'])
            if new_q_name and new_q_code:
                final_q_code = new_q_code
                st.info(f"将创建: {new_q_name} (隶属 {all_roots[sel_root_for_new]['name']})")
        else:  # 全新独立
            st.caption("现有顶级品质一览:")
            st.dataframe(pd.DataFrame([{"代码": k, "名称": v['name']} for k, v in all_roots.items()]).T)
            c_in1, c_in2, c_in3 = st.columns(3)
            new_q_name = c_in1.text_input("全新名称")
            new_q_code = c_in2.text_input("全新代号")
            new_q_price = c_in3.number_input("所需积分", min_value=0.0)
            if new_q_name and new_q_code:
                final_q_code = new_q_code

    st.divider()

    # --- 核心表单区域 ---
    # 第一行：品质相关信息 + 皮肤名 + 积分参考
    # 使用 1.5, 2, 1, 1 的比例，右边留空 spacer
    c_form1, c_form2, c_form3, _ = st.columns([1.5, 2, 1, 1])

    with c_form1:
        # 如果是默认模式，这里已经选完了；如果是新建模式，这里显示确认信息
        if q_mode == "默认品质":
            st.caption("已选品质代码: " + str(final_q_code))
        else:
            st.caption("待创建品质代码: " + str(final_q_code))

    with c_form2:
        name = st.text_input("皮肤名称", placeholder="请输入皮肤名字...")

    with c_form3:
        if q_mode == "默认品质":
            st.metric("万象积分", int(final_list_price))
        else:
            st.metric("万象积分", int(new_q_price) if 'new_q_price' in locals() else 0)

    st.markdown("<br>", unsafe_allow_html=True)

    # 第二行：实价 | 涨幅 | 标签 | 上榜
    c4, c5, c6, c7 = st.columns([1, 1, 2, 1])

    real_price = c4.number_input("售价 (¥)", min_value=0.0, step=1.0)

    growth_input = c5.number_input("涨幅 (%)", value=0.0, step=0.1, help="输入 1 代表 1%")
    growth = growth_input / 100.0

    tag_option = c6.radio("标签", ["新品", "返场", "预设", "绝版"], horizontal=True)

    can_be_on_board = tag_option not in ["预设", "绝版"]
    on_board = c7.checkbox("登上新品榜", value=False, disabled=not can_be_on_board)
    if not can_be_on_board: c7.caption("🚫 默认不上榜")

    st.divider()

    # --- 底部：左操作 右榜单 ---
    col_main_left, col_main_right = st.columns([1, 1.5])

    with col_main_left:
        rank_score = None
        if on_board:
            st.info("📊 排位分设置")
            score_mode = st.radio("分数来源", ["自定义输入", "排位计算"], horizontal=True)
            if score_mode == "自定义输入":
                rank_score = st.number_input("输入排位分 (Rank Pts)", value=0.0, step=0.1)
            else:
                target_rank = st.number_input("目标排名 (1=第一名)", min_value=1, value=1)
                active_list = app.get_active_leaderboard()
                preview_score = round(app.calculate_insertion_score(target_rank, active_list, real_price, growth), 1)
                st.metric("计算结果预览", f"{preview_score} Pts")
                rank_score = preview_score
        else:
            st.caption("未勾选上榜，无需设置分数")

        st.markdown("###")
        submitted = st.button("提交保存", type="primary", use_container_width=True)

    with col_main_right:
        st.subheader("📊 当前新品榜参考 (前10名)")
        active_list_ref = app.get_active_leaderboard()
        if active_list_ref:
            ref_data = []
            for idx, item in enumerate(active_list_ref):
                ref_data.append({
                    "排名": idx + 1,
                    "皮肤": item['name'],
                    "分数": item.get('score', '--'),
                    "售价": item.get('real_price', '--')
                })
            st.dataframe(pd.DataFrame(ref_data), height=350, use_container_width=True, hide_index=True)
        else:
            st.info("暂无数据")

    # --- 提交逻辑 ---
    if submitted:
        if not name:
            st.error("请输入皮肤名称")
        elif not final_q_code:
            st.error("品质选择无效")
        else:
            # 1. 处理新建品质
            if q_mode == "新建品质":
                if final_q_code in app.quality_config:
                    st.warning("⚠️ 该品质代号已存在，将使用现有配置")
                else:
                    parent_code = sel_root_for_new if new_sub_mode == "新建子品质 (归属已有系列)" else None
                    new_cfg = {"price": new_q_price, "name": new_q_name, "parent": parent_code, "scale": 1.0,
                               "bg_color": "#ffffff"}
                    app.quality_config[final_q_code] = new_cfg
                    app.save_data()
                    st.success(f"已创建新品质: {new_q_name}")

            # 2. 准备数据
            is_new = (tag_option == "新品")
            is_rerun = (tag_option == "返场")
            is_preset = (tag_option == "预设")
            is_discontinued = (tag_option == "绝版")
            final_on_board = False if not can_be_on_board else on_board
            final_score = rank_score if final_on_board else None

            # 获取最终定价
            if q_mode == "新建品质":
                final_list_price = new_q_price
            else:
                final_list_price = app._get_list_price_by_quality(
                    float(final_q_code) if '.' in str(final_q_code) else int(final_q_code))

            new_skin = {
                "quality": float(final_q_code) if '.' in str(final_q_code) else int(final_q_code),
                "name": name,
                "is_new": is_new, "is_rerun": is_rerun,
                "is_preset": is_preset, "is_discontinued": is_discontinued,
                "on_leaderboard": final_on_board,
                "score": final_score,
                "real_score": app._calculate_real_score(final_score, final_list_price, real_price),
                "growth": growth,
                "list_price": final_list_price,
                "real_price": real_price,
                "local_img": None
            }
            app.all_skins.append(new_skin)
            app.auto_prune_leaderboard()
            app.save_data()
            st.success(f"✅ 皮肤 [{name}] 已添加！")
            time.sleep(1)
            st.rerun()

# ----------------- Tab 3: 预设上线 -----------------
with t3:
    st.header("🕒 预设皮肤上线管理")
    presets = [s for s in app.all_skins if s.get('is_preset')]
    if not presets:
        st.info("当前没有预设皮肤。")
    else:
        skin_names = [s['name'] for s in presets]
        selected_name = st.selectbox("选择预设皮肤", skin_names)
        target_skin = next((s for s in presets if s['name'] == selected_name), None)

        if target_skin:
            st.divider()
            col_preset_left, col_preset_right = st.columns([1, 1.2])
            with col_preset_left:
                c_p1, c_p2 = st.columns(2)
                new_price = c_p1.number_input("最终售价 (¥)", value=float(target_skin.get('real_price', 0)))
                new_growth_input = c_p2.number_input("涨幅 (%)", value=float(target_skin.get('growth', 0)) * 100,
                                                     step=0.1)
                new_growth = new_growth_input / 100.0

                calc_method = st.radio("分数计算方式", ["根据排名自动计算", "手动输入分数", "不上榜"])

                final_score = None
                manual_score = 0.0
                target_rank = 1
                if calc_method == "根据排名自动计算":
                    target_rank = st.number_input("目标排名", min_value=1, value=1)
                    active = app.get_active_leaderboard()
                    preview_pts = round(app.calculate_insertion_score(target_rank, active, new_price, new_growth), 1)
                    st.metric("预计排位分", f"{preview_pts} Pts")
                elif calc_method == "手动输入分数":
                    manual_score = st.number_input("输入 Rank Pts", value=0.0)

                st.markdown("###")
                if st.button("🚀 确认上线", type="primary", use_container_width=True):
                    target_skin['is_preset'] = False
                    target_skin['is_new'] = True
                    target_skin['real_price'] = new_price
                    target_skin['growth'] = new_growth
                    if calc_method == "不上榜":
                        target_skin['on_leaderboard'] = False
                        target_skin['score'] = None
                    else:
                        target_skin['on_leaderboard'] = True
                        if calc_method == "手动输入分数":
                            target_skin['score'] = manual_score
                        else:
                            active = app.get_active_leaderboard()
                            target_skin['score'] = round(
                                app.calculate_insertion_score(target_rank, active, new_price, new_growth), 1)
                    target_skin['real_score'] = app._calculate_real_score(target_skin['score'],
                                                                          target_skin['list_price'], new_price)
                    app.auto_prune_leaderboard()
                    app.save_data()
                    st.balloons()
                    st.success(f"✅ [{selected_name}] 已成功上线！")
                    time.sleep(1);
                    st.rerun()

            with col_preset_right:
                st.subheader("📊 当前新品榜参考")
                active_list_ref = app.get_active_leaderboard()
                if active_list_ref:
                    ref_data = []
                    for idx, item in enumerate(active_list_ref):
                        ref_data.append({"排名": idx + 1, "皮肤": item['name'], "分数": item.get('score', '--'),
                                         "售价": item.get('real_price', '--')})
                    st.dataframe(pd.DataFrame(ref_data), height=400, use_container_width=True, hide_index=True)
                else:
                    st.info("暂无数据")

# ----------------- Tab 4: 数据编辑 -----------------
with t4:
    st.header("✏️ 全局数据编辑器")
    st.info("💡 提示：在下方表格中直接修改数据，改完后按 Enter 确认，数据会自动保存。")
    df = pd.DataFrame(app.all_skins)
    column_config = {
        "name": st.column_config.TextColumn("皮肤名称", width="medium"),
        "quality": st.column_config.NumberColumn("品质代码", format="%d"),
        "score": st.column_config.NumberColumn("排位分", format="%.1f"),
        "real_price": st.column_config.NumberColumn("售价", format="¥%.1f"),
        "growth": st.column_config.NumberColumn("涨幅%", format="%.2f"),
        "list_price": st.column_config.NumberColumn("万象积分", format="%d"),
        "real_score": st.column_config.NumberColumn("真分", format="%.1f"),
        "is_new": st.column_config.CheckboxColumn("新品?"),
        "is_rerun": st.column_config.CheckboxColumn("返场?"),
        "is_preset": st.column_config.CheckboxColumn("预设?"),
        "is_discontinued": st.column_config.CheckboxColumn("绝版?"),
        "on_leaderboard": st.column_config.CheckboxColumn("在榜?"),
        "local_img": st.column_config.TextColumn("本地图片路径")
    }
    edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, num_rows="dynamic",
                               key="data_editor", height=800)
    if st.button("💾 保存所有修改"):
        updated_data = edited_df.to_dict(orient='records')
        app.all_skins = updated_data
        app._migrate_data_structure()
        st.success("✅ 数据已保存并重新计算！")

# ----------------- Tab 5: 品质管理 -----------------
with t5:
    st.header("💎 品质配置管理")
    q_df = pd.DataFrame.from_dict(app.quality_config, orient='index')
    q_df.index.name = 'code'
    q_df = q_df.reset_index()
    q_column_config = {
        "code": "品质代码", "name": "品质名称",
        "price": st.column_config.NumberColumn("积分/定价", format="%d"),
        "parent": "父级代码", "scale": "缩放比例", "bg_color": st.column_config.TextColumn("背景色")
    }
    st.dataframe(q_df, column_config=q_column_config, use_container_width=True)

    with st.expander("➕ 新增/修改 品质"):
        with st.form("quality_form"):
            c1, c2, c3 = st.columns(3)
            q_code = c1.text_input("代号 (如 0.81)")
            q_name = c2.text_input("名称")
            q_price = c3.number_input("万象积分", min_value=0.0)
            c4, c5 = st.columns(2)
            q_color = c4.color_picker("背景颜色", "#ffffff")
            q_parent = c5.text_input("父级代号 (可选)")
            if st.form_submit_button("保存配置"):
                app.quality_config[q_code] = {"price": q_price, "name": q_name,
                                              "parent": q_parent if q_parent else None, "scale": 1.0,
                                              "bg_color": q_color}
                app.save_data()
                app._migrate_data_structure()
                st.success("✅ 品质配置已更新")
                st.rerun()

    with st.expander("🗑️ 删除品质配置 (慎用)"):
        all_codes = list(app.quality_config.keys())
        del_targets = st.multiselect("选择要删除的品质代号", all_codes)
        if st.button("确认删除选中项", type="primary"):
            for code in del_targets:
                if code in app.quality_config:
                    del app.quality_config[code]
            app.save_data()
            st.success(f"已删除: {', '.join(del_targets)}")
            time.sleep(1)
            st.rerun()

# ----------------- Tab 6: 发布与工具 -----------------
with t6:
    st.header("🚀 部署与工具箱")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("📄 页面生成")
        if st.button("生成 index.html"):
            success, msg = app.generate_html()
            if success:
                st.success(msg)
                with open(os.path.join(hok_logic.LOCAL_REPO_PATH, "index.html"), "r", encoding="utf-8") as f:
                    st.download_button("下载 HTML 文件", f, "index.html", "text/html")
            else:
                st.error(msg)

    with col2:
        st.subheader("🕷️ 头像抓取")
        if st.button("开始爬取缺失头像"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            missing_skins = [s for s in app.all_skins if not s.get('local_img')]
            total = len(missing_skins)
            if total == 0:
                st.info("所有皮肤都有头像了！")
            else:
                for i, skin in enumerate(missing_skins):
                    status_text.text(f"正在处理: {skin['name']}...")
                    success, log = app.crawler.fetch_single_image(skin)
                    if success: print(log)
                    progress_bar.progress((i + 1) / total)
                app.save_data()
                st.success("✅ 抓取完成！")

    with col3:
        st.subheader("🌐 GitHub 发布")
        st.markdown("**Git 代理设置 (默认自动开启)**")
        proxy_port = st.text_input("代理端口", "7897")
        if 'auto_proxy_set' not in st.session_state:
            os.system(f"git config --global http.proxy http://127.0.0.1:{proxy_port}")
            os.system(f"git config --global https.proxy http://127.0.0.1:{proxy_port}")
            st.session_state.auto_proxy_set = True
            st.toast(f"⚡ 已自动挂载代理: {proxy_port}")

        c_p1, c_p2 = st.columns(2)
        if c_p1.button("手动刷新代理"):
            os.system(f"git config --global http.proxy http://127.0.0.1:{proxy_port}")
            os.system(f"git config --global https.proxy http://127.0.0.1:{proxy_port}")
            st.toast(f"已设置代理端口 {proxy_port}")
        if c_p2.button("关闭 Git 代理"):
            os.system("git config --global --unset http.proxy")
            os.system("git config --global --unset https.proxy")
            st.toast("已取消 Git 代理")

        st.divider()
        if st.button("🚀 Push 到 GitHub", type="primary"):
            os.chdir(hok_logic.LOCAL_REPO_PATH)
            with st.spinner("正在生成最新页面数据..."):
                gen_success, gen_msg = app.generate_html()
                if not gen_success:
                    st.error(f"页面生成失败，终止发布: {gen_msg}")
                    st.stop()
            try:
                try:
                    subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "add", "."], check=True)
                    subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "commit", "-m", "update via streamlit"], check=True)
                except subprocess.CalledProcessError:
                    pass
                with st.spinner("正在推送到 GitHub..."):
                    result = subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "push"], capture_output=True, text=True)
                    if result.returncode == 0:
                        st.success(f"✅ 发布成功！")
                        st.markdown(f"[点击访问页面](https://{hok_logic.GITHUB_USERNAME}.github.io/hok-rank/)")
                    else:
                        st.error("❌ 发布失败")
                        st.code(result.stderr)
            except Exception as e:
                st.error(f"执行出错: {e}")