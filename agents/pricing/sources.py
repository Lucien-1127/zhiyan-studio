"""公開方案名冊。{N} 只接受新台幣整數，條款和價格須出現在列出的方案段落。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Offer:
    vendor: str
    plan: str
    group: str
    url: str
    section: tuple[str, str]
    prices: dict[str, str]
    # 特定來源的整頁共同條款；其他附加權益只讀目標方案段落。
    page_terms: tuple[tuple[str, str], ...] = ()


TASKER = "https://www.tasker.com.tw/workroom/"
GREMLIN = "https://gremlinworks.com.tw/service/ai-integration"
INSIN = "https://www.insin.com.tw/services/"
ONLAUNCH = TASKER + "onlaunch/service-detail/47862"
JWAY = "https://www.jway.com.tw/pricing-ai-support.html"
PENSIEVE = "https://pensieve.staruptech.com/pricing"
T = (r"^服務內容$", r"^使用的技能專長$")
FLOW, KB = "工作流建置", "文件檢索知識庫建置"
UNIT_SETUP = "twd_per_project"
G_EXTRA = (
    ("extra", r"^以下皆為單次建置費用;[^\n]+依實際用量另計。"),
    ("extra", r"^\*以上為示意方案與價格[^\n]*"),
)
I_SUPPORT = (("support", r"^維運支援 NT\$[^\n]+"),)
O_SUPPORT = (("support", r"^・維護月費 NT\$[^\n]+|^bug 保固[^\n]+"),)
J_TERMS = (
    ("extra", r"^以上報價均以新台幣[^\n]+未稅[^\n]*"),
    ("allowance", r"^30 天免費試用 PoC\n[^\n]+"),
)


def project(vendor, plan, group, url, scope, price, shared=()):
    return Offer(vendor, plan, group, url, scope, {UNIT_SETUP: price}, shared)


OFFERS = [
    project("Antonio", "單一 n8n 工作流", FLOW, TASKER+"vantage-automation/service-detail/44609",
            T, r"^\${N} 是單一流程的起價,"),
    project("Gremlin Works", "流程自動化", FLOW, GREMLIN,
            (r"^適合:B2B 業務・訂單與行政作業流程$", r"^\*以上為示意方案"),
            r"^NT\${N}\n起・每條流程$", G_EXTRA),
    project("Lucas Liu", "基礎單條流程", FLOW, TASKER+"lucasliuai/service-detail/47233",
            (r"^基礎NT\$[\d,]+/\d+天:1條流程", r"^標準NT\$[\d,]+/\d+天:2[–-]3條流程"),
            r"^基礎NT\${N}/\d+天:1條流程",
            (("features", r"交付流程說明與教學。"),)),
    project("T4140563", "企業流程自動化", FLOW, TASKER+"ebZLej/service-detail/47636",
            T, r"^報價以 NT\${N} 起,依流程步驟數與串接系統數量調整"),
    project("OnLaunch 上線工作室", "流程自動化", FLOW, ONLAUNCH,
            T, r",流程 NT\${N} 起,AI 客服/RAG", O_SUPPORT),
    project("橋序創研", "入門自動化", FLOW, "https://www.bridgeseqlab.com/service/n8n",
            (r"^入門自動化把", r"^標準自動化最多人選"),
            r"^入門自動化[^\n\$]{1,40}NT\$ *{N} 起\+?$",
            (("support", r"^維持既有自動化流程穩定運作。\nNT\$ [\d,]+ / 年"),)),
    project("AI 創界", "單一流程", FLOW, "https://service.aicreateaworld.com/service-n8n.html",
            (r"^費用怎麼計算$", r"^委託前常問$"), r"^單一流程起價 NT\${N}含流程設計"),
    project("Monglo", "快速自動化", FLOW, "https://monglo.co/services/automation",
            (r"^快速自動化$", r"^商務自動化$"), r"^NT\${N} 起\n1[–~-]3 流程$"),
    project("INSIN", "單一企業流程", FLOW, INSIN,
            (r"^流程自動化 — 單一流程 NT", r"^AI/LLM 應用 —"),
            r"^流程自動化 — 單一流程 NT\${N} 起$", I_SUPPORT),
    project("T4140563", "文件問答與客服", KB, TASKER+"ebZLej/service-detail/47637",
            T, r"^報價以 NT\${N} 起,依文件量與串接通路調整"),
    project("OnLaunch 上線工作室", "AI 客服／RAG", KB, ONLAUNCH,
            T, r"AI 客服/RAG NT\${N} 起;Agent/跨系統", O_SUPPORT),
    project("Antonio", "單一文件知識庫", KB, TASKER+"vantage-automation/service-detail/47718",
            T, r"^\${N} 為單一知識庫\(約 [\d,]+ 份文件內\)起價;"),
    project("Gremlin Works", "AI 客服與知識庫", KB, GREMLIN,
            (r"^適合:電商品牌・連鎖門市・會員客服$", r"^適合:B2B 業務・訂單與行政作業流程$"),
            r"^NT\${N}\n起・單次$", G_EXTRA),
    project("Monglo", "知識庫檢索與後台", KB, "https://monglo.co/services/chatbot",
            (r"^AI 客服$", r"^AI 客服專業版$"), r"^NT\${N} 起\n知識庫\+檢索式回答\+後台$"),
    project("INSIN", "企業 AI 應用", KB, INSIN,
            (r"^AI/LLM 應用 —", r"^系統整合與客製系統 —"),
            r"^AI/LLM 應用 — NT\${N} 起$", I_SUPPORT),
    Offer("傑崴科技 JWAY", "官網 AI 客服入門", "建置加月租", JWAY,
          (r"^Starter$", r"^Professional · 推薦$"),
          {UNIT_SETUP: r"^一次性建置費 NT\${N}$", "twd_per_month": r"^NT\${N} / 月$"}, J_TERMS),
    Offer("傑崴科技 JWAY", "超額對話加購", "用量", JWAY,
          (r"^超額對話量$", r"^客製對話流程 / 第三方系統串接$"),
          {"twd_per_1000_conversations": r"每 1,000 次計費\nNT\${N} / 千次$"}, J_TERMS),
    Offer("Pensieve AI", "個人研究版", "訂閱", PENSIEVE,
          (r"^個人研究版$", r"^立即註冊$"),
          {"twd_per_month": r"^NT\${N}/1 個月$", "twd_per_year": r"^NT\${N}/12 個月(?:\([^\n]*\))?$"},
          (("allowance", r"^免費/[\d,]+ 天\n試用期間共 [\d,.]+ 萬 Token"),)),
]
