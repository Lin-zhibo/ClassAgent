#交互式教学 Shell：支持背诵、理解、赏析、测验四种学习模式。

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
from memoryManager import (
    add_wrong_question,
    get_next_recommended_poem,
    load_wrong_questions,
    save_learning_record,
    update_profile_after_quiz,
)
from prompt import (
    APPRECIATION_SYSTEM_PROMPT,
    QUIZ_EVALUATION_SYSTEM_PROMPT,
    QUIZ_SUMMARY_SYSTEM_PROMPT,
    RECITATION_SYSTEM_PROMPT,
    build_appreciation_user_prompt,
    build_quiz_evaluation_user_prompt,
    build_quiz_summary_user_prompt,
)
from RAG import retrieve

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


def get_poem_content_from_rag(poem_name: str) -> str | None:
    """从 RAG 获取诗歌原文。"""
    results = retrieve(query=f"{poem_name} 原文", poet=None, poem=poem_name, k=3)
    for item in results:
        content = item.get("content", "")
        if "原文" in content or any(char in content for char in "，、。"):
            return content
    return None


def handle_recitation(poem_name: str) -> None:
    """背诵模式主流程：支持整诗背诵和诗句填空。"""
    print(f"\n{'='*50}")
    print(f"📖 开始背诵练习：《{poem_name}》")
    print(f"{'='*50}")

    poem_content = get_poem_content_from_rag(poem_name)

    if not poem_content:
        print(f"提示：暂无《{poem_name}》的原文数据，背诵功能需要诗歌原文支持。")
        print("请确保已导入包含诗歌原文的数据。")
        return

    print("\n【整诗展示】")
    print(poem_content)

    mode_choice = input("\n请选择背诵方式：\n1. 整诗背诵\n2. 诗句填空\n0. 返回\n请输入: ").strip()

    if mode_choice == "1":
        _handle_full_recitation(poem_name, poem_content)
    elif mode_choice == "2":
        _handle_fill_blank(poem_name, poem_content)
    else:
        print("已返回。")


def _handle_full_recitation(poem_name: str, poem_content: str) -> None:
    """整诗背诵：学生尝试背诵全诗。"""
    print("\n【整诗背诵】请尝试背诵整首诗，输入 q 退出：")

    lines = [line.strip() for line in poem_content.replace("，", "，\n").replace("。", "。\n").split("\n") if line.strip()]
    if not lines:
        lines = poem_content.split("\n")

    correct_count = 0
    total_count = len(lines)

    for i, expected_line in enumerate(lines, 1):
        expected_clean = normalize_text(expected_line)
        print(f"\n第 {i}/{total_count} 句: {expected_line[:10]}...")
        user_input = input("请背诵这一句（或输入 q 退出）: ").strip()

        if user_input.lower() in QUIT_WORDS:
            break

        user_clean = normalize_text(user_input)
        similarity = SequenceMatcher(None, user_clean, expected_clean).ratio()

        if similarity >= 0.6:
            print("✓ 正确！")
            correct_count += 1
        elif similarity >= 0.3:
            print(f"△ 大致正确（{similarity:.0%}），参考答案：{expected_line}")
            correct_count += 0.5
        else:
            print(f"✗ 不正确。参考答案：{expected_line}")

    score = (correct_count / total_count * 100) if total_count > 0 else 0
    print(f"\n背诵完成！得分：{correct_count:.1f}/{total_count} ({score:.0f}%)")

    save_learning_record(poem_name=poem_name, mode="背诵", score=correct_count/total_count if total_count > 0 else 0, question_count=total_count)


def _handle_fill_blank(poem_name: str, poem_content: str) -> None:
    """诗句填空：给出上句或下句，让学生补全。"""
    print("\n【诗句填空】根据提示补全诗句：")

    all_lines = [line.strip() for line in poem_content.replace("，", "\n").replace("。", "\n").split("\n") if line.strip()]
    if len(all_lines) < 2:
        print("诗句数量不足，无法进行填空练习。")
        return

    random.shuffle(all_lines)
    questions_to_ask = all_lines[:min(5, len(all_lines))]

    correct = 0
    for i, full_line in enumerate(questions_to_ask, 1):
        mid = len(full_line) // 2
        hint = full_line[:mid] + "..." + full_line[-2:] if len(full_line) > 4 else full_line[:2] + "..."

        print(f"\n第 {i}/{len(questions_to_ask)} 题：")
        print(f"诗句：{hint}")
        user_answer = input("补全诗句: ").strip()

        if user_answer.lower() in QUIT_WORDS:
            break

        similarity = SequenceMatcher(None, normalize_text(user_answer), normalize_text(full_line)).ratio()

        if similarity >= 0.7:
            print("✓ 正确！")
            correct += 1
        else:
            print(f"✗ 参考答案：{full_line}")

    score = correct / len(questions_to_ask) if questions_to_ask else 0
    print(f"\n填空完成！得分：{correct}/{len(questions_to_ask)} ({score*100:.0f}%)")

    save_learning_record(poem_name=poem_name, mode="背诵-填空", score=score, question_count=len(questions_to_ask))


def handle_understanding(poem_name: str) -> None:
    """理解模式：展示诗歌注释和翻译，帮助学生理解诗意。"""
    print(f"\n{'='*50}")
    print(f"📚 开始理解学习：《{poem_name}》")
    print(f"{'='*50}")

    client = try_create_llm_client()

    results = retrieve(query=f"{poem_name} 注释 翻译 理解", poem=poem_name, k=5)

    if results:
        print("\n【诗歌注释与翻译】")
        shown_answers = set()
        for item in results:
            answer = item.get("answer", "")
            if answer and answer not in shown_answers and len(answer) > 5:
                print(f"\n{answer}")
                shown_answers.add(answer)
                if len(shown_answers) >= 4:
                    break

        if client:
            print("\n【AI 助手讲解】")
            try:
                poem_content = results[0].get("content", "") if results else ""
                user_prompt = f"请用通俗易懂的语言，为中学生解释《{poem_name}》的含义：\n{poem_content}"
                explanation = client.chat(
                    user_message=user_prompt,
                    system_message="你是一名中学语文老师，请用简单生动的语言解释古诗词，帮助学生理解诗意。",
                    temperature=0.7,
                    max_tokens=300,
                )
                print(explanation)
            except Exception as e:
                print(f"AI讲解暂时不可用: {e}")
    else:
        print(f"\n暂无《{poem_name}》的详细注释和翻译数据。")
        print("请确保题库中包含相关理解性问题。")

    print("\n【学习检测】")
    practice_choice = input("是否进行理解检测？（输入 y 开始，不输入则返回）: ").strip()
    if practice_choice.lower() == "y":
        _run_understanding_quiz(poem_name, client)

    save_learning_record(poem_name=poem_name, mode="理解", score=1.0, question_count=0)


def _run_understanding_quiz(poem_name: str, client: LLMClient | None) -> None:
    """理解模式下的简单检测。"""
    results = retrieve(query=f"{poem_name} 理解 诗意 主旨", poem=poem_name, k=3)

    if not results:
        print("没有找到相关的理解性问题。")
        return

    question_item = results[0]
    question = question_item.get("question", "")
    answer = question_item.get("answer", "")

    print(f"\n理解检测：{question}")
    user_answer = input("你的回答: ").strip()

    if user_answer.lower() in QUIT_WORDS:
        return

    eval_result = evaluate_answer(client, poem_name, question, answer, user_answer)
    print(f"\n判定：{eval_result.result}")
    print(f"反馈：{eval_result.feedback}")
    print(f"参考答案：{answer}")


def handle_appreciation(poem_name: str) -> None:
    """赏析模式：展示诗歌创作背景、艺术手法、意境赏析。"""
    print(f"\n{'='*50}")
    print(f"✨ 开始赏析学习：《{poem_name}》")
    print(f"{'='*50}")

    client = try_create_llm_client()

    results = retrieve(query=f"{poem_name} 赏析 意境 艺术手法", poem=poem_name, k=5)

    if results:
        print("\n【赏析要点】")
        shown_content = set()
        for item in results:
            content = item.get("content", "")
            answer = item.get("answer", "")

            if answer and answer not in shown_content and len(answer) > 10:
                if any(kw in answer for kw in ["赏析", "意境", "艺术", "情感", "手法", "名句"]):
                    print(f"\n{answer}")
                    shown_content.add(answer)

        if client:
            print("\n【AI 赏析】")
            try:
                poem_info = "\n".join([item.get("content", "")[:200] for item in results[:2]])
                user_prompt = build_appreciation_user_prompt(
                    poem_name=poem_name,
                    poem_content=poem_info,
                    poet=results[0].get("poet", "未知")
                )
                appreciation = client.chat(
                    user_message=user_prompt,
                    system_message=APPRECIATION_SYSTEM_PROMPT,
                    temperature=0.7,
                    max_tokens=300,
                )
                print(appreciation)
            except Exception:
                pass
    else:
        if client:
            print("\n【AI 赏析】")
            try:
                user_prompt = f"请为中学生赏析《{poem_name}》，包括创作背景、意象分析、艺术手法、情感体会。"
                appreciation = client.chat(
                    user_message=user_prompt,
                    system_message=APPRECIATION_SYSTEM_PROMPT,
                    temperature=0.7,
                    max_tokens=300,
                )
                print(appreciation)
            except Exception:
                print(f"暂无《{poem_name}》的赏析数据，AI赏析暂时不可用。")
        else:
            print(f"暂无《{poem_name}》的赏析数据。")

    print("\n【名句赏析练习】")
    _practice_famous_line(poem_name, client)

    save_learning_record(poem_name=poem_name, mode="赏析", score=1.0, question_count=0)


def _practice_famous_line(poem_name: str, client: LLMClient | None) -> None:
    """名句赏析练习。"""
    results = retrieve(query=f"{poem_name} 名句 赏析", poem=poem_name, k=3)

    famous_line_keywords = ["大漠孤烟直", "长河落日圆", "海内存知己", "天涯若比邻", "春风得意", "一日看尽"]

    for item in results:
        answer = item.get("answer", "")
        if any(kw in answer for kw in famous_line_keywords):
            question = item.get("question", "")
            print(f"\n题目：{question}")
            print(f"参考赏析：{answer[:150]}...")
            break
    else:
        print("暂无名句赏析练习数据。")


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
    consecutive_errors = 0

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

            if record.get("final_result") == "incorrect":
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    print(f"\n⚠️ 已连续错误3次，自动记录到错题本。")
                    add_wrong_question(
                        poem_name=poem_name,
                        poet=question_item.poet,
                        question=question_item.question,
                        standard_answer=question_item.answer,
                        student_answer=record.get("student_answer", ""),
                    )
            else:
                consecutive_errors = 0

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

    total_score = sum(float(record.get("score", 0.0)) for record in records)
    accuracy = total_score / len(records) if records else 0

    update_profile_after_quiz(poem_name, accuracy)

    wrong_questions = load_wrong_questions()
    poem_wrong = [w for w in wrong_questions if w.get("poem") == poem_name]
    if poem_wrong:
        print(f"\n📝 错题本更新：已记录 {len(poem_wrong)} 道《{poem_name}》相关错题")

    save_learning_record(
        poem_name=poem_name,
        mode="测验",
        score=accuracy,
        question_count=len(records),
    )
    print("✅ 学习记录已保存")

    all_poems = get_available_poems(question_bank)
    next_poem = get_next_recommended_poem(all_poems)
    if next_poem and next_poem != poem_name:
        print(f"\n📌 下一首推荐：《{next_poem}》")
        recommend_choice = input("是否切换到该诗继续学习？（输入 y 切换，不输入则返回菜单）: ").strip()
        if recommend_choice.lower() == "y":
            start_quiz_or_continue(next_poem, question_bank)


def start_quiz_or_continue(poem_name: str, question_bank: list[QuizQuestion]) -> None:
    """开始指定诗词的测验。"""
    print(f"\n切换到《{poem_name}》进行学习。")
    handle_quiz(poem_name, question_bank)


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
