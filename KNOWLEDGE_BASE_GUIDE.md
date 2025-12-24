# 知识库扩充指南

如果你觉得默认知识库内容不够，想添加更多内容，这里有3种实用方案。

---

## 🎯 问题：官网反爬虫怎么办？

NTU官网有反爬虫机制，直接用 `WebBaseLoader` 经常会403。以下是解决方案。

---

## 方案1: 手动整理FAQ（推荐⭐⭐⭐⭐⭐）

**时间**: 30分钟
**难度**: ⭐
**效果**: 最好，质量最高

### 步骤

1. **找素材**（10分钟）
   - 小红书搜索："NTU 宿舍申请"、"NTU 新生指南"
   - 知乎搜索："南洋理工大学"
   - 寄托天下 NTU版精华帖

2. **整理成FAQ格式**（15分钟）

   创建文件 `data/ntu_campus_life.txt`：
   ```
   === NTU 校园生活指南 ===

   Q: NTU有哪些食堂？哪个最好吃？
   A:
   1. North Spine Canteen（北脊）
      - 位置：学校中心
      - 推荐：西餐、韩餐
      - 价格：SGD 4-6/餐

   2. Canteen 2（南洋小厨）
      - 位置：Hall 1-2附近
      - 推荐：中餐、马来菜
      - 价格：SGD 3-5/餐

   Q: 如何办理手机卡？
   A: [详细步骤...]
   ```

3. **添加到配置**（5分钟）

   编辑 `config.py`：
   ```python
   DEFAULT_KNOWLEDGE_FILES = [
       "data/ntu_hall.txt",
       "data/ntu_visa.txt",
       "data/ntu_housing_extended.txt",
       "data/ntu_campus_life.txt",  # ← 新增这一行
   ]
   ```

4. **测试**
   ```bash
   streamlit run app.py
   # 点击"加载默认知识库"
   # 问："NTU哪个食堂好吃？"
   ```

---

## 方案2: Selenium爬虫（绕过反爬）

**时间**: 1小时（含安装）
**难度**: ⭐⭐⭐
**效果**: ⭐⭐⭐

### 步骤

1. **安装依赖**
   ```bash
   pip install selenium webdriver-manager
   ```

2. **运行爬虫**
   ```bash
   python scripts/scraper_selenium.py
   # 默认会爬取几个NTU官网页面
   # 输出保存到 data/scraped/
   ```

3. **添加到知识库**

   编辑 `config.py`：
   ```python
   DEFAULT_KNOWLEDGE_FILES = [
       "data/ntu_hall.txt",
       "data/ntu_visa.txt",
       "data/ntu_housing_extended.txt",
       "data/scraped/accommodation.txt",  # ← 新增
   ]
   ```

详细说明见 [scripts/README.md](scripts/README.md)

---

## 方案3: Reddit内容聚合

**时间**: 30分钟
**难度**: ⭐⭐
**效果**: ⭐⭐⭐⭐（英文内容）

### 步骤

1. **获取Reddit API**
   - 访问：https://www.reddit.com/prefs/apps
   - 创建应用，复制 `client_id` 和 `client_secret`

2. **配置并运行**

   编辑 `scripts/reddit_scraper.py`，填写你的credentials：
   ```python
   CLIENT_ID = "你的client_id"
   CLIENT_SECRET = "你的client_secret"
   ```

   运行：
   ```bash
   pip install praw
   python scripts/reddit_scraper.py
   # 输出：data/reddit_ntu_*.txt
   ```

3. **添加到知识库**
   ```python
   DEFAULT_KNOWLEDGE_FILES = [
       "data/ntu_hall.txt",
       "data/ntu_visa.txt",
       "data/ntu_housing_extended.txt",
       "data/reddit_ntu_accommodation.txt",  # ← 新增
   ]
   ```

---

## 💡 内容质量标准

好的FAQ应该：

✅ **结构化**
```
Q: [具体问题]
A: [详细回答]
   1. [要点1]
   2. [要点2]
```

✅ **细节丰富**
- 包含具体数字（价格、日期、地址）
- 包含操作步骤
- 包含注意事项

✅ **标注时效性**
```
价格：SGD 420-480/月（2024-2025学年）
申请截止：5月31日（2025年参考）
```

---

## 🎯 推荐内容主题

按优先级排序：

### 高优先级（现在就做）
- ✅ 宿舍申请（已完成）
- ✅ 签证办理（已完成）
- [ ] 饮食交通（30分钟可完成）
- [ ] 银行卡/手机卡办理

### 中优先级（本周完成）
- [ ] 选课注册
- [ ] 图书馆使用
- [ ] 校园设施

### 低优先级（慢慢补充）
- [ ] 社团活动
- [ ] 实习就业
- [ ] 周边游玩

---

## 📊 内容规模建议

| 主题 | 目标Q&A数 | 预计字符数 |
|------|-----------|-----------|
| 宿舍 | 15-20个 | 5000-8000 |
| 签证 | 10-15个 | 3000-5000 |
| 饮食交通 | 10-12个 | 2000-3000 |
| 学术 | 8-10个 | 2000-3000 |
| **总计** | **50+个** | **15000+** |

---

## ⚠️ 注意事项

1. **版权**
   - 不要直接复制粘贴大段官方文本
   - 用自己的话改写

2. **时效性**
   - 所有价格、日期标注年份
   - 定期更新

3. **准确性**
   - 涉及政策的内容务必核实
   - 提供官方链接让用户确认

4. **隐私**
   - 不要包含个人信息

---

## 🔧 调试技巧

### 查看哪些问题回答不好

在 `app.py` 中添加统计：
```python
# 记录"文档中未提及"的问题
if "文档中未提及" in answer:
    with open("missing_questions.log", "a") as f:
        f.write(f"{datetime.now()}: {prompt}\n")
```

每周查看 `missing_questions.log`，补充缺失内容。

---

## 📚 参考资源

- [NTU官网](https://www.ntu.edu.sg)
- [小红书NTU标签](https://www.xiaohongshu.com/search_result?keyword=NTU)
- [知乎NTU话题](https://www.zhihu.com/topic/19557906)
- [寄托天下NTU版](https://bbs.gter.net/forum-878-1.html)

---

## 🎉 总结

**最简单的方案**（今天就能做）：
1. 花30分钟在小红书/知乎整理20个FAQ
2. 创建 `data/ntu_campus_life.txt`
3. 添加到 `config.py`
4. 测试效果

**最有效的长期策略**：
- 每月收集新生高频问题
- 每周补充2-3个FAQ
- 定期更新时效性信息

现在就开始吧！🚀
