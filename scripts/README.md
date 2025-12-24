# 数据获取工具

这个目录包含2个爬虫工具，用于扩充知识库。

---

## 1. Selenium爬虫（绕过反爬虫）

**文件**: `scraper_selenium.py`

**用途**: 爬取NTU官网内容，绕过反爬虫机制

### 使用方法

```bash
# 1. 安装
pip install selenium webdriver-manager

# 2. 运行（使用默认URL列表）
python scripts/scraper_selenium.py

# 3. 查看结果
ls data/scraped/

# 4. 加入知识库（编辑 config.py）
DEFAULT_KNOWLEDGE_FILES = [
    "data/ntu_hall.txt",
    "data/ntu_visa.txt",
    "data/scraped/accommodation.txt",  # ← 新增
]
```

### 自定义URL

编辑 `scraper_selenium.py` 第93-98行：
```python
urls = [
    "https://www.ntu.edu.sg/life-at-ntu/accommodation",
    "https://www.ntu.edu.sg/admissions/graduate/requirements",
    # 添加你需要的页面
]
```

---

## 2. Reddit内容聚合

**文件**: `reddit_scraper.py`

**用途**: 从 r/NTU 获取精华内容和讨论

### 使用方法

```bash
# 1. 获取Reddit API
# 访问: https://www.reddit.com/prefs/apps
# 创建应用，获取 client_id 和 client_secret

# 2. 配置（编辑 reddit_scraper.py）
CLIENT_ID = "你的client_id"
CLIENT_SECRET = "你的client_secret"

# 3. 安装并运行
pip install praw
python scripts/reddit_scraper.py

# 4. 查看结果
ls data/reddit_ntu_*.txt
```

---

## 🔧 故障排查

### Selenium相关

**问题**: ChromeDriver版本不匹配
```bash
pip install --upgrade webdriver-manager
```

**问题**: 无头模式失败
```python
# 关闭无头模式调试（编辑scraper_selenium.py）
scraper = NTUWebScraper(headless=False)
```

### Reddit API相关

**问题**: 401 Unauthorized
- 检查credentials是否正确
- 重新创建应用

---

## ⚠️ 注意事项

1. **遵守网站ToS**
   - 不要过于频繁爬取
   - 尊重网站使用条款

2. **数据合规**
   - 不要爬取个人隐私信息
   - 遵守版权法

3. **内容清洗**
   - 爬取后需要手动清洗（删除页眉页脚、导航栏等）

---

更多详情见主目录的 [KNOWLEDGE_BASE_GUIDE.md](../KNOWLEDGE_BASE_GUIDE.md)
