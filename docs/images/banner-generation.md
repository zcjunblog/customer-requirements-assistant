# README 宣传图生成记录

- 日期：2026-11-05。
- 资源：`customer-requirements-banner.png`。
- 工具：内置 imagegen；初版生成后根据用户要求编辑为白蓝办公风格，未使用 CLI/API 回退。
- 参考：用户提供的 Media Resolver README 截图，仅保留横幅构图；最终按用户要求采用白底、浅蓝背景、深蓝文字与蓝色强调。未将原截图加入仓库。
- 用途：README 产品宣传头图；右侧文档卡片为概念示意，不是产品界面截图。
- 检查：标题、说明和卡片中文可读；无裁切、无许可证或已开源声明。图片按原始生成结果保存。

## 白蓝办公风格编辑提示词

```text
Edit the supplied README banner for 客户需求整理助手. Change its color scheme to a bright professional WHITE AND BLUE office productivity aesthetic. Preserve the exact 3:1 aspect ratio, all wording, Chinese characters, layout, hierarchy, margins, large one-line title, right-hand document card and rounded corners.
Replace dark charcoal/brown background with clean near-white #f8fbff, subtle pale blue wash toward the right. Keep only a barely visible pale blue grid. Main title deep navy #15345b. Subtitle and body slate blue-gray, high contrast. Replace ALL peach/orange accents with clear professional blue #2875df. Right-hand document card white with thin pale blue border and restrained soft blue shadow; heading navy; row numbers blue; separators pale blue. Footer blue-gray. Use a clean, airy, calm business-document look; no dark background, no orange, no busy decorative additions.
Keep text EXACTLY:
WORKBUDDY SKILL
客户需求整理助手
把零散沟通，整理成清晰的交付依据。
从沟通记录到需求确认草稿
WORD  /  MARKDOWN  /  CSV
需求确认草稿
01  交付范围
02  待确认问题
03  需求追溯
有来源 · 可核对 · 可修订
No new text, no watermark, no browser frame. Render crisp legible typography.
```

## 初版生成提示词（深色方案，已替换）

```text
Use case: ads-marketing.
Create ONE finished professional GitHub README promotional banner for the software skill "客户需求整理助手". This is the banner artwork only, no GitHub browser chrome, no page screenshot.
Ultra-wide landscape aspect ratio 3:1, target 1800x600, clean precise typography. Visual direction: understated premium developer-tool branding, nearly black charcoal background subtly warming to dark brown on the right, an extremely subtle fine grid, restrained peach accent #f4a883, ivory text. Broad calm negative space, 16px rounded outer corners. Crisp modern Chinese sans serif, editorial layout and strong hierarchy, no cartoon, no photo, no excessive glows or 3D.
Composition: left two-thirds is a strong text block with comfortable 70px outer margin, right third is a thin peach/brown outlined elegant document panel with three neatly aligned rows. It is a conceptual illustration of the outputs, not a real application screenshot. Match the polished dark wide README banner style with big left title and small right code/document card.
Exact text, render all Chinese correctly and legibly; no additional copy:
Left eyebrow with a small peach horizontal rule: "WORKBUDDY SKILL"
Left large bold primary title on ONE LINE: "客户需求整理助手"
Left understated subtitle: "把零散沟通，整理成清晰的交付依据。"
Below a fine divider, a peach line: "从沟通记录到需求确认草稿"
Small spaced footer: "WORD  /  MARKDOWN  /  CSV"
Right panel heading: "需求确认草稿"
Right panel rows with subtle separators: "01  交付范围", "02  待确认问题", "03  需求追溯"
Panel footer small: "有来源 · 可核对 · 可修订"
The entire layout must stay inside generous safe margins, title must be dominant, right panel narrower and secondary, no brand logos, no license badge, no OPEN SOURCE claim, no watermark, no invented interface buttons. Professional, restrained, confident.
```

## v0.2.0 通用定位编辑

使用内置imagegen保留白蓝布局与全部业务文案，仅将WORKBUDDY SKILL改为AGENT SKILL。成图已查看，文字可读、比例3:1。

```text
Edit this existing white-and-blue office productivity README banner. Change ONLY the top-left English eyebrow text from "WORKBUDDY SKILL" to "AGENT SKILL". Preserve all other Chinese and English wording exactly, preserve the large Chinese title 客户需求整理助手, the blue-white palette, layout, 3:1 aspect ratio, right document card, margins, typography and all other visual content. No additions. Clean legible text.
```
