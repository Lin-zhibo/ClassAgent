"""交互式教学 Shell：当前仅完整实现“测验”模式。"""

from __future__ import annotations

import csv
import json
import random
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from agent import LLMClient
from prompt import (
    QUIZ_EVALUATION_SYSTEM_PROMPT,
    QUIZ_SUMMARY_SYSTEM_PROMPT,
    build_quiz_evaluation_user_prompt,
    build_quiz_summary_user_prompt,
)

PROJECT_ROOT = Path(__file__).resolve().parent
QUESTION_BANK_PATH = PROJECT_ROOT / "data" / "questions.CSV"
QUIT_WORDS = {"q", "quit", "exit", "退出"}


@dataclass(frozen=True)
class QuizQuestion:
    """题库中的单题数据结构。"""

    poet: str
    poem: str
    question: str
    answer: str


@dataclass
class EvaluationResult:
    """作答评估结果。"""

    result: str
    feedback: str
    hint: str
    source: str


def load_question_bank(csv_path: Path = QUESTION_BANK_PATH) -> list[QuizQuestion]:
    """读取 CSV 题库并转换成结构化对象列表。"""
    if not csv_path.exists():
        raise FileNotFoundError(f"未找到题库文件: {csv_path}")

    questions: list[QuizQuestion] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            poet = str(row.get("诗人", "")).strip()
            poem = str(row.get("作品", "")).strip()
            question = str(row.get("问题", "")).strip()
            answer = str(row.get("答案", "")).strip()
            if not poem or not question or not answer:
                continue
            questions.append(
                QuizQuestion(
                    poet=poet,
                    poem=poem,
                    question=question,
                    answer=answer,
                )
            )

    if not questions:
        raise ValueError("题库为空，无法开始测验。")

    return questions


def get_available_poems(question_bank: list[QuizQuestion]) -> list[str]:
    """从题库中提取可选诗词。"""
    return sorted({question.poem for question in question_bank})


def choose_poem(poems: list[str]) -> str | None:
    """引导用户选择诗词，支持编号或直接输入诗名。"""
    print("\n可选诗词：")
    for index, poem in enumerate(poems, start=1):
        print(f"{index}. {poem}")

    while True:
        user_input = input("请选择诗词（输入编号/诗名，输入 q 退出）: ").strip()
        if user_input.lower() in QUIT_WORDS:
            return None

        if user_input.isdigit():
            selected_index = int(user_input)
            if 1 <= selected_index <= len(poems):
                return poems[selected_index - 1]

        if user_input in poems:
            return user_input

        print("输入无效，请重新选择。")


def show_mode_menu(poem_name: str) -> str:
    """展示学习模式菜单并获取用户输入。"""
    print(f"\n当前诗词：{poem_name}")
    print("请选择学习模式：")
    print("1. 背诵")
    print("2. 理解")
    print("3. 赏析")
    print("4. 测验")
    print("8. 重新选择诗词")
    print("0. 退出程序")
    return input("请输入模式编号: ").strip()


def handle_recitation(poem_name: str) -> None:
    """背诵模式接口占位。"""
    print(f"[{poem_name}] 背诵功能正在开发中")


def handle_understanding(poem_name: str) -> None:
    """理解模式接口占位。"""
    print(f"[{poem_name}] 理解功能正在开发中")


def handle_appreciation(poem_name: str) -> None:
    """赏析模式接口占位。"""
    print(f"[{poem_name}] 赏析功能正在开发中")


def load_mock_user_profile() -> dict[str, str]:
    """读取用户画像占位实现。"""
    return {
        "学习阶段": "复习",
        "理解能力": "弱",
        "背诵能力": "中",
    }


def decide_teaching_strategy(profile: dict[str, str]) -> str:
    """根据用户画像决定教学策略。"""
    if profile.get("学习阶段") == "新学":
        return "先讲解"
    if profile.get("学习阶段") == "复习":
        return "先抽查"
    if profile.get("理解能力") == "弱":
        return "先解释+追问"
    if profile.get("背诵能力") == "弱":
        return "先分句跟读"
    return "先抽查"


def select_questions_by_strategy(
    all_questions: list[QuizQuestion],
    count: int,
    strategy: str,
) -> list[QuizQuestion]:
    """按策略选择本轮测验题目。"""
    shuffled = all_questions[:]
    random.shuffle(shuffled)

    if strategy == "先讲解":
        shuffled.sort(key=lambda item: len(item.answer))
    elif strategy == "先解释+追问":
        shuffled.sort(key=lambda item: len(item.question))

    return shuffled[:count]


def ask_quiz_count(max_count: int) -> int:
    """获取本轮测验题数。"""
    default_count = min(5, max_count)
    user_input = input(f"请输入测验题数（1-{max_count}，默认 {default_count}）: ").strip()
    if not user_input:
        return default_count

    if user_input.isdigit():
        count = int(user_input)
        if 1 <= count <= max_count:
            return count

    print(f"输入无效，已使用默认题数 {default_count}。")
    return default_count


def try_create_llm_client() -> LLMClient | None:
    """尝试初始化 LLM 客户端，失败则返回 None。"""
    try:
        return LLMClient.from_config()
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"LLM 初始化失败，将自动切换规则判定: {exc}")
        return None


def extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """从文本中提取首个 JSON 对象。"""
    matched = re.search(r"\{[\s\S]*\}", raw_text)
    if not matched:
        return None

    try:
        data = json.loads(matched.group(0))
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    return data


def normalize_text(text: str) -> str:
    """归一化文本，便于做相似度和命中判断。"""
    return re.sub(r"[\s，。！？；：、“”‘’《》【】（）()、,!?;:\-_'\".]+", "", text).lower()


def extract_keywords(standard_answer: str) -> list[str]:
    """从标准答案中提取关键词片段。"""
    parts = re.split(r"[，。！？；：、“”‘’《》【】（）()、,!?;:\s]+", standard_answer)
    return [part.strip() for part in parts if len(part.strip()) >= 2][:10]


def build_simple_hint(standard_answer: str) -> str:
    """构造本地判定时的简短提示。"""
    keywords = extract_keywords(standard_answer)
    if keywords:
        return f"提示：可先回答关键词“{keywords[0]}”。"
    return "提示：先描述诗句核心意象或主旨。"


def evaluate_answer_with_rules(standard_answer: str, student_answer: str) -> EvaluationResult:
    """规则判定答案质量，作为无模型或模型失败时的兜底。"""
    if not student_answer.strip():
        return EvaluationResult(
            result="incorrect",
            feedback="你还没有给出有效作答。",
            hint=build_simple_hint(standard_answer),
            source="rules",
        )

    standard_norm = normalize_text(standard_answer)
    student_norm = normalize_text(student_answer)

    similarity = 0.0
    if standard_norm and student_norm:
        similarity = SequenceMatcher(None, student_norm, standard_norm).ratio()

    keywords = extract_keywords(standard_answer)
    hit_count = sum(1 for keyword in keywords if keyword in student_answer)
    hit_ratio = hit_count / len(keywords) if keywords else 0.0
    direct_hit = bool(student_norm and standard_norm and student_norm in standard_norm)

    if direct_hit or similarity >= 0.62 or hit_ratio >= 0.70:
        return EvaluationResult(
            result="correct",
            feedback="回答准确，核心信息完整，继续保持。",
            hint="下一题继续关注关键词与诗句主旨。",
            source="rules",
        )

    if similarity >= 0.35 or hit_ratio >= 0.30:
        return EvaluationResult(
            result="partial",
            feedback="回答命中了一部分要点，但还不够完整。",
            hint=build_simple_hint(standard_answer),
            source="rules",
        )

    return EvaluationResult(
        result="incorrect",
        feedback="这次回答偏离了题目重点。",
        hint=build_simple_hint(standard_answer),
        source="rules",
    )


def evaluate_answer_with_llm(
    client: LLMClient,
    poem_name: str,
    question: str,
    standard_answer: str,
    student_answer: str,
) -> EvaluationResult | None:
    """使用 LLM 判定答案，失败时返回 None。"""
    user_prompt = build_quiz_evaluation_user_prompt(
        poem_name=poem_name,
        question=question,
        standard_answer=standard_answer,
        student_answer=student_answer,
    )
    try:
        raw_reply = client.chat(
            user_message=user_prompt,
            system_message=QUIZ_EVALUATION_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=300,
        )
    except Exception:
        return None

    data = extract_json_object(raw_reply)
    if data is None:
        return None

    result = str(data.get("result", "")).strip().lower()
    if result not in {"correct", "partial", "incorrect"}:
        return None

    feedback = str(data.get("feedback", "")).strip() or "已完成作答判定。"
    hint = str(data.get("hint", "")).strip() or build_simple_hint(standard_answer)

    return EvaluationResult(
        result=result,
        feedback=feedback,
        hint=hint,
        source="llm",
    )


def evaluate_answer(
    client: LLMClient | None,
    poem_name: str,
    question: str,
    standard_answer: str,
    student_answer: str,
) -> EvaluationResult:
    """优先使用 LLM 判定，失败后回退规则判定。"""
    if client is not None:
        llm_result = evaluate_answer_with_llm(
            client=client,
            poem_name=poem_name,
            question=question,
            standard_answer=standard_answer,
            student_answer=student_answer,
        )
        if llm_result is not None:
            return llm_result

    return evaluate_answer_with_rules(
        standard_answer=standard_answer,
        student_answer=student_answer,
    )


def build_easy_explanation(standard_answer: str) -> str:
    """在“不会”分支提供一个更短的解释文本。"""
    sentence = re.split(r"[。；;]", standard_answer)[0].strip()
    if len(sentence) > 50:
        sentence = sentence[:50] + "..."
    return sentence or "先回忆诗句关键词，再组织完整表达。"


def run_single_quiz_question(
    client: LLMClient | None,
    poem_name: str,
    question_item: QuizQuestion,
    index: int,
    total: int,
) -> tuple[bool, dict[str, Any] | None]:
    """执行单题测验，返回是否主动退出与作答记录。"""
    print(f"\n第 {index}/{total} 题")
    print(f"题目：{question_item.question}")

    first_answer = input("你的回答（输入 q 退出本轮）: ").strip()
    if first_answer.lower() in QUIT_WORDS:
        return True, None

    first_eval = evaluate_answer(
        client=client,
        poem_name=poem_name,
        question=question_item.question,
        standard_answer=question_item.answer,
        student_answer=first_answer,
    )

    print(f"判定：{first_eval.result}（来源: {first_eval.source}）")
    print(f"反馈：{first_eval.feedback}")

    final_eval = first_eval
    final_answer = first_answer
    score = 1.0 if first_eval.result == "correct" else 0.0

    if first_eval.result == "partial":
        print(f"提示后再答：{first_eval.hint}")
    elif first_eval.result == "incorrect":
        print(f"降低难度重讲：{build_easy_explanation(question_item.answer)}")

    if first_eval.result in {"partial", "incorrect"}:
        retry_answer = input("请再试一次（输入 skip 跳过本题）: ").strip()
        if retry_answer.lower() in QUIT_WORDS:
            return True, None

        if retry_answer.lower() != "skip" and retry_answer:
            second_eval = evaluate_answer(
                client=client,
                poem_name=poem_name,
                question=question_item.question,
                standard_answer=question_item.answer,
                student_answer=retry_answer,
            )
            final_eval = second_eval
            final_answer = retry_answer

            print(f"二次判定：{second_eval.result}（来源: {second_eval.source}）")
            print(f"二次反馈：{second_eval.feedback}")

            if first_eval.result == "partial" and second_eval.result == "correct":
                score = 0.8
            elif first_eval.result == "incorrect" and second_eval.result == "correct":
                score = 0.6
            elif second_eval.result == "partial":
                score = 0.4
            else:
                score = 0.0
        else:
            score = 0.4 if first_eval.result == "partial" else 0.0

    print(f"参考答案：{question_item.answer}")

    record: dict[str, Any] = {
        "question": question_item.question,
        "standard_answer": question_item.answer,
        "student_answer": final_answer,
        "first_result": first_eval.result,
        "final_result": final_eval.result,
        "score": round(score, 2),
    }
    return False, record


def build_local_summary(poem_name: str, records: list[dict[str, Any]]) -> str:
    """本地生成学习总结。"""
    total_count = len(records)
    total_score = sum(float(record.get("score", 0.0)) for record in records)
    accuracy = (total_score / total_count) * 100 if total_count else 0.0

    correct_count = sum(1 for record in records if record.get("final_result") == "correct")
    partial_count = sum(1 for record in records if record.get("final_result") == "partial")
    incorrect_count = total_count - correct_count - partial_count

    weak_questions = [
        str(record.get("question", ""))
        for record in records
        if record.get("final_result") != "correct"
    ][:2]

    lines = [
        f"《{poem_name}》测验完成：{total_count} 题。",
        f"综合得分：{total_score:.1f}/{total_count:.1f}（{accuracy:.1f}%）。",
        f"结果分布：答对 {correct_count} 题，半对 {partial_count} 题，不会 {incorrect_count} 题。",
    ]
    if weak_questions:
        lines.append("建议复习题目：")
        for index, question in enumerate(weak_questions, start=1):
            lines.append(f"{index}. {question}")

    return "\n".join(lines)


def build_llm_summary(
    client: LLMClient | None,
    poem_name: str,
    records: list[dict[str, Any]],
) -> str | None:
    """使用 LLM 生成学习总结，失败返回 None。"""
    if client is None:
        return None

    user_prompt = build_quiz_summary_user_prompt(poem_name=poem_name, records=records)
    try:
        return client.chat(
            user_message=user_prompt,
            system_message=QUIZ_SUMMARY_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=220,
        )
    except Exception:
        return None


def handle_quiz(poem_name: str, question_bank: list[QuizQuestion]) -> None:
    """测验模式主流程。"""
    poem_questions = [question for question in question_bank if question.poem == poem_name]
    if not poem_questions:
        print(f"《{poem_name}》暂无可用题目。")
        return

    profile = load_mock_user_profile()
    strategy = decide_teaching_strategy(profile)
    print(f"\n已读取用户画像：{profile}")
    print(f"当前教学策略：{strategy}")

    quiz_count = ask_quiz_count(max_count=len(poem_questions))
    selected_questions = select_questions_by_strategy(
        all_questions=poem_questions,
        count=quiz_count,
        strategy=strategy,
    )

    client = try_create_llm_client()
    if client is None:
        print("当前使用规则判定模式。")
    else:
        print("已启用 LLM 判题模式。")

    print("测验开始，输入 q 可随时结束本轮。")
    records: list[dict[str, Any]] = []

    for index, question_item in enumerate(selected_questions, start=1):
        should_quit, record = run_single_quiz_question(
            client=client,
            poem_name=poem_name,
            question_item=question_item,
            index=index,
            total=len(selected_questions),
        )
        if record is not None:
            records.append(record)
        if should_quit:
            print("已根据你的输入提前结束本轮测验。")
            break

    if not records:
        print("本轮没有有效作答记录。")
        return

    llm_summary = build_llm_summary(client=client, poem_name=poem_name, records=records)
    summary_text = llm_summary if llm_summary else build_local_summary(poem_name, records)

    print("\n学习总结：")
    print(summary_text)
    print("学习记录保存功能正在开发中")
    print("下一首诗推荐功能正在开发中")


def start_shell() -> None:
    """启动交互式教学 Shell。"""
    question_bank = load_question_bank()
    poems = get_available_poems(question_bank)
    if not poems:
        raise ValueError("未发现可用诗词，请检查题库内容。")

    print("欢迎进入古诗词学习系统。")
    selected_poem = choose_poem(poems)
    if selected_poem is None:
        print("已退出程序。")
        return

    while True:
        mode = show_mode_menu(selected_poem)

        if mode == "0":
            print("感谢使用，再见。")
            return

        if mode == "8":
            new_poem = choose_poem(poems)
            if new_poem is None:
                print("已退出程序。")
                return
            selected_poem = new_poem
            continue

        if mode == "1":
            handle_recitation(selected_poem)
            continue

        if mode == "2":
            handle_understanding(selected_poem)
            continue

        if mode == "3":
            handle_appreciation(selected_poem)
            continue

        if mode == "4":
            handle_quiz(selected_poem, question_bank)
            continue

        print("模式编号无效，请重新输入。")


if __name__ == "__main__":
    start_shell()
