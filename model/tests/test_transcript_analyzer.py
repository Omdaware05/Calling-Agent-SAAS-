"""Tests for the one-file offline transcript analyzer.

Run with plain unittest (standard library only — no pytest, no pydantic):
    python -m unittest tests.test_transcript_analyzer -v
from inside model/, or with pytest if available.
"""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcript_analyzer import analyze_transcript, export_excel, export_csv  # noqa: E402

INTERESTED_EN = """Agent: Hello, I am calling from SolarKart about our home solar plans.
Customer: My name is Rohit Sharma. What is the price for a 3kW system?
Agent: It is around 1.8 lakh with subsidy.
Customer: Sounds good. I live in Pune and my budget is 2 lakh rupees.
Customer: Please send details on WhatsApp. My number is 98220 12345 and email is rohit.sharma@gmail.com.
Customer: Can we book a demo tomorrow?
Agent: Certainly, I will schedule it.
"""

NOT_INTERESTED_HINGLISH = """Agent: Namaste, main ABC company se bol raha hoon.
Customer: Mujhe nahi chahiye, not interested. Please do not call again, remove my number.
"""

CALLBACK = """Agent: Hello sir, calling about our insurance plan.
Customer: I am busy right now in a meeting. Call me tomorrow at 5 pm, we can talk then.
Agent: Sure sir.
"""

WRONG_NUMBER = """Agent: Hello, is this Mr. Verma?
Customer: Wrong number, galat number hai ye.
"""

HINDI_INTERESTED = """Agent: नमस्ते, मैं हेल्थ प्लान के बारे में कॉल कर रहा हूँ।
Customer: मुझे चाहिए, बताइए प्लान क्या है और कितना खर्च आएगा?
Customer: मेरा नाम संजय पाटिल है, मैं नाशिक से हूँ।
"""

PRICE_OBJECTION_ENGAGED = """Agent: Our premium plan is 5000 per month.
Customer: That is too expensive, mehenga hai bahut. But tell me more, what features do I get?
Agent: It includes unlimited calls and support.
Customer: Hmm, explain the smaller plan then.
"""

PLAIN_NO_ROLES = "Yes I am interested, please send details. My email is priya@example.com"


class TestClassification(unittest.TestCase):
    def test_interested_english(self):
        r = analyze_transcript(INTERESTED_EN)
        self.assertEqual(r["binary"], "INTERESTED")
        self.assertGreaterEqual(r["lead_score"], 60)

    def test_not_interested_hinglish_optout(self):
        r = analyze_transcript(NOT_INTERESTED_HINGLISH)
        self.assertEqual(r["classification"], "NOT_INTERESTED")
        self.assertTrue(r["opt_out_do_not_call"])
        self.assertEqual(r["lead_score"], 0)

    def test_callback(self):
        r = analyze_transcript(CALLBACK)
        self.assertIn(r["classification"], ("CALLBACK_REQUESTED", "NOT_INTERESTED", "NEEDS_INFORMATION"))
        self.assertIsNotNone(r["customer_info"]["preferred_callback_time"])

    def test_wrong_number(self):
        r = analyze_transcript(WRONG_NUMBER)
        self.assertEqual(r["classification"], "NOT_INTERESTED")
        codes = [x["code"] for x in r["why_not_interested"]]
        self.assertIn("wrong_number", codes)

    def test_hindi_interested(self):
        r = analyze_transcript(HINDI_INTERESTED)
        self.assertEqual(r["binary"], "INTERESTED")

    def test_price_objection_still_engaged(self):
        r = analyze_transcript(PRICE_OBJECTION_ENGAGED)
        codes_not = [x["code"] for x in r["why_not_interested"]]
        self.assertIn("price_too_high", codes_not)

    def test_plain_text_no_roles(self):
        r = analyze_transcript(PLAIN_NO_ROLES)
        self.assertEqual(r["customer_info"]["email"], "priya@example.com")


class TestExtraction(unittest.TestCase):
    def test_full_extraction(self):
        r = analyze_transcript(INTERESTED_EN)
        ci = r["customer_info"]
        self.assertEqual(ci["name"], "Rohit Sharma")
        self.assertEqual(ci["phone"], "+919822012345")
        self.assertEqual(ci["email"], "rohit.sharma@gmail.com")
        self.assertEqual(ci["city"], "Pune")
        self.assertEqual(ci["budget_inr"], 200000)

    def test_agent_speech_does_not_leak_into_customer_info(self):
        # The agent mentions 1.8 lakh pricing BEFORE the customer states a
        # 2 lakh budget; the extracted budget must be the customer's 200000,
        # and no name may be invented from the agent's pitch.
        r = analyze_transcript(INTERESTED_EN)
        self.assertEqual(r["customer_info"]["budget_inr"], 200000)
        self.assertNotEqual(r["customer_info"]["name"], "SolarKart")

    def test_why_reasons_have_evidence(self):
        r = analyze_transcript(INTERESTED_EN)
        self.assertTrue(r["why_interested"])
        for reason in r["why_interested"]:
            self.assertTrue(reason["evidence"])
        codes = [x["code"] for x in r["why_interested"]]
        self.assertIn("price_inquiry", codes)


class TestExports(unittest.TestCase):
    def test_excel_is_valid_xlsx_with_sheets(self):
        results = [analyze_transcript(INTERESTED_EN, "a.txt"),
                   analyze_transcript(NOT_INTERESTED_HINGLISH, "b.txt"),
                   analyze_transcript(CALLBACK, "c.txt")]
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "leads.xlsx")
            export_excel(results, path)
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                self.assertIn("xl/workbook.xml", names)
                self.assertIn("xl/worksheets/sheet2.xml", names)  # Interested sheet
                sheet1 = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertIn("Rohit Sharma", sheet1)
                self.assertIn("Why Not Interested", sheet1)
            # filtered export: only interested
            path2 = str(Path(td) / "interested_only.xlsx")
            export_excel(results, path2, which="interested")
            with zipfile.ZipFile(path2) as z:
                sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertIn("Rohit Sharma", sheet)
                self.assertNotIn("remove my number", sheet.lower())

    def test_csv_written(self):
        results = [analyze_transcript(INTERESTED_EN, "a.txt")]
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "out.csv")
            export_csv(results, path)
            text = Path(path).read_text(encoding="utf-8-sig")
            self.assertIn("Customer Name", text)
            self.assertIn("Rohit Sharma", text)


class TestFirstQuestionYes(unittest.TestCase):
    """Client policy (2026-10-29): a YES to the FIRST question shortlists
    the lead immediately — the old scoring counted a bare 'yes' as a weak
    +1 cue, so Q1-yes callers were never shortlisted."""

    def test_yes_to_first_question_shortlists(self):
        text = (
            "Agent: नमस्कार, मी Sunrise कडून बोलत आहे. आपल्याला माहिती ऐकायला आवडेल का?\n"
            "Customer: हो\n"
            "Agent: आपल्याकडे किती एकर जमीन आहे?\n"
            "Customer: पाच एकर आहे\n"
        )
        r = analyze_transcript(text)
        self.assertTrue(r["first_question_yes"])
        self.assertEqual(r["classification"], "INTERESTED")
        self.assertEqual(r["binary"], "INTERESTED")
        self.assertEqual(r["why_interested"][0]["code"], "first_question_yes")

    def test_english_yes_first_answer_shortlists(self):
        text = (
            "Agent: Hello, are you interested in our course?\n"
            "Customer: Yes\n"
            "Agent: Do you have prior experience?\n"
            "Customer: A little bit\n"
        )
        r = analyze_transcript(text)
        self.assertTrue(r["first_question_yes"])
        self.assertEqual(r["classification"], "INTERESTED")

    def test_opt_out_later_overrides_first_yes(self):
        text = (
            "Agent: नमस्कार, आपल्याला माहिती ऐकायला आवडेल का?\n"
            "Customer: हो\n"
            "Agent: ठीक आहे, पुढचा प्रश्न विचारते\n"
            "Customer: नाही थांबा, परत फोन करू नका\n"
        )
        r = analyze_transcript(text)
        self.assertFalse(r["first_question_yes"])
        self.assertEqual(r["classification"], "NOT_INTERESTED")

    def test_no_to_first_question_not_shortlisted(self):
        text = (
            "Agent: Are you interested in our course?\n"
            "Customer: No, I already have one\n"
            "Agent: Okay, thank you\n"
        )
        r = analyze_transcript(text)
        self.assertFalse(r["first_question_yes"])
        self.assertNotEqual(r["classification"], "INTERESTED")


if __name__ == "__main__":
    unittest.main()
