# ================= HTML 模板层 =================
# 负责定义生成的网页结构、样式和交互逻辑

HTML_TEMPLATE = """
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
        .chart-header { background: var(--header-bg); padding: 15px 20px; color: white; display: flex; align-items: center; justify-content: center; gap: 20px; }
        .header-content { text-align: center; flex: 1; }
        .header-content h1 { font-size: 24px; font-weight: 800; margin: 0; }
        .info-container { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 5px; }
        .info-btn { background: white; color: black; border: none; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold; cursor: pointer; transition: opacity 0.2s; }
        .info-btn:hover { opacity: 0.8; }
        .table-container { width: 100%; overflow-x: auto; }

        /* 表格样式 */
        table { width: 98%; margin: 0 auto; border-collapse: separate; border-spacing: 0 8px; font-size: 14px; min-width: 900px; }
        th { text-align: center; padding: 12px 4px; font-weight: 800; border-bottom: 3px solid #6366f1; white-space: nowrap; cursor: pointer; }
        td { padding: 12px 2px; vertical-align: middle; text-align: center; background: transparent; border: none; }

        .rounded-left { border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
        .rounded-right { border-top-right-radius: 12px; border-bottom-right-radius: 12px; }
        .desc-col { width: 80px; padding: 2px !important; }
        .desc-img { max-width: 100%; height: auto; max-height: 40px; object-fit: contain; display: block; margin: 0 auto; border-radius: 4px; mix-blend-mode: screen; filter: contrast(1.5) saturate(4.0); }
        .qual-header { display: inline-flex; align-items: center; justify-content: center; gap: 6px; position: relative; }
        .multi-select-box { font-size: 11px; border-radius: 4px; border: 1px solid #ddd; padding: 4px 8px; cursor: pointer; background: white; min-width: 85px; }
        .dropdown-menu { display: none; position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; border-radius: 6px; padding: 8px; min-width: 130px; text-align: left; }
        .dropdown-menu.show { display: block; }

        .col-sort::after { content: ' ⇅'; color: #ccc; margin-left: 5px; font-size: 10px; }
        th.sort-asc .col-sort::after, th.sort-asc.col-sort::after { content: ' ▲'; color: #6366f1; }
        th.sort-desc .col-sort::after, th.sort-desc.col-sort::after { content: ' ▼'; color: #6366f1; }

        .quality-icon { height: 28px; width: auto; display: inline-block; vertical-align: middle; transition: transform 0.2s; object-fit: contain; }
        .rare-wushuang-big { height: 60px !important; width: auto !important; margin: -15px 0; }
        .wushuang-big { height: 45px !important; margin: -8px 0; }
        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; object-fit: cover; }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 5px; min-width: 180px; }

        /* 🔥 修复重点 1: 固定名字容器宽度，内容居中 */
        .name-container { 
            display: flex; 
            flex-direction: column; 
            gap: 2px; 
            width: 115px; /* 固定宽度：约等于 "貂蝉-馥梦繁花" 的长度 */
            align-items: center; /* 居中对齐 */
        }

        .song-title { 
            font-weight: 700; 
            font-size: 14px; 
            color: #000; 
            white-space: nowrap; 
            display: inline-block; /* 允许 transform 生效 */
            transform-origin: center; /* 从中心缩放 */
        }

        /* 🔥 修复重点 2: 角标撑满容器，强制等宽 */
        .badge { 
            display: block; 
            width: 100%; /* 撑满 115px */
            text-align: center; 
            padding: 2px 0; 
            font-size: 9px; 
            font-weight: 900; 
            border-radius: 3px; 
            text-transform: uppercase; 
            margin-top: 2px;
            box-sizing: border-box;
        }

        .badge-new { background: #ffd700; color: #000; } 
        .badge-return { background: #1d4ed8; color: #fff; } 
        .badge-preset { background: #06b6d4; color: #fff; } 
        .badge-out { background: #4b5563; color: #fff; }
        .badge-pool { background: #9333ea; color: #fff; }

        .rank-box { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; background: #1d4ed8; color: #fff; font-size: 15px; font-weight: 900; border-radius: 6px; line-height: 1; }
        .box-style { display: inline-block; width: 85px; padding: 4px 0; font-weight: 700; border-radius: 6px; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .growth-down { color: #991b1b !important; } .growth-up-mid { color: #16a34a !important; } .growth-up-high { color: #ea580c !important; } .growth-special { color: #a855f7 !important; font-weight: 900 !important; }
        .header-gifs-container { display: flex; gap: 10px; }
        .header-gif { width: 55px; height: 55px; border-radius: 8px; object-fit: cover; border: 2px solid rgba(255,255,255,0.4); }
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
                                {% for q in quality_config.values()|map(attribute='name')|unique %}
                                <label class="dropdown-item"><input type="checkbox" class="q-check" value="{{ q }}" onchange="handleSingleSelect(this)"> {{ q }}</label>
                                {% endfor %}
                            </div><span class="col-sort" onclick="sortTable(1, 'float')"></span></div></th>
                        <th style="text-align:left; padding-left:20px;">Skin Name</th>
                        <th></th>
                        <th class="col-sort" onclick="sortTable(4, 'float')">销量</th>
                        <th class="col-sort" onclick="sortTable(5, 'float')">销售额</th>
                        <th class="col-sort" onclick="sortTable(6, 'float')">Growth</th>
                        <th class="col-sort" onclick="sortTable(7, 'float')">万象积分</th>
                        <th class="col-sort" onclick="sortTable(8, 'float')">售价</th>
                    </tr>
                </thead>
                <tbody>
                    {% for skin in total_skins %}
                    {% if not skin.is_hidden %}
                    {% set q_str = skin.quality_key %}
                    {% set q_cfg = quality_config.get(q_str, {}) %}
                    {% set parent_id = q_cfg.parent|string if q_cfg.parent else none %}
                    {% set display_img_id = parent_id if parent_id else q_str %}
                    {% set root_cfg = quality_config.get(display_img_id, q_cfg) %}
                    {% set scale_val = q_cfg.get('scale', 1.0) %}
                    {% set bg_c = root_cfg.get('bg_color', '#ffffff') %}
                    {% set q_cls = 'rare-wushuang-big' if root_cfg.name == '珍品无双' else ('wushuang-big' if root_cfg.name == '无双' else '') %}
                    <tr data-quality="{{ q_cfg.name }}">
                        <td>{% if not skin.is_preset and not skin.is_discontinued %}<span class="rank-box">{{ loop.index }}</span>{% else %}-{% endif %}</td>
                        <td class="quality-col" data-val="{{ skin.quality }}">
                            <img src="./images/{{ q_str }}.gif" data-q="{{ q_str }}" data-p="{{ parent_id }}" class="quality-icon {{ q_cls }}" style="transform: scale({{ scale_val }});" onerror="loadFallbackImg(this)">
                        </td>
                        <td class="rounded-left" style="background-color: {{ bg_c }};"><div class="song-col">
                            <img src="./{{ skin.local_img or 'placeholder.jpg' }}" class="album-art">
                            <div class="name-container"><span class="song-title">{{ skin.name }}</span>
                                {% if skin.is_pool %}<span class="badge badge-pool">祈愿</span>
                                {% elif skin.is_discontinued %}<span class="badge badge-out">Out of Print</span>
                                {% elif skin.is_preset %}<span class="badge badge-preset">Coming Soon</span>
                                {% elif skin.is_new %}<span class="badge badge-new">New Arrival</span>
                                {% elif skin.is_rerun %}<span class="badge badge-return">Limit Return</span>{% endif %}
                            </div>
                        </div></td>
                        <td class="desc-col" style="background-color: {{ bg_c }};">{% if skin.desc_img %}<img src="./skin_descs/{{ skin.desc_img }}" class="desc-img">{% endif %}</td>
                        <td style="background-color: {{ bg_c }};"><div class="box-style">{{ skin.sales_volume }}</div></td>
                        <td style="background-color: {{ bg_c }}; color:#6366f1; font-weight:bold;">{{ skin.revenue }}</td>
                        <td style="background-color: {{ bg_c }};">{% if skin.growth %}{% set g_cls = 'growth-special' if skin.growth == 1.9 else ('growth-down' if skin.growth < 0 else ('growth-up-high' if skin.growth >= 10 else ('growth-up-mid' if skin.growth >= 5 else ''))) %}<div class="box-style {{ g_cls }}">{{ skin.growth }}%{% if skin.growth == 1.9 %}!{% endif %}</div>{% else %}--{% endif %}</td>
                        <td style="background-color: {{ bg_c }};">{{ skin.list_price|int }}</td>
                        <td class="rounded-right" style="background-color: {{ bg_c }};"><div class="box-style">{{ skin.real_price }}</div></td>
                    </tr>
                    {% endif %}
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
    window.onload = () => { sortTable(5, 'float'); adjustNameFontSize(); };

    // 🔥 名字自适应缩放逻辑
    function adjustNameFontSize() {
        const containers = document.querySelectorAll('.name-container'); 
        const maxWidth = 115; // 对应 CSS 里的 .name-container width
        containers.forEach(container => {
            const title = container.querySelector('.song-title');
            if (title) {
                // 先复原
                title.style.transform = 'none';
                // 检查实际宽度
                if (title.scrollWidth > maxWidth) {
                    const scale = maxWidth / title.scrollWidth;
                    title.style.transform = `scale(${scale})`;
                }
            }
        });
    }

    function loadFallbackImg(img) {
        const q = img.getAttribute('data-q');
        const p = img.getAttribute('data-p');
        const src = img.src;
        if (src.indexOf(q + '.gif') !== -1) { img.src = './images/' + q + '.jpg'; }
        else if (src.indexOf(q + '.jpg') !== -1 && p && p !== 'None') { img.src = './images/' + p + '.gif'; }
        else if (p && src.indexOf(p + '.gif') !== -1) { img.src = './images/' + p + '.jpg'; }
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

    function parseMixedNum(str) {
        if (!str) return -999999;
        function parseOne(s) {
            s = s.toString().replace(/[¥,%,]/g, '').trim().toUpperCase();
            s = s.replace('>', '').replace('<', ''); 
            let multi = 1;
            if (s.includes('亿') || s.includes('B')) { multi = 100000000; s = s.replace('亿', '').replace('B', ''); } 
            else if (s.includes('万')) { multi = 10000; s = s.replace('万', ''); }
            else if (s.includes('W')) { multi = 10000; s = s.replace('W', ''); }
            else if (s.includes('M')) { multi = 1000000; s = s.replace('M', ''); }
            else if (s.includes('K')) { multi = 1000; s = s.replace('K', ''); }
            let val = parseFloat(s);
            return isNaN(val) ? 0 : val * multi;
        }
        if (str.toString().includes('~')) {
            let parts = str.toString().split('~');
            return (parseOne(parts[0]) + parseOne(parts[1])) / 2;
        }
        let val = parseOne(str);
        if (str.toString().includes('>')) return val + 0.1;
        if (str.toString().includes('<')) return val - 0.1;
        return val;
    }

    function sortTable(n, type) {
        var table = document.getElementById("skinTable"), rows = Array.from(table.rows).slice(1), headers = table.getElementsByTagName("TH"), dir = "desc";
        if (headers[n].classList.contains("sort-desc")) dir = "asc";
        Array.from(headers).forEach(h => h.classList.remove("sort-asc", "sort-desc"));
        headers[n].classList.add(dir === "asc" ? "sort-asc" : "sort-desc");
        rows.sort((a, b) => {
            var valA = a.cells[n].innerText;
            var valB = b.cells[n].innerText;
            var x = parseMixedNum(valA);
            var y = parseMixedNum(valB);
            if (isNaN(x)) x = -9999999; if (isNaN(y)) y = -9999999;
            return dir === "asc" ? x - y : y - x;
        });
        rows.forEach(r => table.tBodies[0].appendChild(r));
    }
    </script>
</body>
</html>
"""