# coding: utf-8
"""日本語出力に調整したLLMバックエンド.

環境変数だけで切り替える:
  FINROBOT_JP_LLM=ollama (既定) | deepseek | openai
  - ollama:   OLLAMA_URL (既定 http://127.0.0.1:11434), OLLAMA_MODEL (既定 gemma4:12b-it-qat)
              思考型モデル対策として /api/generate に think:false を明示する
  - deepseek: DEEPSEEK_API_KEY, DEEPSEEK_MODEL (既定 deepseek-chat)
  - openai:   OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL (OpenAI互換なら何でも)
"""
from __future__ import annotations

import json
import os
import urllib.request


class JapaneseLLM:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or os.environ.get("FINROBOT_JP_LLM", "ollama")).lower()

    def complete(self, prompt: str, system: str = "", max_tokens: int = 4096,
                 temperature: float = 0.2, timeout: int = 300) -> str:
        if self.provider == "ollama":
            return self._ollama(prompt, system, max_tokens, temperature, timeout)
        return self._openai_compat(prompt, system, max_tokens, temperature, timeout)

    def _ollama(self, prompt, system, max_tokens, temperature, timeout) -> str:
        url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        model = os.environ.get("OLLAMA_MODEL", "gemma4:12b-it-qat")
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            # 思考型モデル(gemma4等)では必須: 無効化しないと隠れ推論トークンが
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
        return data["choices"][0]["message"]["content"].strip()
