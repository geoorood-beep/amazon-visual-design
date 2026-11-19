/* 产品资料表的脚本（UTA_STYLE.md 1.15）。读 id 为 sheet 的 JSON 画出表单，生成 UTA-PRODUCT v1。 */
(function () {
  window.__utaProductFormLoaded = true;
  var data = JSON.parse(document.getElementById("sheet").textContent);
  var KEY = "uta-product:" + data.product + ":" + (data.form || "") + ":" + (data.generated || "");
  var size = data.size || {};
  var dims = size.dims || {L: {short: "长", label: "长", en: "long"}, W: {short: "宽", label: "宽", en: "deep"}, H: {short: "高", label: "高", en: "tall"}};
  var extras = size.extra || [];
  var app = document.getElementById("app");
  var previews = {};
  var UNIT_CN = {mm: "毫米", cm: "厘米", m: "米", "in": "英寸", ft: "英尺", L: "升", ml: "毫升", g: "克", kg: "千克"};
  var TO_MM = {mm: 1, cm: 10, m: 1000, "in": 25.4, ft: 304.8};
  var NOUN = {L: "length", W: "depth", H: "height"};
  var RATIOS = size.ratios || [["L", "H"], ["W", "H"]];
  var TYPES = data.types || ["组成部件", "可拆件", "耗材", "随附配件", "宿主产品", "外部物品"];
  var TYPE_TIP = {"组成部件": "长在产品上，跟着产品的状态走", "可拆件": "用户会拆下来洗、加东西的", "耗材": "定期更换的",
    "随附配件": "包装里另附的，只在用到它的画面出现", "宿主产品": "卖的是配件时，它要装上去的那台产品，只当背景",
    "外部物品": "水、粮、宠物、手这类道具，不算产品"};
  function unit(o) { return (o && o.unit) || "mm"; }
  function ucn(o) { return UNIT_CN[unit(o)] || unit(o); }
  function mm(k) { var v = num(st.size[k]); return v && TO_MM[unit(dims[k])] ? v * TO_MM[unit(dims[k])] : null; }

  function blank() { return {q: {}, x: {}, t: {}, add: [], size: {L: "", W: "", H: "", extra: {}, ref: "", cant: false}, photos: {}, notes: ""}; }
  var st = null;
  try { st = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { st = null; }
  if (!st || typeof st !== "object") st = blank();
  var b0 = blank();
  Object.keys(b0).forEach(function (k) { if (st[k] == null) st[k] = b0[k]; });
  if (!st.size.extra) st.size.extra = {};

  function save() { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} refresh(); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
    });
  }
  function has(s) { return s != null && String(s).trim() !== ""; }
  function one(s) { return String(s == null ? "" : s).trim().replace(/\s*\n+\s*/g, "；"); }
  function src(p) { return !p ? "" : (/^(data:|blob:|https?:|\/)/.test(p) ? p : (data.base || "") + p); }
  function num(v) { var n = parseFloat(String(v == null ? "" : v).replace(/[^\d.]/g, "")); return isFinite(n) && n > 0 ? n : null; }
  function r2(x) { return Math.round(x * 100) / 100; }
  function ths(list) {
    list = (list || []).filter(has);
    return list.length ? '<div class="ths">' + list.map(function (p) {
      return '<img class="th" src="' + esc(src(p)) + '" alt="" data-zoom="1">';
    }).join("") + '</div>' : "";
  }
  function badge(c) {
    if (!has(c)) return "";
    return '<span class="badge ' + (c === "确定" ? "ok" : (c === "推定" ? "warn" : "none")) + '">AI ' + esc(c) + '</span>';
  }
  function row(k, v) { return has(v) ? '<div class="row"><i>' + esc(k) + '</i>' + esc(v) + '</div>' : ""; }
  function fixbox(id, label) {
    var x = st.x[id] || {};
    return '<div class="fixbox' + (x.bad ? " on" : "") + '"><button type="button" class="tag' + (x.bad ? " on" : "") +
      '" data-act="bad" data-id="' + esc(id) + '">' + esc(label) + '</button>' +
      '<textarea data-act="badtext" data-id="' + esc(id) + '" placeholder="哪里不对、应该是什么，写一句">' + esc(x.text || "") + '</textarea></div>';
  }
  function findQ(id) { return (data.questions || []).filter(function (q) { return q.id === id; })[0] || {}; }
  function findPhoto(slot) { return (data.photos || []).filter(function (p) { return p.slot === slot; })[0] || {}; }

  var byId = {};
  (data.parts || []).forEach(function (p) { byId[p.id] = p; });
  function depth(p) {
    var d = 0, cur = p, guard = 0;
    while (cur && cur.parent && byId[cur.parent] && guard++ < 6) { d++; cur = byId[cur.parent]; }
    return Math.min(d, 2);
  }

  function photoSlot(p) {
    var mine = st.photos[p.slot];
    var img = previews[p.slot] || (mine ? "" : src(p.img));
    var inner = img ? '<img src="' + esc(img) + '" alt="" data-zoom="1">'
      : '<div class="empty">' + (mine ? "已选 " + esc(mine.name) + "<br>（刷新后不显示预览）" : "把照片拖到这里<br>或点下面「补一张」") + '</div>';
    var tag = mine ? (mine.replace ? "新照片（替换）" : "新照片") : (p.img ? (p.src || "") : "还没有");
    return '<div class="ph' + (mine ? " new" : "") + (!p.img && !mine ? " miss" : "") + '" data-slot="' + esc(p.slot) + '">' +
      '<div class="phimg">' + inner + '</div>' +
      '<div><b>' + esc(p.label) + '</b> <span class="src">' + esc(tag) + '</span></div>' +
      (has(p.tip) ? '<div class="tip">' + esc(p.tip) + '</div>' : "") +
      (mine ? '<div class="tip">文件：' + esc(mine.name) + '　<a href="#" data-act="unphoto" data-slot="' + esc(p.slot) + '">撤回</a></div>' : "") +
      '<label class="pick">' + (p.img || mine ? "换一张" : "补一张") +
      '<input type="file" accept="image/*" data-act="file" data-slot="' + esc(p.slot) + '" hidden></label></div>';
  }

  function render() {
    var h = [];
    var nMiss = (data.photos || []).filter(function (p) { return !p.img; }).length;
    h.push('<header><h1>' + esc(data.title || (data.product + " · 产品资料（选填）")) + '</h1>' +
      (has(data.summary) ? '<div class="summary">' + esc(data.summary) + '</div>' : "") +
      '<div class="meta"><span>' + esc(data.product) + '</span>' +
      (has(data.by) ? '<span>' + esc(data.by) + '</span>' : "") +
      ((data.categories || []).length ? '<span>品类 ' + esc(data.categories.map(function (c) { return c.name; }).join(" + ")) + '</span>' : "") +
      ((data.variant_names || []).length ? '<span>款式 ' + esc(data.variant_names.join(" + ")) + '（AI 从照片或需求里看出来的，不对写在最下面）</span>' : "") +
      (has(data.generated) ? '<span>草稿日期 ' + esc(data.generated) + '</span>' : "") + '</div></header>');
    h.push('<div class="how">这张表<b>不填也能往下做</b>。下面的内容 AI 已经根据产品卡、实拍和造型参考先填好了，每条标着「AI 确定 / 推定 / 不确定」。' +
      '你只改不对的、补你知道的，<b>没动的就按 AI 草稿</b>。填得越多，后面越少返工。改完点底部「生成产品资料」，把结果原样发给 Grok。' +
      '<div class="legend">谁说了算：你改过、填过的 ＞ 你看过没改的 ＞ AI 推定。AI 推定的东西可以照参考图画，但不会当成事实写进文案。</div></div>');

    var qs = data.questions || [];
    if (qs.length) {
      h.push('<section class="sec"><h2>需要你判断<small>' + qs.length + ' 个，只列 AI 拿不准、又会影响画面的。不选就按 ★；没有 ★ 的保持不确定</small></h2>');
      qs.forEach(function (q) {
        var a = st.q[q.id] || {};
        var write = (q.write || []).indexOf(a.i) >= 0;
        h.push('<div class="box" id="q-' + esc(q.id) + '"><div><span class="pid">' + esc(q.id) + '</span><b>' + esc(q.text) + '</b></div>' +
          (has(q.why) ? '<div class="why">' + esc(q.why) + '</div>' : "") +
          '<div class="opts">' + (q.options || []).map(function (o, i) {
            return '<button type="button" class="opt' + (a.i === i ? " on" : "") + '" data-act="opt" data-q="' + esc(q.id) + '" data-i="' + i + '">' +
              (q.rec === i ? '<span class="star">★</span>' : "") + esc(o) + '</button>';
          }).join("") + '</div>' +
          '<textarea class="qwrite" data-act="qtext" data-q="' + esc(q.id) + '" placeholder="写一句" style="display:' + (write ? "block" : "none") + '">' + esc(a.text || "") + '</textarea>' +
          ths(q.imgs) + '</div>');
      });
      h.push('</section>');
    }

    var parts = data.parts || [];
    if (parts.length) {
      h.push('<section class="sec tree"><h2>部件和它们的关系<small>AI 从照片推的结构。不对的点「不对」写一句；关系类型不对直接改；漏了的在最下面加</small></h2>' +
        '<details class="types"><summary>关系类型是什么意思（决定这个部件在哪些画面出现）</summary>' +
        TYPES.map(function (t) { return '<div class="row"><i>' + esc(t) + '</i>' + esc(TYPE_TIP[t] || "") + '</div>'; }).join("") + '</details>');
      parts.forEach(function (p) {
        var x = st.x[p.id] || {};
        var d = depth(p);
        var parent = p.parent && byId[p.parent] ? p.parent + " " + byId[p.parent].name : "";
        var ty = st.t[p.id] || p.type || "";
        var typeSel = has(p.type) ? '<select class="tsel' + (st.t[p.id] ? " on" : "") + '" data-act="ptype" data-id="' + esc(p.id) + '" title="关系类型">' +
          TYPES.map(function (t) { return '<option' + (t === ty ? " selected" : "") + '>' + esc(t) + '</option>'; }).join("") + '</select>' : "";
        h.push('<div class="box d' + d + (x.bad || st.t[p.id] ? " bad" : "") + '"><div class="nb"><div>' +
          '<div><span class="pid">' + esc(p.id) + '</span><b>' + esc(p.name) + '</b>' + typeSel + badge(p.conf) + '<span class="en">' + esc(p.en || "") + '</span></div>' +
          row("属于", parent) + row("在哪", p.where) + row("能拆吗", p.detach) + row("看得见吗", p.visible) + row("依据", p.basis) + row("画图易错", p.pitfall) +
          '</div><div>' + ths(p.imgs) + '</div></div>' + fixbox(p.id, "不对") + '</div>');
      });
      h.push('<div class="box"><b>漏了部件？</b><div class="tip">写名称和它装在哪、跟谁连着。</div>');
      st.add.forEach(function (a, i) {
        h.push('<div class="addrow"><input type="text" data-act="addname" data-i="' + i + '" placeholder="名称" value="' + esc(a.name) + '">' +
          '<input type="text" data-act="addtext" data-i="' + i + '" placeholder="装在哪、跟谁连着、装好时看不看得见" value="' + esc(a.text) + '">' +
          '<button type="button" class="ghost" data-act="deladd" data-i="' + i + '">删掉</button></div>');
      });
      h.push('<button type="button" class="ghost" data-act="add" style="margin-top:6px">＋ 加一件</button></div></section>');
    }

    var states = data.states || [];
    if (states.length) {
      h.push('<section class="sec"><h2>产品有几种样子<small>每张图用哪一种，脚本照这里挑产品参考、写「必须看得见」和「不能出现」</small></h2>');
      states.forEach(function (s) {
        var x = st.x[s.id] || {};
        h.push('<div class="box' + (x.bad ? " bad" : "") + '"><div><span class="pid" style="min-width:auto;margin-right:8px">' + esc(s.id) + '</span><b>' + esc(s.name) + '</b>' + badge(s.conf) + '</div>' +
          row("讲哪几条", s["for"]) + row("看得见", s.show) + row("看不见", s.hide) + row("不能出现", s.never) + row("条件", s.cond) +
          fixbox(s.id, "不对") + '</div>');
      });
      h.push('</section>');
    }

    var fns = data.functions || [];
    if (fns.length) {
      h.push('<section class="sec"><h2>每个卖点怎么做到、画面里用什么证明<small>AI 推的，拍图时照这里；不对的点一下写一句</small></h2>');
      fns.forEach(function (f) {
        var x = st.x[f.fact] || {};
        h.push('<div class="box' + (x.bad ? " bad" : "") + '"><div><span class="pid">' + esc(f.fact) + '</span>' + esc(f.text || "") +
          badge(f.conf || f.confidence) + '</div>' +
          row("怎么做到", f.how) + row("画面证据", f.proof) + row("产品样子", f.state) + row("推荐拍法", f.angle) + row("特效", f.effect) +
          fixbox(f.fact, "不对") + '</div>');
      });
      h.push('</section>');
    }

    var flow = data.flow || [];
    if (flow.length) {
      var fx = st.x.flow || {};
      h.push('<section class="sec"><h2>怎么用<small>从拿到手到日常打理</small></h2><div class="box' + (fx.bad ? " bad" : "") + '"><ol class="flow">' +
        flow.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join("") + '</ol>' + fixbox("flow", "不对") + '</div></section>');
    }

    var inner = data.internal || [];
    if (inner.length) {
      h.push('<section class="sec"><h2>内部结构<small>只列确认过的；透视、剖视特效只能画这里有的</small></h2><div class="box">' +
        inner.map(function (r) { return row(r.name || r.part || "", [r.en, r.where, r.source].filter(has).join("；")); }).join("") + '</div></section>');
    }

    var ups = data.updates || [];
    if (ups.length) {
      h.push('<section class="sec"><h2>AI 发现产品卡要跟着改的地方<small>写入产品卡时一起改；不同意的点一下</small></h2>');
      ups.forEach(function (u) {
        var x = st.x[u.id] || {};
        h.push('<div class="box' + (x.bad ? " bad" : "") + '"><div><span class="pid">' + esc(u.id) + '</span>' + esc(u.text) + '</div>' +
          '<div class="why">' + esc(u.fix) + '</div>' + fixbox(u.id, "不同意") + '</div>');
      });
      h.push('</section>');
    }

    h.push('<section class="sec"><h2>尺寸和大小参照<small>选填</small></h2>' + (has(size.why) ? '<p class="secnote">' + esc(size.why) + '</p>' : "") + '<div class="box"><div class="size">' +
      ["L", "W", "H"].map(function (k) {
        return '<div><label>' + esc(dims[k].label) + '（' + esc(ucn(dims[k])) + '）</label><input type="number" min="0" step="1" inputmode="decimal" data-act="dim" data-k="' + k + '" value="' + esc(st.size[k]) + '"></div>';
      }).join("") +
      extras.map(function (e) {
        return '<div><label>' + esc(e.label) + '（' + esc(ucn(e)) + '，选填）</label><input type="number" min="0" step="1" inputmode="decimal" data-act="extra" data-k="' + esc(e.key) + '" value="' + esc(st.size.extra[e.key] || "") + '"></div>';
      }).join("") + '</div>' +
      (has(size.hint) ? '<div class="tip" style="margin-top:6px">' + esc(size.hint) + '</div>' : "") +
      '<div style="margin-top:10px"><span class="lbl">大小参照：和一样大家都知道大小的东西比，一句话</span>' +
      '<input type="text" data-act="sizeref" placeholder="例如：高度大约到成年猫站着时的肩膀（按实物写）" value="' + esc(st.size.ref) + '"></div>' +
      '<label class="chk"><input type="checkbox" data-act="cant"' + (st.size.cant ? " checked" : "") + '> 暂时量不了：照参考图比例画，总览标「比例推定」</label>' +
      '<div id="geo"></div></div></section>');

    var photos = data.photos || [];
    if (photos.length) {
      h.push('<section class="sec"><h2>照片<small>选填补拍；现有 ' + (photos.length - nMiss) + ' 格，建议补 ' + nMiss + ' 格</small></h2>' +
        '<p class="secnote">拖进对应的格子，或点「补一张」。照片原件和生成的文字一起发；Codex 按格子名给照片改名入库。</p><div class="phs">' +
        photos.map(photoSlot).join("") + '</div></section>');
    }

    h.push('<section class="sec"><h2>还要补充的<small>选填：卖点或参数有变化、有不能写的、其他想说的</small></h2>' +
      '<div class="box"><textarea data-act="notes" placeholder="写在这里">' + esc(st.notes) + '</textarea></div></section>');

    app.innerHTML = h.join("");
    updGeo();
    refresh();
  }

  function ratios() {
    var r = [];
    RATIOS.forEach(function (pair) {
      var a = mm(pair[0]), b = mm(pair[1]);
      if (a && b) r.push(dims[pair[0]].short + "/" + dims[pair[1]].short + " " + r2(a / b));
    });
    return r;
  }
  function geo() {
    var s = st.size, g = [], bits = [], rs = [];
    ["L", "W", "H"].forEach(function (k) {
      var v = num(s[k]);
      if (v) bits.push((bits.length ? "" : "about ") + v + " " + unit(dims[k]) + " " + dims[k].en);
    });
    if (bits.length) g.push(bits.join(", "));
    RATIOS.forEach(function (pair) {
      var a = mm(pair[0]), b = mm(pair[1]);
      if (a && b) rs.push((dims[pair[0]].noun || NOUN[pair[0]]) + " about " + r2(a / b) + " times the " + (dims[pair[1]].noun || NOUN[pair[1]]));
    });
    if (rs.length) g.push(rs.join("; "));
    extras.forEach(function (e) { var v = num(s.extra[e.key]); if (v && e.en) g.push(e.en.replace("{v}", v)); });
    return g;
  }
  function human(k) {
    var v = num(st.size[k]), u = unit(dims[k]);
    if (!v) return "";
    var alt = u === "mm" ? "（约 " + r2(v / 10) + " 厘米）" : (u === "cm" ? "（约 " + r2(v / 100) + " 米）" : "");
    return dims[k].short + " " + v + " " + ucn(dims[k]) + alt;
  }
  function updGeo() {
    var el = document.getElementById("geo");
    if (!el) return;
    var odd = ["L", "W", "H"].some(function (k) { var v = mm(k); return v && (v < 1 || v > 20000); });
    var said = ["L", "W", "H"].map(human).filter(has);
    var r = ratios(), g = geo(), h = "";
    if (said.length) h += '<div class="ratio">你填的是：' + esc(said.join("，")) + '</div>';
    if (r.length) h += '<div class="ratio">比例（自动算）：' + esc(r.join("　")) + '</div>';
    if (odd) h += '<div class="warnline">有个数小于 1 毫米或大于 20 米，确认一下单位。</div>';
    if (g.length) h += '<div class="tip" style="margin-top:8px">写进提示词的英文（自动生成，不用改）：</div><pre class="geo">' + esc(g.map(function (l) { return "- " + l; }).join("\n")) + '</pre>';
    el.innerHTML = h;
  }

  function changes() {
    var n = 0;
    Object.keys(st.q).forEach(function (k) { var a = st.q[k]; if (a && (a.i != null || has(a.text))) n++; });
    Object.keys(st.x).forEach(function (k) { if (st.x[k] && st.x[k].bad) n++; });
    Object.keys(st.t).forEach(function (k) { if (st.t[k]) n++; });
    st.add.forEach(function (a) { if (has(a.name) || has(a.text)) n++; });
    var s = st.size;
    if (has(s.L) || has(s.W) || has(s.H) || has(s.ref) || s.cant || Object.keys(s.extra).some(function (k) { return has(s.extra[k]); })) n++;
    n += Object.keys(st.photos).length;
    if (has(st.notes)) n++;
    return n;
  }
  function refresh() {
    var n = changes();
    document.getElementById("count").innerHTML = n ? "你改了 <b>" + n + "</b> 处，其余按 AI 草稿。" : "还没改任何地方。<b>一处不改也能往下做</b>，全部按 AI 草稿。";
  }

  function grp(label, list, word) {
    var ok = [], bad = [];
    (list || []).forEach(function (it) {
      var x = st.x[it.id], t = st.t[it.id], lines = [];
      if (t && t !== it.type) lines.push("  " + it.id + ": 类型 " + (it.type || "未写") + " → " + t);
      if (x && x.bad) lines.push("  " + it.id + ": " + word + " → " + (has(x.text) ? one(x.text) : "（只点了「" + word + "」）"));
      if (lines.length) bad.push(lines.join("\n")); else ok.push(it.id);
    });
    return [label + ": 同意 " + (ok.join(" ") || "无") + (bad.length ? "；要改 " + bad.length : "")].concat(bad);
  }
  function sizeVal(o, v) { return v + " " + unit(o); }
  function buildOut() {
    var n = changes();
    var lines = ["UTA-PRODUCT v1", "product: " + data.product, "form: " + (data.form || ""), "draft: " + (data.generated || ""),
      "changed: " + n + (n ? "" : "（全部按 AI 草稿）"), ""];
    (data.questions || []).forEach(function (q) {
      var a = st.q[q.id] || {}, line;
      if (a.i != null && q.options[a.i] != null) line = String(q.options[a.i]).replace("（写一句）", "") + (has(a.text) ? " → " + one(a.text) : "");
      else if (q.rec != null && q.rec >= 0) line = q.options[q.rec] + "（未答，按推荐）";
      else line = "未答（保持不确定）";
      lines.push(q.id + ": " + line);
    });
    if ((data.parts || []).length) {
      lines = lines.concat(grp("parts", data.parts, "不对"));
      st.add.forEach(function (a) {
        if (has(a.name) || has(a.text)) lines.push("  新增: " + (has(a.name) ? one(a.name) : "（没写名称）") + (has(a.text) ? " → " + one(a.text) : ""));
      });
    }
    if ((data.states || []).length) lines = lines.concat(grp("states", data.states, "不对"));
    if ((data.functions || []).length) lines = lines.concat(grp("functions", data.functions.map(function (f) { return {id: f.fact}; }), "不对"));
    if ((data.flow || []).length) {
      var fl = st.x.flow;
      lines.push("flow: " + (fl && fl.bad ? "要改 → " + (has(fl.text) ? one(fl.text) : "（只点了「不对」）") : "同意"));
    }
    if ((data.updates || []).length) lines = lines.concat(grp("card_updates", data.updates, "不同意"));

    var s = st.size, L = num(s.L), W = num(s.W), H = num(s.H);
    var ex = extras.filter(function (e) { return num(s.extra[e.key]); });
    var exText = ex.map(function (e) { return (e.short || e.label) + " " + sizeVal(e, num(s.extra[e.key])); }).join("；");
    if (L || W || H) {
      lines.push("size: " + ["L", "W", "H"].map(function (k) { var v = num(s[k]); return dims[k].short + " " + (v ? sizeVal(dims[k], v) : "未填"); }).join(" × ") +
        (ex.length ? "；" + exText : ""));
      var r = ratios();
      if (r.length) lines.push("ratio: " + r.join("；"));
    } else if (ex.length) {
      lines.push("size: " + ["L", "W", "H"].map(function (k) { return dims[k].short; }).join("") + "未填；" + exText);
    } else {
      lines.push("size: " + (s.cant ? "暂时量不了" : "未填") + "（照参考图比例画，总览标「比例推定」）");
    }
    if (has(s.ref)) lines.push("size_ref: " + one(s.ref));
    var g = geo();
    if (g.length) { lines.push("geometry_prompt:"); g.forEach(function (l) { lines.push("- " + l); }); }

    var ph = Object.keys(st.photos);
    lines.push("photos: " + (ph.length ? ph.map(function (k) {
      return k + "=" + st.photos[k].name + (st.photos[k].replace ? "（替换）" : "（新增）");
    }).join("；") : "没有新照片"));
    if (has(st.notes)) lines.push("notes: " + one(st.notes));
    return lines.join("\n");
  }

  function setPhoto(slot, f) {
    var p = findPhoto(slot);
    st.photos[slot] = {name: f.name, replace: !!p.img};
    try { previews[slot] = URL.createObjectURL(f); } catch (e) {}
    save();
    render();
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target.closest ? ev.target.closest("[data-act],[data-zoom]") : null;
    if (!t) return;
    if (t.tagName === "IMG" && t.getAttribute("data-zoom")) {
      var z = document.getElementById("zoom");
      z.querySelector("img").src = t.src;
      z.style.display = "flex";
      return;
    }
    var act = t.getAttribute("data-act");
    if (act === "opt") {
      var qid = t.getAttribute("data-q"), i = +t.getAttribute("data-i"), a = st.q[qid] || {};
      if (a.i === i) delete a.i; else a.i = i;
      st.q[qid] = a;
      var box = document.getElementById("q-" + qid);
      box.querySelectorAll(".opt").forEach(function (o) { o.classList.toggle("on", +o.getAttribute("data-i") === a.i); });
      box.querySelector(".qwrite").style.display = (findQ(qid).write || []).indexOf(a.i) >= 0 ? "block" : "none";
      save();
    } else if (act === "bad") {
      var id = t.getAttribute("data-id"), x = st.x[id] || {};
      x.bad = !x.bad;
      st.x[id] = x;
      t.classList.toggle("on", x.bad);
      t.parentNode.classList.toggle("on", x.bad);
      var card = t.closest(".box");
      if (card) card.classList.toggle("bad", x.bad || !!st.t[id]);
      if (x.bad) t.parentNode.querySelector("textarea").focus();
      save();
    } else if (act === "add") {
      st.add.push({name: "", text: ""});
      save();
      render();
    } else if (act === "deladd") {
      st.add.splice(+t.getAttribute("data-i"), 1);
      save();
      render();
    } else if (act === "unphoto") {
      ev.preventDefault();
      var slot = t.getAttribute("data-slot");
      delete st.photos[slot];
      delete previews[slot];
      save();
      render();
    }
  });
  document.addEventListener("input", function (ev) {
    var t = ev.target, act = t.getAttribute && t.getAttribute("data-act");
    if (!act || act === "cant" || act === "file") return;
    if (act === "qtext") { var qid = t.getAttribute("data-q"), a = st.q[qid] || {}; a.text = t.value; st.q[qid] = a; }
    else if (act === "badtext") { var id = t.getAttribute("data-id"), x = st.x[id] || {}; x.text = t.value; st.x[id] = x; }
    else if (act === "addname") st.add[+t.getAttribute("data-i")].name = t.value;
    else if (act === "addtext") st.add[+t.getAttribute("data-i")].text = t.value;
    else if (act === "dim") { st.size[t.getAttribute("data-k")] = t.value; updGeo(); }
    else if (act === "extra") { st.size.extra[t.getAttribute("data-k")] = t.value; updGeo(); }
    else if (act === "sizeref") st.size.ref = t.value;
    else if (act === "notes") st.notes = t.value;
    else return;
    save();
  });
  document.addEventListener("change", function (ev) {
    var t = ev.target, act = t.getAttribute && t.getAttribute("data-act");
    if (act === "cant") { st.size.cant = t.checked; updGeo(); save(); }
    else if (act === "ptype") {
      var pid = t.getAttribute("data-id"), part = byId[pid] || {};
      if (t.value === part.type) delete st.t[pid]; else st.t[pid] = t.value;
      t.classList.toggle("on", !!st.t[pid]);
      var pbox = t.closest(".box");
      if (pbox) pbox.classList.toggle("bad", !!st.t[pid] || !!(st.x[pid] && st.x[pid].bad));
      save();
    }
    else if (act === "file" && t.files && t.files[0]) setPhoto(t.getAttribute("data-slot"), t.files[0]);
  });
  window.addEventListener("dragover", function (ev) {
    ev.preventDefault();
    var ph = ev.target.closest ? ev.target.closest(".ph") : null;
    document.querySelectorAll(".ph.drag").forEach(function (el) { if (el !== ph) el.classList.remove("drag"); });
    if (ph) ph.classList.add("drag");
  });
  window.addEventListener("drop", function (ev) {
    ev.preventDefault();
    var ph = ev.target.closest ? ev.target.closest(".ph") : null;
    document.querySelectorAll(".ph.drag").forEach(function (el) { el.classList.remove("drag"); });
    var f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
    if (ph && f) setPhoto(ph.getAttribute("data-slot"), f);
  });
  document.getElementById("zoom").addEventListener("click", function () { this.style.display = "none"; });
  document.getElementById("clear").addEventListener("click", function () {
    if (!window.confirm("清空你在这张表里的全部修改？AI 草稿不受影响。")) return;
    st = blank();
    previews = {};
    save();
    render();
    document.getElementById("out").style.display = "none";
  });
  document.getElementById("make").addEventListener("click", function () {
    var out = document.getElementById("result");
    out.value = buildOut();
    document.getElementById("out").style.display = "block";
    out.focus();
    out.select();
    try { navigator.clipboard.writeText(out.value); document.getElementById("make").textContent = "已复制，再生成一次"; } catch (e) {}
  });
  window.__utaProductOut = buildOut;
  render();
})();
