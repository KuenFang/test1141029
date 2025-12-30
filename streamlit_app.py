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
# 0. 全域設定與初始化
# =============================================================================

MODEL_NAME = "gemini-3-pro-preview"

# 初始化 Session State
if 'ui_theme' not in st.session_state:
    st.session_state['ui_theme'] = '跟隨系統'
if 'is_processing' not in st.session_state:
    st.session_state['is_processing'] = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =============================================================================
# 1. 頁面配置與 CSS (V7.6: Messenger 風格 + Typing 動畫)
# =============================================================================

st.set_page_config(
    page_title="AI財報分析系統 (K.R.)",
    page_icon="⚜️",
    layout="wide",
)

# 定義「輸入中...」的三個跳動圓點 HTML/CSS
TYPING_ANIMATION_CSS = """
<style>
    .typing-indicator {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        height: 24px;
    }
    .typing-dot {
        width: 8px;
        height: 8px;
        margin: 0 2px;
        background-color: #b0b0b0; /* 預設灰 */
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out both;
    }
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0); opacity: 0.5;}
        40% { transform: scale(1); opacity: 1;}
    }
    
    /* 根據主題調整圓點顏色 */
    [data-theme="dark"] .typing-dot { background-color: #ffd700; } /* 暗色模式金點 */
    [data-theme="light"] .typing-dot { background-color: #7b2cbf; } /* 亮色模式紫點 */
</style>
<div class="typing-indicator">
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
</div>
"""

# 注入主 CSS
CSS_BASE = """
    /* 隱藏預設元素 */
    header[data-testid="stHeader"] {display: none;}
    footer {display: none;}
    .stDeployButton {display: none;}
    hr { display: none !important; }
    
    /* 設定按鈕樣式 */
    .settings-btn {
        border: none; background: transparent; font-size: 1.5rem; cursor: pointer;
        transition: transform 0.3s ease;
    }
    .settings-btn:hover { transform: rotate(90deg); }

    /* 分析中狀態文字 (左上角) */
    .processing-indicator {
        color: #d4af37; font-weight: bold; font-family: monospace; animation: pulse 1.5s infinite;
        text-align: center; padding: 10px; border: 1px solid #d4af37; border-radius: 10px;
    }
    @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }

    /* 左下角浮水印 */
    .fixed-watermark {
        position: fixed; bottom: 20px; left: 25px; font-size: 20px;
        font-family: 'Times New Roman', serif; font-weight: 900; 
        z-index: 9999; pointer-events: none; letter-spacing: 2px;
    }

    /* 動畫 */
    @keyframes sheen { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }
"""

CSS_DARK = """
    /* 🌑 暗色模式 (V6.3 復刻) */
    .stApp {
        background-color: #05020a !important;
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(123, 44, 191, 0.2) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(255, 215, 0, 0.15) 0%, transparent 50%),
            linear-gradient(135deg, rgba(10, 5, 20, 0.95) 0%, rgba(25, 10, 40, 0.95) 100%) !important;
        background-attachment: fixed !important;
        color: #e0e0e0 !important;
    }
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.05'/%3E%3C/svg%3E");
        pointer-events: none; z-index: 0; mix-blend-mode: overlay;
    }
    h1, h2, h3, .big-title {
        background: linear-gradient(to right, #FFD700, #FFC300, #D4AF37, #9D4EDD, #7B2CBF) !important;
        background-size: 200% auto !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
        text-shadow: 0 2px 15px rgba(157, 78, 221, 0.6) !important; animation: sheen 3s linear infinite !important;
    }
    /* 卡片光暈 */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: rgba(40, 20, 60, 0.4) !important; backdrop-filter: blur(10px) !important;
        border: 2px solid rgba(255, 215, 0, 0.3) !important; border-radius: 20px !important; padding: 30px !important;
        box-shadow: 0 0 0 1px rgba(157, 78, 221, 0.3) inset, 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 40px rgba(123, 44, 191, 0.2) !important;
        margin-bottom: 25px !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #4a1a88 0%, #7B2CBF 100%) !important; color: #FFD700 !important; border: none !important;
        box-shadow: 0 5px 15px rgba(123, 44, 191, 0.5) !important;
    }
    .stTextInput input, .stChatInput textarea, .stFileUploader {
        background-color: rgba(20, 10, 30, 0.6) !important; border: 2px solid #9D4EDD !important; color: #FFD700 !important;
    }
    
    /* V7.6 對話氣泡 - Messenger Dark 風格 */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #7B2CBF, #9D4EDD) !important;
        border: none !important;
        border-radius: 18px 18px 4px 18px !important; /* 圓角調整 */
        margin-left: 20% !important; /* 靠右壓縮 */
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: rgba(60, 60, 60, 0.8) !important; 
        border: 1px solid #D4AF37 !important; color: #f0f0f0 !important;
        border-radius: 18px 18px 18px 4px !important; /* 圓角調整 */
        margin-right: 20% !important; /* 靠左壓縮 */
    }

    .fixed-watermark {
        background: linear-gradient(to right, #FFD700, #FFF, #9D4EDD) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
        filter: drop-shadow(0 0 5px rgba(255,215,0,0.5));
    }
    .royal-divider::before, .royal-divider::after { background: linear-gradient(to right, transparent, #FFD700, #9D4EDD, transparent) !important; }
    .royal-divider-icon { color: #FFD700; }
    .stTabs [aria-selected="true"] { color: #FFD700 !important; border-bottom: 3px solid #9D4EDD !important; }
"""

CSS_LIGHT = """
    /* ☀️ 亮色模式 (V6.9 珍珠白金) */
    .stApp {
        background-color: #fdfbf7 !important;
        background-image: 
            linear-gradient(120deg, #fdfbf7 0%, #f3e5f5 100%),
            radial-gradient(at 0% 0%, rgba(255, 215, 0, 0.15) 0px, transparent 50%), 
            radial-gradient(at 100% 100%, rgba(157, 78, 221, 0.15) 0px, transparent 50%) !important;
        background-attachment: fixed !important;
        color: #2e1065 !important;
    }
    h1, h2, h3, .big-title {
        background: linear-gradient(45deg, #4a1a88, #7b2cbf, #b8860b, #4a1a88) !important;
        background-size: 300% auto !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
        font-weight: 900 !important; padding-bottom: 10px !important; animation: sheen 8s ease infinite !important;
    }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: rgba(255, 255, 255, 0.75) !important; backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(157, 78, 221, 0.2) !important; border-radius: 20px !important; padding: 25px !important;
        box-shadow: 0 10px 30px rgba(100, 50, 150, 0.05), inset 0 0 20px rgba(255, 255, 255, 0.8) !important;
        margin-bottom: 20px !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #7b2cbf 0%, #9d4edd 100%) !important; color: #ffffff !important; border: none !important;
        border-radius: 12px !important; box-shadow: 0 5px 15px rgba(123, 44, 191, 0.3) !important;
    }
    button[kind="secondary"] {
        background: transparent !important; border: 2px solid #7b2cbf !important; color: #7b2cbf !important;
    }
    .stTextInput input, .stChatInput textarea, .stFileUploader {
        background-color: rgba(255,255,255,0.8) !important; border: 2px solid #dcdcdc !important; color: #4a1a88 !important; border-radius: 12px !important;
    }
    
    /* V7.6 對話氣泡 - Messenger Light 風格 */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #9d4edd, #c77dff) !important; 
        color: white !important;
        border-radius: 18px 18px 4px 18px !important;
        margin-left: 20% !important;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: #ffffff !important; 
        border: 1px solid #e0aa3e !important; color: #2e1065 !important;
        border-radius: 18px 18px 18px 4px !important;
        margin-right: 20% !important;
    }

    .royal-divider::before, .royal-divider::after { background: linear-gradient(to right, transparent, #b8860b, transparent) !important; }
    .royal-divider-icon { color: #b8860b; }
    .fixed-watermark {
        background: linear-gradient(to right, #4a1a88, #b8860b) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; opacity: 0.7 !important;
    }
    .stTabs [aria-selected="true"] { color: #7B1FA2 !important; border-bottom: 3px solid #7B1FA2 !important; }
"""

CSS_STRUCTURE = """
    .stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 15px !important; }
    .stTabs [data-baseweb="tab"] { border: none !important; font-weight: 800 !important; font-size: 1.1rem !important; }
    .royal-divider { display: flex; align-items: center; margin: 40px 0; justify-content: center; }
    .royal-divider::before, .royal-divider::after { content: ""; width: 40%; height: 2px; display: block; }
    .royal-divider-icon { padding: 0 15px; font-size: 1.5rem; }
    
    /* V7.5 優化：對話輸入框區域的垂直置中 */
    div[data-testid="column"] { display: flex; flex-direction: column; justify-content: center; }
"""

# 決定 CSS 注入邏輯
theme_selection = st.session_state.get('ui_theme', '跟隨系統')
final_css = CSS_BASE + CSS_STRUCTURE

if theme_selection == '極致黑金 (Dark)':
    final_css += CSS_DARK 
elif theme_selection == '皇家白金 (Light)':
    final_css += CSS_LIGHT
else: # 跟隨系統
    final_css += f"@media (prefers-color-scheme: dark) {{ {CSS_DARK} }} @media (prefers-color-scheme: light) {{ {CSS_LIGHT} }}"

st.markdown(f"<style>{final_css}</style>", unsafe_allow_html=True)
st.markdown('<div class="fixed-watermark">⚜️ (K.R.)</div>', unsafe_allow_html=True)

def royal_divider(icon="⚜️"):
    st.markdown(f"""<div class="royal-divider"><span class="royal-divider-icon">{icon}</span></div>""", unsafe_allow_html=True)

keep_alive = """<script>setInterval(() => { fetch(window.location.href, {mode: 'no-cors'}); }, 300000);</script>"""
st.markdown(keep_alive, unsafe_allow_html=True)


# =============================================================================
# 2. 核心提示詞 (完整還原版 V5.8)
# =============================================================================

PROMPT_COMPANY_NAME = textwrap.dedent("""
請從這份 PDF 財務報告的第一頁或封面頁中，提取出完整的、官方的公司法定全名 (例如 "台灣積體電路製造股份有限公司")。

限制：
1. 僅輸出公司名稱的純文字字串。
2. 禁止包含任何 Markdown、引號、標籤或任何 "公司名稱：" 之類的前綴。
3. 禁止包含任何其他文字或問候語。
""")

PROMPT_BIAO_ZHUN_HUA_CONTENT = textwrap.dedent("""
**請以以下標準來對財報四大表後有項目標號的數十項內容提取資料，並將以下 37 個大項各自生成獨立的 Markdown 表格** (溫度為0)
**限制0：禁止包含任何前言、開場白、問候語或免責聲明 (例如 "好的，這..."). 您的回答必須直接開始於所要求的第一個 Markdown 表格 (例如 '## 公司沿革')。**
限制1：如果標準化之規則財報中無該分類，跳過該分類
**限制2：輸出時嚴禁包含編號 (例如 '一、' 或 '1.')。請直接以 Markdown 標題 (例如 '## 公司沿革') 開始，絕對不要輸出 37 項規則的編號。**
限制3：與變動金額有關的內容，橫軸為時間線與變動比率，縱軸為項目，如果橫軸
限制4：只能使用我們提供的檔案，不能使用外部資訊
限制5：計算時在內部進行雙重核對，確保兩組計算，只使用提供資料且結果完全一致後，才可以輸出內容
限制6：如果有資料缺漏導致無法計算，缺漏的部分不做計算
**限制7.：每一個大項 (例如 '公司沿革', '現金及約當現金') 都必須是一個獨立的 Markdown 表格。如果一個大項下有多個要求事項 (例如 '應收票據及帳款淨額' 下有 '應收帳款淨額三期變動' 和 '帳齡分析表三期變動')，請在同一個表格中用多行來呈現，或生成多個表格。**
限制8：禁止提供任何外部資訊
一、公司沿革,公司名稱,成立日期[yyy/mm/dd],從事業務
二、通過財務報告之日期及程序,核准日期[yyy/mm/dd]
三、新發布及修訂準則及解釋之適用,新發布及修訂準則及解釋之適用對本公司之影響
四、重大會計政策之彙總說明,會計政策對公司之影響
五、重大會計判斷、估計及假設不確定性之主要來源,重大會計判斷、估計及假設不確定性之主要來源之變動
六、現金及約當現金,現金及約當現金合計之變動
七、透過損益按公允價值衡量之金融資產及金融負債,金融資產與金融負債之三期變動
八、透過其他綜合損益按公允價值衡量之金融資產,透過其他綜合損益按公允價值衡量之金融資產之三期變動
九、按攤銷後成本衡量之金融資產,金融資產合計之三期變動
十、避險之金融工具,公允價值避險之方式及當期影響,現金流量避險之方式及當期影響,國外營運機構淨投資避險
十一、應收票據及帳款淨額,應收帳款淨額三期變動,帳齡分析表三期變動,
十二、存貨,製成品之三期變動金額,在製品之三期變動金額,原料之兩期變動金額,如有其餘獨立項目歸類進前三大項,
十三、採用權益法之投資,子公司與關聯企業之名單及其控股百分比三期變動
十四、不動產、廠房及設備,拆分自用與營業租賃後進行三期比較
十五、租賃協議,三期變動
十六、無形資產,三期變動
十七、應付公司債,公司債項目性質,本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),
十八、長期銀行借款,長期銀行借款,本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),
十九、權益,已發行股本本期日期(YYY/MM/DD),上期日期(YYY/MM/DD),去年同期(YYY/MM/DD),本期日期(YYY/MM/DD),股本變動,盈餘分配,
二十、營業收入,客戶合約之收入(應用領域別之兩期變動，如無應用領域別則讀取營業收入總額),合約負債三期變動,暫收款三期變動
二一、利息收入,利息收入總額之兩期變動
二二、財務成本,利息費用總額兩期變動
二三、其他利益及損失淨額,其他利益及損失淨額兩期比較
二四、所得稅,認列於損益之所得稅費用兩期變動
二五、每股盈餘,基本每股盈餘兩期變動,稀釋每股盈餘兩期變動,
二六、股份基礎給付協議,股份基礎給付計畫金額
二七、費用性質之額外資訊,兩期比較
二八、政府補助,兩期比較
二九、現金流量資訊,營業活動之淨現金流入之兩期變動,投資活動之淨現金流出之兩期變動,本期現金及約當現金淨增加數之兩期變動
三十、金融工具,金融資產三期變動,金融負債三期變動,非衍生金融負債三期變動,非衍生金融資產三期變動,衍生金融工具之三期變動,租賃負債之三期變動,透過損益按公允價值衡量之金融資產之三期變動,透過其他綜合損益按公允價值衡量之金融資產之三期變動,避險之金融資產之三期變動,文字部分之總結,
三一、關係人交易,營業收入兩期變動,進貨三期變動,應收關係人款項三期變動,應付關係人款項三期變動,應付費用及其他流動負債三期變動,其他關係人交易三期變動,
三二、質押之資產,質押之資產金額三期變動
三三、重大或有負債及未認列之合約承諾,背書保證金額,或有負債總結,
三四、重大之災害損失,發生原因,日期[yyy/mm],金額[仟元]
三五、外幣金融資產及負債之匯率資訊,金融資產三期變動,金融負債三期變動,
三六、附註揭露事項,請對我提供給你的資料中的附註揭露事項及其提及的附表進行分析
三七、營運部門資訊,擁有哪些營運部門
""")

PROMPT_RATIO_CONTENT = textwrap.dedent("""
請根據以下計算公式及限制，計算股東權益報酬率 (ROE)、本益比 (P/E Ratio)、淨利率 (Net Profit Margin)、毛利率 (Gross Profit Margin)、負債比率 (Debt Ratio)、流動比率 (Current Ratio)、速動比率 (Quick Ratio) 之兩期數據。

**注意：您必須輸出七個獨立的 Markdown 表格。**

**除了本益比以外每個表格必須遵循以下嚴格的 3x2 格式要求 (3 欄 x 2 行)，本益比則只需 2x2 格式要求 (2 欄 x 2 行，無須比較期日期或期間的欄位第二欄名稱為本年度)：**

| 財務比率名稱 (例如: 股東權益報酬率(ROE)) | [最近一期日期或期間] | [比較期日期或期間] |
| :--- | :--- | :--- |
| 比率 | [計算結果及單位，例如: 15.25%] | [計算結果及單位，例如: 12.80%] |

**請嚴格遵守：**
1. 輸出結果**必須是 7 個獨立的 Markdown 表格**，且只包含您計算出的數據和單位。
2. 表格內容**只能是數字和單位** (例如 %、倍、次)。
3. 表格的第一格**必須是比率名稱**，第二行第一格**必須是「比率」**這兩個字。
**4. 禁止包含任何前言、開場白或問候語。您的回答必須直接從第一個 Markdown 表格 (股東權益報酬率) 開始。**

計算公式：
財務比率 (Financial Ratio),計算公式 (Formula),備註 (Notes)
1. 股東權益報酬率 (ROE),(歸屬於母公司業主之本期淨利) / (歸屬於母公司業主之平均權益),當期（例如半年）數據計算。,其中，平均權益 = (期初歸屬於母公司業主之權益 + 期末歸屬於母公司業主之權益) / 2,
2. 本益比 (P/E Ratio) (以當日收盤價格為基準), **(收盤價) / (年化每股盈餘)**。
   **年化每股盈餘 (Annualized EPS) 計算規則 (必須嚴格遵守)：**
   - 步驟 A: 判斷財報期間。
   - 步驟 B: 根據期間調整 EPS：
     - 若為第一季 (Q1, 1-3月): 年化 EPS = 本期 EPS x 4
     - 若為上半年 (H1, 1-6月): 年化 EPS = 本期累計 EPS x 2
     - 若為前三季 (Q3, 1-9月): 年化 EPS = (本期累計 EPS / 3) x 4
     - 若為全年度 (Annual, 1-12月): 年化 EPS = 本期累計 EPS x 1
   - 步驟 C: 使用指定的收盤價除以算出的年化 EPS。
   *注意：使用基本每股盈餘。指定收盤價請使用 Google Search 搜尋該財報截止日或次日的收盤價格。*
3. 淨利率 (Net Profit Margin),(本期淨利) / (營業收入),單季數據計算。
4. 毛利率 (Gross Profit Margin),(營業毛利) / (營業收入),單季數據計算。
5. 負債比率 (Debt Ratio),(負債總計) / (資產總計),期末時點數據計算。
6. 流動比率 (Current Ratio),(流動資產合計) / (流動負債合計),期末時點數據計算。
7. 速動比率 (Quick Ratio),(流動資產合計 - 存貨 - 預付款項) / (流動負債合計),期末時點數據計算，採保守定義。
限制：
唯一數據來源：除了公司的收盤價外所有的計算僅能使用您所提供的PDF財務報告檔案，除收盤價需上網絡查詢外，不得引用任何外部資訊。
計算時間基準：毛利率、淨利率、本益比皆以「單季」數據進行計算；需要平均餘額的比率（ROE）以「當期」期間為基礎。
平均餘額計算：分母的平均餘額必須採用該「當期」期間的期初餘額與期末餘額之平均。
數據替換原則：若缺乏當期「期初」數據，則採用可取得的最近一期餘額來替代期初數據，並在報告中明確註明此近似處理。
不進行年化處理：所有的比率計算結果直接呈現該期間的數據，不轉換為年化率，除非計算式有特別要求進行年化 (如 P/E)。
內部驗證機制：在生成最終報告前，會進行內部雙重計算與核對。
處理資料缺漏：若因缺乏必要的數據而無法計算，將明確標示為**「無法計算」**並註明原因。
""")

PROMPT_ZONG_JIE_CONTENT = textwrap.dedent("""
核心規則與限制
限制部分：
**格式限制：禁止包含任何前言、開場白、問候語或免責聲明 (例如 "好的，這是一份..."）。您的回答必須直接開始於總結的第一句話。**
資料來源限制：僅能使用標準化後的內容表格及財報附註中已提取的文字資訊進行分析,排除對合併資產負債表、合併綜合損益表、合併權益變動表及合併現金流量表四大表本身數據的直接讀取與分析。
數據提取限制：所有分析所需的原始數據與金額，必須從標準化表格中已計算或已提取的結果取得,確保分析的立論點是基於前一步驟的數據整理成果。
分析深度限制：分析內容僅限於揭露與觀察事實與數據變動，禁止提供任何形式的投資或經營建議或評價,恪守中立客觀的立場，僅對資訊進行解讀與歸納。
**內部驗證限制：在輸出總結前，必須進行內部雙重核對，確保所有分析論點均來自標準化表格或附註原文，且完全遵守所有分析規則與限制。**
分析規則部分：
會計基礎分析：關注「公司沿革」、「會計政策」及「重大會計判斷」等項目,用於建立對公司營運範圍、會計處理連續性及潛在風險（如暫定公允價值）的初步認識。
經營細項分析：側重「營業收入結構細分」、「費用性質」、「營業外損益細項」的兩期變動,深入了解營收暴增的驅動力（例如新業務：佣金、廣告）與成本費用的結構性變化（例如折舊、攤銷的增加）。
財務結構細項分析：關注「金融工具」、「質押之資產」、「租賃負債」等項目的三期變動,衡量公司在風險暴露（匯率、利率）、資產擔保情況以及長期承諾（租賃、未計價合約）的變化趨勢。
關係人交易分析：著重於「營業收入」、「應收帳款」、「資金貸與」及「承包工程合約」等項目的類型與金額集中度,識別關係人交易在公司營運中的比重和性質，特別是資金流向與合約承諾。
流動性與承諾分析：關注「流動性風險到期日」分析和「重大或有負債/合約承諾」的總額與結構,判斷公司短期現金壓力、合同義務以及潛在的表外風險。
期後事項分析：僅羅列已發生的重大期後交易。,作為公司未來發展方向和策略變動的客觀資訊補充。
計算規則部分
變動數據呈現：對於金額變動，必須呈現變動金額及變動比率,突顯數據的相對變化幅度，作為分析論點的支撐。
比率計算依據,變動比率計算方式為：,(本期金額−比較期金額)/比較期金額,統一所有分析中的比率計算方法。
N/A 處理：若比較期金額為零，則變動比率標示為 N/A 或以文字描述為「無法計算」。,避免除以零的錯誤，並準確描述從無到有的巨大變化。
幣別一致性：所有金額單位必須保持一致（新台幣千元），並在分析開始前註明。,確保數據的可讀性與準準確性。
""")

PROMPT_JIAN_JIE_CONTENT = textwrap.dedent("""
**格式限制：禁止包含任何前言、開場白、問候語或免責聲明。您的回答必須直接開始於講解的第一句話。**

一、 核心目標與受眾設定 (Analysis Goal and Audience)

目標: 對單一公司已標準化的財務數據（四大表附註）進行深度分析。
受眾: 專為「非專業人士」設計，假設讀者可能不具備基礎會計知識，無法理解融資、邊際貢獻等概念。易讀性（Readability）優先，確保報告內容可以轉化為白話文進行溝通。
風格: 採用「翻譯」和「白話解釋」的語氣，將專業名詞逐一轉化為生活化語言。

二、 數據來源與引用限制 (Data Integrity and Citation)

數據來源: 嚴格依賴已提供的標準化後數據和原始財務報告內容。禁止使用或臆測外部資訊（例如產業新聞、股價、未來預測等）。
資料時間軸: 核心數據對比必須聚焦於「114 年 1-6 月 (本期)」與「113 年 1-6 月 (去年同期)」的兩期比較，以呈現經營成果的變化。資產負債表項目則需呈現三期數據（114/06/30, 113/12/31, 113/06/30）。
單位統一: 所有金額必須統一標註為新台幣仟元，除非原始數據或特殊情況另有說明。
限制輸出: 分析結果中禁止包含任何主觀建議、投資判斷或價值評估，僅陳述數據事實、計算出的比率及趨勢。
**內部驗證要求：在輸出講解前，必須進行內部雙重核對，確保所有「白話轉譯」均準確對應「名詞解釋標準 (Glossary)」，且所有引用的數據事實均與標準化表格一致。**

三、 報告結構與內容要求 (Structure and Content Mandates)

分析報告必須涵蓋以下五個主要區塊，並針對每個數據點提供詳細的解釋：

1. 公司基礎資訊 (Basic Information)
分析點：公司沿革、財務報告核准日、會計準則適用、重大會計估計穩定性。
要求：需將會計政策的穩定性（如 IFRS 適用）解讀為「記帳規則穩定」或「報表可靠」。

2. 資產負債表項目分析 (Statement of Financial Position)
分析點：現金、存貨、PPE、應付公司債、負債總額等。
要求：必須解釋 PPE 的增長趨G勢為「資本支出（CapEx）」，並將其轉譯為「砸錢買新設備和蓋廠」。
要求：必須將存貨中的「在製品」解讀為「產線忙碌」。

3. 綜合損益表項目分析 (Statement of Comprehensive Income)
分析點：營業收入、毛利、淨利、每股盈餘（EPS）、所得稅費用。
要求：強調「營業淨利」的增長率是否高於「營業收入」的增長率，並解釋這代表公司「管錢效率提高」。
要求：需將 EPS 解釋為「平均每一股賺了多少錢」。

4. 現金流量表項目分析 (Statement of Cash Flows)
分析點：營業活動現金流 (CFO)、投資活動現金流 (CFI)、籌資活動現金流 (CFF)。
要求：CFO 必須被稱為「賣晶片收到的現金總額」，並強調其為「核心業務收錢能力」。
要求：必須對比 CFO 和 CFI 的大小關係，並解釋若 CFO > CFI，則公司能「靠自己賺來的錢來支付所有蓋廠和投資的費用」。

5. 特別關注項目 (Special Focus Items)
分析點：政府補助、應收帳款淨額、外幣資產、重大災害損失等。
要求：將政府補助解釋為「海外子公司獲得的當地政府獎勵或補貼」。
要求：將應收帳款的未逾期比例解讀為客戶的「信用質量」。

四、 名詞解釋標準 (Glossary Simplification Standard)

報告中使用的所有專業術術語必須在第一次出現時或在專門的註釋區塊中，按照以下「淺顯易懂」的標準進行轉譯：

專業術語 (Jargon) / 轉譯標準 (Simplified Translation)
資本支出 (CapEx) / 砸錢買新設備和蓋廠、買長期家當
流動性 (Liquidity) / 救命錢或隨時能動用的錢
在製品 (Work in Process) / 正在生產中的晶片、產線非常忙碌
籌資活動 / 向股東或銀行「付錢」的活動
淨利 / 獲利能力 / 最終賺到的利潤、賺錢能力
應付公司債 / 長期大筆借款
營業淨利 / 扣掉所有費用後，純粹靠本業賺到的錢
EPS / 平均每一股股票賺了多少錢
CFO / 公司靠「賣晶片」和「日常營運」收到的現金總額
""")


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
# 3. 核心 API 呼叫
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
    st.session_state['is_processing'] = True
    st.session_state['current_pdf_bytes'] = file_content_to_send
    
    try:
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
        st.session_state['current_page'] = 'Report' 
        
    except Exception as e:
        st.error(f"❌ 分析流程中斷：\n{e}")
    finally:
        st.session_state['is_processing'] = False 
        st.rerun()

# =============================================================================
# 4. 彈窗設定系統
# =============================================================================

@st.dialog("系統設定")
def open_settings_dialog():
    tab_gen, tab_data, tab_about = st.tabs(["⚙️ 一般設定", "🧹 資料管理", "ℹ️ 關於系統"])
    
    with tab_gen:
        # 主題切換
        current_theme_index = ["跟隨系統", "極致黑金 (Dark)", "皇家白金 (Light)"].index(st.session_state.get('ui_theme', '跟隨系統'))
        new_theme = st.radio(
            "🎨 介面主題", 
            ["跟隨系統", "極致黑金 (Dark)", "皇家白金 (Light)"],
            index=current_theme_index,
            horizontal=True
        )
        if new_theme != st.session_state['ui_theme']:
            st.session_state['ui_theme'] = new_theme
            st.rerun() 

        st.divider()
        st.checkbox("啟用進階推理模式 (Beta)", value=True, help="使用更強的模型進行分析")
        st.checkbox("分析完成後自動播放音效", value=False)
        
    with tab_data:
        st.warning("注意：清除資料將無法復原")
        if st.button("清除所有分析紀錄", type="primary"):
            st.session_state['analysis_results'] = None
            st.session_state['chat_history'] = []
            st.session_state['current_pdf_bytes'] = None
            st.session_state['is_processing'] = False
            st.success("已清除所有暫存資料！")
            time.sleep(1)
            st.rerun()
            
    with tab_about:
        st.markdown("### AI 財報分析系統 v7.6")
        st.write("由 K.R. Design 開發")
        st.write("本系統使用 Google Gemini Pro 模型進行財務報表之自動化分析與解讀。")
        st.caption("Copyright © 2025 K.R. All Rights Reserved.")

# =============================================================================
# 5. 頁面邏輯
# =============================================================================

def render_custom_header(title="AI 智能財報分析系統"):
    c_title, c_settings = st.columns([20, 1])
    with c_title:
        st.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'>🏛️ {title}</h1>", unsafe_allow_html=True)
    with c_settings:
        if st.session_state.get('is_processing', False):
            st.markdown("<div class='processing-indicator'>⏳</div>", unsafe_allow_html=True)
        else:
            if st.button("⚙️", key="settings_btn", help="開啟系統設定"):
                open_settings_dialog()
    st.markdown("<p style='text-align: center; font-size: 1.1rem; opacity: 0.8;'>融合頂尖多模態 AI 技術，提供深度數據提取、專業比率計算，以及審計級與白話文雙視角報告。</p>", unsafe_allow_html=True)
    royal_divider()

def home_page():
    render_custom_header()

    if GLOBAL_CONFIG_ERROR:
        st.error(GLOBAL_CONFIG_ERROR)
        return

    with st.container():
        st.markdown("### ⚡ 快速分析 (範例企業)")
        c1, c2, c3, c4 = st.columns(4)
        target_file = None
        status_cont = st.empty()
        
        is_disabled = st.session_state.get('is_processing', False)
        
        with c1: 
            if st.button("📊 2330 (台積電)", use_container_width=True, disabled=is_disabled): target_file = "2330.pdf"
        with c2: 
            if st.button("📈 2382 (廣達)", use_container_width=True, disabled=is_disabled): target_file = "2382.pdf"
        with c3: 
            if st.button("📉 2308 (台達電)", use_container_width=True, disabled=is_disabled): target_file = "2308.pdf"
        with c4: 
            if st.button("💻 2454 (聯發科)", use_container_width=True, disabled=is_disabled): target_file = "2454.pdf"

    royal_divider("📂")

    with st.container():
         st.markdown("### 📜 上傳財務報告")
         uploaded = st.file_uploader("請選擇 PDF 格式的文件...", type=["pdf"], key="uploader", disabled=is_disabled)
    
    royal_divider("🚀")

    with st.container():
        if target_file and os.path.exists(target_file):
            with open(target_file, "rb") as f: run_analysis_flow(f.read(), status_cont)
        elif target_file:
            st.error(f"❌ 找不到範例檔案: {target_file}")
        elif uploaded:
            col_start, col_rest = st.columns([1, 2])
            with col_start:
                 if st.button("✨ 開始執行分析", type="primary", use_container_width=True, disabled=is_disabled):
                    run_analysis_flow(uploaded.read(), status_cont)
        else:
            st.info("請先上傳文件或選擇範例以開始。")

def report_page():
    res = st.session_state.get('analysis_results')
    # V7.5: 更嚴格的數據防呆
    if not res or not isinstance(res, dict):
        st.info("⏳ 數據正在處理中，或請重新開始分析。")
        if st.button("⬅️ 回首頁", type="secondary"): 
            st.session_state['current_page'] = 'Home'
            st.rerun()
        return
    
    render_custom_header(f"📜 **{res.get('company_name', '未命名公司')}** 財報分析")
    
    # 1. 財務比率 (【V7.5】排版邏輯回歸 V5.8)
    with st.container():
        st.subheader("💎 關鍵財務比率")
        ratio_txt = res.get('ratio')
        
        if ratio_txt and isinstance(ratio_txt, str):
            # 嘗試解析表格
            tables = [t.strip() for t in ratio_txt.split('\n\n') if t.strip().startswith('|') and '---' in t]
            
            # 建立比率映射表
            ratio_map = {}
            for table_md in tables:
                first_line = table_md.split('\n')[0]
                if '本益比' in first_line: ratio_map['P/E Ratio'] = table_md
                elif '淨利率' in first_line: ratio_map['Net Profit Margin'] = table_md
                elif '毛利率' in first_line: ratio_map['Gross Profit Margin'] = table_md
                elif '股東權益報酬率' in first_line or 'ROE' in first_line: ratio_map['ROE'] = table_md
                elif '流動比率' in first_line: ratio_map['Current Ratio'] = table_md
                elif '負債比率' in first_line: ratio_map['Debt Ratio'] = table_md
                elif '速動比率' in first_line: ratio_map['Quick Ratio'] = table_md
            
            # V7.5: 嚴格執行 3x4 排版，確保位置固定
            ORDERED_RATIOS = [
                ('ROE', '股東權益報酬率'), ('Net Profit Margin', '淨利率'), ('Gross Profit Margin', '毛利率'),
                ('P/E Ratio', '本益比'), ('Current Ratio', '流動比率'), ('Debt Ratio', '負債比率'), ('Quick Ratio', '速動比率')
            ]

            col1, col2, col3 = st.columns(3)
            cols_row1 = [col1, col2, col3]
            col4, col5, col6, col7 = st.columns(4)
            cols_row2 = [col4, col5, col6, col7]
            all_cols = cols_row1 + cols_row2
            
            # 逐一填入
            for i, (key, _) in enumerate(ORDERED_RATIOS):
                if i < len(all_cols):
                    with all_cols[i]:
                        st.markdown(ratio_map.get(key, f"**{key} 數據未生成**"), unsafe_allow_html=True)
        else:
            st.warning("⚠️ 無法讀取財務比率數據，請重新嘗試分析。")

    royal_divider("🤖")
    
    # 2. AI 對話室引導 (V7.6: 移除說明文字，直接輸入)
    with st.container():
        st.markdown("### 🤖 AI 首席顧問")
        c_input, c_btn = st.columns([5, 1])
        with c_input:
            quick_q = st.text_input("快速提問...", placeholder="例如：請解釋為什麼存貨增加？", label_visibility="collapsed")
        with c_btn:
            if st.button("開始對話 ➤", type="primary", use_container_width=True):
                if quick_q:
                    st.session_state.chat_history.append({"role": "user", "content": quick_q})
                    inputs = []
                    if st.session_state.get('current_pdf_bytes'):
                        try: inputs.append(types.Part.from_bytes(data=st.session_state['current_pdf_bytes'], mime_type='application/pdf'))
                        except: pass
                    
                    std_data = res.get('standardization', '')
                    sys_prompt = f"你是一位專業、客觀且經驗豐富的財務顧問。已附上原始財報PDF與標準化數據摘要:\n{std_data[:3000]}...\n請回答使用者問題：{quick_q}"
                    inputs.append(sys_prompt)
                    
                    st.session_state['pending_query'] = inputs 
                    st.session_state['current_page'] = 'Chat'
                    st.rerun()
                else:
                    st.session_state['current_page'] = 'Chat'
                    st.rerun()

    royal_divider("📄")

    # 3. 三大分頁
    with st.container():
        t1, t2, t3 = st.tabs(["📄 專業審計總結", "🗣️ 白話文數據講解", "📊 標準化資訊提取"])
        with t1: st.markdown(res.get('summary', '⚠️ 數據遺失'))
        with t2: st.markdown(res.get('explanation', '⚠️ 數據遺失'))
        with t3: st.markdown(res.get('standardization', '⚠️ 數據遺失'))
    
    royal_divider("⬅️")
    
    # V7.5: 修正 Button Type 錯誤
    if st.button("⬅️ 結束閱覽，返回首頁", type="secondary"):
        st.session_state['analysis_results'] = None
        st.session_state['current_pdf_bytes'] = None
        st.session_state['current_page'] = 'Home'
        st.rerun()

def chat_page():
    c_back, c_title, c_set = st.columns([1, 10, 1])
    with c_back:
        if st.button("⬅️"):
            st.session_state['current_page'] = 'Report'
            st.rerun()
    with c_title:
        st.markdown("<h2 style='margin-top: 0; text-align: center;'>💬 AI 財報戰情室</h2>", unsafe_allow_html=True)
    with c_set:
        if st.button("⚙️", key="chat_settings"):
            open_settings_dialog()

    royal_divider("📜")

    with st.container():
        if not st.session_state.chat_history:
            st.caption("✨ 戰情室已開啟，請輸入您的問題...")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # V7.6: 處理快速提問，使用 HTML Typing 動畫
        if 'pending_query' in st.session_state:
            pending_inputs = st.session_state.pop('pending_query')
            with st.chat_message("assistant"):
                placeholder = st.empty()
                # 顯示三個跳動圓點
                placeholder.markdown(TYPING_ANIMATION_CSS, unsafe_allow_html=True)
                
                response = call_chat_api(pending_inputs)
                reply = f"❌ 錯誤: {response['error']}" if response.get("error") else response["content"]
                
                placeholder.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun() 

        with st.expander("📎 上傳輔助圖片/截圖 (選用)"):
            chat_uploaded_img = st.file_uploader("選擇圖片文件...", type=["png", "jpg", "jpeg"], key="chat_img_up")

    if prompt := st.chat_input("請輸入您的問題，顧問將即刻分析..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        inputs = []
        if st.session_state.get('current_pdf_bytes'):
            try: inputs.append(types.Part.from_bytes(data=st.session_state['current_pdf_bytes'], mime_type='application/pdf'))
            except: pass
        if chat_uploaded_img:
             try: inputs.append(types.Part.from_bytes(data=chat_uploaded_img.read(), mime_type=chat_uploaded_img.type))
             except: pass

        res = st.session_state.get('analysis_results', {})
        std_data = res.get('standardization', '') if res else ''
        
        sys_prompt = f"你是一位專業、客觀且經驗豐富的財務顧問。已附上原始財報PDF與標準化數據摘要:\n{std_data[:3000]}...\n請回答使用者問題：{prompt}"
        inputs.append(sys_prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            # 顯示三個跳動圓點
            placeholder.markdown(TYPING_ANIMATION_CSS, unsafe_allow_html=True)
            
            response = call_chat_api(inputs)
            reply = f"❌ 錯誤: {response['error']}" if response.get("error") else response["content"]
            
            placeholder.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

# =============================================================================
# 6. 主程式入口
# =============================================================================

if st.session_state['current_page'] == 'Home':
    home_page()
elif st.session_state['current_page'] == 'Report':
    report_page()
elif st.session_state['current_page'] == 'Chat':
    chat_page()