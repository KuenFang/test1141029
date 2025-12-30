import streamlit as st
import os
import textwrap
import time 
from io import BytesIO
import re 

# =============================================================================
# Google Generative AI 導入
# =============================================================================
import google.genai as genai
from google.genai import types
from google.genai import errors
from google.genai.errors import APIError 

# =============================================================================
# 0. 全域設定
# =============================================================================

MODEL_NAME = "gemini-3-pro-preview"

# =============================================================================
# 1. 頁面配置與 CSS 雙模態設計 (V6.4 核心：適應淺色與深色)
# =============================================================================

st.set_page_config(
    page_title="AI財報分析系統 (K.R. Professional)",
    page_icon="📊", # 回歸專業圖標
    layout="wide",
)

# 注入雙模態適應性 CSS
st.markdown("""
<style>
    /* ==========================================================================
       通用基底樣式 (無論深淺都適用)
       ========================================================================== */
    /* 標題通用漸層動畫 */
    h1, h2, h3, .big-title {
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        animation: sheen 5s linear infinite;
        text-align: center;
        padding-bottom: 10px;
    }
    @keyframes sheen { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }
    
    /* 按鈕通用結構 */
    .stButton>button {
        border: none;
        position: relative;
        z-index: 1;
        border-radius: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        overflow: hidden;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); }

    /* 裝飾分隔線通用結構 */
    .royal-divider {
        display: flex; align-items: center; margin: 30px 0;
    }
    .royal-divider::before, .royal-divider::after {
        content: ""; flex: 1; height: 1px; opacity: 0.5;
    }
    .royal-divider::before { margin-right: 15px; }
    .royal-divider::after { margin-left: 15px; }
    .royal-divider-icon { font-size: 1.2rem; }
    hr { display: none; } /* 隱藏預設分隔線 */

    /* 左下角浮水印通用結構 */
    .fixed-watermark {
        position: fixed; bottom: 20px; left: 25px; font-size: 18px;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 900; z-index: 9999; pointer-events: none; opacity: 0.7;
    }

    /* ==========================================================================
       【淺色模式】專用樣式 (針對[data-theme="light"]) - 乾淨、明亮、無壓迫
       ========================================================================== */
    [data-theme="light"] .stApp {
        background-color: #f8f9fa; /* 純淨灰白底 */
        color: #333333; /* 深灰文字，易讀 */
    }
    
    /* 淺色模式標題：深紫到深金，較穩重 */
    [data-theme="light"] h1, [data-theme="light"] h2, [data-theme="light"] h3, [data-theme="light"] .big-title {
        background-image: linear-gradient(to right, #4a1a88, #b8860b, #4a1a88);
        text-shadow: none; /* 移除發光 */
    }

    /* 淺色模式卡片：乾淨白底 + 細緻紫金邊框 + 輕微陰影 */
    [data-theme="light"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: #ffffff;
        border-radius: 15px;
        padding: 25px;
        border: 1px solid transparent; /* 先設透明，用 background-image 實現漸層邊框 */
        background-image: linear-gradient(white, white), linear-gradient(to right, #9D4EDD, #D4AF37);
        background-origin: border-box;
        background-clip: padding-box, border-box;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); /* 極輕柔陰影 */
        margin-bottom: 20px;
    }
    [data-theme="light"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"]:hover {
         box-shadow: 0 8px 25px rgba(157, 78, 221, 0.15); /* hover 時增加一點紫色氛圍 */
    }

    /* 淺色模式按鈕 */
    [data-theme="light"] .stButton>button {
        background: linear-gradient(135deg, #6a3093, #8e44ad); /* 紫色漸層 */
        color: #ffffff !important; /* 白字 */
        box-shadow: 0 4px 10px rgba(106, 48, 147, 0.3);
    }
    [data-theme="light"] .stButton>button:hover {
        box-shadow: 0 6px 15px rgba(106, 48, 147, 0.5);
    }
    /* 淺色模式次要按鈕 */
    [data-theme="light"] button[kind="secondary"] {
        background: transparent !important;
        border: 2px solid #6a3093 !important;
        color: #6a3093 !important;
    }

    /* 淺色模式輸入框 */
    [data-theme="light"] .stTextInput input, [data-theme="light"] .stChatInput textarea, [data-theme="light"] .stFileUploader {
        background-color: #ffffff !important;
        border: 1px solid #ced4da !important;
        color: #495057 !important;
    }
    [data-theme="light"] .stTextInput input:focus, [data-theme="light"] .stChatInput textarea:focus {
        border-color: #9D4EDD !important;
        box-shadow: 0 0 0 3px rgba(157, 78, 221, 0.25) !important;
    }

    /* 淺色模式對話氣泡 */
    [data-theme="light"] .stChatMessage[data-testid="stChatMessageUser"] {
        background: #6a3093; color: white; /* 紫底白字 */
    }
    [data-theme="light"] .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: #f1f3f5; color: #333; border: 1px solid #dcdcdc; /* 灰底黑字 */
    }
    
    /* 淺色模式分隔線與浮水印 */
    [data-theme="light"] .royal-divider { color: #6a3093; }
    [data-theme="light"] .royal-divider::before, [data-theme="light"] .royal-divider::after {
        background: linear-gradient(to right, transparent, #6a3093, transparent);
    }
    [data-theme="light"] .fixed-watermark {
        background: linear-gradient(to right, #6a3093, #b8860b);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }


    /* ==========================================================================
       【深色模式】專用樣式 (針對[data-theme="dark"]) - 延續 V6.3 的華麗，但稍微收斂
       ========================================================================== */
    [data-theme="dark"] .stApp {
        background-color: #0a0510; /* 更深沉的黑 */
        /* 降低紋理對比度，減少雜訊感 */
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(123, 44, 191, 0.1) 0%, transparent 40%),
            radial-gradient(circle at 80% 70%, rgba(255, 215, 0, 0.08) 0%, transparent 40%);
        color: #e0e0e0;
    }
    /* 深色模式標題：亮金亮紫，帶發光 */
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3, [data-theme="dark"] .big-title {
        background-image: linear-gradient(to right, #FFD700, #D4AF37, #9D4EDD);
        text-shadow: 0 2px 15px rgba(157, 78, 221, 0.5); /* 強烈發光 */
    }

    /* 深色模式卡片：毛玻璃 + 強烈光暈 (V6.3 風格) */
    [data-theme="dark"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: rgba(40, 20, 60, 0.5);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 30px;
        border: 1px solid rgba(255, 215, 0, 0.3); 
        /* 調整光暈強度，減少刺眼感 */
        box-shadow: 
            0 0 0 1px rgba(157, 78, 221, 0.2) inset,
            0 15px 30px rgba(0, 0, 0, 0.5),
            0 0 30px rgba(123, 44, 191, 0.2); 
        margin-bottom: 25px;
    }
    [data-theme="dark"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"]:hover {
         border-color: #FFD700;
         box-shadow: 0 0 50px rgba(157, 78, 221, 0.4), 0 0 15px rgba(255, 215, 0, 0.3);
    }

    /* 深色模式按鈕 */
    [data-theme="dark"] .stButton>button {
        background: linear-gradient(135deg, #4a1a88 0%, #7B2CBF 100%);
        color: #FFD700 !important;
        box-shadow: 0 5px 15px rgba(123, 44, 191, 0.5);
    }
    [data-theme="dark"] .stButton>button:hover {
        box-shadow: 0 8px 25px rgba(255, 215, 0, 0.7);
        color: white !important;
    }

    /* 深色模式輸入框 */
    [data-theme="dark"] .stTextInput input, [data-theme="dark"] .stChatInput textarea, [data-theme="dark"] .stFileUploader {
        background-color: rgba(20, 10, 30, 0.7) !important;
        border: 2px solid #9D4EDD !important;
        color: #FFD700 !important;
    }
    [data-theme="dark"] .stTextInput input:focus {
        border-color: #FFD700 !important;
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.5) !important;
    }

    /* 深色模式對話氣泡 */
    [data-theme="dark"] .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #7B2CBF, #9D4EDD); border: 1px solid #FFD700;
    }
    [data-theme="dark"] .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: rgba(40, 40, 45, 0.95); border: 1px solid #D4AF37; color: #f0f0f0;
    }

    /* 深色模式分隔線與浮水印 */
    [data-theme="dark"] .royal-divider { color: #D4AF37; }
    [data-theme="dark"] .royal-divider::before, [data-theme="dark"] .royal-divider::after {
        background: linear-gradient(to right, transparent, #9D4EDD, #FFD700, transparent);
    }
    [data-theme="dark"] .fixed-watermark {
        background: linear-gradient(to right, #FFD700, #FFF, #9D4EDD);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 3px rgba(255,215,0,0.5));
    }

    /* Tab 樣式 (適應兩者) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent; padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        border: none; color: inherit; opacity: 0.7; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        opacity: 1;
        border-bottom: 3px solid #9D4EDD !important;
        color: #9D4EDD !important;
    }
    [data-theme="dark"] .stTabs [aria-selected="true"] {
        border-bottom-color: #FFD700 !important;
        color: #FFD700 !important;
    }

</style>
<div class="fixed-watermark">K.R. FIN-AI</div>
""", unsafe_allow_html=True)

# 輔助函數：產生裝飾分隔線 (圖標改為專業風格)
def royal_divider(icon="◆"):
    st.markdown(f"""
    <div class="royal-divider">
        <span class="royal-divider-icon">{icon}</span>
    </div>
    """, unsafe_allow_html=True)

keep_alive = """<script>setInterval(() => { fetch(window.location.href, {mode: 'no-cors'}); }, 300000);</script>"""
st.markdown(keep_alive, unsafe_allow_html=True)


# =============================================================================
# 2. 核心提示詞 (保持完整)
# =============================================================================
# (為節省篇幅，此處省略提示詞內容，實際程式碼請務必保留完整的 PROMPT 定義)
# 步驟 1：抓取公司名稱
PROMPT_COMPANY_NAME = textwrap.dedent("""請從這份 PDF 財務報告的第一頁或封面頁中，提取出完整的、官方的公司法定全名 (例如 "台灣積體電路製造股份有限公司")。限制：1. 僅輸出公司名稱的純文字字串。2. 禁止包含任何 Markdown、引號、標籤或任何 "公司名稱：" 之類的前綴。3. 禁止包含任何其他文字或問候語。""")
# 步驟 2：標準化提取 (完整版)
PROMPT_BIAO_ZHUN_HUA_CONTENT = textwrap.dedent("""**請以以下標準來對財報四大表後有項目標號的數十項內容提取資料，並將以下 37 個大項各自生成獨立的 Markdown 表格** (溫度為0)**限制0：禁止包含任何前言、開場白、問候語或免責聲明 (例如 "好的，這..."). 您的回答必須直接開始於所要求的第一個 Markdown 表格 (例如 '## 公司沿革')。**限制1：如果標準化之規則財報中無該分類，跳過該分類**限制2：輸出時嚴禁包含編號 (例如 '一、' 或 '1.')。請直接以 Markdown 標題 (例如 '## 公司沿革') 開始，絕對不要輸出 37 項規則的編號。**限制3：與變動金額有關的內容，橫軸為時間線與變動比率，縱軸為項目，如果橫軸限制4：只能使用我們提供的檔案，不能使用外部資訊限制5：計算時在內部進行雙重核對，確保兩組計算，只使用提供資料且結果完全一致後，才可以輸出內容限制6：如果有資料缺漏導致無法計算，缺漏的部分不做計算**限制7.：每一個大項 (例如 '公司沿革', '現金及約當現金') 都必須是一個獨立的 Markdown 表格。如果一個大項下有多個要求事項 (例如 '應收票據及帳款淨額' 下有 '應收帳款淨額三期變動' 和 '帳齡分析表三期變動')，請在同一個表格中用多行來呈現，或生成多個表格。**限制8：禁止提供任何外部資訊一、公司沿革,公司名稱,成立日期[yyy/mm/dd],從事業務二、通過財務報告之日期及程序,核准日期[yyy/mm/dd]三、新發布及修訂準則及解釋之適用,新發布及修訂準則及解釋之適用對本公司之影響四、重大會計政策之彙總說明,會計政策對公司之影響五、重大會計判斷、估計及假設不確定性之主要來源,重大會計判斷、估計及假設不確定性之主要來源之變動六、現金及約當現金,現金及約當現金合計之變動七、透過損益按公允價值衡量之金融資產及金融負債,金融資產與金融負債之三期變動八、透過其他綜合損益按公允價值衡量之金融資產,透過其他綜合損益按公允價值衡量之金融資產之三期變動九、按攤銷後成本衡量之金融資產,金融資產合計之三期變動十、避險之金融工具,公允價值避險之方式及當期影響,現金流量避險之方式及當期影響,國外營運機構淨投資避險十一、應收票據及帳款淨額,應收帳款淨額三期變動,帳齡分析表三期變動,十二、存貨,製成品之三期變動金額,在製品之三期變動金額,原料之兩期變動金額,如有其餘獨立項目歸類進前三大項,十三、採用權益法之投資,子公司與關聯企業之名單及其控股百分比三期變動十四、不動產、廠房及設備,拆分自用與營業租賃後進行三期比較十五、租賃協議,三期變動十六、無形資產,三期變動十七、應付公司債,公司債項目性質,本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),十八、長期銀行借款,長期銀行借款,本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),十九、權益,已發行股本本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),本期日期(YYY/MM/DD),股本變動,盈餘分配,二十、營業收入,客戶合約之收入(應用領域別之兩期變動，如無應用領域別則讀取營業收入總額),合約負債三期變動,暫收款三期變動二一、利息收入,利息收入總額之兩期變動二二、財務成本,利息費用總額兩期變動二三、其他利益及損失淨額,其他利益及損失淨額兩期比較二四、所得稅,認列於損益之所得稅費用兩期變動二五、每股盈餘,基本每股盈餘兩期變動,稀釋每股盈餘兩期變動,二六、股份基礎給付協議,股份基礎給付計畫金額二七、費用性質之額外資訊,兩期比較二八、政府補助,兩期比較二九、現金流量資訊,營業活動之淨現金流入之兩期變動,投資活動之淨現金流出之兩期變動,本期現金及約當現金淨增加數之兩期變動三十、金融工具,金融資產三期變動,金融負債三期變動,非衍生金融負債三期變動,非衍生金融資產三期變動,衍生金融工具之三期變動,租賃負債之三期變動,透過損益按公允價值衡量之金融資產之三期變動,透過其他綜合損益按公允價值衡量之金融資產之三期變動,避險之金融資產之三期變動,文字部分之總結,三一、關係人交易,營業收入兩期變動,進貨三期變動,應收關係人款項三期變動,應付關係人款項三期變動,應付費用及其他流動負債三期變動,其他關係人交易三期變動,三二、質押之資產,質押之資產金額三期變動三三、重大或有負債及未認列之合約承諾,背書保證金額,或有負債總結,三四、重大之災害損失,發生原因,日期[yyy/mm],金額[仟元]三五、外幣金融資產及負債之匯率資訊,金融資產三期變動,金融負債三期變動,三六、附註揭露事項,請對我提供給你的資料中的附註揭露事項及其提及的附表進行分析三七、營運部門資訊,擁有哪些營運部門""")
# 步驟 3：比率計算 (完整版 P/E 修正)
PROMPT_RATIO_CONTENT = textwrap.dedent("""請根據以下計算公式及限制，計算股東權益報酬率 (ROE)、本益比 (P/E Ratio)、淨利率 (Net Profit Margin)、毛利率 (Gross Profit Margin)、負債比率 (Debt Ratio)、流動比率 (Current Ratio)、速動比率 (Quick Ratio) 之兩期數據。**注意：您必須輸出七個獨立的 Markdown 表格。****除了本益比以外每個表格必須遵循以下嚴格的 3x2 格式要求 (3 欄 x 2 行)，本益比則只需 2x2 格式要求 (2 欄 x 2 行，無須比較期日期或期間的欄位第二欄名稱為本年度)：**| 財務比率名稱 (例如: 股東權益報酬率(ROE)) | [最近一期日期或期間] | [比較期日期或期間] || :--- | :--- | :--- || 比率 | [計算結果及單位，例如: 15.25%] | [計算結果及單位，例如: 12.80%] |**請嚴格遵守：**1. 輸出結果**必須是 7 個獨立的 Markdown 表格**，且只包含您計算出的數據和單位。2. 表格內容**只能是數字和單位** (例如 %、倍、次)。3. 表格的第一格**必須是比率名稱**，第二行第一格**必須是「比率」**這兩個字。**4. 禁止包含任何前言、開場白或問候語。您的回答必須直接從第一個 Markdown 表格 (股東權益報酬率) 開始。**計算公式：財務比率 (Financial Ratio),計算公式 (Formula),備註 (Notes)1. 股東權益報酬率 (ROE),(歸屬於母公司業主之本期淨利) / (歸屬於母公司業主之平均權益),當期（例如半年）數據計算。,其中，平均權益 = (期初歸屬於母公司業主之權益 + 期末歸屬於母公司業主之權益) / 2,2. 本益比 (P/E Ratio) (以當日收盤價格為基準), **(收盤價) / (年化每股盈餘)**。   **年化每股盈餘 (Annualized EPS) 計算規則 (必須嚴格遵守)：** - 步驟 A: 判斷財報期間。   - 步驟 B: 根據期間調整 EPS：     - 若為第一季 (Q1, 1-3月): 年化 EPS = 本期 EPS x 4     - 若為上半年 (H1, 1-6月): 年化 EPS = 本期累計 EPS x 2     - 若為前三季 (Q3, 1-9月): 年化 EPS = (本期累計 EPS / 3) x 4     - 若為全年度 (Annual, 1-12月): 年化 EPS = 本期累計 EPS x 1   - 步驟 C: 使用指定的收盤價除以算出的年化 EPS。   *注意：使用基本每股盈餘。指定收盤價請使用 Google Search 搜尋該財報截止日或次日的收盤價格。*3. 淨利率 (Net Profit Margin),(本期淨利) / (營業收入),單季數據計算。4. 毛利率 (Gross Profit Margin),(營業毛利) / (營業收入),單季數據計算。5. 負債比率 (Debt Ratio),(負債總計) / (資產總計),期末時點數據計算。6. 流動比率 (Current Ratio),(流動資產合計) / (流動負債合計),期末時點數據計算。7. 速動比率 (Quick Ratio),(流動資產合計 - 存貨 - 預付款項) / (流動負債合計),期末時點數據計算，採保守定義。限制：唯一數據來源：除了公司的收盤價外所有的計算僅能使用您所提供的PDF財務報告檔案，除收盤價需上網絡查詢外，不得引用任何外部資訊。計算時間基準：毛利率、淨利率、本益比皆以「單季」數據進行計算；需要平均餘額的比率（ROE）以「當期」期間為基礎。平均餘額計算：分母的平均餘額必須採用該「當期」期間的期初餘額與期末餘額之平均。數據替換原則：若缺乏當期「期初」數據，則採用可取得的最近一期餘額來替代期初數據，並在報告中明確註明此近似處理。不進行年化處理：所有的比率計算結果直接呈現該期間的數據，不轉換為年化率，除非計算式有特別要求進行年化 (如 P/E)。內部驗證機制：在生成最終報告前，會進行內部雙重計算與核對。處理資料缺漏：若因缺乏必要的數據而無法計算，將明確標示為**「無法計算」**並註明原因。""")
# 步驟 4：總結 (完整版)
PROMPT_ZONG_JIE_CONTENT = textwrap.dedent("""核心規則與限制限制部分：**格式限制：禁止包含任何前言、開場白、問候語或免責聲明 (例如 "好的，這是一份..."）。您的回答必須直接開始於總結的第一句話。**資料來源限制：僅能使用標準化後的內容表格及財報附註中已提取的文字資訊進行分析,排除對合併資產負債表、合併綜合損益表、合併權益變動表及合併現金流量表四大表本身數據的直接讀取與分析。數據提取限制：所有分析所需的原始數據與金額，必須從標準化表格中已計算或已提取的結果取得,確保分析的立論點是基於前一步驟的數據整理成果。分析深度限制：分析內容僅限於揭露與觀察事實與數據變動，禁止提供任何形式的投資或經營建議或評價,恪守中立客觀的立場，僅對資訊進行解讀與歸納。**內部驗證限制：在輸出總結前，必須進行內部雙重核對，確保所有分析論點均來自標準化表格或附註原文，且完全遵守所有分析規則與限制。**分析規則部分：會計基礎分析：關注「公司沿革」、「會計政策」及「重大會計判斷」等項目,用於建立對公司營運範圍、會計處理連續性及潛在風險（如暫定公允價值）的初步認識。經營細項分析：側重「營業收入結構細分」、「費用性質」、「營業外損益細項」的兩期變動,深入了解營收暴增的驅動力（例如新業務：佣金、廣告）與成本費用的結構性變化（例如折舊、攤銷的增加）。財務結構細項分析：關注「金融工具」、「質押之資產」、「租賃負債」等項目的三期變動,衡量公司在風險暴露（匯率、利率）、資產擔保情況以及長期承諾（租賃、未計價合約）的變化趨勢。關係人交易分析：著重於「營業收入」、「應收帳款」、「資金貸與」及「承包工程合約」等項目的類型與金額集中度,識別關係人交易在公司營運中的比重和性質，特別是資金流向與合約承諾。流動性與承諾分析：關注「流動性風險到期日」分析和「重大或有負債/合約承諾」的總額與結構,判斷公司短期現金壓力、合同義務以及潛在的表外風險。期後事項分析：僅羅列已發生的重大期後交易。,作為公司未來發展方向和策略變動的客觀資訊補充。計算規則部分變動數據呈現：對於金額變動，必須呈現變動金額及變動比率,突顯數據的相對變化幅度，作為分析論點的支撐。比率計算依據,變動比率計算方式為：,(本期金額−比較期金額)/比較期金額,統一所有分析中的比率計算方法。N/A 處理：若比較期金額為零，則變動比率標示為 N/A 或以文字描述為「無法計算」。,避免除以零的錯誤，並準確描述從無到有的巨大變化。幣別一致性：所有金額單位必須保持一致（新台幣千元），並在分析開始前註明。,確保數據的可讀性與準準確性。""")
# 步驟 5：講解 (完整版)
PROMPT_JIAN_JIE_CONTENT = textwrap.dedent("""**格式限制：禁止包含任何前言、開場白、問候語或免責聲明。您的回答必須直接開始於講解的第一句話。**一、 核心目標與受眾設定 (Analysis Goal and Audience)目標: 對單一公司已標準化的財務數據（四大表附註）進行深度分析。受眾: 專為「非專業人士」設計，假設讀者可能不具備基礎會計知識，無法理解融資、邊際貢獻等概念。易讀性（Readability）優先，確保報告內容可以轉化為白話文進行溝通。風格: 採用「翻譯」和「白話解釋」的語氣，將專業名詞逐一轉化為生活化語言。二、 數據來源與引用限制 (Data Integrity and Citation)數據來源: 嚴格依賴已提供的標準化後數據和原始財務報告內容。禁止使用或臆測外部資訊（例如產業新聞、股價、未來預測等）。資料時間軸: 核心數據對比必須聚焦於「114 年 1-6 月 (本期)」與「113 年 1-6 月 (去年同期)」的兩期比較，以呈現經營成果的變化。資產負債表項目則需呈現三期數據（114/06/30, 113/12/31, 113/06/30）。單位統一: 所有金額必須統一標註為新台幣仟元，除非原始數據或特殊情況另有說明。限制輸出: 分析結果中禁止包含任何主觀建議、投資判斷或價值評估，僅陳述數據事實、計算出的比率及趨勢。**內部驗證要求：在輸出講解前，必須進行內部雙重核對，確保所有「白話轉譯」均準確對應「名詞解釋標準 (Glossary)」，且所有引用的數據事實均與標準化表格一致。**三、 報告結構與內容要求 (Structure and Content Mandates)分析報告必須涵蓋以下五個主要區塊，並針對每個數據點提供詳細的解釋：1. 公司基礎資訊 (Basic Information)分析點：公司沿革、財務報告核准日、會計準則適用、重大會計估計穩定性。要求：需將會計政策的穩定性（如 IFRS 適用）解讀為「記帳規則穩定」或「報表可靠」。2. 資產負債表項目分析 (Statement of Financial Position)分析點：現金、存貨、PPE、應付公司債、負債總額等。要求：必須解釋 PPE 的增長趨G勢為「資本支出（CapEx）」，並將其轉譯為「砸錢買新設備和蓋廠」。要求：必須將存貨中的「在製品」解讀為「產線忙碌」。3. 綜合損益表項目分析 (Statement of Comprehensive Income)分析點：營業收入、毛利、淨利、每股盈餘（EPS）、所得稅費用。要求：強調「營業淨利」的增長率是否高於「營業收入」的增長率，並解釋這代表公司「管錢效率提高」。要求：需將 EPS 解釋為「平均每一股賺了多少錢」。4. 現金流量表項目分析 (Statement of Cash Flows)分析點：營業活動現金流 (CFO)、投資活動現金流 (CFI)、籌資活動現金流 (CFF)。要求：CFO 必須被稱為「賣晶片收到的現金總額」，並強調其為「核心業務收錢能力」。要求：必須對比 CFO 和 CFI 的大小關係，並解釋若 CFO > CFI，則公司能「靠自己賺來的錢來支付所有蓋廠和投資的費用」。5. 特別關注項目 (Special Focus Items)分析點：政府補助、應收帳款淨額、外幣資產、重大災害損失等。要求：將政府補助解釋為「海外子公司獲得的當地政府獎勵或補貼」。要求：將應收帳款的未逾期比例解讀為客戶的「信用質量」。四、 名詞解釋標準 (Glossary Simplification Standard)報告中使用的所有專業術術語必須在第一次出現時或在專門的註釋區塊中，按照以下「淺顯易懂」的標準進行轉譯：專業術語 (Jargon) / 轉譯標準 (Simplified Translation)資本支出 (CapEx) / 砸錢買新設備和蓋廠、買長期家當流動性 (Liquidity) / 救命錢或隨時能動用的錢在製品 (Work in Process) / 正在生產中的晶片、產線非常忙碌籌資活動 / 向股東或銀行「付錢」的活動淨利 / 獲利能力 / 最終賺到的利潤、賺錢能力應付公司債 / 長期大筆借款營業淨利 / 扣掉所有費用後，純粹靠本業賺到的錢EPS / 平均每一股股票賺了多少錢CFO / 公司靠「賣晶片」和「日常營運」收到的現金總額""")

# API Key & Session Init
try:
    API_KEY = os.getenv('GEMINI_API_KEY')
    if not API_KEY:
        API_KEY = st.secrets.get("GEMINI_API_KEY") 
except Exception:
    API_KEY = None

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'
if 'analysis_results' not in st.session_state:
    st.session_state['analysis_results'] = None
if 'current_pdf_bytes' not in st.session_state:
    st.session_state['current_pdf_bytes'] = None 
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =============================================================================
# 3. 核心 API 呼叫 (功能不變)
# =============================================================================

@st.cache_resource
def get_gemini_client(api_key):
    if not api_key: return None
    try: return genai.Client(api_key=api_key)
    except: return None

CLIENT = get_gemini_client(API_KEY)
GLOBAL_CONFIG_ERROR = None
if CLIENT is None:
    GLOBAL_CONFIG_ERROR = "❌ 錯誤：GEMINI_API_KEY 無效或未設定。"

def call_multimodal_api(file_content_bytes, prompt, use_search=False):
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}
    try:
        pdf_part = types.Part.from_bytes(data=file_content_bytes, mime_type='application/pdf')
    except Exception as e: return {"error": f"PDF 處理失敗: {e}"} 
    contents = [pdf_part, prompt] 
    tools_config = [{"google_search": {}}] if use_search else None
    config = types.GenerateContentConfig(temperature=0.0, tools=tools_config)
    for attempt in range(4): 
        try:
            response = CLIENT.models.generate_content(model=MODEL_NAME, contents=contents, config=config)
            return {"status": "success", "content": response.text}
        except Exception as e:
            if attempt == 3: return {"error": str(e)}
            time.sleep(2)

def call_text_api(input_text, prompt):
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}
    contents = [input_text, prompt] 
    config = types.GenerateContentConfig(temperature=0.0, tools=None)
    for attempt in range(4):
        try:
            response = CLIENT.models.generate_content(model=MODEL_NAME, contents=contents, config=config)
            return {"status": "success", "content": response.text}
        except Exception as e:
            if attempt == 3: return {"error": str(e)}
            time.sleep(2)

def call_chat_api(contents):
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}
    config = types.GenerateContentConfig(temperature=1.2, tools=[{"google_search": {}}])
    try:
        response = CLIENT.models.generate_content(model=MODEL_NAME, contents=contents, config=config)
        return {"status": "success", "content": response.text}
    except Exception as e:
        return {"error": str(e)}

def run_analysis_flow(file_content_to_send, status_container):
    """執行分析流程 (V6.4: 文字回歸專業用語)"""
    st.session_state['current_pdf_bytes'] = file_content_to_send
    
    try:
        # 使用 container 包裹狀態列，應用卡片樣式
        with st.container():
            with status_container.status("⏳ 正在執行 AI 分析...", expanded=True) as status:
                st.write("📜 步驟 1/5: 正在識別公司名稱...")
                name_resp = call_multimodal_api(file_content_to_send, PROMPT_COMPANY_NAME, False)
                if name_resp.get("error"): raise Exception(name_resp['error'])
                company_name = name_resp["content"].strip()
                
                st.write("🔍 步驟 2/5: 正在提取與標準化財報數據...")
                std_resp = call_multimodal_api(file_content_to_send, PROMPT_BIAO_ZHUN_HUA_CONTENT, False)
                if std_resp.get("error"): raise Exception(std_resp['error'])
                
                st.write("🧮 步驟 3/5: 正在計算關鍵財務比率...")
                ratio_resp = call_multimodal_api(file_content_to_send, PROMPT_RATIO_CONTENT, True)
                if ratio_resp.get("error"): raise Exception(ratio_resp['error'])
                
                st.write("⚖️ 步驟 4/5: 正在生成專業審計總結...")
                sum_resp = call_text_api(std_resp["content"], PROMPT_ZONG_JIE_CONTENT)
                if sum_resp.get("error"): raise Exception(sum_resp['error'])
                
                st.write("🗣️ 步驟 5/5: 正在生成白話文數據講解...")
                exp_resp = call_text_api(std_resp["content"], PROMPT_JIAN_JIE_CONTENT)
                if exp_resp.get("error"): raise Exception(exp_resp['error'])
                
                status.update(label="✅ 分析完成！準備生成報告...", state="complete", expanded=False)

        st.session_state['analysis_results'] = {
            "company_name": company_name,
            "ratio": ratio_resp["content"],
            "summary": sum_resp["content"],
            "explanation": exp_resp["content"],
            "standardization": std_resp["content"]
        }
        time.sleep(0.5)
        st.session_state['current_page'] = 'Report' # 導航到報告頁
        st.rerun()

    except Exception as e:
        st.error(f"❌ 分析流程中斷：\n{e}")

# =============================================================================
# 4. 頁面邏輯 (V6.4: 專業用語 + 卡片式結構)
# =============================================================================

def home_page():
    with st.container():
        st.markdown("<h1 style='text-align: center;'>🏛️ AI 智能財報分析系統</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.1rem; opacity: 0.8;'>融合頂尖多模態 AI 技術，提供深度數據提取、專業比率計算，以及審計級與白話文雙視角報告。</p>", unsafe_allow_html=True)

    royal_divider("💎")

    if GLOBAL_CONFIG_ERROR:
        st.error(GLOBAL_CONFIG_ERROR)
        return

    # 快速通道區塊
    with st.container():
        st.markdown("### ⚡ 快速分析 (範例企業)")
        c1, c2, c3, c4 = st.columns(4)
        target_file = None
        status_cont = st.empty()
        
        with c1: 
            if st.button("📊 2330 (台積電)", use_container_width=True): target_file = "2330.pdf"
        with c2: 
            if st.button("📈 2382 (廣達)", use_container_width=True): target_file = "2382.pdf"
        with c3: 
            if st.button("📉 2308 (台達電)", use_container_width=True): target_file = "2308.pdf"
        with c4: 
            if st.button("💻 2454 (聯發科)", use_container_width=True): target_file = "2454.pdf"

    royal_divider("📂")

    # 上傳區塊
    with st.container():
         st.markdown("### 📜 上傳財務報告")
         uploaded = st.file_uploader("請選擇 PDF 格式的文件...", type=["pdf"], key="uploader")
    
    royal_divider("🚀")

    # 啟動按鈕區塊
    with st.container():
        if target_file and os.path.exists(target_file):
            with open(target_file, "rb") as f: run_analysis_flow(f.read(), status_cont)
        elif target_file:
            st.error(f"❌ 找不到範例檔案: {target_file}")
        elif uploaded:
            col_start, col_rest = st.columns([1, 2])
            with col_start:
                 if st.button("✨ 開始執行分析", type="primary", use_container_width=True):
                    run_analysis_flow(uploaded.read(), status_cont)
        else:
            st.info("請先上傳文件或選擇範例以開始。")

def report_page():
    res = st.session_state.get('analysis_results')
    if not res:
        st.info("請先進行分析。")
        if st.button("⬅️ 回首頁"): 
            st.session_state['current_page'] = 'Home'
            st.rerun()
        return
    
    # 標題卡片
    with st.container():
        st.markdown(f"<h1 style='text-align: center;'>📜 **{res['company_name']}** 財報分析報告</h1>", unsafe_allow_html=True)
    
    royal_divider("💎")

    # 1. 財務比率卡片
    with st.container():
        st.subheader("💎 關鍵財務比率")
        ratio_txt = res['ratio']
        tables = [t.strip() for t in ratio_txt.split('\n\n') if t.strip().startswith('|') and '---' in t]
        key_map = {'ROE': '股東權益報酬率', 'Net Profit': '淨利率', 'Gross Profit': '毛利率','P/E': '本益比', 'Current Ratio': '流動比率', 'Debt Ratio': '負債比率', 'Quick Ratio': '速動比率'}
        
        cols = st.columns(3) + st.columns(4)
        shown_count = 0
        for t in tables:
            for k, v in key_map.items():
                if k in t or v in t:
                    if shown_count < 7:
                        with cols[shown_count]: st.markdown(t, unsafe_allow_html=True)
                        shown_count += 1
                    break
        if shown_count == 0: st.markdown(ratio_txt)

    royal_divider("🤖")
    
    # 2. AI 對話室引導卡片
    with st.container():
        st.markdown("### 🤖 AI 首席顧問")
        st.info("💡 如果您對報告中的數據有任何疑問，請前往戰情室，AI 顧問將為您詳細解答。")
        if st.button("💬 前往 AI 戰情室 (自由對話模式)", type="primary", use_container_width=True):
            st.session_state['current_page'] = 'Chat'
            st.rerun()

    royal_divider("📄")

    # 3. 三大分頁卡片
    with st.container():
        t1, t2, t3 = st.tabs(["📄 專業審計總結", "🗣️ 白話文數據講解", "📊 標準化資訊提取"])
        with t1: st.markdown(res['summary'])
        with t2: st.markdown(res['explanation'])
        with t3: st.markdown(res['standardization'])
    
    royal_divider("⬅️")
    
    # 返回按鈕
    if st.button("⬅️ 結束閱覽，返回首頁", kind="secondary"):
        st.session_state['analysis_results'] = None
        st.session_state['current_pdf_bytes'] = None
        st.session_state['current_page'] = 'Home'
        st.rerun()

def chat_page():
    # 頂部導航卡片
    with st.container():
        c_back, c_title = st.columns([1, 6])
        with c_back:
            if st.button("⬅️ 返回報告"):
                st.session_state['current_page'] = 'Report'
                st.rerun()
        with c_title:
            st.markdown("<h2 style='margin-top: 0;'>💬 AI 財報戰情室</h2>", unsafe_allow_html=True)

    royal_divider("📜")

    # 聊天內容區
    with st.container():
        if not st.session_state.chat_history:
            st.caption("✨ 戰情室已開啟，請輸入您的問題...")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 圖片上傳區 (可收折)
        with st.expander("📎 上傳輔助圖片/截圖 (選用)"):
            chat_uploaded_img = st.file_uploader("選擇圖片文件...", type=["png", "jpg", "jpeg"], key="chat_img_up")

    # 輸入區
    if prompt := st.chat_input("請輸入您的問題，顧問將即刻分析..."):
        # 1. 顯示並紀錄 User 訊息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # 2. 準備 Context
        inputs = []
        # PDF
        if st.session_state.get('current_pdf_bytes'):
            try: inputs.append(types.Part.from_bytes(data=st.session_state['current_pdf_bytes'], mime_type='application/pdf'))
            except: pass
        # 新上傳圖片
        if chat_uploaded_img:
             try: inputs.append(types.Part.from_bytes(data=chat_uploaded_img.read(), mime_type=chat_uploaded_img.type))
             except: pass

        res = st.session_state.get('analysis_results', {})
        std_data = res.get('standardization', '')
        # V6.4: 提示詞回歸專業
        sys_prompt = f"你是一位專業、客觀且經驗豐富的財務顧問。已附上原始財報PDF與標準化數據摘要:\n{std_data[:3000]}...\n請回答使用者問題：{prompt}"
        inputs.append(sys_prompt)

        # 3. 呼叫 API
        with st.chat_message("assistant"):
            with st.spinner("🟣 顧問正在思考中..."):
                response = call_chat_api(inputs)
                reply = f"❌ 錯誤: {response['error']}" if response.get("error") else response["content"]
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

# =============================================================================
# 5. 主程式入口
# =============================================================================

if st.session_state['current_page'] == 'Home':
    home_page()
elif st.session_state['current_page'] == 'Report':
    report_page()
elif st.session_state['current_page'] == 'Chat':
    chat_page()import streamlit as st
import os
import textwrap
import time 
from io import BytesIO
import re 

# =============================================================================
# Google Generative AI 導入
# =============================================================================
import google.genai as genai
from google.genai import types
from google.genai import errors
from google.genai.errors import APIError 

# =============================================================================
# 0. 全域設定
# =============================================================================

MODEL_NAME = "gemini-3-pro-preview"

# =============================================================================
# 1. 頁面配置與 CSS 雙模態設計 (V6.4 核心：適應淺色與深色)
# =============================================================================

st.set_page_config(
    page_title="AI財報分析系統 (K.R. Professional)",
    page_icon="📊", # 回歸專業圖標
    layout="wide",
)

# 注入雙模態適應性 CSS
st.markdown("""
<style>
    /* ==========================================================================
       通用基底樣式 (無論深淺都適用)
       ========================================================================== */
    /* 標題通用漸層動畫 */
    h1, h2, h3, .big-title {
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        animation: sheen 5s linear infinite;
        text-align: center;
        padding-bottom: 10px;
    }
    @keyframes sheen { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }
    
    /* 按鈕通用結構 */
    .stButton>button {
        border: none;
        position: relative;
        z-index: 1;
        border-radius: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
        overflow: hidden;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); }

    /* 裝飾分隔線通用結構 */
    .royal-divider {
        display: flex; align-items: center; margin: 30px 0;
    }
    .royal-divider::before, .royal-divider::after {
        content: ""; flex: 1; height: 1px; opacity: 0.5;
    }
    .royal-divider::before { margin-right: 15px; }
    .royal-divider::after { margin-left: 15px; }
    .royal-divider-icon { font-size: 1.2rem; }
    hr { display: none; } /* 隱藏預設分隔線 */

    /* 左下角浮水印通用結構 */
    .fixed-watermark {
        position: fixed; bottom: 20px; left: 25px; font-size: 18px;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 900; z-index: 9999; pointer-events: none; opacity: 0.7;
    }

    /* ==========================================================================
       【淺色模式】專用樣式 (針對[data-theme="light"]) - 乾淨、明亮、無壓迫
       ========================================================================== */
    [data-theme="light"] .stApp {
        background-color: #f8f9fa; /* 純淨灰白底 */
        color: #333333; /* 深灰文字，易讀 */
    }
    
    /* 淺色模式標題：深紫到深金，較穩重 */
    [data-theme="light"] h1, [data-theme="light"] h2, [data-theme="light"] h3, [data-theme="light"] .big-title {
        background-image: linear-gradient(to right, #4a1a88, #b8860b, #4a1a88);
        text-shadow: none; /* 移除發光 */
    }

    /* 淺色模式卡片：乾淨白底 + 細緻紫金邊框 + 輕微陰影 */
    [data-theme="light"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: #ffffff;
        border-radius: 15px;
        padding: 25px;
        border: 1px solid transparent; /* 先設透明，用 background-image 實現漸層邊框 */
        background-image: linear-gradient(white, white), linear-gradient(to right, #9D4EDD, #D4AF37);
        background-origin: border-box;
        background-clip: padding-box, border-box;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); /* 極輕柔陰影 */
        margin-bottom: 20px;
    }
    [data-theme="light"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"]:hover {
         box-shadow: 0 8px 25px rgba(157, 78, 221, 0.15); /* hover 時增加一點紫色氛圍 */
    }

    /* 淺色模式按鈕 */
    [data-theme="light"] .stButton>button {
        background: linear-gradient(135deg, #6a3093, #8e44ad); /* 紫色漸層 */
        color: #ffffff !important; /* 白字 */
        box-shadow: 0 4px 10px rgba(106, 48, 147, 0.3);
    }
    [data-theme="light"] .stButton>button:hover {
        box-shadow: 0 6px 15px rgba(106, 48, 147, 0.5);
    }
    /* 淺色模式次要按鈕 */
    [data-theme="light"] button[kind="secondary"] {
        background: transparent !important;
        border: 2px solid #6a3093 !important;
        color: #6a3093 !important;
    }

    /* 淺色模式輸入框 */
    [data-theme="light"] .stTextInput input, [data-theme="light"] .stChatInput textarea, [data-theme="light"] .stFileUploader {
        background-color: #ffffff !important;
        border: 1px solid #ced4da !important;
        color: #495057 !important;
    }
    [data-theme="light"] .stTextInput input:focus, [data-theme="light"] .stChatInput textarea:focus {
        border-color: #9D4EDD !important;
        box-shadow: 0 0 0 3px rgba(157, 78, 221, 0.25) !important;
    }

    /* 淺色模式對話氣泡 */
    [data-theme="light"] .stChatMessage[data-testid="stChatMessageUser"] {
        background: #6a3093; color: white; /* 紫底白字 */
    }
    [data-theme="light"] .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: #f1f3f5; color: #333; border: 1px solid #dcdcdc; /* 灰底黑字 */
    }
    
    /* 淺色模式分隔線與浮水印 */
    [data-theme="light"] .royal-divider { color: #6a3093; }
    [data-theme="light"] .royal-divider::before, [data-theme="light"] .royal-divider::after {
        background: linear-gradient(to right, transparent, #6a3093, transparent);
    }
    [data-theme="light"] .fixed-watermark {
        background: linear-gradient(to right, #6a3093, #b8860b);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }


    /* ==========================================================================
       【深色模式】專用樣式 (針對[data-theme="dark"]) - 延續 V6.3 的華麗，但稍微收斂
       ========================================================================== */
    [data-theme="dark"] .stApp {
        background-color: #0a0510; /* 更深沉的黑 */
        /* 降低紋理對比度，減少雜訊感 */
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(123, 44, 191, 0.1) 0%, transparent 40%),
            radial-gradient(circle at 80% 70%, rgba(255, 215, 0, 0.08) 0%, transparent 40%);
        color: #e0e0e0;
    }
    /* 深色模式標題：亮金亮紫，帶發光 */
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3, [data-theme="dark"] .big-title {
        background-image: linear-gradient(to right, #FFD700, #D4AF37, #9D4EDD);
        text-shadow: 0 2px 15px rgba(157, 78, 221, 0.5); /* 強烈發光 */
    }

    /* 深色模式卡片：毛玻璃 + 強烈光暈 (V6.3 風格) */
    [data-theme="dark"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: rgba(40, 20, 60, 0.5);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 30px;
        border: 1px solid rgba(255, 215, 0, 0.3); 
        /* 調整光暈強度，減少刺眼感 */
        box-shadow: 
            0 0 0 1px rgba(157, 78, 221, 0.2) inset,
            0 15px 30px rgba(0, 0, 0, 0.5),
            0 0 30px rgba(123, 44, 191, 0.2); 
        margin-bottom: 25px;
    }
    [data-theme="dark"] div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"]:hover {
         border-color: #FFD700;
         box-shadow: 0 0 50px rgba(157, 78, 221, 0.4), 0 0 15px rgba(255, 215, 0, 0.3);
    }

    /* 深色模式按鈕 */
    [data-theme="dark"] .stButton>button {
        background: linear-gradient(135deg, #4a1a88 0%, #7B2CBF 100%);
        color: #FFD700 !important;
        box-shadow: 0 5px 15px rgba(123, 44, 191, 0.5);
    }
    [data-theme="dark"] .stButton>button:hover {
        box-shadow: 0 8px 25px rgba(255, 215, 0, 0.7);
        color: white !important;
    }

    /* 深色模式輸入框 */
    [data-theme="dark"] .stTextInput input, [data-theme="dark"] .stChatInput textarea, [data-theme="dark"] .stFileUploader {
        background-color: rgba(20, 10, 30, 0.7) !important;
        border: 2px solid #9D4EDD !important;
        color: #FFD700 !important;
    }
    [data-theme="dark"] .stTextInput input:focus {
        border-color: #FFD700 !important;
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.5) !important;
    }

    /* 深色模式對話氣泡 */
    [data-theme="dark"] .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #7B2CBF, #9D4EDD); border: 1px solid #FFD700;
    }
    [data-theme="dark"] .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: rgba(40, 40, 45, 0.95); border: 1px solid #D4AF37; color: #f0f0f0;
    }

    /* 深色模式分隔線與浮水印 */
    [data-theme="dark"] .royal-divider { color: #D4AF37; }
    [data-theme="dark"] .royal-divider::before, [data-theme="dark"] .royal-divider::after {
        background: linear-gradient(to right, transparent, #9D4EDD, #FFD700, transparent);
    }
    [data-theme="dark"] .fixed-watermark {
        background: linear-gradient(to right, #FFD700, #FFF, #9D4EDD);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 3px rgba(255,215,0,0.5));
    }

    /* Tab 樣式 (適應兩者) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent; padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        border: none; color: inherit; opacity: 0.7; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        opacity: 1;
        border-bottom: 3px solid #9D4EDD !important;
        color: #9D4EDD !important;
    }
    [data-theme="dark"] .stTabs [aria-selected="true"] {
        border-bottom-color: #FFD700 !important;
        color: #FFD700 !important;
    }

</style>
<div class="fixed-watermark">K.R. FIN-AI</div>
""", unsafe_allow_html=True)

# 輔助函數：產生裝飾分隔線 (圖標改為專業風格)
def royal_divider(icon="◆"):
    st.markdown(f"""
    <div class="royal-divider">
        <span class="royal-divider-icon">{icon}</span>
    </div>
    """, unsafe_allow_html=True)

keep_alive = """<script>setInterval(() => { fetch(window.location.href, {mode: 'no-cors'}); }, 300000);</script>"""
st.markdown(keep_alive, unsafe_allow_html=True)


# =============================================================================
# 2. 核心提示詞 (保持完整)
# =============================================================================
# (為節省篇幅，此處省略提示詞內容，實際程式碼請務必保留完整的 PROMPT 定義)
# 步驟 1：抓取公司名稱
PROMPT_COMPANY_NAME = textwrap.dedent("""請從這份 PDF 財務報告的第一頁或封面頁中，提取出完整的、官方的公司法定全名 (例如 "台灣積體電路製造股份有限公司")。限制：1. 僅輸出公司名稱的純文字字串。2. 禁止包含任何 Markdown、引號、標籤或任何 "公司名稱：" 之類的前綴。3. 禁止包含任何其他文字或問候語。""")
# 步驟 2：標準化提取 (完整版)
PROMPT_BIAO_ZHUN_HUA_CONTENT = textwrap.dedent("""**請以以下標準來對財報四大表後有項目標號的數十項內容提取資料，並將以下 37 個大項各自生成獨立的 Markdown 表格** (溫度為0)**限制0：禁止包含任何前言、開場白、問候語或免責聲明 (例如 "好的，這..."). 您的回答必須直接開始於所要求的第一個 Markdown 表格 (例如 '## 公司沿革')。**限制1：如果標準化之規則財報中無該分類，跳過該分類**限制2：輸出時嚴禁包含編號 (例如 '一、' 或 '1.')。請直接以 Markdown 標題 (例如 '## 公司沿革') 開始，絕對不要輸出 37 項規則的編號。**限制3：與變動金額有關的內容，橫軸為時間線與變動比率，縱軸為項目，如果橫軸限制4：只能使用我們提供的檔案，不能使用外部資訊限制5：計算時在內部進行雙重核對，確保兩組計算，只使用提供資料且結果完全一致後，才可以輸出內容限制6：如果有資料缺漏導致無法計算，缺漏的部分不做計算**限制7.：每一個大項 (例如 '公司沿革', '現金及約當現金') 都必須是一個獨立的 Markdown 表格。如果一個大項下有多個要求事項 (例如 '應收票據及帳款淨額' 下有 '應收帳款淨額三期變動' 和 '帳齡分析表三期變動')，請在同一個表格中用多行來呈現，或生成多個表格。**限制8：禁止提供任何外部資訊一、公司沿革,公司名稱,成立日期[yyy/mm/dd],從事業務二、通過財務報告之日期及程序,核准日期[yyy/mm/dd]三、新發布及修訂準則及解釋之適用,新發布及修訂準則及解釋之適用對本公司之影響四、重大會計政策之彙總說明,會計政策對公司之影響五、重大會計判斷、估計及假設不確定性之主要來源,重大會計判斷、估計及假設不確定性之主要來源之變動六、現金及約當現金,現金及約當現金合計之變動七、透過損益按公允價值衡量之金融資產及金融負債,金融資產與金融負債之三期變動八、透過其他綜合損益按公允價值衡量之金融資產,透過其他綜合損益按公允價值衡量之金融資產之三期變動九、按攤銷後成本衡量之金融資產,金融資產合計之三期變動十、避險之金融工具,公允價值避險之方式及當期影響,現金流量避險之方式及當期影響,國外營運機構淨投資避險十一、應收票據及帳款淨額,應收帳款淨額三期變動,帳齡分析表三期變動,十二、存貨,製成品之三期變動金額,在製品之三期變動金額,原料之兩期變動金額,如有其餘獨立項目歸類進前三大項,十三、採用權益法之投資,子公司與關聯企業之名單及其控股百分比三期變動十四、不動產、廠房及設備,拆分自用與營業租賃後進行三期比較十五、租賃協議,三期變動十六、無形資產,三期變動十七、應付公司債,公司債項目性質,本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),十八、長期銀行借款,長期銀行借款,本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),十九、權益,已發行股本本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),本期日期(YYY/MM/DD),股本變動,盈餘分配,二十、營業收入,客戶合約之收入(應用領域別之兩期變動，如無應用領域別則讀取營業收入總額),合約負債三期變動,暫收款三期變動二一、利息收入,利息收入總額之兩期變動二二、財務成本,利息費用總額兩期變動二三、其他利益及損失淨額,其他利益及損失淨額兩期比較二四、所得稅,認列於損益之所得稅費用兩期變動二五、每股盈餘,基本每股盈餘兩期變動,稀釋每股盈餘兩期變動,二六、股份基礎給付協議,股份基礎給付計畫金額二七、費用性質之額外資訊,兩期比較二八、政府補助,兩期比較二九、現金流量資訊,營業活動之淨現金流入之兩期變動,投資活動之淨現金流出之兩期變動,本期現金及約當現金淨增加數之兩期變動三十、金融工具,金融資產三期變動,金融負債三期變動,非衍生金融負債三期變動,非衍生金融資產三期變動,衍生金融工具之三期變動,租賃負債之三期變動,透過損益按公允價值衡量之金融資產之三期變動,透過其他綜合損益按公允價值衡量之金融資產之三期變動,避險之金融資產之三期變動,文字部分之總結,三一、關係人交易,營業收入兩期變動,進貨三期變動,應收關係人款項三期變動,應付關係人款項三期變動,應付費用及其他流動負債三期變動,其他關係人交易三期變動,三二、質押之資產,質押之資產金額三期變動三三、重大或有負債及未認列之合約承諾,背書保證金額,或有負債總結,三四、重大之災害損失,發生原因,日期[yyy/mm],金額[仟元]三五、外幣金融資產及負債之匯率資訊,金融資產三期變動,金融負債三期變動,三六、附註揭露事項,請對我提供給你的資料中的附註揭露事項及其提及的附表進行分析三七、營運部門資訊,擁有哪些營運部門""")
# 步驟 3：比率計算 (完整版 P/E 修正)
PROMPT_RATIO_CONTENT = textwrap.dedent("""請根據以下計算公式及限制，計算股東權益報酬率 (ROE)、本益比 (P/E Ratio)、淨利率 (Net Profit Margin)、毛利率 (Gross Profit Margin)、負債比率 (Debt Ratio)、流動比率 (Current Ratio)、速動比率 (Quick Ratio) 之兩期數據。**注意：您必須輸出七個獨立的 Markdown 表格。****除了本益比以外每個表格必須遵循以下嚴格的 3x2 格式要求 (3 欄 x 2 行)，本益比則只需 2x2 格式要求 (2 欄 x 2 行，無須比較期日期或期間的欄位第二欄名稱為本年度)：**| 財務比率名稱 (例如: 股東權益報酬率(ROE)) | [最近一期日期或期間] | [比較期日期或期間] || :--- | :--- | :--- || 比率 | [計算結果及單位，例如: 15.25%] | [計算結果及單位，例如: 12.80%] |**請嚴格遵守：**1. 輸出結果**必須是 7 個獨立的 Markdown 表格**，且只包含您計算出的數據和單位。2. 表格內容**只能是數字和單位** (例如 %、倍、次)。3. 表格的第一格**必須是比率名稱**，第二行第一格**必須是「比率」**這兩個字。**4. 禁止包含任何前言、開場白或問候語。您的回答必須直接從第一個 Markdown 表格 (股東權益報酬率) 開始。**計算公式：財務比率 (Financial Ratio),計算公式 (Formula),備註 (Notes)1. 股東權益報酬率 (ROE),(歸屬於母公司業主之本期淨利) / (歸屬於母公司業主之平均權益),當期（例如半年）數據計算。,其中，平均權益 = (期初歸屬於母公司業主之權益 + 期末歸屬於母公司業主之權益) / 2,2. 本益比 (P/E Ratio) (以當日收盤價格為基準), **(收盤價) / (年化每股盈餘)**。   **年化每股盈餘 (Annualized EPS) 計算規則 (必須嚴格遵守)：** - 步驟 A: 判斷財報期間。   - 步驟 B: 根據期間調整 EPS：     - 若為第一季 (Q1, 1-3月): 年化 EPS = 本期 EPS x 4     - 若為上半年 (H1, 1-6月): 年化 EPS = 本期累計 EPS x 2     - 若為前三季 (Q3, 1-9月): 年化 EPS = (本期累計 EPS / 3) x 4     - 若為全年度 (Annual, 1-12月): 年化 EPS = 本期累計 EPS x 1   - 步驟 C: 使用指定的收盤價除以算出的年化 EPS。   *注意：使用基本每股盈餘。指定收盤價請使用 Google Search 搜尋該財報截止日或次日的收盤價格。*3. 淨利率 (Net Profit Margin),(本期淨利) / (營業收入),單季數據計算。4. 毛利率 (Gross Profit Margin),(營業毛利) / (營業收入),單季數據計算。5. 負債比率 (Debt Ratio),(負債總計) / (資產總計),期末時點數據計算。6. 流動比率 (Current Ratio),(流動資產合計) / (流動負債合計),期末時點數據計算。7. 速動比率 (Quick Ratio),(流動資產合計 - 存貨 - 預付款項) / (流動負債合計),期末時點數據計算，採保守定義。限制：唯一數據來源：除了公司的收盤價外所有的計算僅能使用您所提供的PDF財務報告檔案，除收盤價需上網絡查詢外，不得引用任何外部資訊。計算時間基準：毛利率、淨利率、本益比皆以「單季」數據進行計算；需要平均餘額的比率（ROE）以「當期」期間為基礎。平均餘額計算：分母的平均餘額必須採用該「當期」期間的期初餘額與期末餘額之平均。數據替換原則：若缺乏當期「期初」數據，則採用可取得的最近一期餘額來替代期初數據，並在報告中明確註明此近似處理。不進行年化處理：所有的比率計算結果直接呈現該期間的數據，不轉換為年化率，除非計算式有特別要求進行年化 (如 P/E)。內部驗證機制：在生成最終報告前，會進行內部雙重計算與核對。處理資料缺漏：若因缺乏必要的數據而無法計算，將明確標示為**「無法計算」**並註明原因。""")
# 步驟 4：總結 (完整版)
PROMPT_ZONG_JIE_CONTENT = textwrap.dedent("""核心規則與限制限制部分：**格式限制：禁止包含任何前言、開場白、問候語或免責聲明 (例如 "好的，這是一份..."）。您的回答必須直接開始於總結的第一句話。**資料來源限制：僅能使用標準化後的內容表格及財報附註中已提取的文字資訊進行分析,排除對合併資產負債表、合併綜合損益表、合併權益變動表及合併現金流量表四大表本身數據的直接讀取與分析。數據提取限制：所有分析所需的原始數據與金額，必須從標準化表格中已計算或已提取的結果取得,確保分析的立論點是基於前一步驟的數據整理成果。分析深度限制：分析內容僅限於揭露與觀察事實與數據變動，禁止提供任何形式的投資或經營建議或評價,恪守中立客觀的立場，僅對資訊進行解讀與歸納。**內部驗證限制：在輸出總結前，必須進行內部雙重核對，確保所有分析論點均來自標準化表格或附註原文，且完全遵守所有分析規則與限制。**分析規則部分：會計基礎分析：關注「公司沿革」、「會計政策」及「重大會計判斷」等項目,用於建立對公司營運範圍、會計處理連續性及潛在風險（如暫定公允價值）的初步認識。經營細項分析：側重「營業收入結構細分」、「費用性質」、「營業外損益細項」的兩期變動,深入了解營收暴增的驅動力（例如新業務：佣金、廣告）與成本費用的結構性變化（例如折舊、攤銷的增加）。財務結構細項分析：關注「金融工具」、「質押之資產」、「租賃負債」等項目的三期變動,衡量公司在風險暴露（匯率、利率）、資產擔保情況以及長期承諾（租賃、未計價合約）的變化趨勢。關係人交易分析：著重於「營業收入」、「應收帳款」、「資金貸與」及「承包工程合約」等項目的類型與金額集中度,識別關係人交易在公司營運中的比重和性質，特別是資金流向與合約承諾。流動性與承諾分析：關注「流動性風險到期日」分析和「重大或有負債/合約承諾」的總額與結構,判斷公司短期現金壓力、合同義務以及潛在的表外風險。期後事項分析：僅羅列已發生的重大期後交易。,作為公司未來發展方向和策略變動的客觀資訊補充。計算規則部分變動數據呈現：對於金額變動，必須呈現變動金額及變動比率,突顯數據的相對變化幅度，作為分析論點的支撐。比率計算依據,變動比率計算方式為：,(本期金額−比較期金額)/比較期金額,統一所有分析中的比率計算方法。N/A 處理：若比較期金額為零，則變動比率標示為 N/A 或以文字描述為「無法計算」。,避免除以零的錯誤，並準確描述從無到有的巨大變化。幣別一致性：所有金額單位必須保持一致（新台幣千元），並在分析開始前註明。,確保數據的可讀性與準準確性。""")
# 步驟 5：講解 (完整版)
PROMPT_JIAN_JIE_CONTENT = textwrap.dedent("""**格式限制：禁止包含任何前言、開場白、問候語或免責聲明。您的回答必須直接開始於講解的第一句話。**一、 核心目標與受眾設定 (Analysis Goal and Audience)目標: 對單一公司已標準化的財務數據（四大表附註）進行深度分析。受眾: 專為「非專業人士」設計，假設讀者可能不具備基礎會計知識，無法理解融資、邊際貢獻等概念。易讀性（Readability）優先，確保報告內容可以轉化為白話文進行溝通。風格: 採用「翻譯」和「白話解釋」的語氣，將專業名詞逐一轉化為生活化語言。二、 數據來源與引用限制 (Data Integrity and Citation)數據來源: 嚴格依賴已提供的標準化後數據和原始財務報告內容。禁止使用或臆測外部資訊（例如產業新聞、股價、未來預測等）。資料時間軸: 核心數據對比必須聚焦於「114 年 1-6 月 (本期)」與「113 年 1-6 月 (去年同期)」的兩期比較，以呈現經營成果的變化。資產負債表項目則需呈現三期數據（114/06/30, 113/12/31, 113/06/30）。單位統一: 所有金額必須統一標註為新台幣仟元，除非原始數據或特殊情況另有說明。限制輸出: 分析結果中禁止包含任何主觀建議、投資判斷或價值評估，僅陳述數據事實、計算出的比率及趨勢。**內部驗證要求：在輸出講解前，必須進行內部雙重核對，確保所有「白話轉譯」均準確對應「名詞解釋標準 (Glossary)」，且所有引用的數據事實均與標準化表格一致。**三、 報告結構與內容要求 (Structure and Content Mandates)分析報告必須涵蓋以下五個主要區塊，並針對每個數據點提供詳細的解釋：1. 公司基礎資訊 (Basic Information)分析點：公司沿革、財務報告核准日、會計準則適用、重大會計估計穩定性。要求：需將會計政策的穩定性（如 IFRS 適用）解讀為「記帳規則穩定」或「報表可靠」。2. 資產負債表項目分析 (Statement of Financial Position)分析點：現金、存貨、PPE、應付公司債、負債總額等。要求：必須解釋 PPE 的增長趨G勢為「資本支出（CapEx）」，並將其轉譯為「砸錢買新設備和蓋廠」。要求：必須將存貨中的「在製品」解讀為「產線忙碌」。3. 綜合損益表項目分析 (Statement of Comprehensive Income)分析點：營業收入、毛利、淨利、每股盈餘（EPS）、所得稅費用。要求：強調「營業淨利」的增長率是否高於「營業收入」的增長率，並解釋這代表公司「管錢效率提高」。要求：需將 EPS 解釋為「平均每一股賺了多少錢」。4. 現金流量表項目分析 (Statement of Cash Flows)分析點：營業活動現金流 (CFO)、投資活動現金流 (CFI)、籌資活動現金流 (CFF)。要求：CFO 必須被稱為「賣晶片收到的現金總額」，並強調其為「核心業務收錢能力」。要求：必須對比 CFO 和 CFI 的大小關係，並解釋若 CFO > CFI，則公司能「靠自己賺來的錢來支付所有蓋廠和投資的費用」。5. 特別關注項目 (Special Focus Items)分析點：政府補助、應收帳款淨額、外幣資產、重大災害損失等。要求：將政府補助解釋為「海外子公司獲得的當地政府獎勵或補貼」。要求：將應收帳款的未逾期比例解讀為客戶的「信用質量」。四、 名詞解釋標準 (Glossary Simplification Standard)報告中使用的所有專業術術語必須在第一次出現時或在專門的註釋區塊中，按照以下「淺顯易懂」的標準進行轉譯：專業術語 (Jargon) / 轉譯標準 (Simplified Translation)資本支出 (CapEx) / 砸錢買新設備和蓋廠、買長期家當流動性 (Liquidity) / 救命錢或隨時能動用的錢在製品 (Work in Process) / 正在生產中的晶片、產線非常忙碌籌資活動 / 向股東或銀行「付錢」的活動淨利 / 獲利能力 / 最終賺到的利潤、賺錢能力應付公司債 / 長期大筆借款營業淨利 / 扣掉所有費用後，純粹靠本業賺到的錢EPS / 平均每一股股票賺了多少錢CFO / 公司靠「賣晶片」和「日常營運」收到的現金總額""")

# API Key & Session Init
try:
    API_KEY = os.getenv('GEMINI_API_KEY')
    if not API_KEY:
        API_KEY = st.secrets.get("GEMINI_API_KEY") 
except Exception:
    API_KEY = None

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'
if 'analysis_results' not in st.session_state:
    st.session_state['analysis_results'] = None
if 'current_pdf_bytes' not in st.session_state:
    st.session_state['current_pdf_bytes'] = None 
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =============================================================================
# 3. 核心 API 呼叫 (功能不變)
# =============================================================================

@st.cache_resource
def get_gemini_client(api_key):
    if not api_key: return None
    try: return genai.Client(api_key=api_key)
    except: return None

CLIENT = get_gemini_client(API_KEY)
GLOBAL_CONFIG_ERROR = None
if CLIENT is None:
    GLOBAL_CONFIG_ERROR = "❌ 錯誤：GEMINI_API_KEY 無效或未設定。"

def call_multimodal_api(file_content_bytes, prompt, use_search=False):
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}
    try:
        pdf_part = types.Part.from_bytes(data=file_content_bytes, mime_type='application/pdf')
    except Exception as e: return {"error": f"PDF 處理失敗: {e}"} 
    contents = [pdf_part, prompt] 
    tools_config = [{"google_search": {}}] if use_search else None
    config = types.GenerateContentConfig(temperature=0.0, tools=tools_config)
    for attempt in range(4): 
        try:
            response = CLIENT.models.generate_content(model=MODEL_NAME, contents=contents, config=config)
            return {"status": "success", "content": response.text}
        except Exception as e:
            if attempt == 3: return {"error": str(e)}
            time.sleep(2)

def call_text_api(input_text, prompt):
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}
    contents = [input_text, prompt] 
    config = types.GenerateContentConfig(temperature=0.0, tools=None)
    for attempt in range(4):
        try:
            response = CLIENT.models.generate_content(model=MODEL_NAME, contents=contents, config=config)
            return {"status": "success", "content": response.text}
        except Exception as e:
            if attempt == 3: return {"error": str(e)}
            time.sleep(2)

def call_chat_api(contents):
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}
    config = types.GenerateContentConfig(temperature=1.2, tools=[{"google_search": {}}])
    try:
        response = CLIENT.models.generate_content(model=MODEL_NAME, contents=contents, config=config)
        return {"status": "success", "content": response.text}
    except Exception as e:
        return {"error": str(e)}

def run_analysis_flow(file_content_to_send, status_container):
    """執行分析流程 (V6.4: 文字回歸專業用語)"""
    st.session_state['current_pdf_bytes'] = file_content_to_send
    
    try:
        # 使用 container 包裹狀態列，應用卡片樣式
        with st.container():
            with status_container.status("⏳ 正在執行 AI 分析...", expanded=True) as status:
                st.write("📜 步驟 1/5: 正在識別公司名稱...")
                name_resp = call_multimodal_api(file_content_to_send, PROMPT_COMPANY_NAME, False)
                if name_resp.get("error"): raise Exception(name_resp['error'])
                company_name = name_resp["content"].strip()
                
                st.write("🔍 步驟 2/5: 正在提取與標準化財報數據...")
                std_resp = call_multimodal_api(file_content_to_send, PROMPT_BIAO_ZHUN_HUA_CONTENT, False)
                if std_resp.get("error"): raise Exception(std_resp['error'])
                
                st.write("🧮 步驟 3/5: 正在計算關鍵財務比率...")
                ratio_resp = call_multimodal_api(file_content_to_send, PROMPT_RATIO_CONTENT, True)
                if ratio_resp.get("error"): raise Exception(ratio_resp['error'])
                
                st.write("⚖️ 步驟 4/5: 正在生成專業審計總結...")
                sum_resp = call_text_api(std_resp["content"], PROMPT_ZONG_JIE_CONTENT)
                if sum_resp.get("error"): raise Exception(sum_resp['error'])
                
                st.write("🗣️ 步驟 5/5: 正在生成白話文數據講解...")
                exp_resp = call_text_api(std_resp["content"], PROMPT_JIAN_JIE_CONTENT)
                if exp_resp.get("error"): raise Exception(exp_resp['error'])
                
                status.update(label="✅ 分析完成！準備生成報告...", state="complete", expanded=False)

        st.session_state['analysis_results'] = {
            "company_name": company_name,
            "ratio": ratio_resp["content"],
            "summary": sum_resp["content"],
            "explanation": exp_resp["content"],
            "standardization": std_resp["content"]
        }
        time.sleep(0.5)
        st.session_state['current_page'] = 'Report' # 導航到報告頁
        st.rerun()

    except Exception as e:
        st.error(f"❌ 分析流程中斷：\n{e}")

# =============================================================================
# 4. 頁面邏輯 (V6.4: 專業用語 + 卡片式結構)
# =============================================================================

def home_page():
    with st.container():
        st.markdown("<h1 style='text-align: center;'>🏛️ AI 智能財報分析系統</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.1rem; opacity: 0.8;'>融合頂尖多模態 AI 技術，提供深度數據提取、專業比率計算，以及審計級與白話文雙視角報告。</p>", unsafe_allow_html=True)

    royal_divider("💎")

    if GLOBAL_CONFIG_ERROR:
        st.error(GLOBAL_CONFIG_ERROR)
        return

    # 快速通道區塊
    with st.container():
        st.markdown("### ⚡ 快速分析 (範例企業)")
        c1, c2, c3, c4 = st.columns(4)
        target_file = None
        status_cont = st.empty()
        
        with c1: 
            if st.button("📊 2330 (台積電)", use_container_width=True): target_file = "2330.pdf"
        with c2: 
            if st.button("📈 2382 (廣達)", use_container_width=True): target_file = "2382.pdf"
        with c3: 
            if st.button("📉 2308 (台達電)", use_container_width=True): target_file = "2308.pdf"
        with c4: 
            if st.button("💻 2454 (聯發科)", use_container_width=True): target_file = "2454.pdf"

    royal_divider("📂")

    # 上傳區塊
    with st.container():
         st.markdown("### 📜 上傳財務報告")
         uploaded = st.file_uploader("請選擇 PDF 格式的文件...", type=["pdf"], key="uploader")
    
    royal_divider("🚀")

    # 啟動按鈕區塊
    with st.container():
        if target_file and os.path.exists(target_file):
            with open(target_file, "rb") as f: run_analysis_flow(f.read(), status_cont)
        elif target_file:
            st.error(f"❌ 找不到範例檔案: {target_file}")
        elif uploaded:
            col_start, col_rest = st.columns([1, 2])
            with col_start:
                 if st.button("✨ 開始執行分析", type="primary", use_container_width=True):
                    run_analysis_flow(uploaded.read(), status_cont)
        else:
            st.info("請先上傳文件或選擇範例以開始。")

def report_page():
    res = st.session_state.get('analysis_results')
    if not res:
        st.info("請先進行分析。")
        if st.button("⬅️ 回首頁"): 
            st.session_state['current_page'] = 'Home'
            st.rerun()
        return
    
    # 標題卡片
    with st.container():
        st.markdown(f"<h1 style='text-align: center;'>📜 **{res['company_name']}** 財報分析報告</h1>", unsafe_allow_html=True)
    
    royal_divider("💎")

    # 1. 財務比率卡片
    with st.container():
        st.subheader("💎 關鍵財務比率")
        ratio_txt = res['ratio']
        tables = [t.strip() for t in ratio_txt.split('\n\n') if t.strip().startswith('|') and '---' in t]
        key_map = {'ROE': '股東權益報酬率', 'Net Profit': '淨利率', 'Gross Profit': '毛利率','P/E': '本益比', 'Current Ratio': '流動比率', 'Debt Ratio': '負債比率', 'Quick Ratio': '速動比率'}
        
        cols = st.columns(3) + st.columns(4)
        shown_count = 0
        for t in tables:
            for k, v in key_map.items():
                if k in t or v in t:
                    if shown_count < 7:
                        with cols[shown_count]: st.markdown(t, unsafe_allow_html=True)
                        shown_count += 1
                    break
        if shown_count == 0: st.markdown(ratio_txt)

    royal_divider("🤖")
    
    # 2. AI 對話室引導卡片
    with st.container():
        st.markdown("### 🤖 AI 首席顧問")
        st.info("💡 如果您對報告中的數據有任何疑問，請前往戰情室，AI 顧問將為您詳細解答。")
        if st.button("💬 前往 AI 戰情室 (自由對話模式)", type="primary", use_container_width=True):
            st.session_state['current_page'] = 'Chat'
            st.rerun()

    royal_divider("📄")

    # 3. 三大分頁卡片
    with st.container():
        t1, t2, t3 = st.tabs(["📄 專業審計總結", "🗣️ 白話文數據講解", "📊 標準化資訊提取"])
        with t1: st.markdown(res['summary'])
        with t2: st.markdown(res['explanation'])
        with t3: st.markdown(res['standardization'])
    
    royal_divider("⬅️")
    
    # 返回按鈕
    if st.button("⬅️ 結束閱覽，返回首頁", kind="secondary"):
        st.session_state['analysis_results'] = None
        st.session_state['current_pdf_bytes'] = None
        st.session_state['current_page'] = 'Home'
        st.rerun()

def chat_page():
    # 頂部導航卡片
    with st.container():
        c_back, c_title = st.columns([1, 6])
        with c_back:
            if st.button("⬅️ 返回報告"):
                st.session_state['current_page'] = 'Report'
                st.rerun()
        with c_title:
            st.markdown("<h2 style='margin-top: 0;'>💬 AI 財報戰情室</h2>", unsafe_allow_html=True)

    royal_divider("📜")

    # 聊天內容區
    with st.container():
        if not st.session_state.chat_history:
            st.caption("✨ 戰情室已開啟，請輸入您的問題...")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 圖片上傳區 (可收折)
        with st.expander("📎 上傳輔助圖片/截圖 (選用)"):
            chat_uploaded_img = st.file_uploader("選擇圖片文件...", type=["png", "jpg", "jpeg"], key="chat_img_up")

    # 輸入區
    if prompt := st.chat_input("請輸入您的問題，顧問將即刻分析..."):
        # 1. 顯示並紀錄 User 訊息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # 2. 準備 Context
        inputs = []
        # PDF
        if st.session_state.get('current_pdf_bytes'):
            try: inputs.append(types.Part.from_bytes(data=st.session_state['current_pdf_bytes'], mime_type='application/pdf'))
            except: pass
        # 新上傳圖片
        if chat_uploaded_img:
             try: inputs.append(types.Part.from_bytes(data=chat_uploaded_img.read(), mime_type=chat_uploaded_img.type))
             except: pass

        res = st.session_state.get('analysis_results', {})
        std_data = res.get('standardization', '')
        # V6.4: 提示詞回歸專業
        sys_prompt = f"你是一位專業、客觀且經驗豐富的財務顧問。已附上原始財報PDF與標準化數據摘要:\n{std_data[:3000]}...\n請回答使用者問題：{prompt}"
        inputs.append(sys_prompt)

        # 3. 呼叫 API
        with st.chat_message("assistant"):
            with st.spinner("🟣 顧問正在思考中..."):
                response = call_chat_api(inputs)
                reply = f"❌ 錯誤: {response['error']}" if response.get("error") else response["content"]
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

# =============================================================================
# 5. 主程式入口
# =============================================================================

if st.session_state['current_page'] == 'Home':
    home_page()
elif st.session_state['current_page'] == 'Report':
    report_page()
elif st.session_state['current_page'] == 'Chat':
    chat_page()