"""用当前表单里的地址和密钥做一次最短请求，确认接口能通。"""

import time

import requests

from config.config import load_model_config
from tools.LLM.custom import APIUtils


def probe_model(model_type, base_url, model, api_key, jev_key="", include_jev=False):
    checks = []
    if model_type == "deepseek":
        checks.append(("DeepSeek", lambda: _openai_chat(
            base_url, model, api_key, extra={"thinking": {"type": "disabled"}}
        )))
        if include_jev:
            jev = load_model_config("jev")
            checks.append(("JEV", lambda: _jev(
                jev.get("base_url") or "https://api.typesafe.ai/v1",
                jev.get("model") or "jev-latest",
                jev_key,
            )))
    else:
        checks.append(("自定义模型", lambda: _custom(base_url, model, api_key)))

    results = []
    for name, check in checks:
        started = time.perf_counter()
        try:
            detail = check()
            ok = True
        except Exception as exc:
            detail = _safe_error(exc, api_key, jev_key)
            ok = False
        results.append({
            "name": name,
            "ok": ok,
            "detail": detail,
            "ms": round((time.perf_counter() - started) * 1000),
        })
    return results


def _openai_chat(base_url, model, api_key, extra=None):
    if not api_key:
        raise Exception("未填写 API Key")
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "回复一个字：通"}],
    }
    if extra:
        body.update(extra)
    payload = _post(url, api_key, body)
    return _chat_text(payload)


def _custom(base_url, model, api_key):
    if "dashscope" in base_url.lower() or "aliyuncs" in base_url.lower():
        url = base_url.rstrip("/") + "/compatible-mode/v1/chat/completions"
        payload = _post(url, api_key, {
            "model": model,
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "回复一个字：通"}],
        })
        return _chat_text(payload)
    url = APIUtils.format_api_url(base_url)
    payload = _post(url, api_key, {
        "model": model,
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "回复一个字：通"}],
    })
    return _chat_text(payload)


def _jev(base_url, model, api_key):
    if not api_key:
        raise Exception("未填写 JEV API Key")
    url = base_url.rstrip("/") + "/systemone"
    payload = _post(url, api_key, {
        "model": model,
        "state": "连接测试",
        "questions": {
            "ping": {
                "type": "choice",
                "instructions": "选择 ping",
                "criteria": {"ping": "连接正常", "fail": "连接失败"},
            }
        },
    })
    try:
        choice = payload["answers"]["ping"]["choice"]
    except (KeyError, TypeError) as exc:
        raise Exception("响应里没有选项") from exc
    return f"choice={choice}"


def _post(url, api_key, body):
    if not api_key:
        raise Exception("未填写 API Key")
    response = _request(
        "POST",
        url,
        api_key,
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    return response.json()


def _request(method, url, secret, **kwargs):
    try:
        response = requests.request(method, url, timeout=20, **kwargs)
        response.raise_for_status()
        return response
    except requests.Timeout as exc:
        raise Exception("请求超时") from exc
    except requests.ConnectionError as exc:
        raise Exception("无法连接服务器") from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        body = ""
        if exc.response is not None:
            body = (exc.response.text or "").replace("\n", " ")[:160]
        raise Exception(_safe_error(f"HTTP {status} {body}".strip(), secret)) from exc
    except requests.RequestException as exc:
        raise Exception(_safe_error(exc, secret)) from exc


def _chat_text(payload):
    try:
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise Exception("响应里没有文本") from exc
    text = (text or "").strip().replace("\n", " ")
    if not text:
        raise Exception("模型返回了空内容")
    return text[:40]


def _safe_error(exc, *secrets):
    text = str(exc).replace("\n", " ")
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text[:300]
