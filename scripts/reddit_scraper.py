"""
从 Reddit r/NTU 爬取精华内容

安装依赖:
pip install praw

使用方法:
1. 到 https://www.reddit.com/prefs/apps 创建应用获取 API credentials
2. 填写下面的配置
3. 运行: python scripts/reddit_scraper.py
"""

import praw
from datetime import datetime
from pathlib import Path


class RedditNTUScraper:
    def __init__(self, client_id, client_secret, user_agent):
        """
        初始化 Reddit API 客户端

        Args:
            client_id: Reddit App Client ID
            client_secret: Reddit App Secret
            user_agent: 用户代理字符串
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        self.subreddit = self.reddit.subreddit("NTU")

    def scrape_top_posts(self, limit=50, time_filter="all", min_score=10):
        """
        爬取热门帖子

        Args:
            limit: 数量限制
            time_filter: 时间范围 ("all", "year", "month", "week")
            min_score: 最低点赞数

        Returns:
            帖子列表
        """
        posts = []
        for submission in self.subreddit.top(time_filter=time_filter, limit=limit):
            if submission.score >= min_score:
                posts.append({
                    'title': submission.title,
                    'score': submission.score,
                    'text': submission.selftext,
                    'url': submission.url,
                    'num_comments': submission.num_comments,
                    'created': datetime.fromtimestamp(submission.created_utc),
                })
        return posts

    def search_posts(self, query, limit=30):
        """
        搜索特定关键词的帖子

        Args:
            query: 搜索关键词
            limit: 数量限制

        Returns:
            帖子列表
        """
        posts = []
        for submission in self.subreddit.search(query, limit=limit):
            posts.append({
                'title': submission.title,
                'score': submission.score,
                'text': submission.selftext,
                'url': submission.url,
                'num_comments': submission.num_comments,
            })
        return posts

    def save_to_file(self, posts, output_file):
        """
        保存到文本文件

        Args:
            posts: 帖子列表
            output_file: 输出文件路径
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Reddit r/NTU 内容汇总\n")
            f.write(f"抓取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"共 {len(posts)} 条帖子\n")
            f.write("="*80 + "\n\n")

            for i, post in enumerate(posts, 1):
                f.write(f"【帖子 {i}】{post['title']}\n")
                f.write(f"评分: {post['score']} | 评论数: {post['num_comments']}\n")
                if 'created' in post:
                    f.write(f"发布时间: {post['created']}\n")
                f.write(f"链接: {post['url']}\n")
                f.write("-"*80 + "\n")

                if post['text']:
                    f.write(post['text'])
                    f.write("\n")
                else:
                    f.write("[此帖子无正文内容，可能是链接贴]\n")

                f.write("\n" + "="*80 + "\n\n")

        print(f"✅ 已保存 {len(posts)} 条帖子到: {output_file}")


# === 使用示例 ===
if __name__ == "__main__":
    # ⚠️ 需要先到 https://www.reddit.com/prefs/apps 创建应用
    # 填写你的 credentials
    CLIENT_ID = "YOUR_CLIENT_ID"  # 替换为你的
    CLIENT_SECRET = "YOUR_CLIENT_SECRET"  # 替换为你的
    USER_AGENT = "NTU_Genie_Scraper/1.0"

    # 如果没有配置，跳过
    if CLIENT_ID == "YOUR_CLIENT_ID":
        print("⚠️ 请先配置 Reddit API credentials")
        print("访问: https://www.reddit.com/prefs/apps")
        exit()

    scraper = RedditNTUScraper(CLIENT_ID, CLIENT_SECRET, USER_AGENT)

    # 方案1: 爬取热门帖子
    print("🔍 正在获取 r/NTU 热门帖子...")
    top_posts = scraper.scrape_top_posts(limit=50, min_score=10)
    scraper.save_to_file(top_posts, "data/reddit_ntu_top.txt")

    # 方案2: 搜索特定话题
    topics = [
        "accommodation",
        "housing",
        "student pass",
        "visa",
        "orientation",
    ]

    for topic in topics:
        print(f"\n🔍 搜索话题: {topic}")
        posts = scraper.search_posts(topic, limit=20)
        if posts:
            scraper.save_to_file(posts, f"data/reddit_ntu_{topic}.txt")

    print("\n🎉 Reddit 内容爬取完成！")
