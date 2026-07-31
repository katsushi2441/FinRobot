# coding: utf-8
"""Kurage判断API (kcbrain / kfxbrain / ksbrain) クライアント — Bankr x402 有料レール。

Kurageの判断ブレインは有料サービス。呼び出しごとにx402(Base USDC)で支払う。
無料・自己ホスト経路はこのリポジトリには存在しない。

必要な環境変数:
  KURAGE_X402_WALLET_KEY  支払いに使うEVM秘密鍵(0x…)。Base USDCの残高が必要
  KURAGE_BANKR_BASE       (任意) Bankrサービスのベース。既定は公式エンドポイント

価格(2026-07時点): kcbrain $0.001 / fxbrain $0.05 / ksbrain $0.001(フル分析 $0.003)
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.request

BANKR_BASE = os.environ.get(
    "KURAGE_BANKR_BASE",
    "https://x402.bankr.bot/0x444fadbd6e1fed0cfbf7613b6c9f91b9021eecbd").rstrip("/")

_EIP712_DOMAIN = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
    {"name": "verifyingContract", "type": "address"},
]
_TRANSFER_TYPES = [
    {"name": "from", "type": "address"},
    {"name": "to", "type": "address"},
    {"name": "value", "type": "uint256"},
    {"name": "validAfter", "type": "uint256"},
    {"name": "validBefore", "type": "uint256"},
    {"name": "nonce", "type": "bytes32"},
]

# market -> Bankr上のサービス名と入力エンベロープ
_SERVICES = {
    "crypto": {"service": "kcbrain", "asset_field": "assets", "id_field": "symbol"},
    "fx": {"service": "fxbrain", "asset_field": "pairs", "id_field": "pair"},
    "stock": {"service": "ksbrain", "asset_field": "evidence", "id_field": "symbol"},
}


class KurageBrainClient:
    def __init__(self, timeout: int = 300):
        self.timeout = timeout

    # ---- x402 ----

    @staticmethod
    def _wallet_key() -> str:
        key = os.environ.get("KURAGE_X402_WALLET_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "KURAGE_X402_WALLET_KEY is required: Kurage brain APIs are paid per call "
                "via x402 (fund the wallet with Base USDC)")
        return key

    def available(self, market: str) -> bool:
        return market in _SERVICES and bool(os.environ.get("KURAGE_X402_WALLET_KEY", "").strip())

    def _post(self, url, payload, headers):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except Exception:
                data = {"raw": body[:300]}
            return exc.code, data

    def _sign(self, challenge, private_key):
        from eth_account import Account
        from eth_account.messages import encode_typed_data

        acc = next((a for a in (challenge.get("accepts") or []) if a.get("scheme") == "exact"), None)
        if not acc:
            raise RuntimeError("no 'exact' scheme in x402 challenge")
        account = Account.from_key(private_key)
        authorization = {
            "from": account.address,
            "to": acc["payTo"],
            "value": str(acc["maxAmountRequired"]),
            "validAfter": "0",
            "validBefore": str(int(time.time()) + int(acc.get("maxTimeoutSeconds") or 600)),
            "nonce": "0x" + secrets.token_hex(32),
        }
        extra = acc.get("extra") or {}
        full_message = {
            "types": {"EIP712Domain": _EIP712_DOMAIN,
                      "TransferWithAuthorization": _TRANSFER_TYPES},
            "domain": {"name": extra.get("name", "USD Coin"),
                       "version": extra.get("version", "2"),
                       "chainId": 8453, "verifyingContract": acc["asset"]},
            "primaryType": "TransferWithAuthorization",
            "message": authorization,
        }
        signed = Account.sign_message(encode_typed_data(full_message=full_message), private_key)
        signature = signed.signature.hex()
        if not signature.startswith("0x"):
            signature = "0x" + signature
        payment = {"x402Version": challenge.get("x402Version", 1), "scheme": "exact",
                   "network": acc.get("network"),
                   "payload": {"signature": signature, "authorization": authorization}}
        return base64.b64encode(
            json.dumps(payment, separators=(",", ":")).encode("utf-8")).decode("ascii")

    def call(self, market: str, skill_path: str, payload: dict):
        """Bankrの有料スキルを呼ぶ。402なら自動署名して支払い、結果を返す。"""
        cfg = _SERVICES.get(market)
        if not cfg:
            raise ValueError(f"unknown market: {market}")
        url = f"{BANKR_BASE}/{cfg['service']}{skill_path}"
        status, data = self._post(url, payload, {})
        if status == 402:
            status, data = self._post(url, payload, {"X-PAYMENT": self._sign(data, self._wallet_key())})
        if status == 402:
            raise RuntimeError(f"x402 payment rejected (insufficient USDC?): {str(data)[:160]}")
        if status != 200:
            raise RuntimeError(f"bankr {status}: {str(data)[:160]}")
        return data.get("response") if isinstance(data.get("response"), dict) else data

    # ---- skills ----

    def opportunity_ranking(self, market: str, assets: list[dict], timeframe: str = "H1") -> dict:
        """銘柄一覧をまとめて1回で判定(1コール=1支払い)。"""
        cfg = _SERVICES[market]
        return self.call(market, "/market/opportunity-ranking",
                         {"timeframe": timeframe, cfg["asset_field"]: assets})

    def stock_analyze(self, symbol: str, evidence: list[dict]) -> dict:
        """ksbrain: 証拠つきフル分析(ステートレス。1コール=1支払い)。"""
        return self.call("stock", "/analyze/full", {"symbol": symbol, "evidence": evidence})
