# 客户端兼容与安装

版本：0.2.0；核对日期：2026-11-05。

本项目采用 [Agent Skills 标准](https://agentskills.io/specification)，维护一套宿主中立的技能入口、数据协议和脚本。支持该规范且提供所需能力的 Agent 可以使用；安装目录、技能发现方式、执行权限仍由各宿主决定。

## 兼容层级

| 模式 | 宿主需要提供 | 可获得的结果 |
| --- | --- | --- |
| 完整流程 | 读取文件、Python 3.9+ 执行、任务目录写入 | 来源登记、数据校验、Markdown/CSV/JSON；可选Word和文本PDF读取 |
| 文本整理 | 能读取SKILL.md及参考资料，能处理用户文本 | Markdown草稿和问题清单；明确未运行脚本校验、未生成Word |
| 手动加载 | 没有原生Skill发现，但能读目录并执行指令 | 显式读取SKILL.md后，按宿主实际能力选择上面两种模式 |

没有文件读取、脚本或技能加载能力的纯聊天客户端，不能因收到ZIP就自动获得完整能力。网页端、云端和本地端也可能采用不同的文件/上传入口。

## 客户端目录与验证状态

下表路径均为**技能根目录**，其中放置 `customer-requirements-assistant/` 完整文件夹。不要只复制SKILL.md。

| 客户端 | 安装器参数 | 项目级目录 | 用户级目录 | 本项目验证状态 |
| --- | --- | --- | --- | --- |
| [Codex](https://learn.chatgpt.com/docs/build-skills) | `codex` | `.agents/skills/` | `~/.agents/skills/` | v0.2.0本机CLI发现与任务通过；缺Word依赖时正确降级 |
| [Claude Code](https://code.claude.com/docs/en/skills) | `claude` | `.claude/skills/` | `~/.claude/skills/` | 官方规范核对、安装器与脚本通过；客户端未实测 |
| [Cursor](https://cursor.com/docs/skills) | `cursor` | `.cursor/skills/` | `~/.cursor/skills/` | 官方规范核对、安装器与脚本通过；客户端未实测 |
| [GitHub Copilot / VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) | `copilot` | `.github/skills/` | `~/.copilot/skills/` | 官方规范核对、安装器与脚本通过；客户端未实测 |
| [Gemini CLI](https://geminicli.com/docs/cli/skills/) | `gemini` | `.gemini/skills/` | `~/.gemini/skills/` | 官方规范核对、安装器与脚本通过；客户端未实测 |
| [OpenCode](https://opencode.ai/docs/skills/) | `opencode` | `.opencode/skills/` | `~/.config/opencode/skills/` | 官方规范核对、安装器与脚本通过；客户端未实测 |
| 采用共享目录的宿主 | `generic` | `.agents/skills/` | `~/.agents/skills/` | 目录安装与脚本通过；须确认具体宿主支持此目录 |
| WorkBuddy | 使用专用ZIP | 客户端上传安装 | 客户端管理 | v0.1.0客户端导入/任务通过；v0.2.0专用包解压运行通过，未重测客户端导入 |
| 其他Agent | `--dest` | 由宿主配置指定 | 由宿主配置指定 | 提供标准包和手动加载方法，不保证原生发现 |

目录安装测试在隔离临时目录运行，不会安装或启动所有客户端。不要将本表理解为所有版本、操作系统或云端产品已实测。OpenCode如使用自定义配置根目录，应通过`--dest`传入实际技能根目录。

## 从仓库安装

在取得完整仓库后执行。仓库尚未公开时，下载或克隆需要相应访问权限。

```sh
# 安装到指定项目，只复制技能所需文件
python3 tools/install.py --client codex --project /path/to/your-project

# 替换客户端参数即可选择其他受支持目录
python3 tools/install.py --client claude --project /path/to/your-project
python3 tools/install.py --client cursor --project /path/to/your-project
python3 tools/install.py --client copilot --project /path/to/your-project
python3 tools/install.py --client gemini --project /path/to/your-project
python3 tools/install.py --client opencode --project /path/to/your-project

# 当前用户范围；默认为项目范围，不会自动全局安装
python3 tools/install.py --client codex --scope user

# 自定义技能根目录，安装器会在其下添加同名技能文件夹
python3 tools/install.py --dest /path/to/skills

# 技能根目录的父目录不可写或为挂载点时，显式指定可写的工作目录
# 工作目录必须在技能扫描根目录之外，并与目标位于同一文件系统
python3 tools/install.py --dest /path/to/skills --work-dir /path/to/writable-state

# 只查看目标位置，不写文件
python3 tools/install.py --client codex --scope user --dry-run
```

Windows可将`python3`替换为已安装的`py -3`或`python`，路径按本机实际位置填写。安装器不会安装依赖、修改客户端设置、注册MCP或添加自动执行授权。

### 更新与撤回

同名目标已存在时默认拒绝覆盖。确认要更新后，在原安装命令后加`--replace`，安装器默认先把旧目录移到该客户端`skills/`同级的`skill-backups/`，再部署新目录，并输出备份路径。备份位于原生技能扫描目录之外。使用`--work-dir`时，临时复制与`skill-backups/`改放在该目录中；它必须可写、位于技能扫描目录之外，且与技能目录在同一文件系统。安装器在返回结果中打印实际工作目录和备份路径。

回退时先将当前技能目录移到其他位置，再把备份恢复到原位置；重新加载客户端。安装器拒绝目标目录链中的符号链接，避免更改意外位置；项目根目录本身会先解析为实际路径。若使用自定义递归扫描根目录，务必确保备份目录不在其他已配置的扫描范围内。

## 从安装包手动安装

- **标准包**：[customer-requirements-assistant-0.2.0.zip](../releases/0.2.0/customer-requirements-assistant-0.2.0.zip)。解压后，将完整同名目录放到上表的技能根目录中，避免多嵌套一层文件夹。
- **WorkBuddy包**：[customer-requirements-assistant-workbuddy-0.2.0.zip](../releases/0.2.0/customer-requirements-assistant-workbuddy-0.2.0.zip)。在WorkBuddy的技能页面选择添加/上传技能，按客户端提示导入。

标准包的SKILL.md只有`name`和`description`两个通用字段。`agents/openai.yaml`用于Codex显示信息，其他宿主可以忽略。WorkBuddy包的展示字段由`distribution/workbuddy.json`在构建时注入；两个包共用同一正文、脚本和参考资料。

## 调用与发现

安装后，在客户端的技能列表中查找`customer-requirements-assistant`，必要时重新加载或新建会话。可以用自然语言明确要求“使用客户需求整理助手”，或使用宿主的技能选择器。

Codex可以显式使用`$customer-requirements-assistant`；Claude Code和Cursor可在斜杠菜单中选择技能。自动发现、自动选择和成功执行是不同步骤，安装成功不代表每次都会自动调用。

## 没有原生Skill入口的Agent

解压标准包，将它放入Agent可读取的位置，然后提交：

```text
请读取 /实际路径/customer-requirements-assistant/SKILL.md，
并按其中引用的数据规范和运行说明整理我提供的客户资料。
使用你已有的文件读取、执行和输出能力；如果不能运行Python，
请按同一规范生成Markdown草稿，明确没有执行脚本校验。
```

实际路径须由用户或宿主提供。不要把项目维护用`Agent.md`或`AGENTS.md`当成技能正文，也不要覆盖已有的客户端全局规则文件。未列出的宿主采用此方式接入时，仍需验证它是否读完参考资料、正确生成文件并保留待确认状态。

## 版本与证据

[v0.2.0验证报告](../evidence/0.2.0/verification.md) · [v0.1.0 WorkBuddy实测](../evidence/verification.md) · [变更记录](../CHANGELOG.md)
