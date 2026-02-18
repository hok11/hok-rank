import streamlit as st
import pandas as pd
import os
import subprocess
import time
import math
import hok_logic  # 🔥 核心：导入逻辑层

# ================= 🚀 Streamlit 界面逻辑 =================

st.set_page_config(page_title="王者皮肤榜单管理", page_icon="👑", layout="wide")

# 初始化系统实例
if 'app' not in st.session_state:
    st.session_state.app = hok_logic.SkinSystem()

app = st.session_state.app


# --- 🛠️ 强制英文单位格式化工具 (K/M/B) ---
def format_to_english_unit(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "0"
    try:
        f_val = float(val)
        if f_val >= 1000000000:
            return f"{f_val / 1000000000:.2f}B"
        elif f_val >= 1000000:
            return f"{f_val / 1000000:.2f}M"
        elif f_val >= 1000:
            return f"{f_val / 1000:.2f}K"
        else:
            return str(int(f_val)) if f_val.is_integer() else str(round(f_val, 2))
    except:
        return str(val)


# ----------------- 顶部导航 -----------------
tab_list = ["📊 概览", "➕ 添加", "🕒 预设", "✏️ 编辑", "💎 品质", "🚀 发布"]
t1, t2, t3, t4, t5, t6 = st.tabs(tab_list)

# ----------------- Tab 1: 概览 -----------------
with t1:
    col_ctrl1, col_ctrl2 = st.columns([0.2, 0.8])
    with col_ctrl1:
        show_active = st.toggle("只看活跃皮肤", value=True)
    with col_ctrl2:
        st.subheader("🔥 实时皮肤榜单概览" if show_active else "📚 完整皮肤库存")
    st.divider()

    data_list = app.get_active_leaderboard() if show_active else app.get_total_skins()

    if not data_list:
        st.info("暂无数据")
    else:
        df = pd.DataFrame(data_list)
        df.index = df.index + 1


        def get_tag(row):
            if row.get('is_hidden'): return "🚫隐藏"
            if row.get('is_pool'): return "🎲祈愿"
            if row.get('is_discontinued'): return "💀绝版"
            if row.get('is_preset'): return "🕒预设"
            if row.get('is_rerun'): return "🔵返场"
            if row.get('is_new'): return "🟡新品"
            return ""


        df['tag'] = df.apply(get_tag, axis=1)
        df['quality_name'] = df['quality'].apply(
            lambda x: app.quality_config.get(str(int(x)) if isinstance(x, (int, float)) else str(x), {}).get('name',
                                                                                                             "未知"))

        column_config = {
            "name": st.column_config.TextColumn("皮肤名称", width="medium"),
            "quality_name": st.column_config.TextColumn("品质", width="small"),
            "tag": st.column_config.TextColumn("标签", width="small"),
            "growth": st.column_config.NumberColumn("涨幅%", format="%.1f"),
            "revenue": st.column_config.TextColumn("销售额"),
            "sales_volume": st.column_config.TextColumn("销量"),
            "local_img": st.column_config.ImageColumn("预览")
        }
        display_cols = ['name', 'quality_name', 'tag', 'sales_volume', 'revenue', 'growth', 'real_price', 'local_img']
        st.dataframe(df[display_cols], column_config=column_config, use_container_width=True, height=600)

# ----------------- Tab 2: 添加皮肤 -----------------
with t2:
    q_mode = st.radio("品质来源", ["默认品质", "新建品质"], horizontal=True, label_visibility="collapsed")
    final_q_code = None
    final_list_price = 0.0
    all_roots = {k: v for k, v in app.quality_config.items() if not v.get('parent')}
    all_children = {k: v for k, v in app.quality_config.items() if v.get('parent')}

    # 品质选择逻辑
    if q_mode == "默认品质":
        c_q1, c_q2 = st.columns(2)
        root_opts = {k: f"{v['name']} ({k})" for k, v in all_roots.items()}
        sel_root = c_q1.selectbox("选择父品质", options=list(root_opts.keys()), format_func=lambda x: root_opts[x])
        my_children = {k: v for k, v in app.quality_config.items() if str(v.get('parent')) == str(sel_root)}

        if my_children:
            child_opts = {sel_root: f"{all_roots[sel_root]['name']} (父级)"}
            for k, v in my_children.items(): child_opts[k] = f"{v['name']} ({k})"
            final_q_code = c_q2.selectbox("具体品质", options=list(child_opts.keys()),
                                          format_func=lambda x: child_opts[x])
        else:
            final_q_code = sel_root
        final_list_price = app._get_list_price_by_quality(final_q_code)
    else:
        c_in1, c_in2, c_in3 = st.columns(3)
        new_q_name = c_in1.text_input("子品质名称")
        new_q_code = c_in2.text_input("代码")
        new_q_price = c_in3.number_input("万象积分", value=100.0)
        final_q_code = new_q_code
        final_list_price = new_q_price

    st.divider()
    c1, c2, c3 = st.columns([1.5, 2, 1])
    name = c2.text_input("皮肤名称", placeholder="如：英雄-皮肤名")
    with c3:
        st.metric("积分参考", int(final_list_price))

    c4, c5, c6, c7 = st.columns([1, 1, 1.5, 1])
    real_price = c4.text_input("售价", value="0", key="add_p")
    growth = c5.number_input("涨幅%", value=0.0, step=0.1, key="add_g")
    tag_option = c6.radio("标签", ["新品", "返场", "预设", "绝版", "祈愿"], horizontal=True)
    on_board = c7.checkbox("登上活跃榜", value=tag_option in ["新品", "返场", "祈愿"])

    st.divider()
    col_l, col_r = st.columns([1, 1.5])
    with col_l:
        sales_vol = st.text_input("销量", value="0", key="add_v")
        st.markdown("**销售额 (营收)**")
        # 🔥 恢复：锚定模式选择
        rev_mode = st.radio("录入模式", ["计算", "手动", "锚定"], horizontal=True, label_visibility="collapsed")

        final_rev = "0"
        if rev_mode == "计算":
            if st.button("🔄 自动计算 (转为K/M/B)"):
                p = app.parse_revenue_str(real_price)
                v = app.parse_revenue_str(sales_vol)
                if p > 0 and v > 0:
                    final_rev = format_to_english_unit(p * v)
                    st.success(f"计算结果: {final_rev}")
                else:
                    st.warning("无效数据")
        elif rev_mode == "手动":
            final_rev = st.text_input("直接输入数值", value="0")
        else:
            # 🔥 恢复：添加页面的锚定功能
            all_names = [s['name'] for s in app.all_skins]
            c_link1, c_link2 = st.columns(2)
            starget = c_link1.selectbox("参照皮肤", all_names)
            sop = c_link2.radio("关系", [">", "<", "≈"], horizontal=True)
            vt = next((s['revenue'] for s in app.all_skins if s['name'] == starget), "0")
            final_rev = f"{sop}{vt}"
            st.info(f"生成锚定: {final_rev}")

        if st.button("💾 确认添加皮肤", type="primary", use_container_width=True):
            if not name:
                st.error("请输入名称")
            else:
                new_skin = {
                    "quality": float(final_q_code) if '.' in str(final_q_code) else int(final_q_code),
                    "name": name, "is_new": (tag_option == "新品"), "is_rerun": (tag_option == "返场"),
                    "is_preset": (tag_option == "预设"), "is_discontinued": (tag_option == "绝版"),
                    "is_pool": (tag_option == "祈愿"),
                    "on_leaderboard": on_board, "growth": growth, "list_price": final_list_price,
                    "real_price": real_price, "sales_volume": sales_vol, "revenue": final_rev, "is_hidden": False,
                    "local_img": None
                }
                app.all_skins.append(new_skin)
                app.save_data()
                st.success("添加成功！")
                time.sleep(0.5)
                st.rerun()
    with col_r:
        st.caption("活跃榜参考")
        st.dataframe(pd.DataFrame(app.get_active_leaderboard())[['name', 'revenue']].head(10), use_container_width=True)

# ----------------- Tab 3: 预设上线 -----------------
with t3:
    st.subheader("🕒 预设转正上线")
    presets = [s for s in app.all_skins if s.get('is_preset')]
    if not presets:
        st.info("无预设")
    else:
        skin_names = [s['name'] for s in presets]
        selected_name = st.selectbox("选择要上线的皮肤", [s['name'] for s in presets])
        target = next((s for s in presets if s['name'] == selected_name), None)
        if target:
            c1, c2, c3 = st.columns(3)
            p_price = c1.text_input("最终售价", value=str(target.get('real_price', '0')))
            p_sales = c2.text_input("正式销量", value="0")
            p_growth = c3.number_input("初始涨幅%", value=float(target.get('growth', 0)))

            # 🔥 恢复：预设页面的锚定功能
            st.markdown("**销售额**")
            c4, c5 = st.columns([1, 2])
            rev_mode_p = c4.radio("方式", ["计算", "锚定"], horizontal=True, label_visibility="collapsed")

            final_p_rev = "0"
            if rev_mode_p == "计算":
                if c5.button("自动计算"):
                    v_p = app.parse_revenue_str(p_price)
                    v_s = app.parse_revenue_str(p_sales)
                    final_p_rev = format_to_english_unit(v_p * v_s)
                    st.success(f"{final_p_rev}")
                else:
                    final_p_rev = c5.text_input("或手动输入", value="0")
            else:
                all_names = [s['name'] for s in app.all_skins]
                starget = c5.selectbox("参照", all_names, key="pre_t")
                sop = c5.radio("op", [">", "<"], horizontal=True, key="pre_o")
                vt = next((s['revenue'] for s in app.all_skins if s['name'] == starget), "0")
                final_p_rev = f"{sop}{vt}"
                st.info(f"锚定: {final_p_rev}")

            if st.button("🚀 确认发布上线", type="primary"):
                target['is_preset'] = False;
                target['is_new'] = True;
                target['is_hidden'] = False
                target['real_price'] = p_price;
                target['sales_volume'] = p_sales;
                target['growth'] = p_growth
                target['revenue'] = final_p_rev
                app.save_data()
                st.success("已发布！")
                time.sleep(0.5)
                st.rerun()

# ----------------- Tab 4: 数据编辑 -----------------
with t4:
    st.header("✏️ 全局数据编辑器")

    # 🔥 恢复：【单个皮肤锚定修改】功能块
    with st.expander("🛠️ 单个皮肤锚定修改 (推荐用于调整排名)", expanded=True):
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
                app.auto_prune_leaderboard()  # 重新排序
                app.save_data()
                st.success("更新成功！")
                time.sleep(0.5)
                st.rerun()

    st.divider()
    st.info("💡 提示：勾选 '隐藏' 可在网站隐藏该皮肤。如需删除，选中行左侧勾选框后按 Delete。")

    df_edit = pd.DataFrame(app.all_skins)


    def get_tag_label(row):
        if row.get('is_pool'): return "祈愿"
        if row.get('is_discontinued'): return "绝版"
        if row.get('is_preset'): return "预设"
        if row.get('is_rerun'): return "返场"
        if row.get('is_new'): return "新品"
        return "无"


    df_edit['badge_label'] = df_edit.apply(get_tag_label, axis=1)

    column_order = ["name", "sales_volume", "revenue", "real_price", "growth", "badge_label", "quality", "list_price",
                    "is_hidden"]
    config = {
        "name": st.column_config.TextColumn("名称", width="medium"),
        "badge_label": st.column_config.SelectboxColumn("角标", options=["无", "新品", "返场", "预设", "绝版", "祈愿"],
                                                        width="small"),
        "quality": st.column_config.NumberColumn("代码", format="%g"),
        "list_price": st.column_config.NumberColumn("积分", disabled=True),
        "growth": st.column_config.NumberColumn("涨幅%", format="%.1f"),
        "is_hidden": st.column_config.CheckboxColumn("隐藏?")
    }

    edited_df = st.data_editor(df_edit, column_config=config, column_order=column_order, use_container_width=True,
                               num_rows="dynamic", height=700)

    c_s1, c_s2 = st.columns([1, 4])
    do_clean = c_s2.checkbox("🧹 强制格式化：将所有数据重洗为 K/M/B (去除中文单位)", value=True)

    if c_s1.button("💾 保存并执行操作"):
        updated = edited_df.to_dict(orient='records')
        recalc_count = 0
        for item in updated:
            tag = item.get('badge_label', "无")
            item['is_pool'] = (tag == "祈愿");
            item['is_discontinued'] = (tag == "绝版")
            item['is_preset'] = (tag == "预设");
            item['is_rerun'] = (tag == "返场");
            item['is_new'] = (tag == "新品")
            if 'badge_label' in item: del item['badge_label']

            if do_clean:
                try:
                    val_p = app.parse_revenue_str(item.get('real_price', '0'))
                    val_v = app.parse_revenue_str(item.get('sales_volume', '0'))

                    if val_v > 0:
                        item['sales_volume'] = format_to_english_unit(val_v)

                    current_rev = str(item.get('revenue', ''))
                    # 仅当非锚定数据时才自动重算覆盖
                    if val_p > 0 and val_v > 0 and not ('>' in current_rev or '~' in current_rev or '<' in current_rev):
                        item['revenue'] = format_to_english_unit(val_p * val_v)
                        recalc_count += 1
                except:
                    pass

        app.all_skins = updated
        app._migrate_data_structure()
        st.success(f"✅ 保存完成！已重洗格式化 {recalc_count} 条营收数据。")

# ----------------- Tab 5: 品质管理 -----------------
with t5:
    st.header("💎 品质配置")
    q_df = pd.DataFrame.from_dict(app.quality_config, orient='index')
    q_df.index.name = 'code'
    q_df = q_df.reset_index()
    st.dataframe(q_df, use_container_width=True)
    with st.expander("➕ 新增/修改"):
        with st.form("q_add"):
            c1, c2, c3 = st.columns(3);
            qc = c1.text_input("代号");
            qn = c2.text_input("品质名");
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

# ----------------- Tab 6: 发布 -----------------
with t6:
    st.header("🚀 发布工具")
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 生成 HTML"):
            s, m = app.generate_html();
            st.success(m) if s else st.error(m)

    with col3:
        st.markdown("**Git 代理**")
        port = st.text_input("端口", "7897")
        if 'auto_proxy' not in st.session_state:
            os.system(f"git config --global http.proxy http://127.0.0.1:{port}")
            st.session_state.auto_proxy = True

        if st.button("🚀 Push 到 GitHub 并生成链接", type="primary", use_container_width=True):
            app.generate_html()
            os.chdir(hok_logic.LOCAL_REPO_PATH)
            try:
                try:
                    subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "add", "."], check=True)
                    subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "commit", "-m", "sync via dashboard"], check=True)
                except:
                    pass
                result = subprocess.run([hok_logic.GIT_EXECUTABLE_PATH, "push"], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success(f"✅ 发布成功！")
                    st.markdown(
                        f"### 🔗 点击访问：\n[https://{hok_logic.GITHUB_USERNAME}.github.io/hok-rank/](https://{hok_logic.GITHUB_USERNAME}.github.io/hok-rank/)")
                else:
                    st.error(f"推送失败: {result.stderr}")
            except Exception as e:
                st.error(f"Error: {e}")