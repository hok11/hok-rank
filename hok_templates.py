# 存放 HTML 模板，为逻辑层减负
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
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5); backdrop-filter: blur(2px); }
        .modal-content { background-color: #fefefe; margin: 15% auto; padding: 20px; border-radius: 12px; width: 80%; max-width: 500px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); animation: fadeIn 0.3s; }
        @keyframes fadeIn { from {opacity: 0; transform: translateY(-20px);} to {opacity: 1; transform: translateY(0);} }
        .close-btn { color: #aaa; float: right; font-size: 24px; font-weight: bold; cursor: pointer; line-height: 20px; }
        .close-btn:hover { color: black; }
        .modal-list { text-align: left; margin-top: 15px; padding-left: 20px; font-size: 14px; line-height: 1.6; color: #333; }
        .header-gifs-container { display: flex; gap: 10px; }
        .header-gif { width: 55px; height: 55px; border-radius: 8px; object-fit: cover; border: 2px solid rgba(255,255,255,0.4); }
        .table-container { width: 100%; overflow-x: auto; }
        table { width: 98%; margin: 0 auto; border-collapse: separate; border-spacing: 0 8px; font-size: 14px; min-width: 800px; }
        th { text-align: center; padding: 8px 2px; font-weight: 800; border-bottom: 3px solid #6366f1; white-space: nowrap; }
        td { padding: 12px 2px; vertical-align: middle; text-align: center; background: transparent; border: none; }
        .rounded-left { border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
        .rounded-right { border-top-right-radius: 12px; border-bottom-right-radius: 12px; }
        .desc-col { width: 100px; padding: 2px !important; }
        .desc-img { max-width: 100%; height: auto; max-height: 50px; object-fit: contain; display: block; margin: 0 auto; border-radius: 4px; mix-blend-mode: screen; filter: contrast(1.5) saturate(4.0); }
        .qual-header { display: inline-flex; align-items: center; justify-content: center; gap: 6px; position: relative; }
        .multi-select-box { font-size: 11px; border-radius: 4px; border: 1px solid #ddd; padding: 4px 8px; cursor: pointer; background: white; min-width: 85px; }
        .dropdown-menu { display: none; position: absolute; top: 110%; left: 0; background: white; border: 1px solid #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; border-radius: 6px; padding: 8px; min-width: 130px; text-align: left; }
        .dropdown-menu.show { display: block; }
        .col-sort { cursor: pointer; position: relative; } .col-sort::after { content: ' ⇅'; color: #ccc; margin-left: 5px; font-size: 10px; }
        th.sort-asc .col-sort::after, th.sort-asc.col-sort::after { content: ' ▲'; color: #6366f1; }
        th.sort-desc .col-sort::after, th.sort-desc.col-sort::after { content: ' ▼'; color: #6366f1; }

        .quality-icon { height: 28px; width: auto; display: inline-block; vertical-align: middle; transition: transform 0.2s; object-fit: contain; }
        .rare-wushuang-big { height: 60px !important; width: auto !important; margin: -15px 0; }
        .wushuang-big { height: 45px !important; margin: -8px 0; }
        .album-art { width: 48px; height: 48px; border-radius: 6px; margin-right: 12px; object-fit: cover; }
        .song-col { display: flex; align-items: center; text-align: left; padding-left: 5px; min-width: 180px; }
        .name-container { display: flex; flex-direction: column; gap: 2px; width: 86px; align-items: center; }
        .song-title { font-weight: 700; font-size: 14px; color: #000; white-space: nowrap; transform-origin: center; display: inline-block; }
        .badge { display: block; width: 100%; text-align: center; padding: 1px 0; font-size: 9px; font-weight: 900; border-radius: 3px; text-transform: uppercase; }
        .badge-new { background: #ffd700; color: #000; } .badge-return { background: #1d4ed8; color: #fff; } .badge-preset { background: #06b6d4; color: #fff; } .badge-out { background: #4b5563; color: #fff; }

        .rank-box { 
            display: inline-flex; align-items: center; justify-content: center;
            width: 28px; height: 28px; background: #1d4ed8; color: #fff; 
            font-size: 15px; font-weight: 900; border-radius: 6px; line-height: 1;
        }
        .box-style { display: inline-block; width: 75px; padding: 4px 0; font-weight: 700; border-radius: 6px; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .growth-down { color: #991b1b !important; } .growth-up-mid { color: #16a34a !important; } .growth-up-high { color: #ea580c !important; } .growth-special { color: #a855f7 !important; font-weight: 900 !important; }
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
                        <th style="text-align:left; padding-left:20px;">Skin Name</th><th></th>
                        <th class="col-sort" onclick="sortTable(4, 'float')">Rank Pts</th>
                        <th class="col-sort" onclick="sortTable(5, 'float')">Real Pts</th>
                        <th class="col-sort" onclick="sortTable(6, 'float')">Growth</th>
                        <th class="col-sort" onclick="sortTable(7, 'float')">List P</th>
                        <th class="col-sort" onclick="sortTable(8, 'float')">Real P</th>
                    </tr>
                </thead>
                <tbody>
                    {% for skin in total_skins %}
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
                                {% if skin.is_discontinued %}<span class="badge badge-out">Out of Print</span>{% elif skin.is_preset %}<span class="badge badge-preset">Coming Soon</span>{% elif skin.is_new %}<span class="badge badge-new">New Arrival</span>{% elif skin.is_rerun %}<span class="badge badge-return">Limit Return</span>{% endif %}
                            </div>
                        </div></td>
                        <td class="desc-col" style="background-color: {{ bg_c }};">{% if skin.desc_img %}<img src="./skin_descs/{{ skin.desc_img }}" class="desc-img">{% endif %}</td>
                        <td data-val="{{ skin.score if skin.score is not none else -999 }}" style="background-color: {{ bg_c }};"><div class="box-style">{% if skin.is_discontinued %}{{ '--' }}{% else %}{{ skin.score or '--' }}{% endif %}</div></td>
                        <td style="background-color: {{ bg_c }}; color:#6366f1; font-weight:bold;">{{ skin.real_score or '--' }}</td>
                        <td style="background-color: {{ bg_c }};">{% if skin.growth %}{% set g_cls = 'growth-special' if skin.growth == 1.9 else ('growth-down' if skin.growth < 0 else ('growth-up-high' if skin.growth >= 10 else ('growth-up-mid' if skin.growth >= 5 else ''))) %}<div class="box-style {{ g_cls }}">{{ skin.growth }}%{% if skin.growth == 1.9 %}!{% endif %}</div>{% else %}--{% endif %}</td>
                        <td style="background-color: {{ bg_c }};">¥{{ skin.list_price }}</td>
                        <td class="rounded-right" style="background-color: {{ bg_c }};"><div class="box-style">{% if skin.real_price > 0 %}¥{{ skin.real_price }}{% else %}--{% endif %}</div></td>
                    </tr>
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
    window.onload = () => { sortTable(4, 'float'); adjustNameFontSize(); };
    function adjustNameFontSize() {
        const containers = document.querySelectorAll('.name-container'); const maxWidth = 86; 
        containers.forEach(container => {
            const title = container.querySelector('.song-title');
            if (title && title.scrollWidth > maxWidth) title.style.transform = `scale(${maxWidth / title.scrollWidth})`;
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
    function sortTable(n, type) {
        var table = document.getElementById("skinTable"), rows = Array.from(table.rows).slice(1), headers = table.getElementsByTagName("TH"), dir = "desc";
        if (headers[n].classList.contains("sort-desc")) dir = "asc";
        Array.from(headers).forEach(h => h.classList.remove("sort-asc", "sort-desc"));
        headers[n].classList.add(dir === "asc" ? "sort-asc" : "sort-desc");
        rows.sort((a, b) => {
            var x = parseFloat(a.cells[n].getAttribute("data-val") || a.cells[n].innerText.replace(/[¥%!]/g, ''));
            var y = parseFloat(b.cells[n].getAttribute("data-val") || b.cells[n].innerText.replace(/[¥%!]/g, ''));
            if (isNaN(x)) x = -9999999; if (isNaN(y)) y = -9999999;
            return dir === "asc" ? x - y : y - x;
        });
        rows.forEach(r => table.tBodies[0].appendChild(r));
    }
    </script>
</body>
</html>
"""