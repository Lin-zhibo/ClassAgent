"""用户记忆管理模块：管理长期画像与短期对话上下文。"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def get_project_root() -> Path:
    """获取项目根目录路径。"""
    return Path(__file__).resolve().parent


def get_memory_dir() -> Path:
    """获取记忆存储目录路径。"""
    memory_dir = get_project_root() / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def get_user_data_path(user_id: str = "default") -> Path:
    """获取用户数据文件路径。"""
    return get_memory_dir() / f"{user_id}_learning_data.txt"


def get_wrong_questions_path(user_id: str = "default") -> Path:
    """获取错题本文件路径。"""
    return get_memory_dir() / f"{user_id}_wrong_questions.txt"


def load_user_profile(user_id: str = "default") -> dict[str, Any]:
    """加载用户画像。"""
    data_path = get_user_data_path(user_id)
    if not data_path.exists():
        return _default_profile()

    try:
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "profile" in data:
                return data["profile"]
            return data
    except (json.JSONDecodeError, IOError):
        return _default_profile()


def _default_profile() -> dict[str, Any]:
    """返回默认用户画像。"""
    return {
        "user_id": "default",
        "学习阶段": "新学",
        "理解能力": "中",
        "背诵能力": "中",
        "已完成诗词": [],
        "当前进度": {},
        "创建时间": datetime.now().isoformat(),
        "最后学习时间": None,
    }


def save_user_profile(profile: dict[str, Any], user_id: str = "default") -> None:
    """保存用户画像。"""
    data_path = get_user_data_path(user_id)
    profile["最后学习时间"] = datetime.now().isoformat()

    existing = {}
    if data_path.exists():
        try:
            with data_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, dict):
                    existing = {"profile": existing}
        except (json.JSONDecodeError, IOError):
            existing = {}

    existing["profile"] = profile

    with data_path.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def load_learning_records(user_id: str = "default") -> list[dict[str, Any]]:
    """加载学习记录。"""
    data_path = get_user_data_path(user_id)
    if not data_path.exists():
        return []

    try:
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("learning_records", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_learning_record(
    poem_name: str,
    mode: str,
    score: float,
    question_count: int,
    user_id: str = "default",
) -> None:
    """保存单次学习记录。"""
    data_path = get_user_data_path(user_id)

    existing = {}
    if data_path.exists():
        try:
            with data_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, dict):
                    existing = {}
        except (json.JSONDecodeError, IOError):
            existing = {}

    if "learning_records" not in existing:
        existing["learning_records"] = []

    record = {
        "poem": poem_name,
        "mode": mode,
        "score": score,
        "question_count": question_count,
        "timestamp": datetime.now().isoformat(),
    }
    existing["learning_records"].append(record)

    profile = existing.get("profile", _default_profile())
    if poem_name not in profile.get("已完成诗词", []):
        if score >= 0.6:
            profile.setdefault("已完成诗词", []).append(poem_name)

    if "current_progress" not in profile:
        profile["current_progress"] = {}
    profile["current_progress"][poem_name] = {
        "mode": mode,
        "score": score,
        "last_practiced": datetime.now().isoformat(),
    }
    existing["profile"] = profile

    with data_path.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def load_wrong_questions(user_id: str = "default") -> list[dict[str, Any]]:
    """加载错题本。"""
    wrong_path = get_wrong_questions_path(user_id)
    if not wrong_path.exists():
        return []

    try:
        with wrong_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("wrong_questions", [])
    except (json.JSONDecodeError, IOError):
        return []


def add_wrong_question(
    poem_name: str,
    poet: str,
    question: str,
    standard_answer: str,
    student_answer: str,
    user_id: str = "default",
) -> None:
    """添加错题到错题本。"""
    wrong_path = get_wrong_questions_path(user_id)

    existing = []
    if wrong_path.exists():
        try:
            with wrong_path.open("r", encoding="utf-8") as f:
                existing = json.load(f).get("wrong_questions", [])
        except (json.JSONDecodeError, IOError):
            existing = []

    for item in existing:
        if item.get("poem") == poem_name and item.get("question") == question:
            item["wrong_count"] = item.get("wrong_count", 0) + 1
            item["last_wrong_time"] = datetime.now().isoformat()
            item["student_answer"] = student_answer
            break
    else:
        existing.append({
            "poem": poem_name,
            "poet": poet,
            "question": question,
            "standard_answer": standard_answer,
            "student_answer": student_answer,
            "wrong_count": 1,
            "first_wrong_time": datetime.now().isoformat(),
            "last_wrong_time": datetime.now().isoformat(),
        })

    with wrong_path.open("w", encoding="utf-8") as f:
        json.dump({"wrong_questions": existing}, f, ensure_ascii=False, indent=2)


def remove_wrong_question(poem_name: str, question: str, user_id: str = "default") -> None:
    """从错题本移除已掌握的题目。"""
    wrong_path = get_wrong_questions_path(user_id)
    if not wrong_path.exists():
        return

    try:
        with wrong_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    existing = data.get("wrong_questions", [])
    data["wrong_questions"] = [
        item for item in existing
        if not (item.get("poem") == poem_name and item.get("question") == question)
    ]

    with wrong_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_weak_poems(user_id: str = "default", limit: int = 3) -> list[str]:
    """获取需要加强练习的诗词列表（基于错题本）。"""
    wrong_questions = load_wrong_questions(user_id)

    poem_wrong_count: dict[str, int] = {}
    for item in wrong_questions:
        poem = item.get("poem", "")
        count = item.get("wrong_count", 0)
        poem_wrong_count[poem] = poem_wrong_count.get(poem, 0) + count

    sorted_poems = sorted(poem_wrong_count.items(), key=lambda x: x[1], reverse=True)
    return [poem for poem, _ in sorted_poems[:limit]]


def get_next_recommended_poem(
    all_poems: list[str],
    user_id: str = "default",
) -> str | None:
    """基于用户画像和学习记录推荐下一首诗。"""
    profile = load_user_profile(user_id)
    completed = set(profile.get("已完成诗词", []))
    weak_poems = set(get_weak_poems(user_id))

    unlearned = [p for p in all_poems if p not in completed]
    if not unlearned:
        unlearned = all_poems

    priority_poems = [p for p in unlearned if p in weak_poems]
    if priority_poems:
        return priority_poems[0]

    if profile.get("背诵能力", "中") == "弱":
        priority = [p for p in unlearned if _contains_short_poem(p)]
        if priority:
            return priority[0]

    if profile.get("理解能力", "中") == "弱":
        priority = [p for p in unlearned if _contains_famous_poem(p)]
        if priority:
            return priority[0]

    return unlearned[0] if unlearned else (all_poems[0] if all_poems else None)


def _contains_short_poem(poem_name: str) -> bool:
    """判断是否为短诗（适合背诵能力弱的用户）。"""
    short_keywords = ["绝句", "乐府", "五言绝句", "七言绝句"]
    return any(kw in poem_name for kw in short_keywords)


def _contains_famous_poem(poem_name: str) -> bool:
    """判断是否为名篇（适合理解能力弱的用户）。"""
    famous_keywords = ["望岳", "春晓", "静夜思", "悯农", "登鹳雀楼", "相思"]
    return any(kw in poem_name for kw in famous_keywords)


def update_profile_after_quiz(
    poem_name: str,
    accuracy: float,
    user_id: str = "default",
) -> None:
    """根据测验结果更新用户画像。"""
    profile = load_user_profile(user_id)

    if accuracy >= 0.8:
        if profile.get("理解能力") == "弱":
            profile["理解能力"] = "中"
        elif profile.get("理解能力") == "中":
            profile["理解能力"] = "强"
    elif accuracy < 0.4:
        if profile.get("理解能力") == "强":
            profile["理解能力"] = "中"
        elif profile.get("理解能力") == "中":
            profile["理解能力"] = "弱"

    if poem_name not in profile.get("已完成诗词", []):
        if accuracy >= 0.6:
            profile.setdefault("已完成诗词", []).append(poem_name)
            if profile.get("学习阶段") == "新学":
                profile["学习阶段"] = "复习"

    save_user_profile(profile, user_id)


def clear_memory(user_id: str = "default") -> None:
    """清除用户所有记忆数据。"""
    user_path = get_user_data_path(user_id)
    wrong_path = get_wrong_questions_path(user_id)

    if user_path.exists():
        user_path.unlink()
    if wrong_path.exists():
        wrong_path.unlink()