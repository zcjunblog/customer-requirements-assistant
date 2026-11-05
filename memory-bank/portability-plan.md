# v0.2.0 多客户端适配计划

2026-11-05。用户要求从WorkBuddy专用定位升级为通用Agent Skill；本轮实施并同步GitHub。

## 实现选择

维护一套标准SKILL.md与核心脚本；WorkBuddy展示字段在打包时注入。客户端差异放在安装器和安装指南中，不复制业务实现。按Agent Skills开放规范组织，不预设所有客户端都能执行Python或自动识别Skill。

- [x] 源码迁移至skills/customer-requirements-assistant，使用通用元数据和宿主中立表达。
- [x] 标准包与WorkBuddy包分别构建，版本0.2.0；保留0.1.0历史包。
- [x] 安装器支持Codex、Claude Code、Cursor、Copilot、Gemini CLI、OpenCode及自定义目录；默认项目范围，显式覆盖先备份，不安装依赖或修改客户端设置。
- [x] 安装/构建回归测试先验证失败，再实现；运行原有业务测试。
- [x] 包解压后执行核心流程；有条件时进行Codex实际客户端发现与任务测试。
- [x] README、宣传图、兼容矩阵、memory-bank与GitHub同步；分别标记规范适配、安装验证与客户端实测。

## 能力分层

完整模式需要读取文件与Python 3.9+执行能力，Word/PDF使用可选依赖。仅能读取文件的Agent可按规范产出Markdown，明确未进行脚本校验。没有文件、执行或Skill加载能力的纯聊天客户端不承诺一键安装。

## 验证依据

规范：https://agentskills.io/specification
Codex：https://learn.chatgpt.com/docs/build-skills
Claude Code：https://code.claude.com/docs/en/skills
Cursor：https://cursor.com/docs/skills
Copilot：https://code.visualstudio.com/docs/agent-customization/agent-skills
Gemini CLI：https://geminicli.com/docs/cli/skills/
OpenCode：https://opencode.ai/docs/skills/

上述页面本轮已读取。WorkBuddy保留此前实测元数据格式，本轮官方页面暂时获取超时；新版包解压运行不等同于新版客户端导入测试。
