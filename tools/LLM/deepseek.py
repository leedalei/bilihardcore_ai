import json
import re

import requests
from typing import Dict, Any, Optional
from config.config import BRIEF_PROMPT, PROMPT, load_model_config, load_api_key
from time import time

# 官方当前模型。拉取失败时先用这份，避免下拉是空的。
CURRENT_MODELS = ("deepseek-flash", "deepseek-v4-pro")
_EFFORT_TIMEOUTS = {"disabled": 30, "low": 45, "high": 75, "max": 100}


def thinking_params(effort):
    """关闭思考，或按轻度、高度、最大开启。返回请求字段和超时秒数。"""
    if effort not in _EFFORT_TIMEOUTS:
        effort = "low"
    if effort == "disabled":
        return {"thinking": {"type": "disabled"}}, _EFFORT_TIMEOUTS[effort]
    return {
        "thinking": {"type": "enabled"},
        "reasoning_effort": effort,
        "max_tokens": 4096,
    }, _EFFORT_TIMEOUTS[effort]


def _json_text(content, reasoning):
    text = str(content or "").strip()
    if text:
        return text
    match = re.search(r"\{.*\}", str(reasoning or ""), re.S)
    return match.group(0).strip() if match else ""


def _option_index(content):
    text = str(content or "").strip()
    if re.fullmatch(r"\d+", text):
        return text
    for line in reversed(text.splitlines()):
        line = line.strip()
        if re.fullmatch(r"\d+", line):
            return line
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def parse_model_ids(payload):
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise Exception("模型列表格式不对")
    ids = []
    for item in data:
        model_id = item.get("id") if isinstance(item, dict) else None
        if isinstance(model_id, str):
            model_id = model_id.strip()
        if model_id and model_id not in ids:
            ids.append(model_id)
    if not ids:
        raise Exception("接口没有返回模型")
    return ids


def list_models(base_url: str, api_key: str, timeout: int = 15):
    """读取 DeepSeek 当前可用模型。GET {base_url}/models。"""
    if not api_key:
        raise Exception("未填写 API Key")
    url = base_url.rstrip("/") + "/models"
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise Exception("读取模型列表超时") from exc
    except requests.ConnectionError as exc:
        raise Exception("无法连接 DeepSeek") from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise Exception(f"读取模型列表失败 HTTP {status}") from exc
    except requests.RequestException as exc:
        message = str(exc).replace(api_key, "***")
        raise Exception(f"读取模型列表失败 {message}") from exc
    return parse_model_ids(response.json())

class DeepSeekAPI:
    def __init__(self):
        # 加载DeepSeek模型配置
        config = load_model_config('deepseek')
        self.base_url = config['base_url']
        self.model = config['model']
        self.api_key = load_api_key('deepseek')
        self.reasoning_effort = config.get('reasoning_effort') or 'low'

    def ask(self, question: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        extra, effort_timeout = thinking_params(self.reasoning_effort)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT.format(time(), question)
                }
            ],
            **extra,
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=effort_timeout if timeout is None else timeout
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"].get("content") or ""
        except requests.exceptions.RequestException as e:
            raise Exception(f"DeepSeek API request failed: {str(e)}")
        choice = _option_index(content)
        if not choice:
            raise Exception("DeepSeek 没有返回选项序号")
        return choice

    def brief(self, question: str, options, timeout: Optional[int] = None) -> str:
        """轻度思考后整理上下文，不返回最终序号。"""
        if not self.api_key:
            raise Exception("DeepSeek API Key 未配置")

        material = json.dumps(
            {"question": question, "options": options},
            ensure_ascii=False,
        )
        extra, effort_timeout = thinking_params(self.reasoning_effort)
        data = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            **extra,
            "messages": [
                {
                    "role": "user",
                    "content": BRIEF_PROMPT.format(time(), material),
                }
            ],
        }
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=data,
                timeout=effort_timeout if timeout is None else timeout,
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            content = _json_text(message.get("content"), message.get("reasoning_content"))
        except requests.exceptions.RequestException as e:
            raise Exception(f"DeepSeek API request failed: {str(e)}") from e
        if not content:
            raise Exception("DeepSeek 没有返回梳理结果")
        return content