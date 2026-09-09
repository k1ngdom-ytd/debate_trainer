# -*- coding: utf-8 -*-

import streamlit as st
import requests
import json
import os
import time
import requests_cache
from datetime import datetime

# 启用缓存
requests_cache.install_cache('zhihu_cache', expire_after=600)

# ================== 请替换成你的真实 App_Key ==================
# 建议通过环境变量 ZHIHU_APP_KEY 配置，避免将密钥硬编码在源码中（生产环境请勿使用默认值）
APP_KEY = os.environ.get("ZHIHU_APP_KEY", "51e9514d29dd9183351e5b968793a27e65fa6fb6")
# =============================================================

# ---------- 模拟模式开关 ----------
USE_MOCK = False
# --------------------------------

# ---------- 刘看山GIF动图配置 ----------
KANSHAN_GIFS = {
    "idle": "assets/kanshan_idle.gif",
    "wave": "assets/kanshan_wave.gif",
    "sway": "assets/kanshan_sway.gif",
    "computer": "assets/kanshan_computer.gif",
    "sleepy": "assets/kanshan_sleepy.gif",
    "dribble": "assets/kanshan_dribble.gif"
}
DEFAULT_GIF = KANSHAN_GIFS["idle"]
# ---------------------------------

# ---------- 辩论风格配置 ----------
DEBATE_STYLES = {
    "温和引导型": {
        "description": "语气温和，注重引导思考",
        "prompt_suffix": "语气温和友善，以引导对方思考为主，适当肯定对方观点中的合理之处，再提出不同看法。"
    },
    "犀利攻击型": {
        "description": "言辞犀利，直击逻辑漏洞",
        "prompt_suffix": "语气犀利尖锐，直接攻击对方逻辑漏洞和事实错误，不给对方留情面，用强有力的论据碾压对方。"
    },
    "逻辑严谨型": {
        "description": "理性分析，注重逻辑链条",
        "prompt_suffix": "语气理性严谨，注重逻辑链条的完整性，用严密的推理和事实数据说话，不掺杂情绪。"
    }
}


# ---------------------------------


def call_zhihu_agent(prompt, retries=2):
    """调用知乎直答 API，支持重试"""
    if USE_MOCK:
        if "提炼" in prompt or "论据" in prompt:
            return """【正方论据】
1. 人工智能大幅提升生产效率
2. AI在医疗诊断领域表现优异
3. 推动科学研究加速

【反方论据】
1. 大规模失业风险
2. 算法偏见问题
3. 数据隐私安全担忧"""
        elif "反驳" in prompt:
            return "你的观点缺乏数据支撑，请提供具体案例。"
        elif "快捷回复" in prompt:
            return "1. 请提供具体数据支持你的观点\n2. 这个逻辑存在漏洞\n3. 有没有考虑过反例？"
        elif "评估报告" in prompt:
            return """### 辩论能力评估报告

**逻辑性评分**：7/10
评分依据：论证结构清晰，但缺乏数据支撑

**2个具体改进点**：
1. 建议引用具体案例
2. 注意回应对方核心论点

**优化建议**：
多准备数据和案例，增强说服力"""
        else:
            return "这是模拟回复。请继续辩论。"

    url = "https://developer.zhihu.com/v1/chat/completions"
    timestamp = str(int(time.time()))
    headers = {
        "Authorization": f"Bearer {APP_KEY}",
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-Timestamp": timestamp
    }
    payload = {
        "model": "zhida-fast-1p5",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    for attempt in range(retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.encoding = "utf-8"
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"].get("content", "")
                    if not content:
                        content = result["choices"][0]["message"].get("reasoning_content", "")
                    return content if content else "API返回内容为空"
                else:
                    return f"API返回格式异常：{result}"
            elif response.status_code == 429:
                return "API调用频率超限，请明天再试。"
            else:
                return f"API调用失败：{response.status_code}，{response.text[:200]}"
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(2)
                continue
            else:
                return "请求超时，已重试2次仍失败，请检查网络。"
        except Exception as e:
            return f"请求出错：{e}"


def search_zhihu(query, min_authority=None, min_votes=None, min_comments=None):
    """调用知乎搜索 API，支持内容质量筛选"""
    url = "https://developer.zhihu.com/api/v1/content/zhihu_search"
    timestamp = str(int(time.time()))
    headers = {
        "Authorization": f"Bearer {APP_KEY}",
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-Timestamp": timestamp
    }
    params = {
        "Query": query,
        "Count": 10
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.encoding = "utf-8"
        if response.status_code == 200:
            result = response.json()
            if result.get("Code") == 0:
                data = result.get("Data", {})
                items = data.get("Items", [])

                if min_authority or min_votes or min_comments:
                    filtered = []
                    for item in items:
                        authority = int(item.get("AuthorityLevel", 0))
                        votes = item.get("VoteUpCount", 0)
                        comments = item.get("CommentCount", 0)

                        if min_authority and authority < min_authority:
                            continue
                        if min_votes and votes < min_votes:
                            continue
                        if min_comments and comments < min_comments:
                            continue
                        filtered.append(item)
                    items = filtered

                return {"data": items}
            else:
                st.error(f"搜索API返回错误：{result.get('Message', '未知错误')}")
                return None
        else:
            st.error(f"搜索API调用失败：{response.status_code}")
            return None
    except Exception as e:
        st.error(f"搜索请求出错：{e}")
        return None


def get_hot_list(limit=10):
    """获取知乎热榜"""
    if USE_MOCK:
        return [
            {"Title": "如何评价人工智能对就业的影响？"},
            {"Title": "考研人数下降说明了什么？"},
            {"Title": "996工作制是否应该被禁止？"},
        ]

    url = "https://developer.zhihu.com/api/v1/content/hot_list"
    timestamp = str(int(time.time()))
    headers = {
        "Authorization": f"Bearer {APP_KEY}",
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-Timestamp": timestamp
    }
    params = {"Limit": min(limit, 30)}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.encoding = "utf-8"
        if response.status_code == 200:
            result = response.json()
            if result.get("Code") == 0:
                data = result.get("Data", {})
                return data.get("Items", [])
            else:
                return []
        else:
            return []
    except Exception:
        return []


def get_user_followees():
    """获取关注列表"""
    if USE_MOCK:
        return [{"name": "张三", "follower_count": 1234}, {"name": "李四", "follower_count": 5678}]

    url = "https://developer.zhihu.com/api/v1/user/followees"
    timestamp = str(int(time.time()))
    headers = {
        "Authorization": f"Bearer {APP_KEY}",
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-Timestamp": timestamp
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        if response.status_code == 200:
            result = response.json()
            if result.get("Code") == 0:
                data = result.get("Data", {})
                return data.get("Items", [])
            else:
                return []
        else:
            return []
    except Exception:
        return []


def get_user_followers():
    """获取粉丝列表"""
    if USE_MOCK:
        return [{"name": "王五", "follower_count": 234}, {"name": "赵六", "follower_count": 789}]

    url = "https://developer.zhihu.com/api/v1/user/followers"
    timestamp = str(int(time.time()))
    headers = {
        "Authorization": f"Bearer {APP_KEY}",
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-Timestamp": timestamp
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        if response.status_code == 200:
            result = response.json()
            if result.get("Code") == 0:
                data = result.get("Data", {})
                return data.get("Items", [])
            else:
                return []
        else:
            return []
    except Exception:
        return []


def extract_arguments(search_results, topic):
    """从搜索结果中提炼正反方论据"""
    content_text = ""
    if "data" in search_results:
        for item in search_results["data"][:5]:
            title = item.get("Title", "")
            content = item.get("ContentText", "")
            votes = item.get("VoteUpCount", 0)
            comments = item.get("CommentCount", 0)
            authority = item.get("AuthorityLevel", 0)
            if title:
                content_text += f"- {title}"
                if votes or comments:
                    content_text += f" (赞{votes} 评{comments} 权威等级:{authority})"
                content_text += "\n"
                if content:
                    content_text += f"  {content[:80]}...\n"

    if not content_text:
        content_text = f"关于「{topic}」的知乎讨论内容"

    prompt = f"""
你是一名辩论论据提炼专家。请根据以下知乎讨论内容，分别提炼出正方和反方的核心论据。

话题：{topic}

知乎相关讨论：
{content_text}

请按以下格式输出，每条论据用数字编号：
【正方论据】
1. xxx
2. xxx
3. xxx

【反方论据】
1. xxx
2. xxx
3. xxx

要求：
- 每条论据必须是具体的观点或事实
- 不要使用"我认为"、"我觉得"等主观表述
- 每条论据控制在20字以内
"""
    result = call_zhihu_agent(prompt)

    pro_args = "（正方论据待提取）"
    con_args = "（反方论据待提取）"
    if "【正方论据】" in result and "【反方论据】" in result:
        parts = result.split("【反方论据】")
        if len(parts) >= 2:
            pro_part = parts[0].replace("【正方论据】", "").strip()
            con_part = parts[1].strip()
            pro_args = pro_part if pro_part else "（暂无正方论据）"
            con_args = con_part if con_part else "（暂无反方论据）"
    else:
        pro_args = result
        con_args = "（请查看上方完整内容）"
    return pro_args, con_args


def generate_ai_reply(user_input, opponent_args, opponent_stance, topic, user_stance, style="逻辑严谨型"):
    """生成 AI 反击（支持风格选择）"""
    style_prompt = DEBATE_STYLES.get(style, DEBATE_STYLES["逻辑严谨型"])["prompt_suffix"]

    prompt = f"""
你是一名辩论对手，你的立场是「{opponent_stance}」（与用户相反）。
你方（{opponent_stance}）拥有的论据库如下（你必须使用这些论据来反驳用户）：
{opponent_args}

用户（{user_stance}）刚才的发言是：
{user_input}

请根据你方的论据，对用户的发言进行反驳。
要求：
- 必须引用你方论据库中的具体论据
- 反驳要针对用户发言中的逻辑漏洞或事实错误
- 控制在50字以内
- 直接输出反驳内容
- {style_prompt}
"""
    result = call_zhihu_agent(prompt)
    if len(result) > 100:
        result = result[:100] + "..."
    return result


def generate_quick_replies(user_input, opponent_args, opponent_stance, topic, user_stance, style="逻辑严谨型"):
    """生成快捷回复建议"""
    style_prompt = DEBATE_STYLES.get(style, DEBATE_STYLES["逻辑严谨型"])["prompt_suffix"]

    prompt = f"""
你是一名辩论助手。用户正在和AI进行辩论，用户刚才的发言是：
{user_input}

对方的立场是「{opponent_stance}」，对方拥有的论据库：
{opponent_args}

请生成3条用户可以用来反驳对方的建议回复。
要求：
- 每条建议必须基于对方论据库中的内容进行反驳
- 每条建议控制在15字以内
- 用数字编号输出，每行一条
- {style_prompt}
"""
    result = call_zhihu_agent(prompt)
    lines = result.strip().split("\n")
    replies = []
    for line in lines:
        cleaned = line.strip()
        if cleaned and (cleaned[0].isdigit() or cleaned.startswith("•") or cleaned.startswith("-")):
            cleaned = cleaned[1:].strip()
            if cleaned.startswith(".") or cleaned.startswith("、"):
                cleaned = cleaned[1:].strip()
        if cleaned and len(cleaned) > 0:
            replies.append(cleaned)
    while len(replies) < 3:
        replies.append("请提供更多论据支持你的观点")
    return replies[:3]


def generate_report(history, topic):
    """生成复盘报告"""
    history_text = ""
    for entry in history:
        speaker = "AI对手" if entry["speaker"] == "AI" else "我"
        history_text += f"{speaker}：{entry['content']}\n"
    prompt = f"""
你是一名辩论教练。请根据以下辩论记录，生成一份能力评估报告。

辩论主题：{topic}

辩论记录：
{history_text}

请按以下格式输出评估报告：

### 辩论能力评估报告

**逻辑性评分**：（1-10分，给出具体分数）
评分依据：（说明为什么给这个分数）

**2个具体改进点**：
1. xxx
2. xxx

**优化建议**：
（给出具体的改进建议，100字以内）
"""
    result = call_zhihu_agent(prompt)
    return result


# ============================================================
#                    主函数 - 界面部分
# ============================================================

def main():
    st.set_page_config(
        page_title="观点辩论训练 - 知乎黑客松",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # ----- 自定义CSS（全面美化） -----
    st.markdown("""
    <style>
        /* 全局字体和背景 */
        .stApp {
            background: linear-gradient(135deg, #f0f2f6 0%, #e8ecf1 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* 主标题 */
        .main-title {
            font-size: 2.8rem;
            font-weight: 700;
            color: #1a1a2e;
            letter-spacing: -0.5px;
            margin-bottom: 0.2rem;
        }
        .main-subtitle {
            font-size: 1rem;
            color: #666;
            font-weight: 400;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }

        /* 步骤标题 */
        .step-header {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1a1a2e;
            background: white;
            padding: 0.6rem 1.2rem;
            border-radius: 10px;
            border-left: 4px solid #0066cc;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }

        /* 卡片容器 */
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.2rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.04);
        }

        /* 按钮统一风格 */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
            background: #0066cc;
            color: white;
            border: none;
            padding: 0.4rem 1.2rem;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            background: #0052a3;
            box-shadow: 0 2px 8px rgba(0,102,204,0.3);
            transform: translateY(-1px);
        }
        .stButton > button:active {
            transform: translateY(0px);
        }
        /* 次要按钮（如示例辩题） */
        .stButton > button[kind="secondary"] {
            background: #f0f2f6;
            color: #333;
            border: 1px solid #d0d0d0;
        }
        .stButton > button[kind="secondary"]:hover {
            background: #e4e7ec;
        }

        /* 侧边栏优化 */
        .css-1d391kg, .css-1lcbmhc {
            background: white;
            border-right: 1px solid #e8ecf1;
        }
        .sidebar-content {
            padding: 0.5rem 0.2rem;
        }
        .sidebar-section {
            background: #f8f9fb;
            border-radius: 8px;
            padding: 0.6rem 0.8rem;
            margin-bottom: 0.8rem;
        }

        /* 子标题 */
        .section-label {
            font-size: 0.9rem;
            font-weight: 600;
            color: #444;
            margin-bottom: 0.3rem;
        }

        /* 计时器 */
        .timer-safe {
            font-size: 1.2rem;
            font-weight: 500;
            color: #444;
        }
        .timer-warning {
            font-size: 1.5rem;
            font-weight: 700;
            color: #d32f2f;
            animation: pulse 0.8s ease-in-out infinite alternate;
        }
        @keyframes pulse {
            from { opacity: 1; }
            to { opacity: 0.4; }
        }

        /* 论据卡片 */
        .argument-card {
            background: #f8f9fb;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            border-left: 3px solid #0066cc;
            margin: 0.5rem 0;
        }
        .argument-card-con {
            border-left-color: #cc6600;
        }

        /* 消息气泡 */
        .stChatMessage {
            border-radius: 12px !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }

        /* 分割线 */
        hr {
            margin: 1.2rem 0;
            border: none;
            border-top: 1px solid #e8ecf1;
        }

        /* 选择框和输入框 */
        .stSelectbox, .stTextInput, .stNumberInput {
            border-radius: 8px;
        }

        /* 滑块 */
        .stSlider {
            padding-top: 0.3rem;
        }

        /* 成功/警告/信息提示 */
        .stAlert {
            border-radius: 8px;
            border: none;
        }

        /* 底部版权 */
        .footer {
            text-align: center;
            color: #999;
            font-size: 0.8rem;
            padding: 1.5rem 0 0.5rem 0;
            border-top: 1px solid #e8ecf1;
            margin-top: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # ========================================
    # 标题区
    # ========================================
    st.markdown('<div class="main-title">观点辩论训练</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">基于知乎真实讨论，AI 陪你练辩论 ｜ 知乎黑客松 2026 · 知识炼金场</div>',
                unsafe_allow_html=True)

    # ========================================
    # 侧边栏
    # ========================================
    with st.sidebar:
        # GIF头像
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(DEFAULT_GIF, width=200)
        st.markdown(
            '<p style="text-align:center; color:#666; font-size:0.9rem; margin-top:-0.2rem;">你的AI辩论陪练</p>',
            unsafe_allow_html=True)
        st.divider()

        # AI风格选择
        st.markdown('<div class="section-label">AI辩论风格</div>', unsafe_allow_html=True)
        selected_style = st.selectbox(
            "选择AI对手的风格",
            list(DEBATE_STYLES.keys()),
            index=2,
            label_visibility="collapsed"
        )
        st.caption(DEBATE_STYLES[selected_style]["description"])
        st.divider()

        # 内容质量筛选
        st.markdown('<div class="section-label">内容质量筛选</div>', unsafe_allow_html=True)
        min_authority = st.slider("最低权威等级 (1-4)", min_value=0, max_value=4, value=0)
        min_votes = st.number_input("最低赞同数", min_value=0, value=0, step=10)
        min_comments = st.number_input("最低评论数", min_value=0, value=0, step=5)
        st.divider()

        # 计时器设置
        st.markdown('<div class="section-label">计时器设置</div>', unsafe_allow_html=True)
        timer_seconds = st.slider("每回合限时（秒）", min_value=30, max_value=180, value=60, step=10)
        timer_enabled = st.checkbox("启用计时器", value=True)
        st.divider()

        # 社交关系
        st.markdown('<div class="section-label">社交关系</div>', unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("关注列表", use_container_width=True):
                with st.spinner("加载中..."):
                    followees = get_user_followees()
                    if followees:
                        st.session_state.followees = followees
                    else:
                        st.warning("暂无关注数据或需要登录授权")
        with col_btn2:
            if st.button("粉丝列表", use_container_width=True):
                with st.spinner("加载中..."):
                    followers = get_user_followers()
                    if followers:
                        st.session_state.followers = followers
                    else:
                        st.warning("暂无粉丝数据或需要登录授权")

        if "followees" in st.session_state and st.session_state.followees:
            with st.expander(f"关注列表 ({len(st.session_state.followees)}人)"):
                for f in st.session_state.followees[:10]:
                    st.write(f"• {f.get('name', '未知')} (粉丝:{f.get('follower_count', 0)})")

        if "followers" in st.session_state and st.session_state.followers:
            with st.expander(f"粉丝列表 ({len(st.session_state.followers)}人)"):
                for f in st.session_state.followers[:10]:
                    st.write(f"• {f.get('name', '未知')} (粉丝:{f.get('follower_count', 0)})")

    # ========================================
    # 第一步：输入辩题
    # ========================================
    st.markdown('<div class="step-header">第一步：输入辩题</div>', unsafe_allow_html=True)

    with st.container():
        # 热点话题
        with st.expander("热点话题（点击生成辩题）"):
            with st.spinner("加载热榜..."):
                hot_items = get_hot_list(10)
            if hot_items:
                cols = st.columns(2)
                for idx, item in enumerate(hot_items[:10]):
                    col_idx = idx % 2
                    with cols[col_idx]:
                        title = item.get("Title", "")[:50]
                        if st.button(title, key=f"hot_{idx}", use_container_width=True):
                            st.session_state.topic = title
                            st.rerun()
            else:
                st.info("暂无可用的热点话题")

        # 示例辩题
        st.markdown("**快速选择示例辩题：**")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("AI是福是祸？", use_container_width=True):
                st.session_state.topic = "人工智能对社会是福还是祸"
        with col2:
            if st.button("考研还是就业？", use_container_width=True):
                st.session_state.topic = "大学生应该考研还是直接就业"
        with col3:
            if st.button("996是奋斗还是剥削？", use_container_width=True):
                st.session_state.topic = "996工作制是奋斗还是剥削"

        # 自定义输入
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            topic = st.text_input(
                "或输入自定义辩题：",
                value=st.session_state.get("topic", ""),
                label_visibility="collapsed",
                placeholder="输入你的辩题..."
            )
        with col_btn:
            st.write("")  # 占位对齐
            st.write("")  # 占位对齐
            search_clicked = st.button("搜索", type="primary", use_container_width=True)

        if search_clicked and topic:
            with st.spinner("正在搜索知乎相关内容..."):
                results = search_zhihu(
                    topic,
                    min_authority=min_authority if min_authority > 0 else None,
                    min_votes=min_votes if min_votes > 0 else None,
                    min_comments=min_comments if min_comments > 0 else None
                )
                if results:
                    st.session_state.search_results = results
                    st.session_state.topic = topic
                    item_count = len(results.get("data", []))
                    st.success(f"找到 {item_count} 条相关内容（已应用质量筛选）")
                    # 更换辩题后清空上一场辩论的全部状态，避免立场/回合/论据残留
                    for key in ("pro_args", "con_args", "stance", "opponent_stance",
                                "opponent_args", "round", "history", "messages",
                                "waiting_for_first_speech", "debate_style",
                                "timer_start", "timer_expired", "quick_input"):
                        st.session_state.pop(key, None)
                else:
                    st.warning("未获取到数据，请检查网络或 App_Key")

    if "search_results" not in st.session_state:
        st.info("请输入辩题后点击「搜索」开始")
        return

    # ========================================
    # 第二步：弹药库
    # ========================================
    st.markdown('<div class="step-header">第二步：弹药库（从知乎提炼的论据）</div>', unsafe_allow_html=True)

    with st.container():
        filter_info = []
        if min_authority > 0:
            filter_info.append(f"权威等级≥{min_authority}")
        if min_votes > 0:
            filter_info.append(f"赞同数≥{min_votes}")
        if min_comments > 0:
            filter_info.append(f"评论数≥{min_comments}")
        if filter_info:
            st.caption(f"当前筛选条件：{' + '.join(filter_info)}")

        if "pro_args" not in st.session_state:
            with st.spinner("AI正在提炼论据..."):
                pro_args, con_args = extract_arguments(st.session_state.search_results, st.session_state.topic)
                st.session_state.pro_args = pro_args
                st.session_state.con_args = con_args
        else:
            pro_args = st.session_state.pro_args
            con_args = st.session_state.con_args

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**正方论据**")
            st.markdown(f'<div class="argument-card">{pro_args}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown("**反方论据**")
            st.markdown(f'<div class="argument-card argument-card-con">{con_args}</div>', unsafe_allow_html=True)

    # ========================================
    # 第三步：开始辩论
    # ========================================
    st.markdown('<div class="step-header">第三步：开始辩论</div>', unsafe_allow_html=True)

    with st.container():
        # 辩论一旦开始即锁定立场：AI 立场始终与用户“初始立场”相反，之后不再改变
        debate_started = "messages" in st.session_state

        if debate_started:
            st.info(
                f"✅ 立场已锁定：你选择「{st.session_state.stance}」，"
                f"AI 固定为「{st.session_state.opponent_stance}」（与你初始立场相反，不随立场变化而改变）。"
            )
        else:
            stance = st.radio(
                "选择你的立场：",
                ["正方", "反方"],
                horizontal=True,
                key="stance_choice",
            )

            if st.button("开始辩论", type="primary"):
                opponent_stance = "反方" if stance == "正方" else "正方"
                opponent_args = con_args if stance == "正方" else pro_args

                st.session_state.stance = stance
                st.session_state.opponent_stance = opponent_stance
                st.session_state.opponent_args = opponent_args
                st.session_state.round = 1
                st.session_state.history = []
                st.session_state.messages = []
                st.session_state.waiting_for_first_speech = True
                st.session_state.debate_style = selected_style
                st.session_state.timer_seconds = timer_seconds
                st.session_state.timer_enabled = timer_enabled
                st.session_state.timer_start = None
                st.session_state.timer_expired = False
                st.rerun()

    if "messages" not in st.session_state:
        return

    # ========================================
    # 第四步：辩论进行中
    # ========================================
    # 计时器
    if st.session_state.get("timer_enabled", False) and not st.session_state.get("waiting_for_first_speech", False):
        if st.session_state.get("timer_start") is None:
            st.session_state.timer_start = time.time()

        elapsed = time.time() - st.session_state.timer_start
        remaining = max(0, st.session_state.timer_seconds - elapsed)

        if remaining <= 0 and not st.session_state.get("timer_expired", False):
            st.session_state.timer_expired = True
            st.warning("时间到！本轮结束，进入下一回合。")
            st.session_state.round += 1
            st.session_state.timer_start = None
            st.session_state.timer_expired = False
            st.rerun()

        if remaining > 10:
            st.markdown(f'<span class="timer-safe">⏱ {int(remaining)}秒</span>', unsafe_allow_html=True)
        elif remaining > 0:
            st.markdown(f'<span class="timer-warning">⏱ {int(remaining)}秒</span>', unsafe_allow_html=True)

    # 检查是否结束
    if st.session_state.round > 3:
        st.info("3回合辩论结束！点击下方按钮查看复盘报告")
        if st.button("生成复盘报告", type="primary"):
            with st.spinner("AI正在生成评估报告..."):
                report = generate_report(st.session_state.history, st.session_state.topic)
            st.markdown(report)
        return

    # 显示当前回合
    if st.session_state.get("waiting_for_first_speech", False):
        st.info("请先陈述你的观点（作为立论），然后 AI 会反驳。")
    else:
        st.markdown(
            f'<div style="font-size:1.1rem; font-weight:600; margin:0.8rem 0 0.5rem 0;">第 {st.session_state.round}/3 回合</div>',
            unsafe_allow_html=True)

    # 显示对话历史
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            if st.session_state.get("waiting_for_first_speech", False):
                gif_key = "wave"
            elif st.session_state.get("round", 1) > 3:
                gif_key = "sleepy"
            else:
                gif_key = "computer"

            avatar_path = KANSHAN_GIFS.get(gif_key, KANSHAN_GIFS["idle"])
            with st.chat_message("assistant", avatar=avatar_path):
                st.write(msg["content"])

    # 快捷回复建议
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "assistant":
        with st.expander("快捷回复建议（点击使用）"):
            with st.spinner("生成建议中..."):
                user_last = ""
                for msg in reversed(st.session_state.messages):
                    if msg["role"] == "user":
                        user_last = msg["content"]
                        break
                if user_last:
                    suggestions = generate_quick_replies(
                        user_last,
                        st.session_state.opponent_args,
                        st.session_state.opponent_stance,
                        st.session_state.topic,
                        st.session_state.stance,
                        st.session_state.get("debate_style", "逻辑严谨型")
                    )
                    for i, sug in enumerate(suggestions):
                        if st.button(sug, key=f"quick_{i}", use_container_width=True):
                            st.session_state.quick_input = sug
                            st.rerun()

    # 用户输入
    user_input = st.chat_input("输入你的观点或反驳...")

    if "quick_input" in st.session_state and st.session_state.quick_input:
        user_input = st.session_state.quick_input
        st.session_state.quick_input = None

    if user_input:
        if st.session_state.get("waiting_for_first_speech", False):
            st.session_state.waiting_for_first_speech = False
            st.session_state.timer_start = time.time()

        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.history.append({
            "round": st.session_state.round,
            "speaker": "用户",
            "content": user_input
        })

        with st.spinner(f"AI正在思考第{st.session_state.round}回合的反击..."):
            ai_reply = generate_ai_reply(
                user_input,
                st.session_state.opponent_args,
                st.session_state.opponent_stance,
                st.session_state.topic,
                st.session_state.stance,
                st.session_state.get("debate_style", "逻辑严谨型")
            )

        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.session_state.history.append({
            "round": st.session_state.round,
            "speaker": "AI",
            "content": ai_reply
        })

        st.session_state.round += 1
        st.session_state.timer_start = None
        st.session_state.timer_expired = False
        st.rerun()

    # ========================================
    # 底部
    # ========================================
    st.markdown('<div class="footer">知乎黑客松 2026 · 知识炼金场</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()