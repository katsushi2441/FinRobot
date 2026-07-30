# coding: utf-8
"""Kurage判断API (kcbrain / kfxbrain / ksbrain) クライアント.

いずれも任意接続。URL・トークンは環境変数でのみ与える(このリポジトリには置かない):

  crypto: KCBRAIN_URL,  KCBRAIN_API_TOKEN   (X-KCBRAIN-Token)
  fx:     KFXBRAIN_URL, KFXBRAIN_API_TOKEN  (X-KFXBrain-Token)
  stock:  KSBRAIN_URL,  KSBRAIN_API_TOKEN   (Authorization: Bearer)

入力エンベロープはmarketごとに異なる:
  crypto(kcbrain): {"assets":[{"symbol":"BTC_USDT", ...}]}
  fx(kfxbrain)   : {"pairs":[{"pair":"EUR_USD", ...}]}
  stock(ksbrain) : POST /v1/evidence -> POST /v1/analyze/full

provider="deepseek" を渡すとx402課金レール(DeepSeek)、Noneなら各brainの既定(無料ローカル)。
"""
from __future__ import annotations

import json
import os
import urllib.request


class KurageBrainClient:
    _MARKETS = {
        "crypto": {
            "url_env": "KCBRAIN_URL", "token_env": "KCBRAIN_API_TOKEN",
            "token_header": "X-KCBRAIN-Token", "provider_header": "X-KCBRAIN-Provider",
            "asset_field": "assets", "id_field": "symbol",
        },
        "fx": {
            "url_env": "KFXBRAIN_URL", "token_env": "KFXBRAIN_API_TOKEN",
            "token_header": "X-KFXBrain-Token", "provider_header": "X-KFXBrain-Provider",
            "asset_field": "pairs", "id_field": "pair",
        },
    }

    def __init__(self, provider: str | None = None, timeout: int = 300):
        self.provider = provider
        self.timeout = timeout

    def available(self, market: str) -> bool:
        if market == "stock":
            return bool(os.environ.get("KSBRAIN_URL"))
        cfg = self._MARKETS.get(market)
        return bool(cfg and os.environ.get(cfg["url_env"]))

    def _post(self, url: str, path: str, payload: dict, headers: dict) -> dict:
        req = urllib.request.Request(
            url.rstrip("/") + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---- crypto / fx (kcbrain / kfxbrain) ----

    def opportunity_ranking(self, market: str, assets: list[dict], timeframe: str = "H1") -> dict:
        """銘柄一覧をまとめて1回で判定する(取引ループ内で1銘柄ずつ呼ばないこと)."""
        cfg = self._MARKETS[market]
        url = os.environ[cfg["url_env"]]
        headers = {cfg["token_header"]: os.environ.get(cfg["token_env"], "")}
        if self.provider == "deepseek":
            headers[cfg["provider_header"]] = "deepseek"
        payload = {"timeframe": timeframe, cfg["asset_field"]: assets}
        return self._post(url, "/v1/market/opportunity-ranking", payload, headers)

    # ---- stock (ksbrain) ----

    def stock_analyze(self, symbol: str, evidence: list[dict]) -> dict:
        """ksbrain: 証拠を登録してからfull分析を呼ぶ。根拠IDが判断に紐づく."""
        url = os.environ["KSBRAIN_URL"]
        headers = {"Authorization": f"Bearer {os.environ.get('KSBRAIN_API_TOKEN', '')}"}
        for item in evidence:
            self._post(url, "/v1/evidence", item, headers)
        return self._post(url, "/v1/analyze/full", {"symbol": symbol}, headers)
