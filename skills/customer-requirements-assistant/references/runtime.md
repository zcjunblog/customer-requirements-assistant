# 运行与故障处理

## 定位与依赖

脚本路径相对本SKILL.md；先取得技能的实际安装路径，不假定它在当前工作目录。以下 `SKILL_DIR` 和 `TASK_DIR` 为说明占位，执行前替换为真实绝对路径并正确引用。macOS/Linux用可用的Python 3.9+，Windows用`py -3`或`python`。

```sh
python3 "SKILL_DIR/scripts/requirements_tool.py" doctor
python3 "SKILL_DIR/scripts/requirements_tool.py" ingest "TASK_DIR/客户沟通.txt" --out "TASK_DIR/sources-v1.json"
```

由模型读取sources-v1.json，根据数据协议生成 `requirements-v1.json`（从模板复制并填写）。然后：

```sh
python3 "SKILL_DIR/scripts/requirements_tool.py" validate --model "TASK_DIR/requirements-v1.json" --sources "TASK_DIR/sources-v1.json"
python3 "SKILL_DIR/scripts/requirements_tool.py" render --model "TASK_DIR/requirements-v1.json" --sources "TASK_DIR/sources-v1.json" --out "TASK_DIR/outputs" --docx auto
```

`--docx auto`：能生成则生成Word，缺依赖时交付MD/CSV并在报告中说明。`required`：Word不可用就报错，不伪称成功。`off`：仅基础格式。

Word需要`python-docx`，PDF读取需要`pypdf`。优先使用宿主已提供的环境。若需安装，使用任务专用虚拟环境及包内`requirements-optional.txt`，遵循当前宿主的安装授权规则；不改全局环境，不在用户不知情时联网安装。无依赖也能处理TXT/MD/DOCX正文并生成MD/CSV。

## 修订

```sh
python3 "SKILL_DIR/scripts/requirements_tool.py" ingest "TASK_DIR/补充沟通.txt" --previous "TASK_DIR/sources-v1.json" --out "TASK_DIR/sources-v2.json"
python3 "SKILL_DIR/scripts/requirements_tool.py" render --model "TASK_DIR/requirements-v2.json" --sources "TASK_DIR/sources-v2.json" --previous "TASK_DIR/requirements-v1.json" --out "TASK_DIR/outputs" --docx auto
```

模型负责更新需求并填写变更原因。导出自动生成版本变化文件并保留上一版需求JSON；不会覆盖旧版本。

## 限制

- 每次最多20个输入文件、累计40个来源、单文件5MiB、单来源20万字符、累计50万字符；超限报错而非截断。模型上下文小于这些上限时仍需分批阅读。
- TXT/MD支持UTF-8及GB18030回退。DOCX读取正文段落/表格，忽略图片、批注、页眉页脚、文本框；有修订记录时应提供接受修订后的副本并核对。
- PDF最多100页，只提取文本层；扫描页列为未读取，不含OCR。PDF表格阅读顺序需人工复核。`.doc`、录音和图片不在首版脚本输入范围内。
- 来源文件只读；`ingest --out`拒绝覆盖现有文件；每次render创建新目录。
- 每个来源保存文件名、SHA256与精确位置；相同文件名加相同摘要去重，内容变化产生新来源。
- 工具不扫描目录、不下载资料、不发网络请求。JSON和来源索引含原文，保留在受控任务目录内，勿直接发客户。
- `validate` 非零退出表示数据错误；先修正提取结果，不修改来源索引绕过校验。`ingest`全部失败返回2，部分失败返回0并显示失败列表。
- 输出清单和校验报告记录Word状态及限制；Word生成不代表版式已检查。默认中文字体按系统选择 Heiti SC（macOS）、Microsoft YaHei（Windows）、Noto Sans CJK SC（Linux）；可用 CRA_CJK_FONT 指定已安装字体。跨设备打开需检查字体替换；包内不附带字体。

## 手动降级

Python不可用或不允许执行脚本时，按相同字段直接生成Markdown草稿与问题清单，附原文位置并明确未做脚本检查。宿主若能直接生成Word，可使用已可用的文档工具；必须保留相同内容与草稿标识，检查产物后再交付。
