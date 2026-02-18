import streamlit as st
import pandas as pd
import os
import subprocess
import time
import hok_logic  # 🔥 核心：导入逻辑层

# ================= 🚀 Streamlit 界面逻辑 =================

st.set_page_config(page_title="王者皮肤榜单管理", page_icon="👑", layout="wide")

# 初始化系统实例
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
        # 默认只看非隐藏的
        show_active = st.toggle("只看新品活跃榜 (非隐藏)", value=True)
    with col_ctrl2:
        if show_active:
            st.subheader("🔥 新品活跃榜 (按销售额排序)")
        else:
            st.subheader("📚 完整库存 (按销售额排序)")
    st.divider()

    # 获取数据 (逻辑层已经按销售额排好序了)
    if show_active:
        data_list = app.get_active_leaderboard()
    else:
        data_list = app.get_total_skins()

    if not data_list:
        st.info("暂无数据")
    else:
        df = pd.DataFrame(data_list)
        df.index = df.index + 1  # 序号从1开始


        # 标签展示处理
        def get_tag(row):
            if row.get('is_hidden'): return "🚫隐藏"
            if row.get('is_pool'): return "🎲祈愿池"
            if row.get('is_discontinued'): return "绝版"
            if row.get('is_preset'): return "预设"
            if row.get('is_rerun'): return "返场"
            if row.get('is_new'): return "新品"
            return ""


        df['tag'] = df.apply(get_tag, axis=1)
        df['quality_key'] = df['quality'].apply(lambda x: str(int(x)) if pd.notnull(x) else "")
        df['quality_name'] = df['quality_key'].map(lambda x: app.quality_config.get(x, {}).get('name', "未知"))

        # 🔥 UI配置
        column_config = {
            "name": st.column_config.TextColumn("皮肤名称", width="medium"),
            "quality_name": st.column_config.TextColumn("品质", width="small"),
            "quality": st.column_config.NumberColumn("代码", format="%g", width="small"),
            "tag": st.column_config.TextColumn("标签", width="small"),
            "growth": st.column_config.NumberColumn("涨幅%", format="%.2f", width="small"),
            "list_price": st.column_config.NumberColumn("万象积分", format="%d", width="small"),
            "real_price": st.column_config.TextColumn("售价", width="small"),  # 文本
            "sales_volume": st.column_config.TextColumn("销量", width="small"),  # 文本
            "revenue": st.column_config.TextColumn("销售额", width="small"),  # 文本
            "local_img": st.column_config.ImageColumn("预览", width="small")
        }

        # 移除 RankPts 和 RealPts，只保留营收数据
        display_cols = ['name', 'quality_name', 'quality', 'tag', 'sales_volume', 'revenue', 'growth', 'list_price',
                        'real_price', 'local_img']

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
    # 模式选择
    q_mode = st.radio("品质来源", ["默认品质", "新建品质"], horizontal=True, label_visibility="collapsed")
    final_q_code = None;
    final_list_price = 0.0
    all_roots = {k: v for k, v in app.quality_config.items() if not v.get('parent')}
    all_children = {k: v for k, v in app.quality_config.items() if v.get('parent')}

    # --- 品质选择逻辑 (保持不变) ---
    if q_mode == "默认品质":
        col_q1, col_q2 = st.columns(2)
        root_opts = {k: f"{v['name']} ({k})" for k, v in all_roots.items()}
        sel_root = col_q1.selectbox("选择父品质", options=list(root_opts.keys()), format_func=lambda x: root_opts[x])
        my_children = {k: v for k, v in all_children.items() if str(v['parent']) == str(sel_root)}
        if my_children:
            child_opts = {sel_root: f"{all_roots[sel_root]['name']} (父级本身)"}
            for k, v in my_children.items(): child_opts[k] = f"{v['name']} ({k})"
            sel_child = col_q2.selectbox("选择具体品质", options=list(child_opts.keys()),
                                         format_func=lambda x: child_opts[x])
            final_q_code = sel_child
        else:
            col_q2.info("该品质无子分类")
            final_q_code = sel_root
        final_list_price = app._get_list_price_by_quality(final_q_code)
    else:
        new_sub_mode = st.radio("新建类型", ["新建子品质", "全新独立品质"], horizontal=True)
        if new_sub_mode == "新建子品质":
            c_new1, c_new2 = st.columns(2)
            root_opts = {k: f"{v['name']} ({k})" for k, v in all_roots.items()}
            sel_root_for_new = c_new1.selectbox("选择归属父品质", options=list(root_opts.keys()),
                                                format_func=lambda x: root_opts[x])
            with c_new2:
                st.caption(f"当前父级: {all_roots[sel_root_for_new]['name']}")
            c_in1, c_in2, c_in3 = st.columns(3)
            new_q_name = c_in1.text_input("子品质名称")
            new_q_code = c_in2.text_input("子品质代号")
            new_q_price = c_in3.number_input("积分", value=all_roots[sel_root_for_new]['price'])
            if new_q_name and new_q_code: final_q_code = new_q_code
        else:
            c_in1, c_in2, c_in3 = st.columns(3)
            new_q_name = c_in1.text_input("全新名称")
            new_q_code = c_in2.text_input("全新代号")
            new_q_price = c_in3.number_input("积分", min_value=0.0)
            if new_q_name and new_q_code: final_q_code = new_q_code

    st.divider()

    # --- 基本信息 ---
    c1, c2, c3, _ = st.columns([1.5, 2, 1, 1])
    with c1:
        st.caption(f"品质代码: {final_q_code}")
    name = c2.text_input("皮肤名称", placeholder="请输入...")
    with c3:
        if q_mode == "默认品质":
            st.metric("万象积分", int(final_list_price))
        else:
            st.metric("万象积分", int(new_q_price) if 'new_q_price' in locals() else 0)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 核心数据 (售价/销量/销售额) ---
    c4, c5, c6, c7 = st.columns([1, 1, 1.5, 1])

    real_price = c4.text_input("售价 (支持文本)", value="0", key="add_real_price")
    growth_input = c5.number_input("涨幅 (%)", value=0.0, step=0.1, key="add_growth")
    growth = growth_input / 100.0

    tag_option = c6.radio("标签", ["新品", "返场", "预设", "绝版"], horizontal=True)

    # 隐藏逻辑
    can_be_on_board = tag_option not in ["预设", "绝版"]
    on_board = c7.checkbox("登上新品榜", value=False, disabled=not can_be_on_board, key="add_on_board")

    # 祈愿池标记
    is_pool = c7.checkbox("设为祈愿池", value=False, help="勾选后不显示新品/返场等角标，显示'祈愿池'", key="add_is_pool")

    st.divider()

    # --- 销量计算与提交区 ---
    col_main_left, col_main_right = st.columns([1, 1.5])

    with col_main_left:
        sales_vol = st.text_input("销量", value="0", key="add_sales_vol")

        # 销售额录入模式
        st.markdown("**销售额设置**")
        rev_mode = st.radio("模式", ["直接输入/计算", "锚定范围 (A~B)", "锚定单品 (>A)"], horizontal=True,
                            label_visibility="collapsed", key="add_rev_mode")

        revenue_final = "0"

        if rev_mode == "直接输入/计算":
            revenue_final = st.text_input("销售额 (可中文/英文)", value="0", key="add_revenue_direct")
            if st.button("🔄 自动计算 (售价 × 销量)", key="add_calc_btn"):
                p_val = app.parse_revenue_str(real_price)
                v_val = app.parse_revenue_str(sales_vol)
                if p_val > 0 and v_val > 0:
                    rev_val = p_val * v_val
                    # 🔥 改动：英文单位格式化
                    if rev_val >= 100000000:
                        revenue_final = f"{rev_val / 100000000:.2f}B"  # 1亿 = 1B (根据你的逻辑)
                    elif rev_val >= 1000000:
                        revenue_final = f"{rev_val / 1000000:.2f}M"
                    elif rev_val >= 1000:
                        revenue_final = f"{rev_val / 1000:.2f}K"
                    else:
                        revenue_final = str(int(rev_val))
                    st.info(f"计算结果: {revenue_final}")
                else:
                    st.warning("无法解析数字，请检查输入格式")

        elif rev_mode == "锚定范围 (A~B)":
            all_opts = [s['name'] for s in app.all_skins]
            ca, cb = st.columns(2)
            sa = ca.selectbox("下限皮肤", all_opts, index=0 if all_opts else 0, key="add_a")
            sb = cb.selectbox("上限皮肤", all_opts, index=1 if len(all_opts) > 1 else 0, key="add_b")

            val_a = next((s['revenue'] for s in app.all_skins if s['name'] == sa), "0")
            val_b = next((s['revenue'] for s in app.all_skins if s['name'] == sb), "0")

            revenue_final = f"{val_a}~{val_b}"
            st.info(f"生成锚定: {revenue_final}")

        elif rev_mode == "锚定单品 (>A)":
            all_opts = [s['name'] for s in app.all_skins]
            ct, co = st.columns(2)
            starget = ct.selectbox("参照皮肤", all_opts, key="add_t")
            sop = co.radio("关系", [">", "<", "≈"], horizontal=True, key="add_o")

            val_t = next((s['revenue'] for s in app.all_skins if s['name'] == starget), "0")
            revenue_final = f"{sop}{val_t}"
            st.info(f"生成锚定: {revenue_final}")

        st.markdown("###")
        is_hidden_default = st.checkbox("默认隐藏", value=False, key="add_hidden")
        submitted = st.button("提交保存", type="primary", use_container_width=True, key="add_submit")

    with col_main_right:
        st.subheader("📊 参考榜单 (前10)")
        active = app.get_active_leaderboard()
        if active:
            # 只展示营收数据作为参考
            ref_df = pd.DataFrame(active)[['name', 'revenue', 'real_price']]
            st.dataframe(ref_df, height=350, use_container_width=True, hide_index=True)
        else:
            st.info("暂无数据")

    if submitted:
        if not name:
            st.error("请输入名称")
        elif not final_q_code:
            st.error("品质无效")
        else:
            if q_mode == "新建品质":
                if final_q_code not in app.quality_config:
                    p_code = sel_root_for_new if new_sub_mode == "新建子品质" else None
                    new_cfg = {"price": new_q_price, "name": new_q_name, "parent": p_code, "scale": 1.0,
                               "bg_color": "#ffffff"}
                    app.quality_config[final_q_code] = new_cfg
                    app.save_data()

            is_new = (tag_option == "新品")
            is_rerun = (tag_option == "返场")
            is_preset = (tag_option == "预设")
            is_discontinued = (tag_option == "绝版")
            final_on_board = False if not can_be_on_board else on_board

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
                "growth": growth,
                "list_price": final_list_price,
                "real_price": real_price,
                "sales_volume": sales_vol,
                "revenue": revenue_final,  # 使用计算后的值
                "is_hidden": is_hidden_default,
                "is_pool": is_pool,
                "local_img": None
            }
            app.all_skins.append(new_skin)
            app.auto_prune_leaderboard()
            app.save_data()
            st.success(f"✅ [{name}] 已添加！");
            time.sleep(1);
            st.rerun()

# ----------------- Tab 3: 预设上线 -----------------
with t3:
    st.header("🕒 预设皮肤上线")
    presets = [s for s in app.all_skins if s.get('is_preset')]
    if not presets:
        st.info("无预设")
    else:
        skin_names = [s['name'] for s in presets]
        selected_name = st.selectbox("选择皮肤", skin_names, key="preset_select")
        target_skin = next((s for s in presets if s['name'] == selected_name), None)

        if target_skin:
            c1, c2 = st.columns(2)
            new_price = c1.text_input("最终售价", value=str(target_skin.get('real_price', '0')), key="preset_price")
            new_growth_in = c2.number_input("涨幅%", value=float(target_skin.get('growth', 0)) * 100,
                                            key="preset_growth")
            new_growth = new_growth_in / 100.0

            c3, c4 = st.columns(2)
            new_sales = c3.text_input("销量", value="0", key="preset_sales")

            # 销售额处理 (支持锚定)
            with c4:
                rev_mode_p = st.radio("销售额", ["直接", "锚定"], horizontal=True, label_visibility="collapsed",
                                      key="preset_rev_mode")
                new_revenue = "0"
                if rev_mode_p == "直接":
                    new_revenue = st.text_input("数值", value="0", label_visibility="collapsed", key="preset_rev_val")
                else:
                    # 简化锚定，只提供单品
                    all_opts = [s['name'] for s in app.all_skins]
                    starget = st.selectbox("参照", all_opts, key="pre_t")
                    sop = st.radio("op", [">", "<"], horizontal=True, key="pre_o", label_visibility="collapsed")
                    val_t = next((s['revenue'] for s in app.all_skins if s['name'] == starget), "0")
                    new_revenue = f"{sop}{val_t}"
                    st.caption(f"预览: {new_revenue}")

            on_board = st.checkbox("上线并加入榜单", value=True, key="preset_onboard")

            if st.button("🚀 确认上线", type="primary", key="preset_submit"):
                target_skin['is_preset'] = False
                target_skin['is_new'] = True
                target_skin['real_price'] = new_price
                target_skin['growth'] = new_growth
                target_skin['sales_volume'] = new_sales
                target_skin['revenue'] = new_revenue
                target_skin['on_leaderboard'] = on_board
                target_skin['is_hidden'] = False

                app.auto_prune_leaderboard()
                app.save_data()
                st.success("上线成功！");
                time.sleep(1);
                st.rerun()

# ----------------- Tab 4: 数据编辑 -----------------
with t4:
    st.header("✏️ 全局数据编辑器")

    # 🔥 功能：单个皮肤锚定修改
    with st.expander("🛠️ 单个皮肤锚定修改 (设置 >A, A~B 等)", expanded=True):
        col_edit1, col_edit2 = st.columns(2)
        all_skin_names = [s['name'] for s in app.all_skins]

        edit_target_name = col_edit1.selectbox("选择要修改的皮肤", all_skin_names, key="edit_target_select")
        edit_target_skin = next((s for s in app.all_skins if s['name'] == edit_target_name), None)

        if edit_target_skin:
            col_edit2.info(f"当前销售额: **{edit_target_skin.get('revenue', '0')}**")

            edit_rev_mode = st.radio("修改模式", ["直接输入", "锚定范围 (A~B)", "锚定单品 (>A)"], horizontal=True,
                                     key="edit_rev_mode_select")
            final_edit_rev = edit_target_skin.get('revenue', '0')

            if edit_rev_mode == "直接输入":
                final_edit_rev = st.text_input("新销售额", value=final_edit_rev, key="edit_rev_direct")

            elif edit_rev_mode == "锚定范围 (A~B)":
                ce_a, ce_b = st.columns(2)
                sa = ce_a.selectbox("下限皮肤", all_skin_names, key="edit_anchor_a")
                sb = ce_b.selectbox("上限皮肤", all_skin_names, key="edit_anchor_b")
                va = next((s['revenue'] for s in app.all_skins if s['name'] == sa), "?")
                vb = next((s['revenue'] for s in app.all_skins if s['name'] == sb), "?")
                final_edit_rev = f"{va}~{vb}"
                st.info(f"预览: {final_edit_rev}")

            elif edit_rev_mode == "锚定单品 (>A)":
                ce_t, ce_o = st.columns(2)
                stgt = ce_t.selectbox("对象", all_skin_names, key="edit_anchor_t")
                sop = ce_o.radio("关系", [">", "<"], horizontal=True, key="edit_anchor_op")
                vt = next((s['revenue'] for s in app.all_skins if s['name'] == stgt), "?")
                final_edit_rev = f"{sop}{vt}"
                st.info(f"预览: {final_edit_rev}")

            if st.button(f"💾 更新 [{edit_target_name}] 销售额", type="primary", key="edit_save_btn"):
                edit_target_skin['revenue'] = final_edit_rev
                app.auto_prune_leaderboard()
                app.save_data()
                st.success("更新成功！")
                time.sleep(0.5)
                st.rerun()

    st.markdown("---")
    st.info("💡 提示：勾选 '隐藏' 可在网站隐藏该皮肤。如需删除，请选中行左侧勾选框后按 Delete。")

    df = pd.DataFrame(app.all_skins)
    # 🔥 关键修改：自定义列顺序 (销量/销售额提前)
    column_order = [
        "name",  # 1. 皮肤名称
        "sales_volume",  # 2. 销量 (提前)
        "revenue",  # 3. 销售额 (提前)
        "real_price",  # 4. 售价 (提前)
        "growth",  # 5. 涨幅 (提前)
        "quality",  # 6. 品质代码
        "list_price",  # 7. 积分
        "is_hidden",  # 8. 隐藏
        "on_leaderboard",
        "is_pool",
        "is_discontinued",
        "is_preset",
        "local_img"
    ]

    column_config = {
        "name": st.column_config.TextColumn("皮肤名称", width="medium"),
        "quality": st.column_config.NumberColumn("品质代码", format="%g"),
        "list_price": st.column_config.NumberColumn("积分", disabled=True),
        "real_price": "售价",
        "sales_volume": "销量",
        "revenue": "销售额",
        "growth": st.column_config.NumberColumn("涨幅%", format="%.2f"),
        "is_hidden": st.column_config.CheckboxColumn("隐藏?", help="勾选后在网站不显示"),
        "is_pool": st.column_config.CheckboxColumn("祈愿池?"),
        "on_leaderboard": st.column_config.CheckboxColumn("在榜?"),
        "is_discontinued": "绝版?",
        "is_preset": "预设?"
    }

    edited_df = st.data_editor(
        df,
        column_config=column_config,
        column_order=column_order,  # 应用列顺序
        use_container_width=True,
        num_rows="dynamic",
        key="data_editor",
        height=800
    )

    # 🔥 核心功能：批量保存时自动计算 (英文单位支持)
    col_save, col_opt = st.columns([1, 3])
    with col_opt:
        auto_calc = st.checkbox("💾 保存时自动刷新销售额 (当售价和销量均有效时覆盖)", value=True)

    if col_save.button("💾 保存所有修改"):
        updated_data = edited_df.to_dict(orient='records')

        # 自动计算逻辑
        if auto_calc:
            calc_count = 0
            for item in updated_data:
                try:
                    # 解析
                    p_val = app.parse_revenue_str(item.get('real_price', '0'))
                    v_val = app.parse_revenue_str(item.get('sales_volume', '0'))

                    # 只有当两个都大于0时才重算
                    if p_val > 0 and v_val > 0:
                        rev_val = p_val * v_val
                        # 格式化 (英文单位)
                        if rev_val >= 100000000:
                            item['revenue'] = f"{rev_val / 100000000:.2f}B"
                        elif rev_val >= 1000000:
                            item['revenue'] = f"{rev_val / 1000000:.2f}M"
                        elif rev_val >= 1000:
                            item['revenue'] = f"{rev_val / 1000:.2f}K"
                        else:
                            item['revenue'] = str(int(rev_val))
                        calc_count += 1
                except:
                    pass
            if calc_count > 0:
                st.toast(f"已自动重算 {calc_count} 条数据的销售额")

        app.all_skins = updated_data
        app._migrate_data_structure()
        st.success("✅ 保存成功！")

# ----------------- Tab 5 & 6 (保持不变) -----------------
with t5:
    st.header("💎 品质配置");
    st.dataframe(pd.DataFrame.from_dict(app.quality_config, orient='index'))
    with st.expander("➕ 新增/修改"):
        with st.form("q_add"):
            c1, c2, c3 = st.columns(3);
            qc = c1.text_input("代号");
            qn = c2.text_input("名称");
            qp = c3.number_input("积分", 0.0)
            c4, c5 = st.columns(2);
            qcol = c4.color_picker("颜色");
            qpar = c5.text_input("父级")
            if st.form_submit_button("保存"):
                app.quality_config[qc] = {"price": qp, "name": qn, "parent": qpar, "scale": 1.0, "bg_color": qcol}
                app.save_data();
                st.rerun()
    with st.expander("🗑️ 删除"):
        dels = st.multiselect("选择删除", list(app.quality_config.keys()))
        if st.button("确认删除"):
            for d in dels: del app.quality_config[d]
            app.save_data();
            st.rerun()

with t6:
    st.header("🚀 发布工具")

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 生成 HTML"):
            s, m = app.generate_html()
            if s:
                st.success(m)
            else:
                st.error(m)

    with col3:
        st.markdown("**Git 代理**")
        port = st.text_input("端口", "7897")
        if 'auto_proxy' not in st.session_state:
            os.system(f"git config --global http.proxy http://127.0.0.1:{port}")
            st.session_state.auto_proxy = True

        if st.button("🚀 Push GitHub"):
            os.chdir(hok_logic.LOCAL_REPO_PATH)
            app.generate_html()
            try:
                try:
                    subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "add", "."], check=True)
                    subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "commit", "-m", "update"], check=True)
                except:
                    pass
                subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "push"])
                st.success("发布成功")
            except Exception as e:
                st.error(f"Error: {e}")