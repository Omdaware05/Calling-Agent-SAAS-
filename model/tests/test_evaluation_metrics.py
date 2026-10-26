import time
import unittest
from collections import defaultdict
from typing import Dict, Any

from classifier.engine import IntentClassifier
from classifier.models import IntentClassification, InterestStrength
from tests.evaluation_dataset import EVALUATION_DATASET


class TestEvaluationMetrics(unittest.TestCase):
    """
    Comprehensive automated evaluation test suite running the 170-example
    multilingual dataset across English, Hindi, Marathi, Hinglish, and Marathish.
    
    Computes and asserts:
    - Overall Classification Accuracy
    - Class-wise Precision, Recall, F1 Score
    - Macro F1 Score
    - False Positive & False Negative Rates
    - Negation Handling Accuracy
    - Romanized & Code-Mixed Accuracy
    - Callback Detection Accuracy
    - Real-Time Inference Latency
    """

    @classmethod
    def setUpClass(cls):
        cls.classifier = IntentClassifier()
        cls.dataset = EVALUATION_DATASET
        cls.results = []
        cls.classes = [
            "INTERESTED",
            "NOT_INTERESTED",
            "CALLBACK_REQUESTED",
            "NEEDS_INFORMATION",
            "UNCERTAIN"
        ]

        # Run evaluation and measure latency
        start_time = time.perf_counter()
        for item in cls.dataset:
            diag = cls.classifier.classify_detailed(item["transcript"])
            cls.results.append({
                "id": item["id"],
                "language": item["language"],
                "test_category": item["test_category"],
                "expected_classification": item["expected_classification"],
                "predicted_classification": diag.classification.value,
                "expected_interest_strength": item.get("expected_interest_strength"),
                "predicted_interest_strength": diag.interest_strength.value,
                "correct_class": (diag.classification.value == item["expected_classification"]),
                "correct_strength": (diag.interest_strength.value == item.get("expected_interest_strength")),
                "transcript": item["transcript"],
                "reason": diag.reason,
            })
        cls.total_duration_sec = time.perf_counter() - start_time
        cls.avg_latency_ms = (cls.total_duration_sec / len(cls.dataset)) * 1000.0

    def test_overall_accuracy_and_macro_f1(self):
        total = len(self.results)
        correct = sum(1 for r in self.results if r["correct_class"])
        overall_accuracy = (correct / total) * 100.0

        # Confusion matrix: truth -> pred -> count
        matrix = {c: {p: 0 for p in self.classes} for c in self.classes}
        for r in self.results:
            matrix[r["expected_classification"]][r["predicted_classification"]] += 1

        class_metrics = {}
        f1_scores = []

        print("\n" + "=" * 78)
        print("    MULTILINGUAL CUSTOMER INTENT EVALUATION METRICS REPORT")
        print("=" * 78)
        print(f"Total Test Utterances: {total}")
        print(f"Overall Accuracy:      {overall_accuracy:.2f}% ({correct}/{total})")
        print(f"Average Latency:       {self.avg_latency_ms:.3f} ms / utterance")
        print("-" * 78)
        print(f"{'Class':<22} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
        print("-" * 78)

        for c in self.classes:
            tp = matrix[c][c]
            fp = sum(matrix[other][c] for other in self.classes if other != c)
            fn = sum(matrix[c][other] for other in self.classes if other != c)
            support = sum(matrix[c].values())

            precision = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 0.0
            recall = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            class_metrics[c] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
                "tp": tp,
                "fp": fp,
                "fn": fn
            }
            f1_scores.append(f1)
            print(f"{c:<22} | {precision:>8.2f}% | {recall:>8.2f}% | {f1:>8.2f}% | {support:>8}")

        macro_f1 = sum(f1_scores) / len(f1_scores)
        print("-" * 78)
        print(f"{'Macro Average':<22} | {'':<10} | {'':<10} | {macro_f1:>8.2f}% | {total:>8}")
        print("=" * 78)

        # False Positives for INTERESTED: Truth was NOT_INTERESTED/UNCERTAIN but marked as INTERESTED
        fp_interested = sum(
            1 for r in self.results
            if r["expected_classification"] != "INTERESTED" and r["predicted_classification"] == "INTERESTED"
        )
        # False Negatives for INTERESTED: Truth was INTERESTED but marked as another class
        fn_interested = sum(
            1 for r in self.results
            if r["expected_classification"] == "INTERESTED" and r["predicted_classification"] != "INTERESTED"
        )
        # Incorrect Rejections: Customer was NOT rejecting, but classified as NOT_INTERESTED
        incorrect_rejections = sum(
            1 for r in self.results
            if r["expected_classification"] != "NOT_INTERESTED" and r["predicted_classification"] == "NOT_INTERESTED"
        )

        print(f"False Positives for INTERESTED: {fp_interested} ({fp_interested/total*100:.1f}%)")
        print(f"False Negatives for INTERESTED: {fn_interested} ({fn_interested/total*100:.1f}%)")
        print(f"Incorrect Rejections:           {incorrect_rejections} ({incorrect_rejections/total*100:.1f}%)")
        print("=" * 78 + "\n")

        # Assertions
        self.assertGreaterEqual(overall_accuracy, 95.0, "Overall accuracy should exceed 95%")
        self.assertGreaterEqual(macro_f1, 92.0, "Macro F1 score should exceed 92%")
        self.assertEqual(fp_interested, 0, "No false positive interest should occur on rejections/neutral responses")

    def test_subset_category_accuracies(self):
        category_counts = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in self.results:
            cat = r["test_category"]
            category_counts[cat]["total"] += 1
            if r["correct_class"]:
                category_counts[cat]["correct"] += 1

        print("--- Diagnostic Category Breakdown ---")
        for cat, data in sorted(category_counts.items()):
            acc = (data["correct"] / data["total"]) * 100.0
            print(f"  {cat:<28}: {acc:6.2f}% ({data['correct']}/{data['total']})")
            self.assertGreaterEqual(acc, 90.0, f"Category '{cat}' accuracy fell below 90%")
        print("--------------------------------------\n")

    def test_language_breakdown_accuracy(self):
        lang_counts = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in self.results:
            lang = r["language"]
            lang_counts[lang]["total"] += 1
            if r["correct_class"]:
                lang_counts[lang]["correct"] += 1

        print("--- Language Breakdown Accuracy ---")
        for lang, data in sorted(lang_counts.items()):
            acc = (data["correct"] / data["total"]) * 100.0
            print(f"  {lang:<24}: {acc:6.2f}% ({data['correct']}/{data['total']})")
            self.assertGreaterEqual(acc, 90.0, f"Language '{lang}' accuracy fell below 90%")
        print("-----------------------------------\n")

    def test_latency_performance(self):
        # Must execute comfortably under 5ms per utterance (real-time voice requirement)
        self.assertLess(self.avg_latency_ms, 5.0, "Per-turn latency exceeds 5ms limit for real-time voice calls")


if __name__ == "__main__":
    unittest.main()
