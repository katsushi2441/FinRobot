# coding: utf-8
"""日本語マーケットレポート生成.

yfinanceで価格・銘柄情報を取得し、任意でKurage判断API(kbrain)の所見を加えて、
日本語のアナリストレポート(Markdown)を生成する。

例:
    from finrobot_jp import JapaneseMarketAnalyst
    print(JapaneseMarketAnalyst().report("7203.T"))
"""
from __future__ import annotations

import json

import yfinance as yf

from .kbrain import KurageBrainClient
from .llm_ja import JapaneseLLM
from .prompts_ja import ANALYST_SYSTEM_JA, REPORT_PROMPT_JA

_INFO_KEYS = [
    ("longName", "名称"), ("sector", "セクター"), ("industry", "業種"),
    ("marketCap", "時価総額"), ("trailingPE", "PER(実績)"), ("dividendYield", "配当利回り"),
    ("fiftyTwoWeekHigh", "52週高値"), ("fiftyTwoWeekLow", "52週安値"),
]


class JapaneseMarketAnalyst:
    def __init__(self, llm: JapaneseLLM | None = None,
                 brain: KurageBrainClient | None = None):
        self.llm = llm or JapaneseLLM()
        self.brain = brain or KurageBrainClient()

    def collect(self, symbol: str, period: str = "3mo") -> dict:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            raise ValueError(f"no price data for {symbol}")
        info = {}
        try:
            raw = ticker.info or {}
            for key, label in _INFO_KEYS:
                if raw.get(key) is not None:
                    info[label] = raw[key]
        except Exception:
            pass  # yfinanceのinfoは不安定。価格データだけでもレポートは成立する

        close = hist["Close"]
        summary = {
            "終値(最新)": round(float(close.iloc[-1]), 2),
            "期間高値": round(float(close.max()), 2),
            "期間安値": round(float(close.min()), 2),
            "期間騰落率(%)": round((float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100, 2),
            "直近5日騰落率(%)": round((float(close.iloc[-1]) / float(close.iloc[-6]) - 1) * 100, 2)
            if len(close) >= 6 else None,
            "平均出来高": int(hist["Volume"].mean()),
            "データ期間": f"{hist.index[0].date()} 〜 {hist.index[-1].date()} ({len(hist)}営業日)",
        }
        return {"info": info, "price_summary": {k: v for k, v in summary.items() if v is not None}}

    def brain_judgment(self, symbol: str, market: str, data: dict) -> dict | None:
        """支払いウォレットが設定されていれば有料判断を取得(fail-open: 失敗してもレポートは出す)."""
        if market not in ("crypto", "fx") or not self.brain.available(market):
            return None
        try:
            price = data["price_summary"]["終値(最新)"]
            asset = {("symbol" if market == "crypto" else "pair"): symbol,
                     "market": {"last_price": price}}
            return self.brain.opportunity_ranking(market, [asset])
        except Exception:
            return None

    def report(self, symbol: str, market: str = "stock", period: str = "3mo") -> str:
        data = self.collect(symbol, period)
        judgment = self.brain_judgment(symbol, market, data)
        if judgment:
            brain_section = ("## Kurage判断API(kbrain)の所見\n"
                             + json.dumps(judgment, ensure_ascii=False, indent=2)[:4000])
            brain_heading = "4. kbrain所見の解説(上記JSONを日本語で要約)"
        else:
            brain_section = ""
            brain_heading = "4. (kbrain未接続のためスキップ)"
        prompt = REPORT_PROMPT_JA.format(
            symbol=symbol,
            info=json.dumps(data["info"], ensure_ascii=False, indent=2) or "データなし",
            price_summary=json.dumps(data["price_summary"], ensure_ascii=False, indent=2),
            brain_section=brain_section,
            brain_heading=brain_heading,
        )
        return self.llm.complete(prompt, system=ANALYST_SYSTEM_JA)
