# coding: utf-8
"""日本語出力に調整したLLMバックエンド.

環境変数だけで切り替える:
  FINROBOT_JP_LLM=deepseek (既定) | ollama | openai
  - deepseek: DEEPSEEK_API_KEY, DEEPSEEK_MODEL (既定 deepseek-chat)。x402課金レールと同じ系列
  - ollama:   OLLAMA_URL (既定 http://127.0.0.1:11434), OLLAMA_MODEL (必須)
              思考型モデル対策として /api/generate に think:false を明示する
  - openai:   OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL (OpenAI互換なら何でも)
"""
from __future__ import annotations

import json
import os
import urllib.request


class JapaneseLLM:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or os.environ.get("FINROBOT_JP_LLM", "deepseek")).lower()

    def complete(self, prompt: str, system: str = "", max_tokens: int = 8192,
                 temperature: float = 0.2, timeout: int = 300) -> str:
        if self.provider == "ollama":
            return self._ollama(prompt, system, max_tokens, temperature, timeout)
        return self._openai_compat(prompt, system, max_tokens, temperature, timeout)

    def _ollama(self, prompt, system, max_tokens, temperature, timeout) -> str:
        url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        model = os.environ.get("OLLAMA_MODEL", "")
        if not model:
            raise RuntimeError("OLLAMA_MODEL is required for provider=ollama")
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            # 思考型モデルでは必須: 無効化しないと隠れ推論トークンが
            # num_predictを食い潰し、responseが空になる
            "think": False,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        req = urllib.request.Request(
            f"{url}/api/generate",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("response") or "").strip()

    def _openai_compat(self, prompt, system, max_tokens, temperature, timeout) -> str:
        if self.provider == "deepseek":
            base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            key = os.environ.get("DEEPSEEK_API_KEY", "")
            model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        else:
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            key = os.environ.get("OPENAI_API_KEY", "")
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        if not key:
            raise RuntimeError(f"API key not set for provider={self.provider}")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model, "messages": messages,
                   "max_tokens": max_tokens, "temperature": temperature}
        req = urllib.request.Request(
            f"{base.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        message = data["choices"][0]["message"]
        content = (message.get("content") or "").strip()
        if not content and message.get("reasoning_content"):
            # 推論型モデル(DeepSeek等)はmax_tokensが小さいと推論だけで枠を使い切り
            # contentが空になる。無言で空を返さず原因が分かるエラーにする
            raise RuntimeError(
                "empty content from reasoning model; increase max_tokens "
                f"(finish_reason={data['choices'][0].get('finish_reason')})")
        return content
