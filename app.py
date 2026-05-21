import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient

# 1. 網頁標題與排版設定
st.set_page_config(page_title="Threads 醫美素材自選改寫器", layout="wide")
st.title("Threads 醫美素材自選與 PTT 風格改寫器")

# 2. 側邊欄設定區（支援自動記憶金鑰）
st.sidebar.header("操作設定")

default_gemini = ""
default_apify = ""

try:
    default_gemini = st.secrets["GEMINI_API_KEY"]
    default_apify = st.secrets["APIFY_TOKEN"]
except Exception:
    pass

gemini_api_key = st.sidebar.text_input("輸入 Gemini API Key", value=default_gemini, type="password")
apify_token = st.sidebar.text_input("輸入 Apify API Token", value=default_apify, type="password")
category = st.sidebar.selectbox("篩選類別", ["電波", "針劑", "診所", "閒聊"])

# 3. 醫美關鍵字庫
keywords = {
    "電波": ["鳳凰電波", "玩美電波", "海芙音波", "索夫波"],
    "針劑": ["玻尿酸", "肉毒", "精靈針", "洢蓮絲"],
    "診所": ["醫美診所推薦", "醫美避雷", "醫美諮詢"],
    "閒聊": ["容貌焦慮", "醫美保養", "術後恢復"]
}

# 4. 呼叫 Apify 爬蟲函式
def fetch_threads_via_apify(keyword, token):
    client = ApifyClient(token)
    actor_id = "watcher.data/search-threads-by-keywords"
    
    run_input = {
        "keywords": [keyword],
        "maxItems": 15,  # 多抓幾篇讓選擇更多
        "sortByRecent": False
    }
    
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else run.default_dataset_id
        items = list(client.dataset(dataset_id).iterate_items())
        return items
    except Exception as e:
        st.error(f"Apify 爬蟲執行失敗: {e}")
        return []

# 5. 初始化 Session State 來記憶抓到的文章，避免網頁重新整理時消失
if "fetched_posts" not in st.session_state:
    st.session_state.fetched_posts = []
if "current_keyword" not in st.session_state:
    st.session_state.current_keyword = ""

search_term = keywords[category][0]

# 按鈕一：先搜尋熱門清單
if st.button(f"🔎 搜尋「{search_term}」熱門文章"):
    if not apify_token:
        st.error("請先在左側輸入你的 Apify Token！")
    else:
        with st.spinner(f'正在前往 Threads 撈取最新的 {search_term} 討論池...'):
            st.session_state.fetched_posts = fetch_threads_via_apify(search_term, apify_token)
            st.session_state.current_keyword = search_term

# 6. 如果有抓到資料，顯示清單供使用者挑選
if st.session_state.fetched_posts:
    st.success(f"成功撈回 {len(st.session_state.fetched_posts)} 篇相關文章！請在下方挑選你覺得適合的素材：")
    
    # 建立選單顯示的文字（作者 + 內文前 30 字摘要）
    options = []
    for p in st.session_state.fetched_posts:
        author_data = p.get('author')
        author = author_data.get('username', '未知') if isinstance(author_data, dict) else p.get('username', '未知')
        text = p.get('text', p.get('caption', '無內文')).replace('\n', ' ')[:30]
        options.append(f"👤 @{author} | 📝 {text}...")
        
    # 讓使用者人肉篩選真正有行銷價值的貼文
    selected_index = st.selectbox("🎯 請選擇你想改寫的文章：", range(len(options)), format_func=lambda x: options[x])
    
    chosen_post = st.session_state.fetched_posts[selected_index]
    content = chosen_post.get('text', chosen_post.get('caption', '無文字內容'))
    url = chosen_post.get('url', '')
    
    st.info(f"**💡 你已選定素材：** {content}")
    
    # 按鈕二：針對選定的文章進行 AI 改寫
    if st.button("🔥 開始將所選文章改寫為 PTT 格式"):
        if not gemini_api_key:
            st.error("請填寫 Gemini API Key！")
        else:
            # 修正 404 Bug：明確指定最新的 gemini-2.5-flash 模型名稱
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            st.subheader("PTT 風格轉換結果")
            prompt = f"""
            你是一位熟悉台灣 PTT 論壇生態的資深鄉民。請將以下這篇來自 Threads 的醫美短文，重新改寫成 PTT (例如 facelift 板) 的發文風格。
            
            【原始內容】：{content}
            
            【絕對要遵守的改寫規則】：
            1. 絕對不要在文章開頭或是任何地方提到「年份開頭」。
            2. 標題必須加上 PTT 的分類標籤（例如 [問題]、[心得]、[討論]）。
            3. 嚴格控制視覺排版：強制斷行，每句話不要太長，段落與段落之間必須有空白行。
            4. 語氣轉換：轉為 PTT 用語（例如：原PO、大大、小妹等），並清除所有 Emoji 表情符號。
            5. 模擬回文：在文章最下方生成 5 條模擬推文反應（需正確使用「推」、「噓」、「→」）。
            """
            
            with st.spinner('Gemini 正在為你客製化轉譯為 PTT 生態用語...'):
                try:
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"AI 生成失敗：{e}")
