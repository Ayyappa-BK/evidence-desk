import unittest

import domain


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.saved = [dict(d) for d in domain.DOCUMENTS]

    def tearDown(self):
        domain.DOCUMENTS[:] = self.saved

    def test_answer_has_existing_citation(self):
        result = domain.search("invalid records quarantine")
        self.assertIsNotNone(result["answer"])
        self.assertIn(result["answer"]["citation"], [h["id"] for h in result["hits"]])
        self.assertIn(result["answer"]["text"], result["hits"][0]["text"])

    def test_retry_question_ranks_retry_runbook(self):
        result = domain.search("How are inference requests retried?")
        self.assertEqual(result["hits"][0]["paragraph"], 1)
        self.assertIn("retry", result["answer"]["text"].lower())

    def test_unrelated_query_abstains(self):
        result = domain.search("volcano penguin orbital")
        self.assertEqual(result["hits"], [])
        self.assertIsNone(result["answer"])

    def test_overlap_and_stable_ids(self):
        documents = [
            {"title": "Long", "text": " ".join(f"word{i}" for i in range(250))}
        ]
        a, b = domain.chunks(documents), domain.chunks(documents)
        self.assertEqual([p["id"] for p in a], [p["id"] for p in b])
        self.assertIn("word100", a[0]["text"])
        self.assertIn("word100", a[1]["text"])

    def test_replace_is_validated_before_mutation(self):
        with self.assertRaises(ValueError):
            domain.replace([{"title": "ok", "text": "hello"}, {"title": "missing"}])
        self.assertEqual(domain.DOCUMENTS, self.saved)

    def test_bad_query_and_limit(self):
        for query, limit in [("", 5), ("x", 0), ("x", True)]:
            with self.assertRaises(ValueError):
                domain.search(query, limit)
