import streamlit as st
import google.generativeai as genai
from apify_client import ApifyClient

st.set_page_config(page_title="Threads 醫美素材 PTT 改寫器", layout="wide")
st.title("Threads 自動搜尋與 PTT 風格改寫器")

# 側邊欄設定區
st.sidebar.header("操作設定")

# 建立一個安全讀取機制，避免本地端測試時找不到 Secrets 而報錯
default_gemini = ""
default_apify = ""

try:
    default_gemini = st.secrets["GEMINI_API_KEY"]
    default_apify = st.secrets["APIFY_TOKEN"]
except Exception:
    pass # 如果保險箱裡沒東西，就維持空字串

# 將保險箱拿到的金鑰設為預設值 (value)
gemini_api_key = st.sidebar.text_input("輸入 Gemini API Key", value=default_gemini, type="password")
apify_token = st.sidebar.text_input("輸入 Apify API Token", value=default_apify, type="password")
category = st.sidebar.selectbox("篩選類別", ["電波", "針劑", "診所", "閒聊"])

# 醫美關鍵字庫 (取第一個字作為搜尋關鍵字)
keywords = {
    "電波": ["鳳凰電波", "玩美電波", "海芙音波", "索夫波"],
    "針劑": ["玻尿酸", "肉毒", "精靈針", "洢蓮絲"],
    "診所": ["醫美診所推薦", "醫美避雷", "醫美諮詢"],
    "閒聊": ["容貌焦慮", "醫美保養", "術後恢復"]
}

# 呼叫 Apify 的函式
def fetch_threads_via_apify(keyword, token):
    client = ApifyClient(token)
    actor_id = "watcher.data/search-threads-by-keywords"
    
    run_input = {
        "keywords": [keyword],
        "maxItems": 10,
        "sortByRecent": False
    }
    
    try:
        # 執行爬蟲
        run = client.actor(actor_id).call(run_input=run_input)
        
        # 修正取值邏輯：改用 get() 或是直接讀取屬性，相容新版 SDK
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else run.default_dataset_id
        
        # 撈取資料集內容
        items = list(client.dataset(dataset_id).iterate_items())
        return items
    except Exception as e:
        st.error(f"Apify 爬蟲執行失敗: {e}")
        return []

# 執行區塊
if st.button("開始自動搜尋與改寫"):
    if not gemini_api_key or not apify_token:
        st.error("請確認左側的 Gemini API Key 與 Apify Token 皆已填寫！")
    else:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        search_term = keywords[category][0]
        
        with st.spinner(f'正在驅動 Apify 爬蟲前往 Threads 搜尋「{search_term}」...'):
            posts = fetch_threads_via_apify(search_term, apify_token)
            
            if not posts:
                st.warning(f"目前沒有找到「{search_term}」相關的熱門 Threads 貼文。")
            else:
                st.success(f"成功抓回 {len(posts)} 篇貼文！(自動取按讚數最高的一篇進行改寫)")
                
                # 依照按讚數 (likeCount) 排序，找出最熱門的文章
                top_post = sorted(posts, key=lambda x: x.get('likeCount', 0), reverse=True)[0]
                content = top_post.get('text', '無文字內容')
                author = top_post.get('author', {}).get('username', '未知作者')
                url = top_post.get('url', '')
                
                st.subheader("原始文章 (Threads)")
                st.write(f"**作者：** @{author} | **連結：** [點此前往 Threads]({url})")
                st.write(f"**內文：** {content}")
                
                st.subheader("PTT 風格轉換結果")
                prompt = f"""
                你是一位熟悉台灣 PTT 論壇生態的資深鄉民。請將以下這篇來自 Threads 的醫美短文，重新改寫成 PTT (例如 facelift 板) 的發文風格。
                
                【原始內容】：{content}
                
                【絕對要遵守的改寫規則】：
                1. 絕對不要在文章開頭或是任何地方提到「年份開頭」。
                2. 標題必須加上 PTT 的分類標籤（例如 [問題]、[心得]、[討論]）。
                3. 嚴格控制視覺排版：強制斷行，每句話不要太長，段落與段落之間必須有空白行。
                4. 語氣轉換：轉為 PTT 用語（例如：原PO、大大等），並清除 Threads 常見的過多 Emoji。
                5. 模擬回文：在文章最下方生成 5 條模擬推文反應（需正確使用「推」、「噓」、「→」）。
                """
                
                with st.spinner('Gemini 正在將內容轉譯為 PTT 生態用語...'):
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"AI 生成失敗：{e}")
