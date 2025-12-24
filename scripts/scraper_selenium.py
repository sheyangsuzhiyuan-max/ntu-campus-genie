"""
使用 Selenium 绕过反爬虫机制爬取 NTU 网站

安装依赖:
pip install selenium webdriver-manager

使用方法:
python scripts/scraper_selenium.py
"""

import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class NTUWebScraper:
    def __init__(self, headless=True):
        """
        初始化 Selenium WebDriver

        Args:
            headless: 是否无头模式（不显示浏览器窗口）
        """
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        # 伪装成真实浏览器
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # 自动下载并使用 ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(10)  # 隐式等待10秒

    def scrape_page(self, url, output_file=None):
        """
        爬取单个页面

        Args:
            url: 目标URL
            output_file: 输出文件路径（可选）

        Returns:
            页面文本内容
        """
        print(f"正在访问: {url}")
        self.driver.get(url)

        # 等待页面加载（等待某个关键元素出现）
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            print(f"页面加载超时: {e}")
            return None

        # 滚动页面以触发懒加载
        self._scroll_page()

        # 提取文本内容
        try:
            # 尝试找主要内容区域（根据NTU网站结构调整）
            main_content = self.driver.find_element(By.TAG_NAME, "main")
            text = main_content.text
        except:
            # 如果没有 main 标签，就用 body
            text = self.driver.find_element(By.TAG_NAME, "body").text

        # 保存到文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"来源: {url}\n")
                f.write(f"抓取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n\n")
                f.write(text)
            print(f"✅ 已保存到: {output_file}")

        return text

    def scrape_multiple(self, urls, output_dir="data/scraped"):
        """
        批量爬取多个页面

        Args:
            urls: URL列表
            output_dir: 输出目录
        """
        results = {}
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 处理: {url}")

            # 生成文件名（从URL提取）
            filename = url.split('/')[-1] or 'index'
            filename = filename.replace('?', '_').replace('&', '_')
            output_file = f"{output_dir}/{filename}.txt"

            text = self.scrape_page(url, output_file)
            results[url] = text

            # 礼貌延迟，避免被ban
            time.sleep(2)

        return results

    def _scroll_page(self):
        """滚动页面以触发懒加载内容"""
        # 获取页面高度
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # 滚动到底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # 计算新的滚动高度
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def close(self):
        """关闭浏览器"""
        self.driver.quit()
        print("\n✅ 浏览器已关闭")


# === 使用示例 ===
if __name__ == "__main__":
    # NTU 重要页面列表
    urls = [
        "https://www.ntu.edu.sg/life-at-ntu/accommodation",
        "https://www.ntu.edu.sg/admissions/graduate/requirements",
        "https://www.ntu.edu.sg/education/academic-calendar",
        # 添加更多你需要的页面
    ]

    scraper = NTUWebScraper(headless=True)

    try:
        print("🚀 开始爬取...")
        scraper.scrape_multiple(urls)
        print("\n🎉 爬取完成！")
    except Exception as e:
        print(f"\n❌ 爬取失败: {e}")
    finally:
        scraper.close()
