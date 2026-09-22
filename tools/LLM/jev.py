import os

import requests

from config.config import load_api_key, load_model_config


class JevAPI:
    """TypeSafe JEV：在给定选项里选出一个序号。"""

    def __init__(self):
        config = load_model_config('jev')
        self.base_url = (config.get('base_url') or 'https://api.typesafe.ai/v1').rstrip('/')
        self.model = config.get('model') or os.environ.get('TYPESAFE_MODEL') or 'jev-latest'
        self.api_key = load_api_key('jev') or os.environ.get('TYPESAFE_API_KEY', '')

    def choose(self, brief, timeout=25):
        if not self.api_key:
            raise Exception("JEV API Key 未配置，请在设置里填写 TypeSafe API Key")

        criteria = {}
        structured = []
        for option in brief.get('options') or []:
            index = str(option.get('index'))
            text = option.get('text') or ''
            note = option.get('note') or ''
            criteria[index] = f"{text}\n{note}".strip() if note else text
            structured.append({"index": index, "text": text, "note": note})
        if not criteria:
            raise Exception("没有可提交给 JEV 的选项")

        context = brief.get("context") or ""
        instructions = "结合上下文和每个选项的说明，选出正确选项的序号。只能选择给出的序号。"
        if context:
            instructions = f"上下文：{context}\n{instructions}"

        body = {
            "model": self.model,
            "state": {
                "question": brief.get("question", ""),
                "context": context,
                "options": structured,
            },
            "questions": {
                "option": {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": criteria,
                }
            },
        }
        try:
            response = requests.post(
                f"{self.base_url}/systemone",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=body,
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            answer = payload["answers"]["option"]
            choice = str(answer["choice"]).strip()
        except requests.exceptions.RequestException as e:
            raise Exception(f"JEV API request failed: {str(e)}") from e
        except (KeyError, TypeError, ValueError) as e:
            raise Exception(f"JEV 没有返回有效选项: {str(e)}") from e

        if choice not in criteria:
            raise Exception(f"JEV 返回了选项之外的序号: {choice}")
        return choice, {
            "confidence": answer.get("confidence"),
            "probabilities": answer.get("probabilities") or {},
            "model": payload.get("model", self.model),
        }
