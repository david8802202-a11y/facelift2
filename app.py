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

# 改寫：針對特定關鍵字進行搜尋的函式
def fetch_dcard_search(query):
    # 使用 Dcard 搜尋 API，直接找醫美板、符合關鍵字的文章，並抓取 30 筆
    url = f"https://www.dcard.tw/service/api/v2/search/posts?query={query}&forum=facelift&limit=30"
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
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 拿該類別的第一個關鍵字（例如針劑的"玻尿酸"）當作主要搜尋詞
        search_term = keywords[category][0] 
        
        with st.spinner(f'正在 Dcard 搜尋「{search_term}」相關的文章...'):
            posts = fetch_dcard_search(search_term)
            
            # 過濾出真的有內容，且按讚數或留言數大於 5 的文章，確保具有討論度
            filtered_posts = [p for p in posts if p.get('likeCount', 0) > 5 or p.get('commentCount', 0) > 5]
            
            if not filtered_posts:
                st.warning(f"近期沒有找到討論度足夠的「{category}」相關文章。")
            else:
                st.success(f"成功搜出 {len(filtered_posts)} 篇有討論度的文章！(取最熱門示範)")
                
                # 依照愛心數重新排序，強制取最高的一篇
                top_post = sorted(filtered_posts, key=lambda x: x.get('likeCount', 0), reverse=True)[0]
                title = top_post['title']
                excerpt = top_post['excerpt']
                url = f"https://www.dcard.tw/f/facelift/p/{top_post['id']}"
                
                st.subheader("原始文章 (Dcard)")
                st.write(f"**標題：** [{title}]({url})")
                st.write(f"**內文摘要：** {excerpt}")
                
                st.subheader("PTT 風格轉換結果")
                prompt = f"""
                你是一位熟悉台灣 PTT 論壇生態的資深鄉民。請將以下這篇 Dcard 的醫美文章，重新改寫成 PTT (例如 facelift 板) 的發文風格。
                
                【原始標題】：{title}
                【原始內容】：{excerpt}
                
                【絕對要遵守的改寫規則】：
                1. 絕對不要在文章開頭或是任何地方提到「年份開頭」。
                2. 標題必須加上 PTT 的分類標籤（例如 [問題]、[心得]、[討論]）。
                3. 嚴格控制視覺排版：強制斷行，每句話不要太長，段落與段落之間必須有空白行。
                4. 語氣轉換：轉為 PTT 用語（例如：原PO、大大等），並清除 Emoji。
                5. 模擬回文：在文章最下方生成 5 條模擬推文反應（需正確使用「推」、「噓」、「→」）。
                """
                
                with st.spinner('Gemini 正在將內容轉譯為 PTT 生態用語...'):
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"AI 生成失敗：{e}")

