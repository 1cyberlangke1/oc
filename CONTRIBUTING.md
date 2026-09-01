# 角色贡献指南

欢迎来到 **OC** 项目！🎉

本项目旨在收集与沉淀各类高品质的**开放/自由角色**资产。我们非常欢迎大家提交自己设计或开源的开放角色，或者为已有角色扩充表情包、生图提示词与语音资产喵！₍^ > ヮ < ^₎⟆

为了保证项目结构相对统一，并保障每一位贡献者的合法权益与署名清晰，请在提交角色时遵循以下规范。

---

## 📜 1. 开源协议与版权规范（必读）

- **必须采用开放/自由协议**：提交的角色资产必须基于开源、开放或自由文化协议（如 MIT, Apache-2.0, CC-BY, CC-BY-SA, CC0, Unlicense 等）。具体的自由协议种类可以由作者自行选择，但**必须是开放/自由协议**。
- **必须附带独立 `LICENSE` 文件**：每个提交的角色目录内**必须包含** `LICENSE`（或 `LICENSE.txt`）文件，并在其中注明**您自己的作者名称/版权声明**。
  > **为什么不能默认继承仓库根目录协议？**  
  > 仓库根目录的 LICENSE 署名属于主仓库维护者。为了尊重每一位创作者的独立著作权，严禁混淆署名，每个角色必须在自身目录下明确归属自己的开源协议与版权信息。

---

## 📁 2. 角色目录结构规范

每个角色存放在 `character/<角色名>/` 目录下：

```text
character/<角色名>/
├── system_prompt.txt       # 【必选】系统人设提示词（必须以此命名）
├── LICENSE                 # 【必选】角色专属的开放/自由协议文件（注明作者署名）
├── sd_prompt.txt           # 【推荐】Stable Diffusion / AI 生图提示词
├── emote/                  # 【推荐】表情包与立绘资产目录（统一 1024x1024 WebP）
│   ├── <name>.webp         # 看板娘立绘/默认形象
│   └── <动作/情绪>.webp     # 情绪表情包（如 开心.webp, 害羞.webp）
└── voice/                  # 【推荐】角色语音与 TTS 声线资产目录
    ├── <name>_base_voice.wav   # 角色官方基准参考音频（克隆母本）
    └── 01_xxx.wav ~ 0N_xxx.wav # 日常交互与台词音频
```

---

## 📝 3. 文件与资产要求

### 📄 系统提示词 (`system_prompt.txt`)
- **命名要求**：文件名**必须严格命名为 `system_prompt.txt`**（统一使用纯文本 `.txt` 后缀）。
- **内容格式**：**未强制限定内部格式**。您可以根据角色的设计需求自由书写人设。
- **推荐格式（仅供参考）**：仓库内现存角色的极简 DSL 格式（包含 `LOOK`, `BODY`, `PERSONALITY`, `SPEECH`, `EXAMPLES_CN_ZH` 等字段）。

### 🎨 生图提示词 (`sd_prompt.txt`)
- 用于生成角色表情包、立绘或头像的 Prompt 模版。

### 🖼️ 表情包资产 (`emote/`)
- 表情包与立绘统一推荐存放在 `emote/` 目录下。
- 图片格式统一为 **`1024x1024 WebP`**。若有原始图片，可利用仓库提供的超分脚本批量转换。

### 🎙️ 语音资产 (`voice/`)
- 声线克隆母本与台词音频统一存放在 `voice/` 目录下。
- 建议提供 `<name>_base_voice.wav` 基准参考音频及各状态对话音频。

---

## 🛠️ 4. 辅助工具与脚本使用教程

本项目在 `scripts/` 目录下提供了完整的表情包超分与 TTS 语音处理工具链。

### ⚡ 4.1 环境准备 (`uv`)
本项目推荐使用 `uv` 极速管理依赖环境：
```powershell
# 1. 创建虚拟环境 (Python 3.11)
uv venv .venv --python 3.11

# 2. 安装项目全部依赖
uv pip install -r requirements.txt
```

### 🖼️ 4.2 表情包高清超分与格式转换 (`scripts/upscale_to_webp.py`)
该脚本基于 Real-CUGAN 算法，可将目录下的 PNG/JPG 等图片统一超分放大为 1024×1024 高保真 WebP，默认自动清理原始大文件：

```powershell
# 1. 默认推荐：CPU 处理 + models-se 轻量模型 + 自动清理原图（单张 ~8s）
.\.venv\Scripts\python scripts/upscale_to_webp.py --device cpu --dir character/<角色名>/emote

# 2. GPU 极速加速模式（单张 <1s）
.\.venv\Scripts\python scripts/upscale_to_webp.py --device gpu --dir character/<角色名>/emote

# 3. 极致画质模式（采用 models-pro 深度去噪模型）
.\.venv\Scripts\python scripts/upscale_to_webp.py --device cpu --model models-pro --dir character/<角色名>/emote

# 4. 保留原始图片文件（不自动删除 PNG/JPG）
.\.venv\Scripts\python scripts/upscale_to_webp.py --keep-original --dir character/<角色名>/emote
```

### 🎙️ 4.3 角色语音制作工作流 (`scripts/tts_suite.py`)

套件支持 **Qwen3-TTS 1.7B** 与 **VoxCPM 2.0** 语音引擎。推荐的标准制作流程分为两步：**先用 Qwen 抽角色声线，再用 VoxCPM 批量克隆台词**。

#### 步骤一：使用 Qwen3-TTS VoiceDesign 设计/抽取基准声线
通过自然语言描述期望的声音特征，批量抽卡生成候选音频，挑选最满意的一条作为角色的官方参考母本：

```powershell
# 使用 Qwen3-TTS VoiceDesign 根据人设描述批量抽卡 5 组不同音色
.\.venv\Scripts\python scripts/tts_suite.py --engine voicedesign --prompt "22岁年轻温柔的大姐姐女声，中音清甜温润，语速轻柔舒缓，带着满满的治愈感与温暖微笑" --text "主人，欢迎回家~ 今天在外面辛苦了呢" --num-samples 5
```
> 生成后，从 `output/voice/` 目录中选取最符合形象的音频，重命名并保存为 `character/<角色名>/voice/<name>_base_voice.wav`。

#### 步骤二：使用 VoxCPM 2.0 高保真克隆全套台词
以步骤一生成的基准音频为参考母本，批量或交互式生成角色的全部日常交互与状态对话音频：

```powershell
# 1. 单句克隆生成
.\.venv\Scripts\python scripts/tts_suite.py --engine voxcpm --ref character/<角色名>/voice/<name>_base_voice.wav --text "今天工作好累啊，千千给你揉揉太阳穴好吗？" --output character/<角色名>/voice/01_tired_care.wav

# 2. 交互式常驻 REPL 模式（模型常驻显存，零冷启动等待，适合连续制作全套台词）
.\.venv\Scripts\python scripts/tts_suite.py --interactive --ref character/<角色名>/voice/<name>_base_voice.wav

# 3. 极速试听模式（6步快速采样，单句 <5s 极速出音）
.\.venv\Scripts\python scripts/tts_suite.py --engine voxcpm --ref character/<角色名>/voice/<name>_base_voice.wav --text "早安喵！" --fast

# 4. 运行硬件与实时率 (RTF) 性能压测
.\.venv\Scripts\python scripts/tts_suite.py --benchmark
```

---

## 🚫 5. 内容合规规范

- **严禁直球 NSFW 与敏感词汇**：**严禁在 Git Commit 描述以及提交的公共资产中出现直球、露骨、低俗或敏感词汇**。

---

## 🚀 6. 提交流程 (Pull Request)

1. **Fork** 本仓库到你的 GitHub 账号。
2. 创建特性分支：
   ```bash
   git checkout -b character/my-character-name
   ```
3. 在 `character/` 目录下创建你的角色文件夹，放入 `system_prompt.txt`、`LICENSE` 及相关资源。
4. 提交 Commit（推荐常规格式，如 `feat: 新增角色 xxx`）：
   ```bash
   git add character/my-character-name
   git commit -m "feat: 新增角色 my-character-name"
   ```
5. 推送分支并发起 **Pull Request**，我们会尽快审核并合并喵！₍^ ✿ ╸𖥦 ╸✿ ^₎⟆
