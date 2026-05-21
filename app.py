import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient

# 1. 網頁標題與排版設定
st.set_page_config(page_title="Threads 醫美素材精準改寫器", layout="wide")
st.title("Threads 醫美素材自選與 PTT 鄉民風格改寫器")

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
        "maxItems": 15,
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

# 5. 初始化 Session State 記憶資料
if "fetched_posts" not in st.session_state:
    st.session_state.fetched_posts = []
if "current_keyword" not in st.session_state:
    st.session_state.current_keyword = ""

search_term = keywords[category][0]

# 按鈕一：搜尋熱門清單
if st.button(f"🔎 搜尋「{search_term}」熱門文章"):
    if not apify_token:
        st.error("請先在左側輸入你的 Apify Token！")
    else:
        with st.spinner(f'正在前往 Threads 撈取最新的 {search_term} 討論池...'):
            st.session_state.fetched_posts = fetch_threads_via_apify(search_term, apify_token)
            st.session_state.current_keyword = search_term

# 6. 顯示自選清單與 AI 精準改寫
if st.session_state.fetched_posts:
    st.success(f"成功撈回 {len(st.session_state.fetched_posts)} 篇相關文章！請挑選素材：")
    
    options = []
    for p in st.session_state.fetched_posts:
        author_data = p.get('author')
        author = author_data.get('username', '未知') if isinstance(author_data, dict) else p.get('username', '未知')
        text = p.get('text', p.get('caption', '無內文')).replace('\n', ' ')[:30]
        options.append(f"👤 @{author} | 📝 {text}...")
        
    selected_index = st.selectbox("🎯 請選擇你想改寫的文章：", range(len(options)), format_func=lambda x: options[x])
    
    chosen_post = st.session_state.fetched_posts[selected_index]
    content = chosen_post.get('text', chosen_post.get('caption', '無文字內容'))
    url = chosen_post.get('url', '')
    
    st.info(f"**💡 你已選定素材：** {content}")
    
    # 按鈕二：四大情境與真實推文格式改寫
    if st.button("🔥 開始將所選文章改寫為 PTT 格式"):
        if not gemini_api_key:
            st.error("請填寫 Gemini API Key！")
        else:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            st.subheader("PTT 風格轉換結果")
            
            prompt = f"""
            你是一位精通台灣 PTT 論壇（如 facelift、BeautySalon 板）文化與口碑操作的頂尖操盤手。
            請根據以下提供的 Threads 原始內容，先判斷其屬於哪一種「情境分類」，並嚴格模仿該分類的 PTT 真人發文與回文精髓進行重寫。
            
            【Threads 原始內容】：
            {content}
            
            【行銷操盤手必須死守的 PTT 真人寫作規範】：
            1. 視覺高碎裂感（最重要）：每句話絕對不能過長（大約 15 個字內），只要講完一個短句就必須「強制斷行」。段落與段落之間必須留下一條完整的「空白行」。禁止出現任何長篇大論的文字方塊！
            2.
