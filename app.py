import streamlit as st
import requests
import google.generativeai as genai

# 設定網頁標題
st.set_page_config(page_title="醫美口碑素材改寫器", layout="wide")
st.title("醫美輿情搜集與 PTT 風格改寫器")

# 側邊欄：設定與篩選
st.sidebar.header("操作設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password")
platform = st.sidebar.selectbox("來源平台", ["Dcard (醫美板)"]) # 第一版先實作 Dcard
category = st.sidebar.selectbox("篩選類別", ["電波", "針劑", "診所", "閒聊"])

# 建立分類關鍵字庫
keywords = {
    "電波": ["電波", "鳳凰", "玩美", "海芙", "索夫波", "探頭", "發數"],
    "針劑": ["玻尿酸", "肉毒", "精靈針", "洢蓮絲", "消脂針", "補山根"],
    "診所": ["推薦", "避雷", "諮詢", "醫生", "報價", "踩雷"],
    "閒聊": ["容貌焦慮", "保養", "猶豫", "痛感"]
}

# 抓取 Dcard 醫美板熱門文章的函式
def fetch_dcard_posts():
    url = "https://www.dcard.tw/service/api/v2/forums/facelift/posts?popular=true&limit=50"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"抓取失敗: {e}")
    return []

# 主要執行區塊
if st.button("開始抓取與改寫"):
    if not api_key:
        st.error("請先在左側輸入你的 Gemini API Key！")
    else:
        # 初始化 Gemini API
        genai.configure(api_key=api_key)
        # 使用 1.5 Flash 模型，速度快且免費額度高
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner('正在從 Dcard 抓取最新熱門文章...'):
            posts = fetch_dcard_posts()
            
            # 依照選擇的類別進行篩選
            target_kw = keywords[category]
            filtered_posts = []
            for p in posts:
                title_text = p.get('title', '')
                excerpt_text = p.get('excerpt', '')
                if any(kw in title_text or kw in excerpt_text for kw in target_kw):
                    filtered_posts.append(p)
            
            if not filtered_posts:
                st.warning(f"目前熱門文章中，沒有找到符合「{category}」標籤的內容。")
            else:
                st.success(f"成功篩選出 {len(filtered_posts)} 篇相關文章！(此處先取最熱門的 1 篇進行示範)")
                
                # 取討論度最高的第一篇
                top_post = filtered_posts[0]
                title = top_post['title']
                excerpt = top_post['excerpt']
                url = f"https://www.dcard.tw/f/facelift/p/{top_post['id']}"
                
                # 顯示原始文章
                st.subheader("原始文章 (Dcard)")
                st.write(f"**標題：** [{title}]({url})")
                st.write(f"**內文摘要：** {excerpt}")
                
                # 準備發送給 AI 的 Prompt
                st.subheader("PTT 風格轉換結果")
                prompt = f"""
                你是一位熟悉台灣 PTT 論壇生態的資深鄉民。請將以下這篇 Dcard 的醫美文章，重新改寫成 PTT (例如 facelift 板) 的發文風格。
                
                【原始標題】：{title}
                【原始內容】：{excerpt}
                
                【絕對要遵守的改寫規則】：
                1. 絕對不要在文章開頭或是任何地方提到「年份開頭」（例如 2026年）。
                2. 標題必須加上 PTT 的分類標籤（例如 [問題]、[心得]、[討論]）。
                3. 嚴格控制視覺排版：PTT 鄉民不喜歡密集的文字方塊。請確保「強制斷行」，每句話不要太長，段落與段落之間必須有空白行。
                4. 語氣轉換：將 Dcard 習慣用語轉為 PTT 用語（例如：原PO、各位大大、小妹等），並清除所有 Emoji 表情符號。
                5. 模擬回文：在文章最下方，請根據內文自動生成 5 條符合 PTT 格式的模擬推文反應（必須正確使用「推」、「噓」、「→」）。
                """
                
                with st.spinner('Gemini 正在將內容轉譯為 PTT 生態用語...'):
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"AI 生成失敗，請確認 API Key 是否正確或額度是否達上限。錯誤訊息：{e}")
