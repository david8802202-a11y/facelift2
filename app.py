import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient

# 1. 網頁標題與排版設定
st.set_page_config(page_title="Threads 醫美素材精準改寫器", layout="wide")
st.title("Threads 醫美素材自選與 PTT 鄉民風格改寫器")

# 2. 側邊欄設定區（安全讀取 Secrets 變數）
st.sidebar.header("操作設定")

# 預設值為空字串
default_gemini = ""
default_apify = ""

# 【超強防呆】嘗試讀取 Secrets，如果失敗就略過，絕對不讓網頁崩潰
if "GEMINI_API_KEY" in st.secrets:
    default_gemini = st.secrets["GEMINI_API_KEY"]
if "APIFY_TOKEN" in st.secrets:
    default_apify = st.secrets["APIFY_TOKEN"]

gemini_api_key = st.sidebar.text_input("輸入 Gemini API Key", value=default_gemini, type="password")
apify_token = st.sidebar.text_input("輸入 Apify API Token", value=default_apify, type="password")

# 安全抓取 Apify 餘額
if apify_token:
    try:
        client = ApifyClient(apify_token)
        account_info = client.account().get()
        if account_info and "currentMonthUsageUsd" in account_info:
            current_month_usage = account_info["currentMonthUsageUsd"]
            st.sidebar.metric(label="本月已用 Apify 額度", value=f"${current_month_usage:.3f} / $5.000")
    except Exception:
        pass

category = st.sidebar.selectbox("篩選類別", ["電波", "針劑", "診所", "閒聊"])

# 3. 醫美關鍵字庫
keywords_pool = {
    "電波": ["音波", "電波"],
    "針劑": ["玻尿酸", "肉毒", "精靈針", "洢蓮絲", "鼻基底玻尿酸", "逆時針"],
    "診所": ["醫美診所推薦", "醫美避雷", "醫美諮詢", "台北醫美推薦", "高雄醫美推薦", "台中醫美推薦"],
    "閒聊": ["醫美", "醫美保養", "術後恢復", "醫美+術後"]
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

# 6. 搜尋與自訂話題核心區
st.write("---")
st.subheader("第一步：獲取 Threads 素材來源")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**模式 A：從字庫隨機搜熱門**")
    if st.button("🎲 隨機挑選療程並搜尋 Threads"):
        if not apify_token:
            st.error("請先在左側輸入你的 Apify Token！")
        else:
            import random
            search_term = random.choice(keywords_pool[category])
            st.session_state.current_keyword = search_term
            with st.spinner(f'正在搜尋庫存關鍵字「{search_term}」...'):
                st.session_state.fetched_posts = fetch_threads_via_apify(search_term, apify_token)

with col2:
    st.markdown("**模式 B：自訂話題精準搜尋**")
    custom_input = st.text_input("想搜什麼？直接輸入（例如：皮秒、消脂針、雙眼皮失敗）：", key="custom_term")
    if st.button("🎯 用自訂話題搜尋 Threads"):
        if not apify_token:
            st.error("請先在左側輸入你的 Apify Token！")
        elif not custom_input:
            st.warning("請先輸入你想自訂的話題關鍵字！")
        else:
            st.session_state.current_keyword = custom_input
            with st.spinner(f'正在精準搜尋自訂話題「{custom_input}」...'):
                st.session_state.fetched_posts = fetch_threads_via_apify(custom_input, apify_token)

if st.session_state.current_keyword:
    st.info(f"當前鎖定主題：**{st.session_state.current_keyword}**")

# 7. 顯示自選清單與 AI 精準改寫
if st.session_state.fetched_posts:
    st.write("---")
    st.subheader("第二步：挑選素材與 AI 口碑轉化")
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
    
    st.info(f"**💡 你已選定素材：** {content}")
    
    if st.button("🔥 開始將所選文章改寫為 PTT 格式"):
        if not gemini_api_key:
            st.error("請填寫 Gemini API Key！")
        else:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            st.subheader("PTT 風格轉換結果")
            
            prompt = f"""
            你是一位精通台灣 PTT 論壇文化與口碑操作的頂尖操盤手。
            請將以下提供的 Threads 原始內容，改寫成 PTT (例如 facelift 板) 的發文與回文。
            
            【Threads 原始內容】：
            {content}
            
            【發文排版死命令】：
            1. 視覺高碎裂感：每句話不能過長（大約 15 字內），講完一個短句就必須「強制斷行」。段落之間必須留一條完整的「空白行」。禁止出現長篇大論的文字方塊！
            2. 語氣：模仿真人先碎碎念交代情境再切入主題。清除所有 Emoji、清除任何年份字眼。
            3. 標題格式：自動加上 [問題]、[討論]、[心得]、[閒聊] 之一的分類標籤。
            
            【回文輸出死命令（不准有任何例外）】：
            請在文章最下方，精準輸出 10 則模擬回文。
            我不管你對 PTT 的預設印象是什麼，回文格式「必須且只能」完全符合下方的要求。
            
            1. 絕對禁止出現任何使用者 ID（例如禁止出現 user123、hater456）。
            2. 絕對禁止出現任何英文冒號（:）。
            3. 絕對禁止出現任何日期與時間（例如禁止出現 05/14 18:23）。
            4. 絕對禁止出現任何噓文。
            5. 每則回文各自獨立一行。開頭只能是「推|」或「直接是純文字內容」。
            
            請完全參照以下 10 則輸出格式樣本作改寫（字數短、口語化）：
            推|原PO拍拍
            這家水很深根本強推銷
            推|之前去諮詢也這樣，聽完超有壓力
            推|卡位等熱心大大分享心得
            真的還是要看醫生技術，一堆業務只想拉客
            推|打完肉毒真的咀嚼無力一陣子
            吃大腸包小腸咬不動笑死
            推|這家避雷+1 諮詢師臉超臭
            推|眼周音波真的比較少人討論
            想知道完整療程次數診所都不先說
            """
            
            with st.spinner('Gemini 正在為你生成最道地的 PTT 文章與 10 則推文...'):
                try:
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"AI 生成失敗：{e}")
