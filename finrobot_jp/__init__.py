# coding: utf-8
"""finrobot_jp — FinRobotの日本語ファースト層.

- llm_ja: 日本語出力に調整したLLMバックエンド (Ollama / DeepSeek / OpenAI互換)
- kbrain: Kurage判断API (kcbrain / kfxbrain / ksbrain) クライアント
- analyst: 日本語マーケットレポート生成

This package is part of a Japanese-first derivative fork built on
FinRobot (Apache 2.0). It is NOT the official FinRobot product.
"""

from .analyst import JapaneseMarketAnalyst
from .llm_ja import JapaneseLLM
from .kbrain import KurageBrainClient

__all__ = ["JapaneseMarketAnalyst", "JapaneseLLM", "KurageBrainClient"]
