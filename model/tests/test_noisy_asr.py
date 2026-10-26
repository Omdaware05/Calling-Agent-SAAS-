import unittest
from classifier.engine import IntentClassifier

class TestNoisyASRAndAmbiguity(unittest.TestCase):
    """
    Tests speech-to-text noisy transcripts, partial/broken sentences,
    and the conservative high-recall ambiguity rule.
    """

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_noisy_spelling_positive(self):
        """
        ASR transcription errors: 'watsp pe detils snd krna'
        """
        transcript = """
        Agent: Hello sir we have an accounting software.
        Customer: accha watsp pe detils bhej do dekhta hu.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_call_disconnect_after_positive_signal(self):
        """
        Section 12: If transcript contains meaningful positive signal before call ends:
        'Yes, send me the information.' followed by call ending -> INTERESTED.
        """
        transcript = """
        Agent: Can we share our insurance catalogue with you?
        Customer: Yes, send me the information.
        [call disconnected]
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_long_conversation_with_engagement_and_no_rejection(self):
        """
        Section 7: Long conversation / multi-turn engagement without clear rejection:
        Customer continues engaging, listens, discusses -> INTERESTED.
        """
        transcript = """
        Agent: Hello, I am calling from Zenith Cloud services.
        Customer: Yes, who is speaking?
        Agent: I am Rahul, we provide managed cloud security.
        Customer: Okay, we are currently evaluating different options.
        Agent: We have 24/7 incident response.
        Customer: I see, how do you handle data backups?
        Agent: We do daily automated snapshots.
        Customer: Alright, understood.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_ambiguous_transcript_rescued_as_lead(self):
        """
        Section 13 & 14: If transcript is genuinely unclear / noisy and model cannot
        confidently determine rejection -> classify as INTERESTED (lead preservation).
        """
        transcript = """
        Agent: Calling regarding business loan schemes for your shop.
        Customer: Hmm loan toh ... pata nahi abhi ... dekhna padega ...
        Agent: We have low interest rates.
        Customer: Theek hai sun raha hu bataiye ...
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

if __name__ == "__main__":
    unittest.main()
