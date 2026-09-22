import json
import re

from tools.LLM.deepseek import DeepSeekAPI
from tools.LLM.jev import JevAPI
from tools.logger import logger


def canonical_options(answers):
    options = []
    for index, answer in enumerate(answers or [], 1):
        text = answer.get('ans_text') if isinstance(answer, dict) else str(answer)
        options.append({"index": str(index), "text": text or ""})
    return options


def parse_brief(raw):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("梳理结果不是 JSON 对象")
    return data


def merge_brief(question, canonical, parsed):
    notes = {}
    by_text = {}
    for option in parsed.get("options") or []:
        if not isinstance(option, dict):
            continue
        note = str(option.get("note") or "")
        if option.get("index") is not None:
            notes[str(option["index"])] = note
        if option.get("text"):
            by_text[str(option["text"]).strip()] = note

    options = []
    for item in canonical:
        note = notes.get(item["index"]) or by_text.get(item["text"].strip(), "")
        options.append({**item, "note": note})

    facts = parsed.get("facts") if isinstance(parsed.get("facts"), list) else []
    context = str(parsed.get("context") or "").strip()
    fact_lines = [str(fact) for fact in facts if str(fact).strip()]
    if context and context not in fact_lines:
        fact_lines.insert(0, context)
    return {
        "question": str(parsed.get("question") or question or ""),
        "context": context,
        "facts": fact_lines,
        "options": options,
    }


def decide(question, answers):
    """DeepSeek 梳理题目，JEV 选出选项序号。"""
    canonical = canonical_options(answers)
    brief = merge_brief(question, canonical, parse_brief(DeepSeekAPI().brief(question, canonical)))
    logger.info(f"DeepSeek梳理: {brief['question']}")
    if brief.get("context"):
        logger.info(f"DeepSeek上下文: {brief['context']}")
    for option in brief["options"]:
        note = option.get("note") or ""
        if note:
            logger.info(f"选项{option['index']} {option['text']}: {note}")

    choice, meta = JevAPI().choose(brief)
    logger.info("JEV选出选项: {} 置信度: {}".format(choice, meta.get("confidence")))
    probabilities = meta.get("probabilities") or {}
    if probabilities:
        logger.info("JEV概率: " + ", ".join(f"{key}={value}" for key, value in probabilities.items()))
    return choice
