"""
Comprehensive Multilingual Customer Interest Evaluation Dataset.
Contains 170 structured examples covering English, Hindi, Marathi, Hinglish,
Marathish, Romanized Hindi, Romanized Marathi, and mixed-language code-switching.

Covers all 5 target categories:
- INTERESTED (40 examples)
- NOT_INTERESTED (40 examples)
- CALLBACK_REQUESTED (30 examples)
- NEEDS_INFORMATION (30 examples)
- UNCERTAIN (30 examples)
"""

from typing import List, Dict, Any

EVALUATION_DATASET: List[Dict[str, Any]] = [
    # =========================================================================
    # 1. INTERESTED (40 examples: High Intent & General Engagement)
    # =========================================================================
    {
        "id": "INT_EN_01",
        "transcript": "Agent: Would you like to try our premium marketing tool?\nCustomer: Yes, I'm interested.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Direct explicit expression of customer interest."
    },
    {
        "id": "INT_EN_02",
        "transcript": "Agent: We provide automated inventory management.\nCustomer: Tell me more.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Customer requests to hear more about the product."
    },
    {
        "id": "INT_EN_03",
        "transcript": "Agent: The setup takes less than two minutes.\nCustomer: That sounds good, send me the details.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Positive reaction followed by request for details."
    },
    {
        "id": "INT_EN_04",
        "transcript": "Agent: Our package is currently on a seasonal offer.\nCustomer: Please place my order.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Explicit request to book and place an order demonstrates HIGH buying intent."
    },
    {
        "id": "INT_EN_05",
        "transcript": "Agent: We offer enterprise security suites.\nCustomer: I want to buy it, send me the payment link.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Definitive purchase commitment with request for payment link."
    },
    {
        "id": "INT_EN_06",
        "transcript": "Agent: This course covers complete data science skills.\nCustomer: Can you give me a discount? I want to register.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Customer intends to register and requests purchase discount."
    },
    {
        "id": "INT_EN_07",
        "transcript": "Agent: The standard subscription is 2000 rupees.\nCustomer: It's expensive, but I'm interested.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "mixed_sentiment",
        "explanation": "Price objection accompanied by explicit interest affirmation."
    },
    {
        "id": "INT_EN_08",
        "transcript": "Agent: Would you like to know more about this product?\nCustomer: Yes, please explain.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "contextual_acknowledgement",
        "explanation": "Affirmative agreement following a product presentation inquiry."
    },
    {
        "id": "INT_EN_09",
        "transcript": "Agent: Are you interested in our rooftop solar installation?\nCustomer: Sure, can I get a demo first?",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Positive confirmation with request for demonstration."
    },
    {
        "id": "INT_EN_10",
        "transcript": "Agent: Our billing platform simplifies GST.\nCustomer: I am ready to proceed with the signup.",
        "language": "English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "High intent to immediately proceed with onboarding."
    },
    # Hindi Devanagari
    {
        "id": "INT_HI_11",
        "transcript": "Agent: क्या मैं आपको हमारे नए बिजनेस लोन के बारे में बता सकता हूँ?\nCustomer: हाँ, मुझे इसमें रुचि है।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Direct expression of interest in Hindi Devanagari."
    },
    {
        "id": "INT_HI_12",
        "transcript": "Agent: यह मशीन पानी को 99.9% शुद्ध करती है।\nCustomer: मुझे इसके बारे में और जानकारी चाहिए।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Customer requests more detailed information."
    },
    {
        "id": "INT_HI_13",
        "transcript": "Agent: हमारे पास फसल सुरक्षा के नए उत्पाद हैं।\nCustomer: इसके बारे में विस्तार से बताइए।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Customer requests an in-depth explanation."
    },
    {
        "id": "INT_HI_14",
        "transcript": "Agent: हमारे पास केवल 5 स्लॉट बचे हैं।\nCustomer: मुझे यह खरीदना है, मेरा ऑर्डर बुक कर दीजिए।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "High buying intent to immediately purchase and book order."
    },
    {
        "id": "INT_HI_15",
        "transcript": "Agent: यह सॉफ्टवेयर सभी बिल ऑटोमेटिक बनाता है।\nCustomer: मैं इसे लेना चाहता हूँ।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Direct purchase willingness expressed by customer."
    },
    {
        "id": "INT_HI_16",
        "transcript": "Agent: हमारे पास नया हेल्थ इन्श्योरेंस प्लान है।\nCustomer: मैं इसे लेना चाहती हूँ।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Female grammatical variant of purchase intent."
    },
    {
        "id": "INT_HI_17",
        "transcript": "Agent: इस पैकेज में 1 साल की वारंटी है।\nCustomer: मुझे पूरी जानकारी व्हाट्सएप पर भेज दीजिए।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Request to send details via messaging channel."
    },
    {
        "id": "INT_HI_18",
        "transcript": "Agent: कोर्स की फीस 5000 रुपये है।\nCustomer: क्या इसमें कोई छूट मिलेगी? मुझे एडमिशन लेना है।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Discount inquiry tied to explicit intent to take admission."
    },
    {
        "id": "INT_HI_19",
        "transcript": "Agent: हम सोलर इन्वर्टर सप्लाई करते हैं।\nCustomer: मुझे यह उत्पाद चाहिए, आगे की प्रक्रिया बताइए।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Direct requirement stated with request for next procurement steps."
    },
    {
        "id": "INT_HI_20",
        "transcript": "Agent: हमारी सर्विस का मासिक शुल्क 1000 रुपये है।\nCustomer: महंगा है, लेकिन मुझे रुचि है।",
        "language": "Hindi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "mixed_sentiment",
        "explanation": "Price objection overridden by positive interest affirmation."
    },
    # Marathi Devanagari
    {
        "id": "INT_MR_21",
        "transcript": "Agent: आम्ही शेतीसाठी ठिबक सिंचन योजना देत आहोत.\nCustomer: हो, मला यात रस आहे.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Direct Marathi affirmation of customer interest."
    },
    {
        "id": "INT_MR_22",
        "transcript": "Agent: आम्ही दुग्ध व्यवसायासाठी ऑटोमेशन मशीन पुरवतो.\nCustomer: मला याबद्दल अधिक माहिती हवी आहे.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Customer requests more information in Marathi."
    },
    {
        "id": "INT_MR_23",
        "transcript": "Agent: आमच्याकडे सौर पंप उपलब्ध आहेत.\nCustomer: मला हे घ्यायचे आहे.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Direct purchase desire in Marathi."
    },
    {
        "id": "INT_MR_24",
        "transcript": "Agent: आमचे डिजिटल बिलिंग मशीन सोपे आहे.\nCustomer: मला हे खरेदी करायचे आहे, माझी ऑर्डर बुक करा.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "High intent to buy and book order in Marathi."
    },
    {
        "id": "INT_MR_25",
        "transcript": "Agent: आमची सर्व्हिस 24 तास सुरू असते.\nCustomer: मला माहिती व्हॉट्सअॅपवर पाठवा.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Customer requests details over WhatsApp in Marathi."
    },
    {
        "id": "INT_MR_26",
        "transcript": "Agent: या मशीनची किंमत 15000 रुपये आहे.\nCustomer: काही सूट मिळेल का? पुढची प्रक्रिया सांगा.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Discount query tied to next procedural steps to buy."
    },
    {
        "id": "INT_MR_27",
        "transcript": "Agent: आम्ही सेंद्रिय खते थेट पोहोचवतो.\nCustomer: मला हे उत्पादन पाहिजे, मला याबद्दल सविस्तर सांगा.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Product wanted with detailed inquiry."
    },
    {
        "id": "INT_MR_28",
        "transcript": "Agent: हे मॉडेल थोडे प्रीमियम आहे.\nCustomer: महाग आहे, पण घ्यायचे आहे.",
        "language": "Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "mixed_sentiment",
        "explanation": "Cost objection with explicit resolution to purchase in Marathi."
    },
    # Hinglish & Romanized Hindi
    {
        "id": "INT_HG_29",
        "transcript": "Agent: Sir hamari company cyber security training provide karti hai.\nCustomer: Haan, mujhe interest hai.",
        "language": "Hinglish",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Romanized Hindi affirmation of interest."
    },
    {
        "id": "INT_HG_30",
        "transcript": "Agent: We have launched an online tax filing system.\nCustomer: Mujhe iske baare mein bataiye, sun raha hu.",
        "language": "Hinglish",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Hinglish request to explain the product."
    },
    {
        "id": "INT_HG_31",
        "transcript": "Agent: Our stock trading toolkit has high accuracy.\nCustomer: Mujhe order karna hai, payment link bhej do.",
        "language": "Hinglish",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Romanized Hindi explicit order and payment link request."
    },
    {
        "id": "INT_HG_32",
        "transcript": "Agent: We can install fiber broadband at your shop.\nCustomer: Haan bhai, booking kardo mere naam se.",
        "language": "Hinglish",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Colloquial booking request in Hinglish."
    },
    {
        "id": "INT_HG_33",
        "transcript": "Agent: We have special coaching for competitive exams.\nCustomer: WhatsApp pe details bhej sakte ho?",
        "language": "Hinglish",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Hinglish request for WhatsApp information."
    },
    {
        "id": "INT_HG_34",
        "transcript": "Agent: Annual plan 12000 ka padega.\nCustomer: Mehnga lag raha hai, lekin main ready hoon lene ke liye.",
        "language": "Hinglish",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "mixed_sentiment",
        "explanation": "Objection overridden by ready-to-buy signal."
    },
    # Marathish & Romanized Marathi
    {
        "id": "INT_MRR_35",
        "transcript": "Agent: Namaskar sir, solar water heater offers suru ahet.\nCustomer: Ho, mala mahiti pahije.",
        "language": "Romanized Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "direct_positive",
        "explanation": "Romanized Marathi expression of interest."
    },
    {
        "id": "INT_MRR_36",
        "transcript": "Agent: Aamhi commercial kitchen equipment deto.\nCustomer: Mala he ghyaycha aahe, details pathva.",
        "language": "Romanized Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Romanized Marathi desire to purchase and receive details."
    },
    {
        "id": "INT_MRR_37",
        "transcript": "Agent: Aamhi loan approval 24 tasat karto.\nCustomer: Ho sir, details pathva na.",
        "language": "Romanized Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "general_interest",
        "explanation": "Romanized Marathi confirmation with request for details."
    },
    {
        "id": "INT_MRR_38",
        "transcript": "Agent: Would you like to attend the tech workshop in Pune?\nCustomer: Yes sir, mala information pahije, registration link dya.",
        "language": "Mixed Marathi-English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Mixed Marathi-English code-switching asking for registration."
    },
    {
        "id": "INT_MRR_39",
        "transcript": "Agent: Machine chi cost thodi jasti aahe.\nCustomer: Mahag aahe pan mala nakki ghyayche aahe.",
        "language": "Romanized Marathi",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "MEDIUM",
        "test_category": "mixed_sentiment",
        "explanation": "Objection with strong commitment in Romanized Marathi."
    },
    {
        "id": "INT_MIX_40",
        "transcript": "Agent: We provide integrated retail accounting.\nCustomer: Sounds good, mala yachi booking karaychi aahe.",
        "language": "Mixed Marathi-English",
        "expected_classification": "INTERESTED",
        "expected_interest_strength": "HIGH",
        "test_category": "strong_buying",
        "explanation": "Code-mixed English-Marathi booking request."
    },

    # =========================================================================
    # 2. NOT_INTERESTED (40 examples: Direct Rejection, DNC, Indirect Refusal)
    # =========================================================================
    {
        "id": "NOT_EN_41",
        "transcript": "Agent: Would you like to switch to our broadband plan?\nCustomer: I'm not interested.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Direct explicit rejection."
    },
    {
        "id": "NOT_EN_42",
        "transcript": "Agent: We are offering personal loans at low interest.\nCustomer: No, thank you.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "polite_rejection",
        "explanation": "Polite rejection statement."
    },
    {
        "id": "NOT_EN_43",
        "transcript": "Agent: Can I tell you about our new insurance policy?\nCustomer: I don't need this.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Customer expresses lack of need for the offer."
    },
    {
        "id": "NOT_EN_44",
        "transcript": "Agent: This water filter has multi-stage filtration.\nCustomer: I don't want this product, I'm not going to buy it.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Clear refusal to purchase product."
    },
    {
        "id": "NOT_EN_45",
        "transcript": "Agent: We offer car maintenance packages.\nCustomer: This isn't useful to me, I already have a similar product.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Customer already possesses an equivalent solution."
    },
    {
        "id": "NOT_EN_46",
        "transcript": "Agent: We can upgrade your website security.\nCustomer: It's not relevant to me. Please don't call me again.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "Irrelevant offer with explicit do-not-contact demand."
    },
    {
        "id": "NOT_EN_47",
        "transcript": "Agent: Can I speak with the business owner regarding credit cards?\nCustomer: Remove my number from your list, I don't want any more calls.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "Hard opt-out demanding removal from calling list."
    },
    {
        "id": "NOT_EN_48",
        "transcript": "Agent: Would you like to review our real estate options?\nCustomer: I have no interest in this offer.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Customer affirms zero interest."
    },
    {
        "id": "NOT_EN_49",
        "transcript": "Agent: We are upgrading telecom subscriptions today.\nCustomer: No, thanks. Maybe another time.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "polite_rejection",
        "explanation": "Indirect polite dismissal without request for callback."
    },
    {
        "id": "NOT_EN_50",
        "transcript": "Agent: Can we send you our cloud storage quote?\nCustomer: I'm happy with my current product, I don't need anything right now.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "polite_rejection",
        "explanation": "Satisfaction with existing provider precludes interest."
    },
    {
        "id": "NOT_EN_51",
        "transcript": "Agent: Is this Mr. Sharma from Apex Enterprises?\nCustomer: Wrong number, you have the wrong person.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "wrong_person",
        "explanation": "Wrong person reached; caller is not relevant."
    },
    {
        "id": "NOT_EN_52",
        "transcript": "Agent: Our annual membership is 50000 rupees.\nCustomer: It's expensive. I don't want it.",
        "language": "English",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "mixed_sentiment_rejection",
        "explanation": "Cost objection followed by definite rejection."
    },
    # Hindi Devanagari
    {
        "id": "NOT_HI_53",
        "transcript": "Agent: क्या आपको लोन की आवश्यकता है?\nCustomer: मुझे इसमें रुचि नहीं है।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Direct refusal of interest in Hindi."
    },
    {
        "id": "NOT_HI_54",
        "transcript": "Agent: हम आयुर्वेदिक दवाओं की होम डिलीवरी करते हैं।\nCustomer: मुझे यह नहीं चाहिए, मुझे इसकी जरूरत नहीं है।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Direct lack of requirement in Hindi."
    },
    {
        "id": "NOT_HI_55",
        "transcript": "Agent: यह नया स्मार्टफोन बहुत किफायती है।\nCustomer: मैं इसे नहीं खरीदना चाहता।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Male refusal to buy in Hindi."
    },
    {
        "id": "NOT_HI_56",
        "transcript": "Agent: हमारी ब्यूटी सर्विस पर 50% छूट है।\nCustomer: मैं इसे नहीं खरीदना चाहती।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Female refusal to buy in Hindi."
    },
    {
        "id": "NOT_HI_57",
        "transcript": "Agent: हम वाटर प्यूरीफायर सर्विस दे रहे हैं।\nCustomer: मुझे यह उत्पाद नहीं चाहिए, मुझे इस ऑफर में दिलचस्पी नहीं है।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Unambiguous lack of interest in offer."
    },
    {
        "id": "NOT_HI_58",
        "transcript": "Agent: सर क्रेडिट कार्ड का स्पेशल ऑफर है।\nCustomer: कृपया मुझे दोबारा फोन मत कीजिए। मेरा नंबर अपनी लिस्ट से हटा दीजिए।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "Hindi DNC request demanding list removal."
    },
    {
        "id": "NOT_HI_59",
        "transcript": "Agent: क्या आप हमारी बीमा योजना देखना चाहेंगे?\nCustomer: मुझे आगे से कॉल मत कीजिए, मुझे इसकी जानकारी नहीं चाहिए।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "Explicit instruction not to contact again."
    },
    {
        "id": "NOT_HI_60",
        "transcript": "Agent: क्या मैं आपको हमारे इन्वेस्टमेंट प्लान समझा सकता हूँ?\nCustomer: रहने दीजिए, मुझे नहीं चाहिए।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "polite_rejection",
        "explanation": "Colloquial dismissal in Hindi."
    },
    {
        "id": "NOT_HI_61",
        "transcript": "Agent: नमस्ते, क्या आप सुनील जी से बात करा सकते हैं?\nCustomer: गलत नंबर है, परेशान मत करो।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "wrong_person",
        "explanation": "Wrong number reached."
    },
    {
        "id": "NOT_HI_62",
        "transcript": "Agent: यह मशीन 50000 रुपये की है।\nCustomer: बहुत महंगा है, नहीं चाहिए।",
        "language": "Hindi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "mixed_sentiment_rejection",
        "explanation": "Cost complaint ending in explicit refusal."
    },
    # Marathi Devanagari
    {
        "id": "NOT_MR_63",
        "transcript": "Agent: आम्ही नवीन विमा पॉलिसी आणली आहे.\nCustomer: मला यात रस नाही.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Marathi statement of zero interest."
    },
    {
        "id": "NOT_MR_64",
        "transcript": "Agent: सोलर पॅनेल इन्स्टॉल करून घ्या.\nCustomer: मला हे नको आहे, मला याची गरज नाही.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Direct lack of requirement in Marathi."
    },
    {
        "id": "NOT_MR_65",
        "transcript": "Agent: शेतीसाठी ट्रॅक्टर लोन उपलब्ध आहे.\nCustomer: मला हे घ्यायचे नाही, मला हे खरेदी करायचे नाही.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Customer refuses to buy in Marathi."
    },
    {
        "id": "NOT_MR_66",
        "transcript": "Agent: आमच्याकडे सणासुदीचा खास ऑफर आहे.\nCustomer: मला हा ऑफर नको आहे, हे माझ्या उपयोगाचे नाही.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Offer not useful for customer."
    },
    {
        "id": "NOT_MR_67",
        "transcript": "Agent: क्रेडिट कार्ड लिमिट वाढवून मिळेल.\nCustomer: मला पुन्हा फोन करू नका, माझा नंबर यादीतून काढून टाका.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "Marathi DNC demanding number deletion."
    },
    {
        "id": "NOT_MR_68",
        "transcript": "Agent: आम्ही बिझनेस लोन देतो.\nCustomer: मला यापुढे कॉल करू नका, मला यात अजिबात रस नाही.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "No further calls wanted in Marathi."
    },
    {
        "id": "NOT_MR_69",
        "transcript": "Agent: आमची नवीन सेवा सुरू झाली आहे.\nCustomer: राहू द्या, काही नको.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "polite_rejection",
        "explanation": "Colloquial Marathi dismissal."
    },
    {
        "id": "NOT_MR_70",
        "transcript": "Agent: हॅलो, मी श्री. देशमुखांशी बोलतोय का?\nCustomer: चुकीचा नंबर आहे, फोन ठेवा.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "wrong_person",
        "explanation": "Wrong number in Marathi."
    },
    {
        "id": "NOT_MR_71",
        "transcript": "Agent: या उत्पादनाची किंमत 5000 रुपये आहे.\nCustomer: महाग आहे, नको.",
        "language": "Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "mixed_sentiment_rejection",
        "explanation": "Expensive objection resulting in Marathi refusal."
    },
    # Hinglish & Romanized
    {
        "id": "NOT_HG_72",
        "transcript": "Agent: Sir hum cloud backup provide karte hain.\nCustomer: Nahi chahiye.",
        "language": "Hinglish",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Direct Hinglish refusal."
    },
    {
        "id": "NOT_HG_73",
        "transcript": "Agent: We are providing website development.\nCustomer: Mujhe interest nahi hai, time waste mat karo.",
        "language": "Hinglish",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Zero interest stated in Hinglish."
    },
    {
        "id": "NOT_HG_74",
        "transcript": "Agent: Special loan offer available today.\nCustomer: Mujhe iski zarurat nahi hai, pehle se loan hai.",
        "language": "Hinglish",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Customer lacks need in Hinglish."
    },
    {
        "id": "NOT_HG_75",
        "transcript": "Agent: Sir telecom sim upgrade kar lijiye.\nCustomer: Dobara call mat karna, number delete kar do mera.",
        "language": "Hinglish",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "Hinglish DNC request."
    },
    {
        "id": "NOT_HG_76",
        "transcript": "Agent: Can I explain the discount coupons?\nCustomer: Rehne do bhai, nahi chahiye.",
        "language": "Hinglish",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "polite_rejection",
        "explanation": "Colloquial refusal in Hinglish."
    },
    # Marathish & Romanized Marathi
    {
        "id": "NOT_MRR_77",
        "transcript": "Agent: Sir solar pump yojana baddal boltoy.\nCustomer: Mala nako aahe.",
        "language": "Romanized Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "Direct refusal in Romanized Marathi."
    },
    {
        "id": "NOT_MRR_78",
        "transcript": "Agent: We have tractor servicing offers.\nCustomer: Mala yat interest nahi, mala yachi garaj nahi.",
        "language": "Romanized Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "direct_negative",
        "explanation": "No interest or need in Romanized Marathi."
    },
    {
        "id": "NOT_MRR_79",
        "transcript": "Agent: Would you like to check our new health card?\nCustomer: Nako sir, thank you. No sir, mala nako.",
        "language": "Romanized Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "polite_rejection",
        "explanation": "Polite bilingual refusal in Marathish."
    },
    {
        "id": "NOT_MRR_80",
        "transcript": "Agent: Namaskar, credit card verification sathi call kela hota.\nCustomer: Punha phone karu naka, number kadhun taka list madhun.",
        "language": "Romanized Marathi",
        "expected_classification": "NOT_INTERESTED",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "opt_out",
        "explanation": "DNC request in Romanized Marathi."
    },

    # =========================================================================
    # 3. CALLBACK_REQUESTED (30 examples: Specific and General Callback)
    # =========================================================================
    {
        "id": "CB_EN_81",
        "transcript": "Agent: Hello, calling regarding health checkup packages.\nCustomer: Call me tomorrow.",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Explicit request for tomorrow callback."
    },
    {
        "id": "CB_EN_82",
        "transcript": "Agent: We are offering corporate tax audit consultations.\nCustomer: Please call me later, I'm busy right now.",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Customer is busy, requests later call without rejection."
    },
    {
        "id": "CB_EN_83",
        "transcript": "Agent: Calling from Zenith Financial.\nCustomer: Call me in the evening.",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Evening callback window requested."
    },
    {
        "id": "CB_EN_84",
        "transcript": "Agent: Would you like to review our fleet management solution?\nCustomer: I'm busy now; call later.",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Unavailable now, asks to call later."
    },
    {
        "id": "CB_EN_85",
        "transcript": "Agent: We have new real estate developments in North Sector.\nCustomer: Can you call next week?",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Next week callback window."
    },
    {
        "id": "CB_EN_86",
        "transcript": "Agent: Calling regarding business loan schemes.\nCustomer: Call me after lunch.",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Post-lunch callback requested."
    },
    {
        "id": "CB_EN_87",
        "transcript": "Agent: Sir we have solar panel offers.\nCustomer: I am currently driving, call me back in an hour.",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Driver temporarily occupied, asks for call in an hour."
    },
    {
        "id": "CB_EN_88",
        "transcript": "Agent: Hello from Apex Cloud Services.\nCustomer: I am in a meeting right now, please reach out tomorrow.",
        "language": "English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Customer occupied in meeting, asks for tomorrow call."
    },
    # Hindi Devanagari
    {
        "id": "CB_HI_89",
        "transcript": "Agent: नमस्ते, हम बिजनेस इंश्योरेंस के बारे में बात कर रहे हैं।\nCustomer: मुझे कल फोन कीजिए।",
        "language": "Hindi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Tomorrow callback requested in Hindi."
    },
    {
        "id": "CB_HI_90",
        "transcript": "Agent: क्या आप अपने खाते की लिमिट बढ़ाना चाहते हैं?\nCustomer: बाद में कॉल कीजिए।",
        "language": "Hindi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Later callback requested in Hindi."
    },
    {
        "id": "CB_HI_91",
        "transcript": "Agent: सर हम डिजिटल बिलिंग सॉफ्टवेयर उपलब्ध कराते हैं।\nCustomer: शाम को फोन करना।",
        "language": "Hindi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Evening callback in Hindi."
    },
    {
        "id": "CB_HI_92",
        "transcript": "Agent: हमारे पास नया क्रेडिट कार्ड ऑफर है।\nCustomer: अभी व्यस्त हूँ, बाद में फोन करना।",
        "language": "Hindi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Busy currently, requests later call in Hindi."
    },
    {
        "id": "CB_HI_93",
        "transcript": "Agent: क्या मैं आपको हमारे इन्वेस्टमेंट प्लान के बारे में बताऊँ?\nCustomer: अगले हफ्ते फोन कीजिए।",
        "language": "Hindi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Next week callback in Hindi."
    },
    {
        "id": "CB_HI_94",
        "transcript": "Agent: नमस्ते, सोलर पैनल योजना के संदर्भ में कॉल है।\nCustomer: मुझे शाम को कॉल करिए।",
        "language": "Hindi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Evening callback instruction in Hindi."
    },
    {
        "id": "CB_HI_95",
        "transcript": "Agent: सर हम ट्रैक्टर फाइनेंसिंग स्कीम के बारे में बात कर रहे हैं।\nCustomer: अभी गाड़ी चला रहा हूँ, एक घंटे बाद बात करना।",
        "language": "Hindi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Driving currently, asks for call after 1 hour."
    },
    # Marathi Devanagari
    {
        "id": "CB_MR_96",
        "transcript": "Agent: आम्ही सोलर रूफटॉप योजनेबद्दल बोलत आहोत.\nCustomer: मला उद्या फोन करा.",
        "language": "Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Tomorrow callback requested in Marathi."
    },
    {
        "id": "CB_MR_97",
        "transcript": "Agent: नमस्कार, शेतीसाठी नवीन सिंचन उपकरणे उपलब्ध आहेत.\nCustomer: नंतर फोन करा.",
        "language": "Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Later callback in Marathi."
    },
    {
        "id": "CB_MR_98",
        "transcript": "Agent: आम्ही बिझनेस लोन देतो.\nCustomer: संध्याकाळी फोन करा.",
        "language": "Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Evening callback in Marathi."
    },
    {
        "id": "CB_MR_99",
        "transcript": "Agent: आमच्याकडे नवीन विमा योजना आहे.\nCustomer: आत्ता वेळ नाही, नंतर फोन करा.",
        "language": "Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "No time currently, call later in Marathi."
    },
    {
        "id": "CB_MR_100",
        "transcript": "Agent: दुग्ध व्यवसायासाठी ऑटोमेशन मशीन बद्दल बोलायचे होते.\nCustomer: पुढच्या आठवड्यात फोन करा.",
        "language": "Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Next week callback in Marathi."
    },
    {
        "id": "CB_MR_101",
        "transcript": "Agent: ट्रॅक्टर लोन योजना उपलब्ध आहे.\nCustomer: जेवणानंतर फोन करा.",
        "language": "Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Post-meal callback in Marathi."
    },
    {
        "id": "CB_MR_102",
        "transcript": "Agent: नमस्ते सर, क्रेडिट कार्ड बद्दल माहिती द्यायची आहे.\nCustomer: मी गाडी चालवतोय, नंतर फोन करा.",
        "language": "Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Driving currently in Marathi."
    },
    # Hinglish & Romanized
    {
        "id": "CB_HG_103",
        "transcript": "Agent: Sir telecom sim upgrade offers available.\nCustomer: Kal call karna.",
        "language": "Hinglish",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Tomorrow callback in Hinglish."
    },
    {
        "id": "CB_HG_104",
        "transcript": "Agent: We are calling regarding online accounting software.\nCustomer: Baad mein phone karna.",
        "language": "Hinglish",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Later callback in Hinglish."
    },
    {
        "id": "CB_HG_105",
        "transcript": "Agent: Special trade account discounts available.\nCustomer: Shaam ko call karna.",
        "language": "Hinglish",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Evening callback in Hinglish."
    },
    {
        "id": "CB_HG_106",
        "transcript": "Agent: Sir health policy renewal reminder.\nCustomer: Abhi busy hoon, baad me call karo.",
        "language": "Hinglish",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Currently busy in Hinglish."
    },
    # Marathish & Romanized Marathi
    {
        "id": "CB_MRR_107",
        "transcript": "Agent: Namaskar sir, solar rooftop subsidy badal bolayche hote.\nCustomer: Ata vel nahi, nantar phone kara.",
        "language": "Romanized Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "No time now, call later in Romanized Marathi."
    },
    {
        "id": "CB_MRR_108",
        "transcript": "Agent: Krishi yojana antargat loan offer ahe.\nCustomer: Udya phone kara.",
        "language": "Romanized Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Tomorrow callback in Romanized Marathi."
    },
    {
        "id": "CB_MRR_109",
        "transcript": "Agent: Business automation machine badal aamhi mahiti det aahot.\nCustomer: Nantar call kara.",
        "language": "Romanized Marathi",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Later call in Romanized Marathi."
    },
    {
        "id": "CB_MIX_110",
        "transcript": "Agent: I am calling from Apollo diagnostics.\nCustomer: I'm in meeting right now, shaam ko 6 baje phone kara.",
        "language": "Mixed Marathi-English",
        "expected_classification": "CALLBACK_REQUESTED",
        "expected_interest_strength": "LOW",
        "test_category": "callback",
        "explanation": "Code-mixed English-Marathi specific time callback."
    },

    # =========================================================================
    # 4. NEEDS_INFORMATION (30 examples: Exploration, Price, How it Works)
    # =========================================================================
    {
        "id": "INF_EN_111",
        "transcript": "Agent: We provide cloud hosting solutions.\nCustomer: What is the price?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Price inquiry alone indicates exploratory information seeking."
    },
    {
        "id": "INF_EN_112",
        "transcript": "Agent: Our CRM software automates customer outreach.\nCustomer: What are the benefits?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Customer explores value proposition and benefits."
    },
    {
        "id": "INF_EN_113",
        "transcript": "Agent: We have launched an AI calling solution.\nCustomer: Can you explain it? How does it work?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Customer inquires about operational mechanism."
    },
    {
        "id": "INF_EN_114",
        "transcript": "Agent: We provide corporate health coverage.\nCustomer: What are the available options?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Customer asks about plan options."
    },
    {
        "id": "INF_EN_115",
        "transcript": "Agent: Our professional package starts at $50 per month.\nCustomer: Is there a cheaper option?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Customer explores lower-cost alternatives."
    },
    {
        "id": "INF_EN_116",
        "transcript": "Agent: We offer turnkey solar installation.\nCustomer: What is included in the package?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Customer inquires about package inclusions."
    },
    {
        "id": "INF_EN_117",
        "transcript": "Agent: We have enterprise fiber connections.\nCustomer: How long does the setup take?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Setup duration inquiry."
    },
    {
        "id": "INF_EN_118",
        "transcript": "Agent: Our billing software supports multi-store operations.\nCustomer: Is there a free trial period?",
        "language": "English",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Trial exploration inquiry."
    },
    # Hindi Devanagari
    {
        "id": "INF_HI_119",
        "transcript": "Agent: हम डिजिटल बिलिंग मशीन उपलब्ध कराते हैं।\nCustomer: इसकी कीमत क्या है?",
        "language": "Hindi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Hindi price inquiry."
    },
    {
        "id": "INF_HI_120",
        "transcript": "Agent: हमारे पास जैविक कीटनाशक का नया फॉर्मूला है।\nCustomer: इसके क्या फायदे हैं?",
        "language": "Hindi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Benefits inquiry in Hindi."
    },
    {
        "id": "INF_HI_121",
        "transcript": "Agent: यह सोलर ड्रायर सब्जियों को सुखाता है।\nCustomer: यह कैसे काम करता है?",
        "language": "Hindi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Operational mechanism inquiry in Hindi."
    },
    {
        "id": "INF_HI_122",
        "transcript": "Agent: हम स्मार्ट वाटर फिल्टर की बात कर रहे हैं।\nCustomer: क्या आप समझा सकते हैं?",
        "language": "Hindi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Request for explanation in Hindi."
    },
    {
        "id": "INF_HI_123",
        "transcript": "Agent: हमारे पास हेल्थ पॉलिसी के विभिन्न प्लान हैं।\nCustomer: इसके दूसरे विकल्प क्या हैं?",
        "language": "Hindi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Plan options inquiry in Hindi."
    },
    {
        "id": "INF_HI_124",
        "transcript": "Agent: यह मशीन 25000 रुपये की है।\nCustomer: क्या कोई सस्ता विकल्प है?",
        "language": "Hindi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Cheaper option inquiry in Hindi."
    },
    {
        "id": "INF_HI_125",
        "transcript": "Agent: हम ऑनलाइन कोचिंग देते हैं।\nCustomer: पैकेज में क्या-क्या शामिल है?",
        "language": "Hindi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Package inclusion inquiry in Hindi."
    },
    # Marathi Devanagari
    {
        "id": "INF_MR_126",
        "transcript": "Agent: आम्ही शेतीसाठी ठिबक सिंचन युनिट पुरवतो.\nCustomer: याची किंमत किती आहे?",
        "language": "Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Price inquiry in Marathi."
    },
    {
        "id": "INF_MR_127",
        "transcript": "Agent: आमच्या सेंद्रिय खतामुळे मातीचा पोत सुधारतो.\nCustomer: याचे फायदे काय आहेत?",
        "language": "Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Benefits inquiry in Marathi."
    },
    {
        "id": "INF_MR_128",
        "transcript": "Agent: आमचे सोलर इन्व्हर्टर लोड शेडिंगवर चालते.\nCustomer: हे कसे काम करते?",
        "language": "Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Mechanism inquiry in Marathi."
    },
    {
        "id": "INF_MR_129",
        "transcript": "Agent: आम्ही डिजिटल पेमेंट मशीन बद्दल सांगत आहोत.\nCustomer: तुम्ही समजावून सांगू शकता का?",
        "language": "Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Explanation request in Marathi."
    },
    {
        "id": "INF_MR_130",
        "transcript": "Agent: आम्ही दुग्ध व्यवसायासाठी ऑटोमेशन देतो.\nCustomer: दुसरे पर्याय आहेत का?",
        "language": "Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Alternatives inquiry in Marathi."
    },
    {
        "id": "INF_MR_131",
        "transcript": "Agent: हा सिंचन संच 18000 रुपयांचा आहे.\nCustomer: यापेक्षा स्वस्त पर्याय आहे का?",
        "language": "Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Cheaper alternative inquiry in Marathi."
    },
    # Hinglish & Romanized
    {
        "id": "INF_HG_132",
        "transcript": "Agent: Sir hum business inventory tracking service provide karte hain.\nCustomer: Price kitna hai?",
        "language": "Hinglish",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Price inquiry in Hinglish."
    },
    {
        "id": "INF_HG_133",
        "transcript": "Agent: We offer cloud payroll management.\nCustomer: Kaise work karta hai?",
        "language": "Hinglish",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Operational inquiry in Hinglish."
    },
    {
        "id": "INF_HG_134",
        "transcript": "Agent: We have launched automated customer support agents.\nCustomer: Kya benefits hain iske?",
        "language": "Hinglish",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Benefits inquiry in Hinglish."
    },
    {
        "id": "INF_HG_135",
        "transcript": "Agent: Gold membership 20000 per year.\nCustomer: Koi sasta option hai kya?",
        "language": "Hinglish",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Cheaper alternative inquiry in Hinglish."
    },
    {
        "id": "INF_HG_136",
        "transcript": "Agent: Fleet GPS trackers with fuel sensors.\nCustomer: Package me kya kya milega?",
        "language": "Hinglish",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Package components inquiry in Hinglish."
    },
    # Marathish & Romanized Marathi
    {
        "id": "INF_MRR_137",
        "transcript": "Agent: Namaskar sir, solar water heater installation det aahot.\nCustomer: Yachi price kiti aahe?",
        "language": "Romanized Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Price inquiry in Romanized Marathi."
    },
    {
        "id": "INF_MRR_138",
        "transcript": "Agent: Krishi micro-irrigation unit badal bolat aahot.\nCustomer: Kasa work karto he?",
        "language": "Romanized Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Mechanism inquiry in Romanized Marathi."
    },
    {
        "id": "INF_MRR_139",
        "transcript": "Agent: Aamhi commercial billing software dakhvat aahot.\nCustomer: Dusre kahi options ahet ka? Kahi swasta option aahe ka?",
        "language": "Romanized Marathi",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Cheaper option inquiry in Romanized Marathi."
    },
    {
        "id": "INF_MIX_140",
        "transcript": "Agent: Calling from Zenith Cloud solutions.\nCustomer: What is the cost, kitna padega monthly?",
        "language": "Hinglish",
        "expected_classification": "NEEDS_INFORMATION",
        "expected_interest_strength": "MEDIUM",
        "test_category": "needs_information",
        "explanation": "Bilingual cost inquiry."
    },

    # =========================================================================
    # 5. UNCERTAIN (30 examples: Hesitation, Family Discussion, Ambiguity, Indecision)
    # =========================================================================
    {
        "id": "UNC_EN_141",
        "transcript": "Agent: Would you like to sign up for our gym membership?\nCustomer: Maybe.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "ambiguity",
        "explanation": "Single word ambiguous response without commitment."
    },
    {
        "id": "UNC_EN_142",
        "transcript": "Agent: We are enrolling candidates for the coding bootcamp.\nCustomer: I'll think about it.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Customer needs deliberation time."
    },
    {
        "id": "UNC_EN_143",
        "transcript": "Agent: Do you want to upgrade your car insurance?\nCustomer: I'm not sure.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Direct statement of uncertainty."
    },
    {
        "id": "UNC_EN_144",
        "transcript": "Agent: We have limited units remaining in Phase 2.\nCustomer: Let me decide, I'll discuss it with my family.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "family_discussion",
        "explanation": "Customer must discuss with family before deciding."
    },
    {
        "id": "UNC_EN_145",
        "transcript": "Agent: The offer expires at the end of the week.\nCustomer: I'll let you know, not right now.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Postponement without commitment."
    },
    {
        "id": "UNC_EN_146",
        "transcript": "Agent: Would you like to place a preliminary deposit?\nCustomer: I need some time to decide.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Deliberation time requested."
    },
    {
        "id": "UNC_EN_147",
        "transcript": "Agent: Am I speaking with Mr. Patil?\nCustomer: Yes.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "contextual_acknowledgement",
        "explanation": "Agreement to identity verification cannot infer product interest."
    },
    {
        "id": "UNC_EN_148",
        "transcript": "Agent: Hello, can you hear me clearly?\nCustomer: Yeah.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "contextual_acknowledgement",
        "explanation": "Audio connection confirmation is neutral."
    },
    {
        "id": "UNC_EN_149",
        "transcript": "Agent: Do you want our financial advisory plan?\nCustomer: I'm not sure if I'm interested.",
        "language": "English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "negation_nuance",
        "explanation": "Explicit statement that customer is unsure if interested."
    },
    # Hindi Devanagari
    {
        "id": "UNC_HI_150",
        "transcript": "Agent: क्या आप हमारी नई सर्विस लेना चाहेंगे?\nCustomer: शायद।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "ambiguity",
        "explanation": "Ambiguous one-word response in Hindi."
    },
    {
        "id": "UNC_HI_151",
        "transcript": "Agent: यह वाटर प्यूरीफायर आपके परिवार के लिए उपयोगी है।\nCustomer: सोचकर बताऊँगा।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Male deliberation statement in Hindi."
    },
    {
        "id": "UNC_HI_152",
        "transcript": "Agent: हमारी ब्यूटी मेंबरशिप पर विशेष छूट है।\nCustomer: सोचकर बताऊँगी।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Female deliberation statement in Hindi."
    },
    {
        "id": "UNC_HI_153",
        "transcript": "Agent: क्या हम आपकी पॉलिसी रिन्यू कर दें?\nCustomer: अभी तय नहीं किया है, मुझे थोड़ा समय चाहिए।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Undecided customer requesting time in Hindi."
    },
    {
        "id": "UNC_HI_154",
        "transcript": "Agent: इस कोर्स में प्रैक्टिकल ट्रेनिंग मिलेगी।\nCustomer: घर पर पूछकर बताऊँगा।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "family_discussion",
        "explanation": "Family consultation required before deciding."
    },
    {
        "id": "UNC_HI_155",
        "transcript": "Agent: क्या आपको इस पैकेज में रुचि है?\nCustomer: अभी नहीं पता, बाद में बताता हूँ।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Customer does not know currently."
    },
    {
        "id": "UNC_HI_156",
        "transcript": "Agent: क्या मैं राजेश जी से बात कर रहा हूँ?\nCustomer: हाँ।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "contextual_acknowledgement",
        "explanation": "Identity confirmation in Hindi does not infer buying intent."
    },
    {
        "id": "UNC_HI_157",
        "transcript": "Agent: क्या आपको लोन की आवश्यकता है?\nCustomer: मुझे इसमें रुचि है या नहीं, अभी पता नहीं।",
        "language": "Hindi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "negation_nuance",
        "explanation": "Customer does not know whether interested in Hindi."
    },
    # Marathi Devanagari
    {
        "id": "UNC_MR_158",
        "transcript": "Agent: तुम्ही आमच्या नवीन योजनेत भाग घेणार का?\nCustomer: बघूया.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "ambiguity",
        "explanation": "Colloquial non-committal response in Marathi."
    },
    {
        "id": "UNC_MR_159",
        "transcript": "Agent: हे सोलर उपकरण शेतीसाठी फायदेशीर ठरेल.\nCustomer: विचार करून सांगतो.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Male deliberation statement in Marathi."
    },
    {
        "id": "UNC_MR_160",
        "transcript": "Agent: महिलांसाठी विशेष बचत योजना आहे.\nCustomer: विचार करून सांगते.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Female deliberation statement in Marathi."
    },
    {
        "id": "UNC_MR_161",
        "transcript": "Agent: आम्ही बुकिंग सुरू केली आहे.\nCustomer: अजून ठरवले नाही, मला थोडा वेळ द्या.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Undecided and requesting time in Marathi."
    },
    {
        "id": "UNC_MR_162",
        "transcript": "Agent: मुलांच्या शिक्षणासाठी विमा पॉलिसी घ्यायची का?\nCustomer: घरी विचारून सांगतो.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "family_discussion",
        "explanation": "Family consultation statement in Marathi."
    },
    {
        "id": "UNC_MR_163",
        "transcript": "Agent: आम्ही ऑफर बद्दल सांगत आहोत.\nCustomer: नंतर सांगतो, नंतर बघू.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Non-committal postponement in Marathi."
    },
    {
        "id": "UNC_MR_164",
        "transcript": "Agent: काय मी सुरेश देशमुखांशी बोलत आहे का?\nCustomer: हो.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "contextual_acknowledgement",
        "explanation": "Marathi identity confirmation does not infer product interest."
    },
    {
        "id": "UNC_MR_165",
        "transcript": "Agent: तुम्हाला आमच्या उत्पादनात रस आहे का?\nCustomer: मला रस आहे की नाही ते माहीत नाही.",
        "language": "Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "negation_nuance",
        "explanation": "Direct statement of not knowing if interested in Marathi."
    },
    # Hinglish & Romanized
    {
        "id": "UNC_HG_166",
        "transcript": "Agent: Would you like to reserve the venue for next month?\nCustomer: Shayad, soch ke batata hoon.",
        "language": "Hinglish",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Hinglish deliberation statement."
    },
    {
        "id": "UNC_HG_167",
        "transcript": "Agent: Can we sign you up for the annual AMC?\nCustomer: Abhi pakka nahi hai, ghar pe poochkar bataunga.",
        "language": "Hinglish",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "family_discussion",
        "explanation": "Family discussion needed in Hinglish."
    },
    {
        "id": "UNC_HG_168",
        "transcript": "Agent: Aap Rahul bol rahe hain?\nCustomer: Haan.",
        "language": "Hinglish",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "contextual_acknowledgement",
        "explanation": "Identity confirmation in Hinglish."
    },
    # Marathish & Romanized Marathi
    {
        "id": "UNC_MRR_169",
        "transcript": "Agent: Sir solar package booking karaychi ka?\nCustomer: Baghuya, vichar karun sangto.",
        "language": "Romanized Marathi",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "deliberation",
        "explanation": "Deliberation in Romanized Marathi."
    },
    {
        "id": "UNC_MIX_170",
        "transcript": "Agent: Aamhi aamcha plan activate karava ka?\nCustomer: Not sure right now, ghari vicharun sangto.",
        "language": "Mixed Marathi-English",
        "expected_classification": "UNCERTAIN",
        "expected_interest_strength": "UNKNOWN",
        "test_category": "family_discussion",
        "explanation": "Code-mixed family discussion statement."
    }
]
