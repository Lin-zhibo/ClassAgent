"""RAG module for poetry QA retrieval using LangChain + Chroma."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import chromadb
import pandas as pd
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from agent import get_project_root, load_api_key


def load_embedding_config(config_path: Path | None = None) -> dict[str, str]:
    """Load embedding model config from config/models.json."""
    if config_path is None:
        config_path = get_project_root() / "config" / "models.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Missing model config file: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        config_data = json.load(config_file)

    embedding_model_name = str(config_data.get("EMBEDDING_MODEL_NAME", "")).strip()
    embedding_model_url = str(config_data.get("EMBEDDING_MODEL_URL", "")).strip()

    if not embedding_model_name:
        raise ValueError("Config EMBEDDING_MODEL_NAME cannot be empty.")
    if not embedding_model_url:
        raise ValueError("Config EMBEDDING_MODEL_URL cannot be empty.")

    return {
        "EMBEDDING_MODEL_NAME": embedding_model_name,
        "EMBEDDING_MODEL_URL": embedding_model_url,
    }


def _build_embedding_client(model_name: str, base_url: str, api_key: str) -> OpenAIEmbeddings:
    """Create OpenAIEmbeddings with compatibility for argument names."""
    try:
        return OpenAIEmbeddings(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
            check_embedding_ctx_length=False,
            chunk_size=10,
        )
    except TypeError:
        return OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            check_embedding_ctx_length=False,
            chunk_size=10,
        )


class PoetryRAG:
    """Vector index for poetry QA data."""

    def __init__(
        self,
        csv_path: Path | None = None,
        persist_directory: Path | None = None,
        collection_name: str = "poetry_qa",
    ) -> None:
        project_root = get_project_root()

        self.csv_path = csv_path or project_root / "data" / "questions.CSV"
        self.persist_directory = persist_directory or project_root / "db" / "rag_chroma"
        self.collection_name = collection_name

        self.persist_directory.mkdir(parents=True, exist_ok=True)

        embedding_cfg = load_embedding_config()
        api_key = load_api_key()

        self.embedding_model_name = embedding_cfg["EMBEDDING_MODEL_NAME"]
        self.embedding_model_url = embedding_cfg["EMBEDDING_MODEL_URL"]
        self.embeddings = _build_embedding_client(
            model_name=self.embedding_model_name,
            base_url=self.embedding_model_url,
            api_key=api_key,
        )

        self.vectorstore = self._create_vectorstore()

    def _create_vectorstore(self) -> Chroma:
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory),
        )

    def _collection_count(self) -> int:
        collection = getattr(self.vectorstore, "_collection", None)
        if collection is None:
            return 0
        try:
            return int(collection.count())
        except Exception:
            return 0

    def _reset_collection(self) -> None:
        client = chromadb.PersistentClient(path=str(self.persist_directory))
        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.vectorstore = self._create_vectorstore()

    def _read_csv(self) -> pd.DataFrame:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Missing QA dataset: {self.csv_path}")

        for encoding in ("utf-8-sig", "utf-8", "gbk"):
            try:
                return pd.read_csv(self.csv_path, encoding=encoding)
            except UnicodeDecodeError:
                continue

        return pd.read_csv(self.csv_path)

    def _build_documents(self) -> tuple[list[Document], list[str]]:
        frame = self._read_csv().fillna("")

        required_columns = {"诗人", "作品", "问题", "答案"}
        missing_columns = required_columns - set(frame.columns)
        if missing_columns:
            missing_text = ", ".join(sorted(missing_columns))
            raise ValueError(f"Dataset missing required columns: {missing_text}")

        documents: list[Document] = []
        ids: list[str] = []

        for _, row in frame.iterrows():
            poet = str(row.get("诗人", "")).strip()
            poem = str(row.get("作品", "")).strip()
            question = str(row.get("问题", "")).strip()
            answer = str(row.get("答案", "")).strip()

            if not question or not answer:
                continue

            content = (
                f"诗人：{poet}\n"
                f"作品：{poem}\n"
                f"问题：{question}\n"
                f"答案：{answer}"
            )

            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "poet": poet,
                        "poem": poem,
                        "question": question,
                        "answer": answer,
                    },
                )
            )

            raw_id = f"{poet}|{poem}|{question}|{answer}"
            ids.append(hashlib.md5(raw_id.encode("utf-8")).hexdigest())

        if not documents:
            raise ValueError("No valid QA records found in dataset.")

        return documents, ids

    def ensure_index(self, force_rebuild: bool = False) -> int:
        if force_rebuild:
            self._reset_collection()

        if self._collection_count() > 0 and not force_rebuild:
            return self._collection_count()

        documents, ids = self._build_documents()
        self.vectorstore.add_documents(documents=documents, ids=ids)

        if hasattr(self.vectorstore, "persist"):
            self.vectorstore.persist()

        return self._collection_count()

    def retrieve(
        self,
        query: str,
        k: int = 3,
        poet: str | None = None,
        poem: str | None = None,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        if self._collection_count() == 0:
            self.ensure_index()

        search_filter: dict[str, str] = {}
        if poet:
            search_filter["poet"] = poet
        if poem:
            search_filter["poem"] = poem

        kwargs: dict[str, Any] = {}
        if search_filter:
            kwargs["filter"] = search_filter

        results = self.vectorstore.similarity_search_with_score(query, k=k, **kwargs)

        parsed: list[dict[str, Any]] = []
        for document, score in results:
            metadata = document.metadata or {}
            parsed.append(
                {
                    "poet": str(metadata.get("poet", "")),
                    "poem": str(metadata.get("poem", "")),
                    "question": str(metadata.get("question", "")),
                    "answer": str(metadata.get("answer", "")),
                    "score": float(score),
                    "content": document.page_content,
                }
            )

        return parsed


_DEFAULT_RAG: PoetryRAG | None = None


def get_default_rag() -> PoetryRAG:
    """Get lazily initialized singleton RAG instance."""
    global _DEFAULT_RAG
    if _DEFAULT_RAG is None:
        _DEFAULT_RAG = PoetryRAG()
    return _DEFAULT_RAG


def retrieve(
    query: str,
    k: int = 3,
    poet: str | None = None,
    poem: str | None = None,
) -> list[dict[str, Any]]:
    """Module-level retrieve helper."""
    return get_default_rag().retrieve(query=query, k=k, poet=poet, poem=poem)


def test_rag(query: str = "王维使至塞上表达了什么情感") -> list[dict[str, Any]]:
    """Quick local test for retrieval."""
    rag = get_default_rag()
    rag.ensure_index()
    return rag.retrieve(query=query, k=3)


if __name__ == "__main__":
    items = test_rag()
    print(json.dumps(items, ensure_ascii=False, indent=2))
