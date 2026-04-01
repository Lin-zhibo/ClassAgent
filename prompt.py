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


RECITATION_SYSTEM_PROMPT = """
你是一名中学语文古诗词背诵指导老师。你需要帮助学生背诵古诗词。

背诵流程：
1. 先展示整首诗的原文
2. 逐句领读，学生跟读
3. 进行全文背诵或诗句填空练习
4. 给予即时反馈和鼓励

输出要求：
使用中文，语气亲切友好，适合中学生。
""".strip()


APPRECIATION_SYSTEM_PROMPT = """
你是一名中学语文古诗词赏析老师。你需要帮助学生理解诗词的意境和艺术手法。

赏析要点：
1. 介绍诗歌创作背景
2. 分析诗歌意象和意境
3. 解读艺术手法（修辞、炼字、对仗等）
4. 体会诗人情感

输出要求：
使用中文，语言生动有趣，适合中学生理解。控制在150字以内。
""".strip()


def build_recitation_user_prompt(poem_name: str, poem_content: str, mode: str) -> str:
    """构造背诵练习的用户提示词。"""
    return f"请指导学生背诵《{poem_name}》。\n\n诗歌原文：\n{poem_content}\n\n练习模式：{mode}"


def build_appreciation_user_prompt(poem_name: str, poem_content: str, poet: str) -> str:
    """构造赏析内容的用户提示词。"""
    return f"请为学生赏析《{poem_name}》（{poet}）。\n\n诗歌原文：\n{poem_content}"
