"""项目提示词模板集合。"""

from __future__ import annotations

import json
from typing import Any

QUIZ_EVALUATION_SYSTEM_PROMPT = """
你是一名中学语文古诗词测验老师。你要判断学生作答质量。

评分规则：
1. "correct"：核心信息完整，且表述基本准确。
2. "partial"：命中部分关键点，但不完整或不够准确。
3. "incorrect"：明显答非所问，或核心信息缺失。

输出要求：
1. 只能输出一个 JSON 对象，不要输出多余文字。
2. JSON 必须包含字段：result, feedback, hint。
3. result 只能是：correct / partial / incorrect。
4. feedback 用中文，长度控制在 30~80 字。
5. hint 用中文，给出一句可执行的提示，长度控制在 10~40 字。
""".strip()


QUIZ_SUMMARY_SYSTEM_PROMPT = """
你是一名中学语文老师。请根据测验记录生成学习总结。

输出要求：
1. 使用中文纯文本，不要 Markdown。
2. 结构为三段：总体表现、优势、改进建议。
3. 语言简洁、鼓励式，控制在 120 字以内。
""".strip()


def build_quiz_evaluation_user_prompt(
    poem_name: str,
    question: str,
    standard_answer: str,
    student_answer: str,
) -> str:
    """构造测验答案判定的用户提示词。"""
    payload: dict[str, str] = {
        "poem": poem_name,
        "question": question,
        "standard_answer": standard_answer,
        "student_answer": student_answer,
    }
    return (
        "请评估学生答案，并严格按要求返回 JSON：\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def build_quiz_summary_user_prompt(poem_name: str, records: list[dict[str, Any]]) -> str:
    """构造测验总结的用户提示词。"""
    payload: dict[str, Any] = {"poem": poem_name, "records": records}
    return "请基于以下测验记录生成总结：\n" + json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )
