import hashlib
import json
import math
import re
import threading
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.RLock()
DOCUMENTS = json.loads((ROOT / "data/documents.json").read_text())
STOP = {
    "the",
    "a",
    "an",
    "is",
    "to",
    "and",
    "of",
    "in",
    "for",
    "how",
    "what",
    "do",
    "i",
    "we",
    "on",
    "with",
    "does",
    "are",
    "be",
    "should",
    "when",
    "where",
}

INFLECTIONS = {
    "retried": "retry",
    "retries": "retry",
    "retrying": "retry",
    "requests": "request",
    "records": "record",
    "failures": "failure",
    "models": "model",
}


def tokens(text):
    return [
        INFLECTIONS.get(w, w)
        for w in re.findall(r"[a-z0-9]+", text.lower())
        if w not in STOP
    ]


def chunks(documents):
    result = []
    for document in documents:
        for index, paragraph in enumerate(re.split(r"\n\s*\n", document["text"])):
            words = paragraph.split()
            for offset in range(0, len(words), 100):
                text = " ".join(words[offset : offset + 120])
                result.append(
                    {
                        "id": hashlib.sha256(
                            f"{document['title']}:{index}:{offset}:{text}".encode()
                        ).hexdigest()[:12],
                        "title": document["title"],
                        "paragraph": index + 1,
                        "text": text,
                        "terms": Counter(tokens(text)),
                    }
                )
    return result


def search(query, limit=5):
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError("Query must contain 1–500 characters")
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("Limit must be an integer from 1 to 10")
    terms = set(tokens(query))
    with LOCK:
        passages = chunks(DOCUMENTS)
    if not passages:
        return {
            "query": query,
            "hits": [],
            "answer": None,
            "coverage": 0,
            "reason": "Empty collection",
        }
    average = sum(sum(p["terms"].values()) for p in passages) / len(passages) or 1
    frequencies = {term: sum(term in p["terms"] for p in passages) for term in terms}
    hits = []
    for passage in passages:
        score = 0
        length = sum(passage["terms"].values())
        matched = []
        for term in terms:
            tf = passage["terms"][term]
            if tf:
                idf = math.log(
                    1
                    + (len(passages) - frequencies[term] + 0.5)
                    / (frequencies[term] + 0.5)
                )
                score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * length / average))
                matched.append(term)
        if score:
            hits.append(
                {k: v for k, v in passage.items() if k != "terms"}
                | {"score": round(score, 4), "matched": sorted(matched)}
            )
    hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
    hits = hits[:limit]
    coverage = len(set(hits[0]["matched"])) / len(terms) if hits and terms else 0
    answer = None
    if hits and coverage >= 0.5:
        sentences = re.split(r"(?<=[.!?])\s+", hits[0]["text"])
        best = max(sentences, key=lambda text: len(set(tokens(text)) & terms))
        answer = {
            "text": best,
            "citation": hits[0]["id"],
            "title": hits[0]["title"],
            "paragraph": hits[0]["paragraph"],
        }
    return {
        "query": query,
        "hits": hits,
        "coverage": coverage,
        "answer": answer,
        "reason": "Extracted source sentence"
        if answer
        else "Insufficient lexical coverage; inspect passages or rephrase",
    }


def replace(documents):
    if not isinstance(documents, list) or not 1 <= len(documents) <= 100:
        raise ValueError("Supply 1–100 documents")
    titles = set()
    for doc in documents:
        if (
            not isinstance(doc, dict)
            or not isinstance(doc.get("title"), str)
            or not doc["title"].strip()
        ):
            raise ValueError("Every document needs a title")
        if doc["title"] in titles:
            raise ValueError("Document titles must be unique")
        titles.add(doc["title"])
        if (
            not isinstance(doc.get("text"), str)
            or not doc["text"].strip()
            or len(doc["text"]) > 50000
        ):
            raise ValueError("Document text must contain 1–50000 characters")
    with LOCK:
        DOCUMENTS[:] = [{"title": d["title"], "text": d["text"]} for d in documents]
    return snapshot()


def snapshot():
    with LOCK:
        docs = [dict(d) for d in DOCUMENTS]
        count = len(chunks(docs))
    return {
        "documents": docs,
        "passages": count,
        "examples": [
            "How are inference requests retried?",
            "Where do invalid records go?",
            "When should we roll back a model?",
        ],
    }


def handle(path, body):
    if path == "/api/search":
        return search(body.get("query"), body.get("limit", 5))
    if path == "/api/documents":
        return replace(body.get("documents"))
    raise ValueError("Unknown endpoint")
