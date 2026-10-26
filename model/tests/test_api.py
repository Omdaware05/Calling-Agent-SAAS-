import unittest
from fastapi.testclient import TestClient
from api.main import app

class TestAPI(unittest.TestCase):
    """
    Tests the REST API endpoints.
    """

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("INTERESTED", data["classification_classes"])

    def test_classify_strict(self):
        payload = {
            "transcript": "Agent: Can I tell you about our plans? Customer: Yes, please send details on WhatsApp."
        }
        response = self.client.post("/classify", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, {"classification": "INTERESTED"})

    def test_classify_rejection_strict(self):
        payload = {
            "transcript": "Agent: Would you like to switch? Customer: No, I don't want this service."
        }
        response = self.client.post("/classify", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, {"classification": "NOT_INTERESTED"})

    def test_classify_explain_mode(self):
        payload = {
            "transcript": "Agent: Do you need cloud hosting? Customer: Thoda expensive hai, but what are the specs?",
            "explain": True
        }
        response = self.client.post("/classify", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["classification"], "INTERESTED")
        self.assertIn("confidence", data)
        self.assertIn("rule_applied", data)
        self.assertIn("turns", data)

    def test_batch_classify(self):
        payload = {
            "transcripts": [
                "Agent: Hi. Customer: Iska price kitna hai?",
                "Agent: Hi. Customer: Call mat karna dobara."
            ]
        }
        response = self.client.post("/classify/batch", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["interested_count"], 1)
        self.assertEqual(data["not_interested_count"], 1)

if __name__ == "__main__":
    unittest.main()
