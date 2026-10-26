import unittest
from classifier.engine import IntentClassifier

class TestMultilingual(unittest.TestCase):
    """
    Tests multilingual support: English, Hindi, Marathi, Hinglish, Marathish,
    Devanagari script, and code-switching mixtures.
    """

    def setUp(self):
        self.classifier = IntentClassifier()

    def test_hinglish_interest(self):
        """
        Section 15 example:
        Agent: Sir, hamari service ke baare mein batana tha.
        Customer: Haan bolo, exactly kya service hai?
        Agent: Hum aapko digital solution provide karte hain...
        Customer: Achha, iska price kya hai?
        -> INTERESTED
        """
        transcript = """
        Agent: Sir, hamari service ke baare mein batana tha.
        Customer: Haan bolo, exactly kya service hai?
        Agent: Hum aapko digital solution provide karte hain...
        Customer: Achha, iska price kya hai?
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_marathish_interest(self):
        """
        Marathi Romanized:
        Customer: Ho sanga na, kasa work karto? Kiti rupaye padel?
        -> INTERESTED
        """
        transcript = """
        Agent: Namaskar, aamhi solar rooftop installation service det aahot.
        Customer: Ho sanga na, kasa work karto? Kiti rupaye padel?
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_marathish_rejection(self):
        """
        Marathi Romanized rejection:
        Customer: Mala kahi garaj nahi, nako ahe.
        -> NOT_INTERESTED
        """
        transcript = """
        Agent: Hello sir, loan requirement ahe ka?
        Customer: Mala kahi garaj nahi, nakoy mala. Phone theva.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_marathish_dnc(self):
        """
        Marathi Romanized DNC:
        Customer: Punha phone karu naka, number kadhun taka.
        -> NOT_INTERESTED
        """
        transcript = """
        Agent: Sir ek credit card offer ahe.
        Customer: Punha phone karu naka, number delete kara aani tras deu naka.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_devanagari_hindi_interest(self):
        """
        Hindi in Devanagari:
        Customer: हाँ बताओ, पूरी जानकारी व्हाट्सएप पर भेजो।
        -> INTERESTED
        """
        transcript = """
        Agent: नमस्ते सर, हम बिज़नेस अकाउंटिंग सॉफ्टवेयर के बारे में बात कर रहे हैं।
        Customer: हाँ बताओ, पूरी जानकारी व्हाट्सएप पर भेजो।
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_devanagari_marathi_interest(self):
        """
        Marathi in Devanagari:
        Customer: हो सांगा, खर्च किती येईल आणि माहिती द्या।
        -> INTERESTED
        """
        transcript = """
        Agent: नमस्कार, आम्ही जलशुद्धीकरण सेवेबद्दल बोलत आहोत.
        Customer: हो सांगा, खर्च किती येईल आणि माहिती द्या.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

    def test_devanagari_hindi_rejection(self):
        """
        Hindi in Devanagari rejection:
        Customer: मुझे यह नहीं चाहिए, बिल्कुल ज़रूरत नहीं है।
        -> NOT_INTERESTED
        """
        transcript = """
        Agent: क्या आप हमारी इंश्योरेंस पॉलिसी देखना चाहेंगे?
        Customer: मुझे यह नहीं चाहिए, बिल्कुल ज़रूरत नहीं है।
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_devanagari_marathi_rejection(self):
        """
        Marathi in Devanagari rejection:
        Customer: मला काही गरज नाही, नको आहे.
        -> NOT_INTERESTED
        """
        transcript = """
        Agent: सर तुम्हाला पर्सनल लोन हवे आहे का?
        Customer: मला काही गरज नाही, नको आहे.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "NOT_INTERESTED")

    def test_code_switching_mixture(self):
        """
        Mixture of Hindi + Marathi + English:
        Customer: Accha explain karo, but monthly kitna charge padel?
        -> INTERESTED
        """
        transcript = """
        Agent: We have an ERP software suite for small business.
        Customer: Accha explain karo, but monthly kitna charge padel?
        Agent: It is 999 per month.
        Customer: Theek ahe, send details on WhatsApp.
        """
        res = self.classifier.classify_strict(transcript)
        self.assertEqual(res["classification"], "INTERESTED")

if __name__ == "__main__":
    unittest.main()
