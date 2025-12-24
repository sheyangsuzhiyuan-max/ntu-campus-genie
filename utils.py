"""
工具函数 - 通用辅助功能
"""
import os
import csv
import datetime
import streamlit as st
from typing import Dict, Any, Optional
from config import FEEDBACK_LOG_FILE


def log_feedback(label: str, interaction: Optional[Dict[str, Any]]) -> bool:
    """
    记录用户反馈到 CSV 文件

    Args:
        label: "up" 或 "down"
        interaction: 最近一次问答的信息

    Returns:
        bool: 是否成功记录
    """
    if not interaction:
        return False

    try:
        row = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "label": label,
            "question": interaction.get("question", ""),
            "answer": interaction.get("answer", "")[:200],  # 截断避免过长
            "used_rag": interaction.get("used_rag", False),
            "sources": "|".join(interaction.get("sources") or []),
        }

        file_exists = os.path.exists(FEEDBACK_LOG_FILE)
        fieldnames = list(row.keys())

        with open(FEEDBACK_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        return True
    except Exception as e:
        st.warning(f"⚠️ 反馈记录失败: {e}")
        return False


def get_feedback_stats() -> Dict[str, Any]:
    """
    获取反馈统计数据

    Returns:
        包含统计信息的字典
    """
    if not os.path.exists(FEEDBACK_LOG_FILE):
        return {
            "total": 0,
            "ups": 0,
            "downs": 0,
            "recent": []
        }

    try:
        rows = []
        with open(FEEDBACK_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total = len(rows)
        ups = sum(1 for r in rows if r.get("label") == "up")
        downs = sum(1 for r in rows if r.get("label") == "down")

        return {
            "total": total,
            "ups": ups,
            "downs": downs,
            "recent": rows[-5:]  # 最近 5 条
        }
    except Exception as e:
        st.warning(f"⚠️ 读取反馈数据失败: {e}")
        return {
            "total": 0,
            "ups": 0,
            "downs": 0,
            "recent": []
        }


def format_sources(sources: list) -> str:
    """
    格式化文档来源列表

    Args:
        sources: 来源列表

    Returns:
        格式化后的字符串
    """
    if not sources:
        return "无来源"

    formatted = []
    for i, src in enumerate(sources, 1):
        # 如果是文件路径，只显示文件名
        if "/" in src or "\\" in src:
            src = os.path.basename(src)
        formatted.append(f"{i}. {src}")

    return "\n".join(formatted)


def init_session_state():
    """
    初始化 Streamlit session state
    """
    if "messages" not in st.session_state:
        from config import WELCOME_MESSAGE
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE,
            }
        ]

    if "last_interaction" not in st.session_state:
        st.session_state["last_interaction"] = None

    if "prefill" not in st.session_state:
        st.session_state["prefill"] = ""


def get_unique_button_key(prefix: str) -> str:
    """
    生成唯一的按钮 key，避免冲突

    Args:
        prefix: key 前缀

    Returns:
        唯一的 key
    """
    import time
    return f"{prefix}_{int(time.time() * 1000000)}"
