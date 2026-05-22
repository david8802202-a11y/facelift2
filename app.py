import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient
import random

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

# 3. 豐富的醫美關鍵字庫（優化：改為多療程隨機挑選機制）
keywords_pool = {
    "電波": ["鳳凰電波", "玩美電波", "海芙音波", "索夫波", "眼周音波"],
    "針劑": ["玻尿酸", "肉毒咀嚼肌", "精靈針", "洢蓮絲", "鼻基底玻尿酸"],
    "診所": ["醫美診所推薦", "醫美避雷", "醫美諮詢", "台北醫美推薦"],
    "閒聊": ["容貌焦慮", "醫美保養", "術後恢復", "失戀醫美"]
}

# 4. 呼看 Apify 爬蟲函式
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

# 【優化】每次執行時，從字庫中隨機抽樣一個療程或主題作為本次搜尋詞
if st.button("🔎 隨機挑選療程並搜尋 Threads"):
    if not apify_token:
        st.error("請先在左側輸入你的 Apify Token！")
    else:
        # 隨機選擇該類別下的一個特定療程
        search_term = random.choice(keywords_pool[category])
        st.session_state.current_keyword = search_term
        
        with st.spinner(f'正在隨機選定主題「{search_term}」並前往 Threads 撈取讨论池...'):
            st.session_state.fetched_posts = fetch_threads_via_apify(search_term, apify_token)

# 顯示當前鎖定的隨機關鍵字
if st.session_state.current_keyword:
    st.info(f"當前搜尋主題：**{st.session_state.current_keyword}**")

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
            2. 語氣與禁忌：徹底清除所有 Emoji（如 😂, ✨, 🥺）。絕對不能出現年份字眼。
            3. 情境分類與對應語氣（請自行判斷套用）：
               - A.【問題/詢問類】：外貌焦慮、特定生理困擾起手。內文必須帶有「爬過文了、諮詢過但猶豫、怕被強推銷、求救QQ」的人設。
               - B.【術後心得/體感類】：著重在「極其細微的生理體感描繪」（如：吃東西臉超酸、大腸包小腸咬不動、一邊臉腫起來、擔心假體破掉）。語氣優缺點並陳、碎碎念。
               - C.【避雷/抱怨/吐槽類】：起手式為「在其他平台看到八卦、身邊朋友踩雷、去諮詢發現診所都不講清楚」。語氣要帶點忿忿不平與酸度。
               - D.【社會觀察/閒聊類】：以第三人稱視角切入（如：感嘆妹子失戀背債大整型、朋友當醫美業務後變得很像直銷瘋狂拉客）。語氣帶有吃瓜群眾感。
            4. 標題格式：根據你挑選的情境，自動加上分類標籤（例：[問題]、[討論]、[心得]、[閒聊]）。
            
            5. 【嚴格執行的 PTT 回文格式規範（必須與參考檔案完全一致）】：
               在文章最下方，請模擬生成 10 條高質量回文。
               
               【格式死命令】：
               - 必須精準生成 10 則回文，不能多也不能少。
               - 絕對不允許出現任何使用者帳號、ID（例如禁止出現 user123）。
               - 絕對不允許出現任何冒號（:）或引號。
               - 絕對不允許出現任何日期與時間（例如禁止出現 05/14 18:23）。
               - 絕對不允許出現任何噓文。
               
               請交替使用以下兩種真實檔案格式輸出（每條回文獨立一行）：
               格式一：以「推|」開頭，後面直接接回文內容。
               格式二：沒有任何開頭標籤，直接輸出純回文內容（模擬長推文被拆行的效果）。
               
               【回文範例樣式】：
               推|原PO拍拍
               這家水很深根本強推銷
               推|之前去諮詢也這樣，聽完超有壓力
               推|卡位等熱心大大分享心得
               真的還是要看醫生技術，一堆業務只想拉客
            """
            
            with st.spinner('Gemini 正在為你生成最道地的 PTT 文章與 10 則推文...'):
                try:
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"AI 生成失敗：{e}")
