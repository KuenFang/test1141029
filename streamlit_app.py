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
# 0. 全域設定 (模型名稱在此修改)
# =============================================================================

MODEL_NAME = "gemini-3-pro-preview"

# =============================================================================
# 1. 核心規則與 API Key 設置
# =============================================================================

# 步驟 1：抓取公司名稱
PROMPT_COMPANY_NAME = textwrap.dedent("""
請從這份 PDF 財務報告的第一頁或封面頁中，提取出完整的、官方的公司法定全名 (例如 "台灣積體電路製造股份有限公司")。

限制：
1. 僅輸出公司名稱的純文字字串。
2. 禁止包含任何 Markdown、引號、標籤或任何 "公司名稱：" 之類的前綴。
3. 禁止包含任何其他文字或問候語。
""")

# 步驟 2：標準化提取
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

# 步驟 3：比率計算 (P/E 修正版)
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
   *注意：使用基本每股盈餘。指定收盤價請使用 Google Search 搜尋使用本分析系統當日或前一日的收盤價格。*
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

# 步驟 4：總結
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

# 步驟 5：講解
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


# API Key 設置
try:
    API_KEY = os.getenv('GEMINI_API_KEY')
    if not API_KEY:
        API_KEY = st.secrets.get("GEMINI_API_KEY") 
except Exception:
    API_KEY = None

# 初始化 Session State
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'
if 'analysis_results' not in st.session_state:
    st.session_state['analysis_results'] = None
if 'current_pdf_bytes' not in st.session_state:
    st.session_state['current_pdf_bytes'] = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if 'ui_theme' not in st.session_state:
    st.session_state['ui_theme'] = '跟隨系統'
if 'pending_question' not in st.session_state:
    st.session_state['pending_question'] = None

# =============================================================================
# 2. CLIENT 初始化
# =============================================================================

@st.cache_resource
def get_gemini_client(api_key):
    """安全地初始化 Gemini Client。"""
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        return None

CLIENT = get_gemini_client(API_KEY)
GLOBAL_CONFIG_ERROR = None
if CLIENT is None and API_KEY is None:
    GLOBAL_CONFIG_ERROR = "❌ 錯誤：GEMINI_API_KEY 未設定，無法連線至 Gemini API。"
elif CLIENT is None:
    GLOBAL_CONFIG_ERROR = "❌ 錯誤：CLIENT 初始化失敗，請檢查 API Key 是否有效。"


# --- 頁面配置與主頁導航 ---
st.set_page_config(
    page_title="AI財報分析系統 (K.R.)",
    page_icon="⚜️",
    layout="wide",
)

# =============================================================================
# CSS 樣式系統
# =============================================================================

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

    /* 進度條置頂 */
    .processing-indicator {
        color: #d4af37; font-weight: bold; font-family: monospace; animation: pulse 1.5s infinite;
        text-align: center; padding: 10px; border: 1px solid #d4af37; border-radius: 10px;
    }
    @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }

    /* 左下角浮水印 (透明度修正) */
    .fixed-watermark {
        position: fixed; bottom: 20px; left: 25px; font-size: 20px;
        font-family: 'Times New Roman', serif; font-weight: 900; 
        z-index: 9999; pointer-events: none; letter-spacing: 2px;
        opacity: 0.1 !important; 
    }

    /* 動畫 */
    @keyframes sheen { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }
    
    /* 表單按鈕強制樣式 (皇家紫金) */
    div[data-testid="stForm"] button[kind="primary"] {
        background: linear-gradient(135deg, #7B2CBF 0%, #9D4EDD 100%) !important;
        color: #ffffff !important;
        border: 2px solid #FFD700 !important;
        box-shadow: 0 4px 10px rgba(123, 44, 191, 0.3) !important;
        border-radius: 8px !important;
        height: 46px !important;
        width: 100% !important;
        margin-top: 0px !important;
    }
    div[data-testid="stForm"] button[kind="primary"]:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 15px rgba(123, 44, 191, 0.5) !important;
    }

    /* 強制對齊 Form 內的元件底部 */
    div[data-testid="stForm"] [data-testid="column"] {
        align-items: flex-end !important;
    }
    
    /* 頁面切換按鈕樣式 */
    .page-nav-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
"""

CSS_DARK = """
    /* 🌑 暗色模式 */
    .stApp {
        background-color: #05020a !important;
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(123, 44, 191, 0.2) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(255, 215, 0, 0.15) 0%, transparent 50%),
            linear-gradient(135deg, rgba(10, 5, 20, 0.95) 0%, rgba(25, 10, 40, 0.95) 100%) !important;
        background-attachment: fixed !important;
        color: #e0e0e0 !important;
    }
    h1, h2, h3, .big-title {
        background: linear-gradient(to right, #FFD700, #FFC300, #D4AF37, #9D4EDD, #7B2CBF) !important;
        background-size: 200% auto !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
        text-shadow: 0 2px 15px rgba(157, 78, 221, 0.6) !important; animation: sheen 3s linear infinite !important;
    }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background: rgba(40, 20, 60, 0.4) !important; backdrop-filter: blur(10px) !important;
        border: 2px solid rgba(255, 215, 0, 0.3) !important; border-radius: 20px !important; padding: 30px !important;
        box-shadow: 0 0 0 1px rgba(157, 78, 221, 0.3) inset, 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 40px rgba(123, 44, 191, 0.2) !important;
        margin-bottom: 25px !important;
    }
    /* 非 Form 的普通按鈕 */
    .stButton>button:not([kind="primary"]) {
        background: linear-gradient(135deg, #4a1a88 0%, #7B2CBF 100%) !important; color: #FFD700 !important; border: none !important;
        box-shadow: 0 5px 15px rgba(123, 44, 191, 0.5) !important;
    }
    .stTextInput input, .stChatInput textarea, .stFileUploader {
        background-color: rgba(20, 10, 30, 0.6) !important; border: 2px solid #9D4EDD !important; color: #FFD700 !important;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #7B2CBF, #9D4EDD) !important; 
        border: none !important;
        border-radius: 18px 18px 4px 18px !important;
        margin-left: 20% !important;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: rgba(60, 60, 60, 0.8) !important; 
        border: 1px solid #D4AF37 !important; color: #f0f0f0 !important;
        border-radius: 18px 18px 18px 4px !important;
        margin-right: 20% !important;
    }
    .fixed-watermark {
        background: linear-gradient(to right, #FFD700, #FFF, #9D4EDD) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
    }
    .royal-divider::before, .royal-divider::after { background: linear-gradient(to right, transparent, #FFD700, #9D4EDD, transparent) !important; }
    .royal-divider-icon { color: #FFD700; }
    .stTabs [aria-selected="true"] { color: #FFD700 !important; border-bottom: 3px solid #9D4EDD !important; }
"""

CSS_LIGHT = """
    /* ☀️ 亮色模式 */
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
    /* 非 Form 的普通按鈕 */
    .stButton>button:not([kind="primary"]) {
        background: linear-gradient(135deg, #7b2cbf 0%, #9d4edd 100%) !important; color: #ffffff !important; border: none !important;
        border-radius: 12px !important; box-shadow: 0 5px 15px rgba(123, 44, 191, 0.3) !important;
    }
    button[kind="secondary"] {
        background: transparent !important; border: 2px solid #7b2cbf !important; color: #7b2cbf !important;
    }
    .stTextInput input, .stChatInput textarea, .stFileUploader {
        background-color: rgba(255,255,255,0.8) !important; border: 2px solid #dcdcdc !important; color: #4a1a88 !important; border-radius: 12px !important;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #9d4edd, #c77dff) !important; color: white !important;
        border-radius: 18px 18px 4px 18px !important;
        margin-left: 20% !important;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background: #ffffff !important; border: 1px solid #e0aa3e !important; color: #2e1065 !important;
        border-radius: 18px 18px 18px 4px !important;
        margin-right: 20% !important;
    }
    .royal-divider::before, .royal-divider::after { background: linear-gradient(to right, transparent, #b8860b, transparent) !important; }
    .royal-divider-icon { color: #b8860b; }
    .fixed-watermark {
        background: linear-gradient(to right, #4a1a88, #b8860b) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
    }
    .stTabs [aria-selected="true"] { color: #7B1FA2 !important; border-bottom: 3px solid #7B1FA2 !important; }
"""

CSS_STRUCTURE = """
    .stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 15px !important; }
    .stTabs [data-baseweb="tab"] { border: none !important; font-weight: 800 !important; font-size: 1.1rem !important; }
    .royal-divider { display: flex; align-items: center; margin: 40px 0; justify-content: center; }
    .royal-divider::before, .royal-divider::after { content: ""; width: 40%; height: 2px; display: block; }
    .royal-divider-icon { padding: 0 15px; font-size: 1.5rem; }
    
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

st.markdown("""<style>html { lang: "zh-Hant"; }</style>""", unsafe_allow_html=True)
keep_alive = """<script>setInterval(() => { fetch(window.location.href, {mode: 'no-cors'}); }, 300000);</script>"""
st.markdown(keep_alive, unsafe_allow_html=True)


# =============================================================================
# 3. 設定對話框
# =============================================================================

@st.dialog("⚙️ 系統設定")
def open_settings_dialog():
    """彈窗設定介面"""
    tab_gen, tab_data, tab_about = st.tabs(["⚙️ 一般設定", "🧹 資料管理", "ℹ️ 關於系統"])
    
    with tab_gen:
        current_theme_index = ["跟隨系統", "極致黑金 (Dark)", "皇家白金 (Light)"].index(
            st.session_state.get('ui_theme', '跟隨系統')
        )
        new_theme = st.radio(
            "🎨 介面主題", 
            ["跟隨系統", "極致黑金 (Dark)", "皇家白金 (Light)"],
            index=current_theme_index,
            horizontal=True
        )
        if new_theme != st.session_state['ui_theme']:
            st.session_state['ui_theme'] = new_theme
            st.rerun()
        
    with tab_data:
        st.warning("⚠️ 清除資料將無法復原")
        if st.button("🗑️ 清除所有分析紀錄", type="primary"):
            st.session_state['analysis_results'] = None
            st.session_state['chat_history'] = []
            st.session_state['current_pdf_bytes'] = None
            st.success("✅ 已清除所有暫存資料！")
            time.sleep(1)
            st.rerun()
            
    with tab_about:
        st.markdown("### 🤖 AI 財報分析系統")
        st.write("**版本：** v1.0.0")
        st.write("**開發：** K.R. Design")
        st.write("本系統使用 Google Gemini Pro 模型進行財務報表之自動化分析與解讀。")
        st.caption("Copyright © 2025 K.R. All Rights Reserved.")

# =============================================================================
# 4. 輔助函數
# =============================================================================

def navigate_to(page_name):
    """更改 session state 並強制重新渲染頁面。"""
    st.session_state['current_page'] = page_name
    st.rerun()

def render_custom_header(title="AI 智能財報分析系統", show_nav=False):
    """渲染自訂標題與導航按鈕"""
    c_title, c_settings = st.columns([20, 1])
    with c_title:
        st.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'>🏛️ {title}</h1>", unsafe_allow_html=True)
    with c_settings:
        if st.button("⚙️", key=f"settings_btn_{st.session_state['current_page']}", help="開啟系統設定"):
            open_settings_dialog()
    st.markdown("<p style='text-align: center; font-size: 1.1rem; opacity: 0.8;'>融合頂尖多模態 AI 技術，提供深度數據提取、專業比率計算，以及審計級與白話文雙視角報告。</p>", unsafe_allow_html=True)
    
    # 顯示頁面導航按鈕 (僅在 Report 和 Chat 頁面)
    if show_nav and st.session_state.get('analysis_results'):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            nav_col1, nav_col2 = st.columns(2)
            with nav_col1:
                current = st.session_state['current_page']
                if current == 'Chat':
                    if st.button("📊 返回分析報告", use_container_width=True, key="nav_to_report"):
                        navigate_to('Report')
                else:
                    st.button("📊 分析報告", use_container_width=True, disabled=True, key="nav_report_disabled")
            with nav_col2:
                if current == 'Report':
                    chat_label = "💬 AI 助手" + (f" ({len(st.session_state.chat_history)})" if st.session_state.chat_history else "")
                    if st.button(chat_label, use_container_width=True, key="nav_to_chat"):
                        navigate_to('Chat')
                else:
                    st.button("💬 AI 助手", use_container_width=True, disabled=True, key="nav_chat_disabled")
    
    royal_divider()

# =============================================================================
# 5. 核心分析邏輯
# =============================================================================

def run_analysis_flow(file_content_to_send, status_container):
    """
    執行 5 步驟分析流程，並將 PDF 存入 session_state 供對話使用。
    """
    company_name = None
    standardization_data = None
    ratio_data = None
    summary_data = None
    explanation_data = None
    
    # 儲存原始 PDF bytes 供後續對話功能使用
    st.session_state['current_pdf_bytes'] = file_content_to_send
    # 清空舊的對話紀錄
    st.session_state['chat_history'] = []
    
    try:
        # --- 步驟 1: 抓取公司名稱 (PDF -> Text) ---
        with status_container.status("⏳ 正在執行 AI 分析...", expanded=True) as status:
            
            st.write("📜 步驟 1/5: 正在識別公司名稱...")
            name_response = call_multimodal_api(
                file_content_bytes=file_content_to_send,
                prompt=PROMPT_COMPANY_NAME, 
                use_search=False
            )
            if name_response.get("error"):
                raise Exception(f"抓取公司名稱失敗: {name_response['error']}")
            company_name = name_response["content"].strip()
            
            # --- 步驟 2: 標準化 (PDF -> Text) ---
            st.write("🔍 步驟 2/5: 正在提取與標準化財報數據...")
            std_response = call_multimodal_api(
                file_content_bytes=file_content_to_send,
                prompt=PROMPT_BIAO_ZHUN_HUA_CONTENT, 
                use_search=False
            )
            if std_response.get("error"):
                raise Exception(f"標準化失敗: {std_response['error']}")
            standardization_data = std_response["content"]

            # --- 步驟 3: 比率計算 (PDF -> Text) ---
            st.write("🧮 步驟 3/5: 正在計算關鍵財務比率...")
            ratio_response = call_multimodal_api(
                file_content_bytes=file_content_to_send,
                prompt=PROMPT_RATIO_CONTENT, 
                use_search=True 
            )
            if ratio_response.get("error"):
                raise Exception(f"比率計算失敗: {ratio_response['error']}")
            ratio_data = ratio_response["content"]

            # --- 步驟 4: 總結 (Text -> Text) ---
            st.write("⚖️ 步驟 4/5: 正在生成專業審計總結...")
            summary_response = call_text_api(
                input_text=standardization_data,
                prompt=PROMPT_ZONG_JIE_CONTENT 
            )
            if summary_response.get("error"):
                raise Exception(f"總結生成失敗: {summary_response['error']}")
            summary_data = summary_response["content"]

            # --- 步驟 5: 講解 (Text -> Text) ---
            st.write("🗣️ 步驟 5/5: 正在生成白話文數據講解...")
            explanation_response = call_text_api(
                input_text=standardization_data,
                prompt=PROMPT_JIAN_JIE_CONTENT 
            )
            if explanation_response.get("error"):
                raise Exception(f"講解生成失敗: {explanation_response['error']}")
            explanation_data = explanation_response["content"]
            
            status.update(label="✅ 分析完成！準備生成報告...", state="complete", expanded=False)

        # --- 處理結果 ---
        parsed_content = {
            "company_name": company_name,
            "ratio": ratio_data,
            "summary": summary_data,
            "explanation": explanation_data,
            "standardization": standardization_data
        }
        
        st.session_state['analysis_results'] = parsed_content
        time.sleep(0.5)
        navigate_to('Report')

    except Exception as e:
        st.error(f"❌ 分析流程中斷：\n{e}")


# =============================================================================
# 6. 頁面內容定義
# =============================================================================

# --- A. Home Page ---

def home_page():
    """主頁：包含上傳區塊、評審專用快速按鍵、設定按鈕。"""
    
    render_custom_header()

    if GLOBAL_CONFIG_ERROR:
        st.error(GLOBAL_CONFIG_ERROR)
        return

    status_container = st.empty()

    with st.container():
        st.markdown("### ⚡ 快速分析 (範例企業)")
        c1, c2, c3, c4 = st.columns(4)
        target_file = None
        
        with c1: 
            if st.button("📊 2330 (台積電)", use_container_width=True): target_file = "2330.pdf"
        with c2: 
            if st.button("📈 2382 (廣達)", use_container_width=True): target_file = "2382.pdf"
        with c3: 
            if st.button("📉 2308 (台達電)", use_container_width=True): target_file = "2308.pdf"
        with c4: 
            if st.button("💻 2454 (聯發科)", use_container_width=True): target_file = "2454.pdf"

    royal_divider("📂")

    with st.container():
        st.markdown("### 📜 上傳財務報告")
        uploaded = st.file_uploader("請選擇 PDF 格式的文件...", type=["pdf"], key="uploader")
    
    royal_divider("🚀")

    with st.container():
        if target_file and os.path.exists(target_file):
            with open(target_file, "rb") as f: 
                run_analysis_flow(f.read(), status_container)
        elif target_file:
            st.error(f"❌ 找不到範例檔案: {target_file}")
        elif uploaded:
            if st.button("✨ 開始執行分析", type="primary", use_container_width=True):
                run_analysis_flow(uploaded.read(), status_container)
        else:
            st.info("請先上傳文件或選擇範例以開始。")


# --- B. Report Page ---

def report_page():
    """報告結果頁面：包含財務比率和分析報告，底部有快速提問入口"""
    
    results = st.session_state.get('analysis_results')
    if not results:
        st.info("請先在開始介面中上傳檔案並執行分析。")
        if st.button("⬅️ 回首頁", type="secondary"):
            navigate_to('Home')
        return
    
    # 動態標題與導航
    company_name = results.get("company_name", "財報分析") 
    render_custom_header(f"📜 **{company_name}** 財報分析", show_nav=True)
    
    # --- 財務比率區塊 ---
    with st.container():
        st.subheader("💎 關鍵財務比率")
        ratio_output = results['ratio']
        ratio_tables = results['ratio'].split('\n\n') 
        valid_tables = [t.strip() for t in ratio_tables if t.strip().startswith('|') and '---' in t]

        ratio_map = {}
        for table_md in valid_tables:
            first_line = table_md.split('\n')[0]
            if '本益比' in first_line: ratio_map['P/E Ratio'] = table_md
            elif '淨利率' in first_line: ratio_map['Net Profit Margin'] = table_md
            elif '毛利率' in first_line: ratio_map['Gross Profit Margin'] = table_md
            elif '股東權益報酬率' in first_line or 'ROE' in first_line: ratio_map['ROE'] = table_md
            elif '流動比率' in first_line: ratio_map['Current Ratio'] = table_md
            elif '負債比率' in first_line: ratio_map['Debt Ratio'] = table_md
            elif '速動比率' in first_line: ratio_map['Quick Ratio'] = table_md
                
        ORDERED_RATIOS = [
            ('ROE', '股東權益報酬率'), ('Net Profit Margin', '淨利率'), ('Gross Profit Margin', '毛利率'),
            ('P/E Ratio', '本益比'), ('Current Ratio', '流動比率'), ('Debt Ratio', '負債比率'), ('Quick Ratio', '速動比率')
        ]

        col1, col2, col3 = st.columns(3)
        cols_row1 = [col1, col2, col3]
        col4, col5, col6, col7 = st.columns(4)
        cols_row2 = [col4, col5, col6, col7]
        all_cols = cols_row1 + cols_row2
        found_ratios_count = len(ratio_map)

        if found_ratios_count >= 7:
            for i, (key, _) in enumerate(ORDERED_RATIOS):
                if i < len(all_cols):
                    with all_cols[i]:
                        st.markdown(ratio_map.get(key, f"**無法找到 {key} 數據**"), unsafe_allow_html=True) 
        else:
            st.warning(f"比率計算表格解析失敗，僅找到 {found_ratios_count} 個所需比率。")
            st.code(ratio_output, language='markdown') 

    royal_divider("📄")

    # --- 報告分頁區塊 ---
    with st.container():
        tab1, tab2, tab3 = st.tabs([
            "📄 財報總結 (專業審計視角)", 
            "🗣️ 數據講解 (非專業人士白話文)", 
            "📊 資訊提取 (標準化數據)", 
        ])

        with tab1:
            st.subheader("📄 財報總結")
            st.markdown(results['summary'] if results['summary'] else "財報總結生成失敗。")
        with tab2:
            st.subheader("🗣️ 數據講解")
            st.markdown(results['explanation'] if results['explanation'] else "數據講解生成失敗。")
        with tab3:
            st.subheader("📊 資訊提取")
            st.markdown(results['standardization'] if results['standardization'] else "標準化資訊提取失敗。")

    royal_divider("💬")
    
    # --- 快速提問入口 ---
    with st.container():
        st.markdown("### 💬 有任何疑問？詢問 AI 財報助手")
        st.caption("🤖 輸入問題後將自動跳轉至對話頁面")
        
        with st.form(key="quick_question_form", clear_on_submit=True):
            col_input, col_btn = st.columns([9, 1])
            with col_input:
                quick_question = st.text_input(
                    "快速提問...", 
                    placeholder="例如：請解釋這家公司的營收成長原因",
                    label_visibility="collapsed",
                    key="quick_chat_input"
                )
            with col_btn:
                submit_btn = st.form_submit_button("▶", type="primary", use_container_width=True)
        
        if submit_btn and quick_question:
            # 儲存問題並跳轉到聊天頁
            st.session_state['pending_question'] = quick_question
            navigate_to('Chat')

    royal_divider("⬅️")

    # --- 回上頁按鈕 ---
    if st.button("⬅️ 結束閱覽，返回首頁", type="secondary"):
        st.session_state['analysis_results'] = None
        st.session_state['current_pdf_bytes'] = None
        st.session_state['chat_history'] = []
        st.session_state['pending_question'] = None
        navigate_to('Home')


# --- C. Chat Page (新增獨立聊天頁面) ---

def chat_page():
    """獨立的 AI 財報助手聊天頁面"""
    
    results = st.session_state.get('analysis_results')
    if not results:
        st.info("請先在開始介面中上傳檔案並執行分析。")
        if st.button("⬅️ 回首頁", type="secondary"):
            navigate_to('Home')
        return
    
    company_name = results.get("company_name", "財報分析")
    render_custom_header(f"💬 **{company_name}** AI 財報助手", show_nav=True)
    
    st.caption("🤖 對話模式 (溫度 1.2) - 可自由詢問財報細節，支援上傳圖片")
    
    # 處理待處理的問題 (從 Report 頁面跳轉過來的)
    if st.session_state.get('pending_question'):
        pending_q = st.session_state['pending_question']
        st.session_state['pending_question'] = None
        
        # 記錄使用者訊息
        st.session_state.chat_history.append({"role": "user", "content": pending_q})
        
        # 呼叫 API 取得回覆
        response = process_chat_message(pending_q, results)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # 顯示對話歷史
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # 額外上傳圖片 (選用)
    with st.expander("📎 上傳圖片或檔案 (選用)", expanded=False):
        chat_uploaded_file = st.file_uploader(
            "上傳圖片或 PDF", 
            type=["png", "jpg", "jpeg", "pdf"], 
            key="chat_uploader",
            label_visibility="collapsed"
        )
        if chat_uploaded_file:
            st.success(f"✅ 已載入: {chat_uploaded_file.name}")
    
    # 聊天輸入
    user_input = st.chat_input("輸入您的問題...")
    
    if user_input:
        # 顯示使用者訊息
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # 顯示 AI 思考中
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = process_chat_message(user_input, results)
            st.markdown(response)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()
    
    royal_divider("🗑️")
    
    # 清除對話按鈕
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🗑️ 清除對話紀錄", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


def process_chat_message(user_question, results):
    """處理聊天訊息並呼叫 API"""
    
    input_contents = []
    
    # (A) 原始財報 PDF
    if st.session_state.get('current_pdf_bytes'):
        try:
            pdf_part = types.Part.from_bytes(
                data=st.session_state['current_pdf_bytes'], 
                mime_type='application/pdf'
            )
            input_contents.append(pdf_part)
        except: 
            pass
    
    # (B) 標準化數據
    std_data = results.get('standardization', '')
    system_prompt_text = f"""
    你是一位專業且靈活的財務顧問。
    
    【資料來源 1】你已經閱讀了這家公司的原始財報 PDF (已附上)。
    【資料來源 2】以下是我們已經整理好的標準化財務數據：
    {std_data[:5000]} (節錄)
    
    【任務】
    請根據使用者的問題進行回答。
    與之前的嚴格分析不同，你可以自由發揮、使用外部知識(如果需要)、並以輕鬆但專業的口吻對話。
    """
    
    input_contents.append(system_prompt_text)
    input_contents.append(f"使用者問題: {user_question}")
    
    # 呼叫 API
    response = call_chat_api(input_contents)
    
    if response.get("error"):
        return f"❌ 發生錯誤: {response['error']}"
    else:
        return response["content"]


# =============================================================================
# 7. API 呼叫函數
# =============================================================================

def call_multimodal_api(file_content_bytes, prompt, use_search=False):
    """標準分析用 (Temperature=0.0)"""
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}
    
    try:
        pdf_part = types.Part.from_bytes(data=file_content_bytes, mime_type='application/pdf')
    except Exception as e: return {"error": f"PDF 檔案處理失敗: {e}"} 

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
    """純文字分析用 (Temperature=0.0)"""
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
    """對話專用 API (Temperature=1.2, 高自由度)"""
    global CLIENT 
    if CLIENT is None: return {"error": GLOBAL_CONFIG_ERROR}

    config = types.GenerateContentConfig(
        temperature=1.2, 
        tools=[{"google_search": {}}] 
    )

    try:
        response = CLIENT.models.generate_content(
            model=MODEL_NAME, 
            contents=contents, 
            config=config
        )
        return {"status": "success", "content": response.text}
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# 8. 運行主邏輯
# =============================================================================

if st.session_state['current_page'] == 'Home':
    home_page()
elif st.session_state['current_page'] == 'Report':
    report_page()
elif st.session_state['current_page'] == 'Chat':
    chat_page()