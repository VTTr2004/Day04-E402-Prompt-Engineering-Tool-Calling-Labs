from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def normalize_content(raw: Any) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        text = raw.get("text")
        return str(text).strip() if text is not None else str(raw).strip()
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            text = normalize_content(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    return str(raw).strip()

def parse_google_api_keys(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [key.strip() for key in raw.split(",") if key.strip()]


def google_key_has_quota(api_key: str, model_name: str) -> bool:
    model = model_name.removeprefix("models/")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{urllib.parse.quote(model)}:generateContent"
        f"?key={urllib.parse.quote(api_key)}"
    )

    payload = json.dumps(
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "."}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 1,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15):
            return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")

        if exc.code == 429 or "RESOURCE_EXHAUSTED" in body:
            return False

        # Key sai, model sai, hoặc lỗi quyền thì không nên dùng key này.
        if exc.code in {400, 401, 403}:
            return False

        raise
    except urllib.error.URLError:
        # Lỗi mạng không phải quota, để app biết mà fail rõ ràng.
        raise


def iter_google_api_keys_with_quota(model_name: str):
    keys = parse_google_api_keys(os.getenv("GOOGLE_API_KEY"))

    if not keys:
        raise ValueError("GOOGLE_API_KEY is empty.")

    for key in keys:
        if google_key_has_quota(key, model_name):
            yield key


def pick_google_api_key_with_quota(model_name: str) -> str:
    for key in iter_google_api_keys_with_quota(model_name):
        return key
    raise RuntimeError("All GOOGLE_API_KEY values are out of quota or unusable.")


def is_google_quota_error(error: BaseException) -> bool:
    error_text = str(error)
    error_name = error.__class__.__name__
    return (
        "RESOURCE_EXHAUSTED" in error_text
        or "429" in error_text
        or error_name == "ResourceExhausted"
    )


class QuotaCheckedGoogleChatModel:
    def __init__(self, *, model_name: str, temperature: float):
        self.model_name = model_name
        self.temperature = temperature

    def _build_model(self, api_key: str):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=api_key,
        )

    def _call_with_quota_checked_key(self, call: Callable[[Any], Any]) -> Any:
        last_error: BaseException | None = None

        for api_key in iter_google_api_keys_with_quota(self.model_name):
            model = self._build_model(api_key)
            try:
                return call(model)
            except BaseException as exc:
                if not is_google_quota_error(exc):
                    raise
                last_error = exc

        if last_error is not None:
            raise RuntimeError("All GOOGLE_API_KEY values ran out of quota during the LLM call.") from last_error

        raise RuntimeError("All GOOGLE_API_KEY values are out of quota or unusable.")

    async def _acall_with_quota_checked_key(self, call: Callable[[Any], Any]) -> Any:
        last_error: BaseException | None = None

        for api_key in iter_google_api_keys_with_quota(self.model_name):
            model = self._build_model(api_key)
            try:
                return await call(model)
            except BaseException as exc:
                if not is_google_quota_error(exc):
                    raise
                last_error = exc

        if last_error is not None:
            raise RuntimeError("All GOOGLE_API_KEY values ran out of quota during the LLM call.") from last_error

        raise RuntimeError("All GOOGLE_API_KEY values are out of quota or unusable.")

    def invoke(self, *args, **kwargs):
        return self._call_with_quota_checked_key(lambda model: model.invoke(*args, **kwargs))

    async def ainvoke(self, *args, **kwargs):
        return await self._acall_with_quota_checked_key(lambda model: model.ainvoke(*args, **kwargs))

    def stream(self, *args, **kwargs):
        def stream_with_fallback():
            last_error: BaseException | None = None

            for api_key in iter_google_api_keys_with_quota(self.model_name):
                model = self._build_model(api_key)
                try:
                    yield from model.stream(*args, **kwargs)
                    return
                except BaseException as exc:
                    if not is_google_quota_error(exc):
                        raise
                    last_error = exc

            if last_error is not None:
                raise RuntimeError("All GOOGLE_API_KEY values ran out of quota during the LLM call.") from last_error

            raise RuntimeError("All GOOGLE_API_KEY values are out of quota or unusable.")

        return stream_with_fallback()

    def bind_tools(self, *args, **kwargs):
        return QuotaCheckedGoogleBoundChatModel(
            parent=self,
            bind_args=args,
            bind_kwargs=kwargs,
        )

    def __getattr__(self, name: str):
        api_key = pick_google_api_key_with_quota(self.model_name)
        return getattr(self._build_model(api_key), name)


class QuotaCheckedGoogleBoundChatModel:
    def __init__(self, *, parent: QuotaCheckedGoogleChatModel, bind_args, bind_kwargs):
        self.parent = parent
        self.bind_args = bind_args
        self.bind_kwargs = bind_kwargs

    def _bind_model(self, model):
        return model.bind_tools(*self.bind_args, **self.bind_kwargs)

    def invoke(self, *args, **kwargs):
        return self.parent._call_with_quota_checked_key(
            lambda model: self._bind_model(model).invoke(*args, **kwargs)
        )

    async def ainvoke(self, *args, **kwargs):
        return await self.parent._acall_with_quota_checked_key(
            lambda model: self._bind_model(model).ainvoke(*args, **kwargs)
        )

    def stream(self, *args, **kwargs):
        def stream_with_fallback():
            last_error: BaseException | None = None

            for api_key in iter_google_api_keys_with_quota(self.parent.model_name):
                model = self._bind_model(self.parent._build_model(api_key))
                try:
                    yield from model.stream(*args, **kwargs)
                    return
                except BaseException as exc:
                    if not is_google_quota_error(exc):
                        raise
                    last_error = exc

            if last_error is not None:
                raise RuntimeError("All GOOGLE_API_KEY values ran out of quota during the LLM call.") from last_error

            raise RuntimeError("All GOOGLE_API_KEY values are out of quota or unusable.")

        return stream_with_fallback()

    def __getattr__(self, name: str):
        api_key = pick_google_api_key_with_quota(self.parent.model_name)
        return getattr(self._bind_model(self.parent._build_model(api_key)), name)


def build_chat_model(
    *,
    provider: str = "google",
    model_name: str | None = None,
    temperature: float = 0.0,
):
    if provider == "google":
        selected_model = model_name or os.getenv("LLM_MODEL", "gemini-2.5-flash")

        return QuotaCheckedGoogleChatModel(
            model_name=selected_model,
            temperature=temperature,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model_name or os.getenv("OLLAMA_MODEL", "qwen3.5:3b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
        )
    raise ValueError("This lab supports only the `google` and `ollama` providers.")


def extract_json_object(raw: Any) -> dict[str, Any]:
    text = normalize_content(raw)
    if "```" in text:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if blocks:
            text = blocks[0].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output.")
    return json.loads(text[start : end + 1])


def judge_answer_with_llm(
    *,
    query: str,
    answer: str,
    rubric: str,
    provider: str,
    model_name: str | None = None,
) -> dict[str, Any]:
    model = build_chat_model(provider=provider, model_name=model_name, temperature=0.0)
    prompt = f"""
You are grading a student order-agent answer.
Return JSON only with:
- score: integer from 0 to 10
- verdict: short string
- feedback: short list of strings

Rubric:
{rubric}

User query:
{query}

Student answer:
{answer}
""".strip()
    payload = extract_json_object(model.invoke(prompt).content)
    score = max(0, min(10, int(payload.get("score", 0))))
    return {
        "score": score,
        "verdict": str(payload.get("verdict", "")).strip(),
        "feedback": [str(item).strip() for item in payload.get("feedback", []) if str(item).strip()],
    }
