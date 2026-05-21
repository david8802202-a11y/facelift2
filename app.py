import random  # 記得在最上方或這個區塊前確保有 import random

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
                st.success(f"成功抓回 {len(posts)} 篇貼文！(已從前 10 篇熱門討論中隨機挑選一篇改寫，避免內容重複)")
                
                # 【優化：解決 BUG】不再死板取第 1 名，改從熱門池中隨機挑選 1 篇
                top_post = random.choice(posts)
                
                content = top_post.get('text', top_post.get('caption', '無文字內容'))
                
                # 【優化：解決報錯】超安全取作者欄位邏輯，層層防護
                author_data = top_post.get('author')
                if isinstance(author_data, dict):
                    author = author_data.get('username', author_data.get('username', '未知作者'))
                elif isinstance(author_data, str):
                    author = author_data
                else:
                    author = top_post.get('username', '未知作者')
                
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
