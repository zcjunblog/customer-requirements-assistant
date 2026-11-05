# 客户需求整理助手 v0.1.0 实施计划

日期：2026-11-05。依据：design.md；用户已授权开发、打包及同步 GitHub。

目标：交付独立 WorkBuddy ZIP，含模型工作流、结构化数据规范、资料读取、证据校验、Markdown/CSV/Word 导出、四行业样例和验证记录。

方案：Python 3.9+ 标准库处理文本、DOCX 读取、数据校验和基础输出；python-docx 用于 Word，pypdf 用于 PDF 文本提取，两项可选并检测缺失。模型由 WorkBuddy 提供，不接额外模型 API。源码在 skills/customer-requirements-assistant。开发在当前专用项目的功能分支进行，保留用户熟悉的路径。

## 任务与接口

- [x] T1 读取：`scripts/intake.py: ingest(paths, previous=None) -> bundle`；TXT/MD 行、DOCX 段落和表格单元格、PDF 页；逐文件错误、总量限制、来源稳定 ID、原文不改。测试空输入、混合有效与无效文件、扫描页、重复来源、超限。
- [x] T2 校验：`scripts/validate.py: validate(model,bundle,previous=None) -> {errors,warnings}`；精确引文、数字、引用 ID、事实/建议、确认凭据、冲突、修订。测试伪造引文/数字/确认、重复 ID、错误类型、删除和来源丢失。
- [x] T3 输出：`scripts/render.py: render(model,bundle,out,docx_mode,previous=None) -> manifest`；新建版本目录、MD/CSV/DOCX、追溯、问题、变更、覆盖说明；文档缺依赖明确降级。测试CSV公式注入、完整内容、中文、失败与防覆盖。
- [x] T4 Skill：SKILL.md、references/schema.md、行业提示、模板、运行说明；四行业虚构样例。先无技能基线，再独立使用技能实际产出；不将人工样例的正确性当成模型泛化证明。
- [x] T5 交付：ZIP 白名单打包、离线完整性校验、解压运行、真实 WorkBuddy 导入与任务测试、文档渲染检查、独立代码审查、同步项目记忆与 GitHub。

每个工具任务先写有意义的失败测试，再实现并通过；命令 `python3 -m unittest discover -s tests -v`。Word 验证用宿主提供的 bundled Python 与 LibreOffice，并查看所有页面。

## 全局约束与审查重点

- 默认是需求确认草稿；明确提出与客户确认是两个维度。
- 保留数字与原文来源、冲突双方、修订历史；脚本不能证明自然语言蕴含，语义需模型/人工复核。
- 不自动访问账号、发送消息、报价或提交审核。
- 无法读取的资料、扫描 PDF 页、无依赖环境、超长输入不得静默省略。
- 文件名含空格或中文、JSON异常类型、CSV公式、DOCX XML特殊字符、相同文件名、重复执行和修订是测试重点。
- 本地自动测试、独立代理测试、真实客户端测试、真实用户试用分别记录，未做项目不勾选。

## 执行记录

- 基线：独立代理对培训样例保留了日期、人数和录播的不确定性，未观察到臆造确认。不能声称技能修复了基线已有的事实问题；后测重点验证结构化来源及可用文件。
- Ruling：用户已明确按现有设计开发，不重复请求方案批准；采用设计推荐方案并将可选依赖和限制写入交付说明。

- 完成记录：24项完整依赖测试通过；四行业ZIP流程通过；8页样例Word和4页实际客户端Word逐页检查；WorkBuddy V5.9.3导入与真实任务成功。详细限制及复验材料见evidence/verification.md；GitHub同步由最终提交与远程核对留痕。
