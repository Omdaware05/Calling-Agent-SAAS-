import unittest
from classifier.engine import IntentClassifier

class TestPriorityOverrides(unittest.TestCase):
    """
    Tests priority hierarchy, temporal overriding, and sentiment vs intent.
    """

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_dnc_overrides_earlier_interest(self):
        """
        Priority 1: Even if customer showed interest earlier, an explicit opt-out
        must result in NOT_INTERESTED.
        """
        transcript = """
        Agent: Hello, calling regarding health coverage plans.
        Customer: Oh that sounds nice, how much is the monthly premium?
        Agent: It starts at 500 rupees per month.
        Customer: Actually don't call me again, please remove my number from your list.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_late_positive_overrides_initial_rejection(self):
        """
        Priority 3 overrides earlier soft rejection:
        Customer initially says no, then asks a price or feature question.
        """
        transcript = """
        Agent: Sir, we have an automated billing software for retail stores.
        Customer: No, I don't think I need it.
        Agent: We also do automatic GST filing directly with one click.
        Customer: Can you send me the details? I'll check it out.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_wrong_person(self):
        """
        Wrong number / irrelevant person -> NOT_INTERESTED.
        """
        transcript = """
        Agent: Hello, is this Ramesh from Apex Logistics?
        Customer: No, wrong number. You have the wrong person.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_angry_sentiment_with_positive_intent(self):
        """
        Sentiment is angry/impatient, but intent is inquiring about price.
        Section 16: "Aap pehle price batao, phir main decide karunga." -> INTERESTED
        """
        transcript = """
        Agent: Sir, we have a specialized fleet management platform.
        Customer: Aap faltu baat band karo aur pehle price batao, phir main decide karunga!
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_polite_sentiment_with_negative_intent(self):
        """
        Sentiment is polite/grateful, but intent is clear rejection.
        Section 16: "Thank you for explaining, but mujhe bilkul interest nahi hai." -> NOT_INTERESTED
        """
        transcript = """
        Agent: May I explain how our online tutoring works?
        Customer: Thank you so much for explaining, you were very sweet, but mujhe bilkul interest nahi hai. No thanks.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_agent_words_do_not_contaminate_customer(self):
        """
        Agent uses words like 'interested', 'demo', 'benefits', but customer rejects.
        Must classify as NOT_INTERESTED.
        """
        transcript = """
        Agent: Are you interested in our service? We have a great demo and many benefits for you!
        Customer: No, I am not interested.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_conditional_future_interest(self):
        """
        Section 6: Conditional interest -> INTERESTED.
        "Let me check with my partner and I'll get back to you. Call me next week."
        """
        transcript = """
        Agent: Would you like to sign up for our cloud backup?
        Customer: Let me check with my partner and I'll get back to you. Call me next week.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

if __name__ == "__main__":
    unittest.main()
