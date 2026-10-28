# 可视化模板库（viz-templates）——兜底自绘用

> **兜底模板库**：当宿主无可视化工具（SKILL.md 第五节路由第 4 层）时套用本库模板自绘 SVG 单图 / HTML 看板，不从零自绘；宿主已装可视化工具（doubao-visualization / visualize / WorkBuddy 组件）时优先走工具通道，不用本库。
> 演进：2026-09-24 泛化调研实测（ZCode 桌面端图片内联渲染成功，SVG 直呈对话流）→ 2026-10-28 路由化改版后定位为兜底层。

## 一、选模板决策

| 交付需求 | 选哪个 | 说明 |
| --- | --- | --- |
| 单图直呈 | **模板 A（SVG 条形图，首选）** | 一次 Write 即成，图片内联直呈对话流 |
| 折线 / 环形单图 | 模板 A 的 **A2 / A3** | 同为 SVG 单文件，零依赖 |
| 多图或交互 | **模板 B（零依赖 HTML）** | 默认；内网安全，无任何外部引用 |
| CDN 可达且需强交互 | 模板 C（ECharts） | 需 tooltip / 图例切换 / 下钻时 |
| 留档 PNG | **不在本库** | 仅留档场景，走 Python 且须 visual-judge 验收 |

## 二、通用规范（三套模板共用）

- **配色语义**（与 `dashboard-playbook.md` 第二节一致）：P0 红 `#d93025`、P1 橙 `#e8710a`、P2 黄 `#f9ab00`、P3 蓝 `#1a73e8`、正常/达标 绿 `#188038`、正文 `#333333`、次要 `#888888`；同一看板主色 ≤ 4 种。
- **字体**：`Microsoft YaHei, PingFang SC, sans-serif`（系统字体，不引外部字体文件）。
- **每图必含**：标题、来源标注（格式「来源：{实体名}（{环境}，{日期}）」）。
- **数值同源**：图上数值必须等于工具返回值，禁止为美观修数（违反「禁止重判」优先）。
- **名称规范**：仓库/工厂/物料/SKU 一律「中文名称（编码）」，图上禁止只写编码。
- **文件命名**：`viz_<主题>_<yyyymmdd>.svg` / `.html`（例 `viz_warehouse_risk_20260924.svg`）。
- **交付方式**：桌面端宿主用 `![]({绝对路径})` 内联直呈（ZCode 实测可用）；HTML 看板生成后按宿主能力打开（ZCode 用 browser-use 新建标签页 / WorkBuddy `present_files`）并同时给出文件链接。
- **色盲友好（冗余编码）**：同图用红与绿区分语义时（如 P0 红与正常绿并存的风险图），必须叠加颜色之外的冗余编码——符号（条外标注 ⚠ / ✓）、条长差或描边样式，不得仅靠颜色传达判定。
- **零基线**：数值型条形/柱形长度与数值成正比且从零起算，禁止截断坐标轴或非零基线放大差异；等级型序数映射（P0=4~无=0）天然满足。
- **克制装饰**：不使用 3D 效果、阴影和渐变填充；单图信息不过载——超过 ~12 个数据条时取 Top N 并注明「共 N 条取前 M」，不为全量而堆砌。

## 三、模板 A：SVG 单图——横向条形图（首选）

画布约定（与 2026-09-24 实测通过样例一致）：宽 720、行距 48px、条高 26px、条起点 x=160、标签右对齐于 x=150、条内标注 x=175。

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{{SVG高度}}" font-family="Microsoft YaHei, PingFang SC, sans-serif">
  <!-- 文件名：viz_{{主题}}_{{yyyymmdd}}.svg ｜ 模板 A：横向条形图 -->
  <!-- 外框白底 -->
  <rect width="720" height="{{SVG高度}}" fill="#ffffff"/>
  <!-- 居中加粗标题 -->
  <text x="360" y="34" text-anchor="middle" font-size="18" font-weight="bold" fill="#1a1a1a">{{标题：一句话说明谁多谁少}}</text>

  <!-- ===== 数据行：每行一组，按序复制 N 次（首行基线 y=84、条顶 y=66，其后每行 +48）===== -->
  <text x="150" y="{{行基线y}}" text-anchor="end" font-size="14" fill="#333333">{{实体中文名称（编码）}}</text>
  <rect x="160" y="{{条顶y＝行基线y－18}}" width="{{条长px}}" height="26" rx="4" fill="{{语义色}}"/>
  <!-- 标注二选一：深色长条 → 条内白字；浅/短条 → 条右外深灰字 -->
  <text x="175" y="{{行基线y}}" font-size="12" fill="#ffffff">{{条内标注}}</text>
  <text x="{{条右端x＋8}}" y="{{行基线y}}" font-size="12" fill="#333333">{{条外标注}}</text>

  <!-- ===== 底部等级刻度：五档竖线（等级型图必含；数值型图改刻数值或删去此段）===== -->
  <line x1="160" y1="{{刻度线y}}" x2="160" y2="{{刻度线y＋6}}" stroke="#999999" stroke-width="1"/>
  <text x="160" y="{{刻度文字y}}" text-anchor="middle" font-size="11" fill="#888888">无风险</text>
  <line x1="280" y1="{{刻度线y}}" x2="280" y2="{{刻度线y＋6}}" stroke="#999999" stroke-width="1"/>
  <text x="280" y="{{刻度文字y}}" text-anchor="middle" font-size="11" fill="#888888">P3</text>
  <line x1="400" y1="{{刻度线y}}" x2="400" y2="{{刻度线y＋6}}" stroke="#999999" stroke-width="1"/>
  <text x="400" y="{{刻度文字y}}" text-anchor="middle" font-size="11" fill="#888888">P2</text>
  <line x1="520" y1="{{刻度线y}}" x2="520" y2="{{刻度线y＋6}}" stroke="#999999" stroke-width="1"/>
  <text x="520" y="{{刻度文字y}}" text-anchor="middle" font-size="11" fill="#888888">P1</text>
  <line x1="640" y1="{{刻度线y}}" x2="640" y2="{{刻度线y＋6}}" stroke="#999999" stroke-width="1"/>
  <text x="640" y="{{刻度文字y}}" text-anchor="middle" font-size="11" fill="#888888">P0</text>

  <!-- ===== 左下角来源标注 ===== -->
  <text x="20" y="{{SVG高度－12}}" font-size="11" fill="#888888">来源：{{实体名}}（{{环境}}，{{日期}}）</text>
</svg>
```

**条长换算两条规则**：

1. **数值型**：按最大值归一化——最长条固定 480px，其余 `条长px = 480 × 数值 ÷ 最大值`（无风险且数值为 0 时给 12px 占位条 + 绿色「当前无风险记录」条外标注）。
2. **等级型**：按严重度序数映射条长——P0=4 / P1=3 / P2=2 / P3=1 / 无=0，每单位 120px（即 P0 条 480px 对齐最右刻度），且须在图注或文中注明「**序数仅作条长展示映射，非库存数值**」。

标注配色：条内文本用白色（深色条：红/橙/蓝），条外文本用深灰 `#333333`（浅/短条：黄、绿占位条）；条外标注起点 x = 条右端 + 8。

### A2 折线图（时间趋势）

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{{SVG高度}}" font-family="Microsoft YaHei, PingFang SC, sans-serif">
  <!-- 文件名：viz_{{主题}}_{{yyyymmdd}}.svg ｜ 模板 A2：折线图（时间趋势） -->
  <rect width="720" height="{{SVG高度}}" fill="#ffffff"/>
  <text x="360" y="34" text-anchor="middle" font-size="18" font-weight="bold" fill="#1a1a1a">{{标题}}</text>
  <!-- Y 轴参考网格线 + 刻度（至少 0 / 中值 / 最大值三条；y 按数值线性换算）-->
  <line x1="80" y1="{{网格y}}" x2="700" y2="{{网格y}}" stroke="#eeeeee" stroke-width="1"/>
  <text x="72" y="{{网格y＋4}}" text-anchor="end" font-size="11" fill="#888888">{{刻度值}}</text>
  <!-- 数据折线：points 为按数据换算的 x,y 对序列（可多系列各一条 polyline）-->
  <polyline points="{{x1}},{{y1}} {{x2}},{{y2}} {{x3}},{{y3}} {{x4}},{{y4}}" fill="none" stroke="{{语义色}}" stroke-width="2"/>
  <!-- 数据点（每折线点一个）-->
  <circle cx="{{x}}" cy="{{y}}" r="3" fill="{{语义色}}"/>
  <!-- X 轴时间标签（每个数据点一个）-->
  <text x="{{x}}" y="{{X轴文字y}}" text-anchor="middle" font-size="11" fill="#888888">{{时间标签}}</text>
  <!-- 图例（多系列时每系列一条）-->
  <text x="{{图例x}}" y="{{图例y}}" font-size="12" fill="#333333">— {{系列名}}</text>
  <!-- 左下角来源标注 -->
  <text x="20" y="{{SVG高度－12}}" font-size="11" fill="#888888">来源：{{实体名}}（{{环境}}，{{日期}}）</text>
</svg>
```

### A3 环形图（占比，分类 ≤ 5）

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{{SVG高度}}" font-family="Microsoft YaHei, PingFang SC, sans-serif">
  <!-- 文件名：viz_{{主题}}_{{yyyymmdd}}.svg ｜ 模板 A3：环形图（占比，分类 ≤ 5） -->
  <rect width="720" height="{{SVG高度}}" fill="#ffffff"/>
  <text x="360" y="34" text-anchor="middle" font-size="18" font-weight="bold" fill="#1a1a1a">{{标题}}</text>
  <!-- 环形：r=80，周长 ≈ 502.65；分段计算：每段弧长 = 502.65 × 占比%，第 i 段 dashoffset = -(前 i-1 段弧长之和)；rotate(-90) 从 12 点钟方向起笔 -->
  <g transform="rotate(-90 {{圆心x}} {{圆心y}})">
    <circle cx="{{圆心x}}" cy="{{圆心y}}" r="80" fill="none" stroke="#f1f3f4" stroke-width="30"/>
    <circle cx="{{圆心x}}" cy="{{圆心y}}" r="80" fill="none" stroke="{{语义色}}" stroke-width="30" stroke-dasharray="{{弧长}} 502.65" stroke-dashoffset="{{-累计偏移}}"/>
  </g>
  <!-- 中心文本：总量或主占比 -->
  <text x="{{圆心x}}" y="{{圆心y－6}}" text-anchor="middle" font-size="26" font-weight="bold" fill="#333333">{{中心数值}}</text>
  <text x="{{圆心x}}" y="{{圆心y＋18}}" text-anchor="middle" font-size="12" fill="#888888">{{中心标签}}</text>
  <!-- 右侧图例（每分类一行）-->
  <rect x="{{图例x}}" y="{{图例y}}" width="12" height="12" rx="2" fill="{{语义色}}"/>
  <text x="{{图例x＋18}}" y="{{图例y＋10}}" font-size="13" fill="#333333">{{分类中文名称（编码）}} {{数值}}（{{百分比}}%）</text>
  <!-- 左下角来源标注 -->
  <text x="20" y="{{SVG高度－12}}" font-size="11" fill="#888888">来源：{{实体名}}（{{环境}}，{{日期}}）</text>
</svg>
```

## 四、模板 B：零依赖 HTML 看板（默认）

单文件、无任何外部引用（无 CDN、无外部字体、无 JS——纯 CSS + 内联 SVG），内网安全。内置豆包式四段骨架：结论段（最前）→ 口径行 → 图表区 → 明细表 → 洞察结语。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{{看板标题}}</title>
<!-- 文件名：viz_{{主题}}_{{yyyymmdd}}.html ｜ 模板 B：零依赖 HTML 看板（纯 CSS + 内联 SVG，无 JS）-->
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #333333; background: #f5f6f8; margin: 0; padding: 24px; }
  .card { background: #ffffff; border-radius: 8px; padding: 16px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  h1 { font-size: 20px; margin: 0 0 8px; }
  h2 { font-size: 15px; margin: 0 0 12px; }
  .conclusion { font-size: 15px; font-weight: bold; border-left: 4px solid #1a73e8; padding: 8px 12px; background: #f8f9fa; }
  .meta { font-size: 12px; color: #888888; line-height: 1.8; }
  /* 语义色 class（配色见通用规范） */
  .p0 { background: #d93025; } .p1 { background: #e8710a; } .p2 { background: #f9ab00; }
  .p3 { background: #1a73e8; } .ok { background: #188038; }
  /* 横向条形图：外层轨道灰底圆角，内层条按百分比宽度 */
  .bar-row { display: flex; align-items: center; margin: 8px 0; }
  .bar-label { width: 240px; font-size: 13px; text-align: right; padding-right: 12px; flex-shrink: 0; }
  .bar-track { flex: 1; background: #f1f3f4; border-radius: 4px; height: 22px; }
  .bar-fill { height: 22px; border-radius: 4px; min-width: 2px; }
  .bar-value { margin-left: 8px; font-size: 12px; white-space: nowrap; }
  /* 明细表：斑马纹 */
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th { background: #f8f9fa; text-align: left; padding: 8px 10px; border-bottom: 2px solid #e0e0e0; }
  td { padding: 7px 10px; border-bottom: 1px solid #eeeeee; }
  tr:nth-child(even) td { background: #fafafa; }
  .tag { color: #ffffff; border-radius: 3px; padding: 1px 8px; font-size: 12px; }
  .note { font-size: 12px; color: #888888; margin-top: 8px; }
  .insight { font-size: 14px; line-height: 1.7; }
</style>
</head>
<body>

<!-- ⓪ 结论段（最前：一句话结论先说答案） -->
<div class="card">
  <h1>{{看板标题}}</h1>
  <div class="conclusion">结论：{{一句话结论，先说答案}}</div>
</div>

<!-- ① 口径行：来源 / 时间 / 范围 / 指标定义 -->
<div class="card">
  <div class="meta">口径：来源 {{实体名}}（{{环境}}）｜时间 {{数据时间戳或查询时间}}｜范围 {{仓群/工厂群/筛选条件}}｜指标定义 {{口径一句话}}</div>
</div>

<!-- ② 图表区：横向条形图（div 宽度百分比实现，零 JS） -->
<div class="card">
  <h2>{{图表标题：谁多谁少}}</h2>
  <!-- 对每行数据复制以下一组；width = 该行数值 ÷ 最大值 × 100%；等级型按序数映射（P0=4/P1=3/P2=2/P3=1/无=0，除以 4 × 100%） -->
  <div class="bar-row">
    <div class="bar-label">{{实体中文名称（编码）}}</div>
    <div class="bar-track">
      <div class="bar-fill {{p0|p1|p2|p3|ok}}" style="width: {{百分比}}%"></div>
    </div>
    <div class="bar-value">{{数值}}（{{判定}}）</div>
  </div>
  <!-- 折线 / 饼图：嵌内联 SVG（骨架套用本文件模板 A2 / A3） -->
  <div class="note">{{条长口径注记：按最大值归一化；或「序数仅作条长展示映射，非库存数值」}}</div>
</div>

<!-- ③ 明细表：承载逐条证据，可溯源（>20 行取前 10 并注明可展开） -->
<div class="card">
  <h2>明细（Top {{10}}）</h2>
  <table>
    <tr><th>{{维度列}}</th><th>{{指标1}}</th><th>{{指标2}}</th><th>判定</th></tr>
    <!-- 对每行数据复制以下一行；判定 tag 的 class 用 p0/p1/p2/p3/ok 之一 -->
    <tr><td>{{实体中文名称（编码）}}</td><td>{{数值1}}</td><td>{{数值2}}</td><td><span class="tag {{p0|p1|p2|p3|ok}}">{{判定}}</span></td></tr>
  </table>
  <div class="note">共 {{N}} 条，取最相关前 10 行；可展开完整明细</div>
</div>

<!-- ④ 洞察结语：差异点 + 归因 + 建议动作 -->
<div class="card">
  <div class="insight"><b>洞察</b>：{{差异点 + 归因}}。<b>建议动作</b>：{{下一步做什么}}</div>
  <div class="note">来源：{{实体名}}（{{环境}}，{{日期}}）｜生成：viz_{{主题}}_{{yyyymmdd}}.html（模板 B，零依赖）</div>
</div>

</body>
</html>
```

## 五、模板 C：ECharts CDN 看板（增强，外网/CDN 可达时）

**何时用**：目标环境可达 jsdelivr / unpkg 公网 CDN，且交付需要 tooltip、图例切换、下钻交互——否则一律用模板 B。CDN 地址仅本模板出现，不移植到其他模板。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{{看板标题}}</title>
<!-- 文件名：viz_{{主题}}_{{yyyymmdd}}.html ｜ 模板 C：ECharts CDN 看板（仅外网/CDN 可达环境） -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #333333; background: #f5f6f8; margin: 0; padding: 24px; }
  .conclusion { font-size: 15px; font-weight: bold; border-left: 4px solid #1a73e8; padding: 8px 12px; background: #ffffff; border-radius: 4px; }
  .meta { font-size: 12px; color: #888888; margin: 12px 0 16px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .card { background: #ffffff; border-radius: 8px; padding: 8px 16px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .full { grid-column: 1 / -1; }
  .chart { width: 100%; height: 320px; }
  .note { font-size: 12px; color: #888888; margin-top: 8px; }
</style>
</head>
<body>

<div class="conclusion">结论：{{一句话结论，先说答案}}</div>
<div class="meta">口径：来源 {{实体名}}（{{环境}}）｜时间 {{数据时间戳}}｜范围 {{筛选条件}}｜指标定义 {{口径一句话}}</div>

<div class="grid">
  <div class="card full"><div id="bar" class="chart"></div></div>
  <div class="card"><div id="line" class="chart"></div></div>
  <div class="card"><div id="pie" class="chart"></div></div>
</div>
<div class="note">来源：{{实体名}}（{{环境}}，{{日期}}）｜生成：viz_{{主题}}_{{yyyymmdd}}.html（模板 C，ECharts）</div>

<script>
// 全部图表数据集中一处：内联 JSON（数值必须等于工具返回值，禁止修数）
var DATA = {{DATA：内联 JSON，如 {"bar":[{"name":"苏州区域仓（WH002）","value":3,"level":"p0"}],"line":{"dates":["08-01"],"series":[{"name":"缺货量","data":[3]}]},"pie":[{"name":"P0","value":3}]}} }};
var COLORS = { p0: '#d93025', p1: '#e8710a', p2: '#f9ab00', p3: '#1a73e8', ok: '#188038' };

// 图 1：横向条形图（谁多谁少，首选形态）
echarts.init(document.getElementById('bar')).setOption({
  title: { text: '{{图表标题：谁多谁少}}', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: {},
  grid: { left: 200 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: DATA.bar.map(function (d) { return d.name; }) },
  series: [{ type: 'bar', data: DATA.bar.map(function (d) { return { value: d.value, itemStyle: { color: COLORS[d.level] || '#1a73e8' } }; }) }]
});

// 图 2：折线图（时间趋势）
echarts.init(document.getElementById('line')).setOption({
  title: { text: '{{图表标题：时间趋势}}', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0 },
  xAxis: { type: 'category', data: DATA.line.dates },
  yAxis: { type: 'value' },
  series: DATA.line.series.map(function (s) { return { name: s.name, type: 'line', data: s.data }; })
});

// 图 3：环形图（占比，分类 ≤ 5）
echarts.init(document.getElementById('pie')).setOption({
  title: { text: '{{图表标题：占比}}', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'item' },
  series: [{ type: 'pie', radius: ['45%', '70%'], data: DATA.pie.map(function (d) { return { name: d.name, value: d.value, itemStyle: { color: COLORS[d.level] || '#1a73e8' } }; }) }]
});
</script>

</body>
</html>
```

> **CDN 不可达时回落模板 B**，不修网络、不换源重试超过一次。

## 六、自绘例外与验收

- 模板覆盖不了的图形允许自绘，**配色 / 来源 / 口径 / 名称四规范必须保持**。
- 对话内 SVG/HTML 交付**免 visual-judge**（模板保证结构）；**PNG 留档交付仍须 visual-judge 验收**。
