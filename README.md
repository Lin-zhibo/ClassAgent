# ClassAgent 古诗词学习系统

## 功能特性

- **四种学习模式**：背诵、理解、赏析、测验
- **智能教学策略**：根据用户画像自动调整教学难度
- **RAG 知识检索**：基于向量数据库的诗词问答
- **用户记忆管理**：记录学习进度、错题本、智能推荐

## 预先准备

### 环境要求

- **Python**: 3.10+
- **操作系统**: Windows 10/11, macOS, Linux

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包括：
- `openai` - OpenAI API 客户端
- `langchain>=0.3.0` - LLM 框架
- `chromadb>=0.5.0` - 向量数据库
- `langchain-chroma` / `langchain-community` - Chroma 向量存储

### 2. 配置 API Key

在 `config/models.json` 中配置模型信息：

```json
{
    "MODEL_NAME": "your-model-name",
    "URL": "https://api.openai.com/v1",
    "EMBEDDING_MODEL_NAME": "your-embedding-model",
    "EMBEDDING_MODEL_URL": "https://api.openai.com/v1"
}
```

在 `config/.env` 中配置你的 API Key：

```env
API_KEY = "your-api-key-here"
```

### 3. 启动主程序

```powershell
# Windows
.\start.ps1
```

```bash
# Linux/macOS
python main.py
```

---

## 学习流程

1. **选择诗词**：从题库中选择想要学习的古诗
2. **选择模式**：
   - `1. 背诵` - 整诗背诵 / 诗句填空练习
   - `2. 理解` - 注释翻译 / AI 讲解 / 学习检测
   - `3. 赏析` - 创作背景 / 艺术手法 / 名句赏析
   - `4. 测验` - 智能出题 / 错题记录 / 学习总结
3. **学习反馈**：根据作答情况获得即时反馈
4. **记录保存**：自动保存学习记录和错题

---

## 数据说明

- `data/questions.CSV` - 问答知识题库（诗人、作品、问题、答案）
- `data/poems.CSV` - 诗歌原文数据（注释、翻译、赏析）【可选】
- `memory/` - 用户画像、学习记录、错题本存储

---

## 文档

- [工作区结构文档](./docs/ARCHITECTURE.md)
- [教学业务逻辑](./docs/LOGIC.md)
