import unittest
from classifier.engine import IntentClassifier
from classifier.models import IntentClassification

class TestSpecExamples(unittest.TestCase):
    """
    Validates all 8 reference examples from Section 19 of the specification.
    """

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_example_1(self):
        """
        Example 1:
        Agent: We provide an online business management service.
        Customer: Achha, ye kaise work karta hai?
        Agent: It helps you manage...
        Customer: Iska price kya hai?
        Output: INTERESTED
        """
        transcript = """
        Agent: We provide an online business management service.
        Customer: Achha, ye kaise work karta hai?
        Agent: It helps you manage...
        Customer: Iska price kya hai?
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_example_2(self):
        """
        Example 2:
        Agent: Would you like to know more?
        Customer: Nahi, mujhe iski zarurat nahi hai.
        Output: NOT_INTERESTED
        """
        transcript = """
        Agent: Would you like to know more?
        Customer: Nahi, mujhe iski zarurat nahi hai.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_example_3(self):
        """
        Example 3:
        Agent: We can provide the service at a monthly price.
        Customer: Hmm, thoda expensive lag raha hai.
        Agent: We also have another plan.
        Customer: Achha, woh plan kitne ka hai?
        Output: INTERESTED
        """
        transcript = """
        Agent: We can provide the service at a monthly price.
        Customer: Hmm, thoda expensive lag raha hai.
        Agent: We also have another plan.
        Customer: Achha, woh plan kitne ka hai?
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_example_4(self):
        """
        Example 4:
        Agent: Can I explain the service?
        Customer: Haan, batao.
        Agent: ...
        Customer: WhatsApp pe details bhej sakte ho?
        Output: INTERESTED
        """
        transcript = """
        Agent: Can I explain the service?
        Customer: Haan, batao.
        Agent: ...
        Customer: WhatsApp pe details bhej sakte ho?
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_example_5(self):
        """
        Example 5:
        Agent: Would you like us to contact you later?
        Customer: Nahi. Please don't call me again.
        Output: NOT_INTERESTED
        """
        transcript = """
        Agent: Would you like us to contact you later?
        Customer: Nahi. Please don't call me again.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_example_6(self):
        """
        Example 6:
        Agent: Would you like to try the service?
        Customer: Abhi sure nahi hoon.
        Agent: I can explain how it works.
        Customer: Haan, explain karo.
        Output: INTERESTED
        """
        transcript = """
        Agent: Would you like to try the service?
        Customer: Abhi sure nahi hoon.
        Agent: I can explain how it works.
        Customer: Haan, explain karo.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_example_7(self):
        """
        Example 7:
        Agent: Can I tell you about our service?
        Customer: No.
        Agent: We also provide...
        Customer: Oh, actually I need something like that. How much does it cost?
        Output: INTERESTED
        """
        transcript = """
        Agent: Can I tell you about our service?
        Customer: No.
        Agent: We also provide...
        Customer: Oh, actually I need something like that. How much does it cost?
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_example_8(self):
        """
        Example 8:
        Agent: Can I explain our service?
        Customer: Hello?
        Agent: ...
        Customer: Hello?
        [call disconnected]
        Output: NOT_INTERESTED
        """
        transcript = """
        Agent: Can I explain our service?
        Customer: Hello?
        Agent: ...
        Customer: Hello?
        [call disconnected]
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

if __name__ == "__main__":
    unittest.main()
