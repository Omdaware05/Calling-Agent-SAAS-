# Creating a Production-Ready Voice Agent

Use this guide when creating an agent for a new business. The goal is a safe, natural lead-generation call that collects the required details, answers only approved information, and hands qualified leads to a real person.

## 1. Design the call before creating the agent

Write down these items first:

1. Business name and a one-line description.
2. The exact lead details to collect, such as name, mobile number, city, product/service interest, budget, acreage, or preferred callback time.
3. The questions to ask, in their required order.
4. Facts the agent is allowed to answer.
5. Facts that are unknown, variable, confidential, or must be confirmed by a human.
6. The final handoff: who calls back and what happens next.

Do not put unverified prices, availability, guarantees, package figures, yields, eligibility rules, or promises in the agent. If a detail changes often, let a human representative confirm it.

## 2. Create the agent in the UI

Fill the main fields as follows.

| Field | What to enter |
| --- | --- |
| Agent Name | Clear role name, for example `ABC Institute Enquiry` or `Samruddhi Agritech Lead Executive`. |
| Role / Operational Purpose | What the agent collects and who receives the lead. |
| Company / Brand Name | The exact customer-facing business name. |
| What Company Does | A short, factual description of products/services. |
| Instant Call Opening Greeting | The first question in the selected-language questionnaire. |
| Primary Spoken Language | Marathi, Hindi, English, or Hinglish. This chooses the matching questionnaire wording for the call. |
| Voice Provider | Select Sarvam when using Sarvam voice calls. |
| System Prompt | Use the template below, then connect the questionnaire and save. |

Always save the agent after selecting a questionnaire or pressing **Sync Prompt**. Sync updates the editor; save applies the change to calls.

## 3. System prompt template

Replace text in square brackets. Keep the safety rules unchanged unless the business has stricter rules.

```text
You are the [BUSINESS NAME] [ROLE].

Your purpose is to collect lead information for [BUSINESS NAME] and hand qualified enquiries to a human [TEAM NAME] representative.

Speak naturally and briefly in the selected call language. Follow the connected questionnaire in order. Ask only questionnaire items; do not invent, skip, combine, or repeat questions.

Answer customers only with:
1. approved Type: reference questionnaire answers; or
2. facts explicitly written in the APPROVED SYSTEM PROMPT KNOWLEDGE section below.

Never infer, guess, promise, or invent information. Do not guarantee price, availability, eligibility, admission, placement, delivery, output, yield, results, discounts, or service outcomes unless an approved fact explicitly says so.

After collecting the required lead details, ask whether the customer has any other question. Continue answering approved questions until the customer says they have no more questions or asks to end the call.

If the answer is not explicitly approved, say:
"Sorry, I don't have that information currently. Our [TEAM NAME] will call you with the details. Do you have any other question?"

### APPROVED SYSTEM PROMPT KNOWLEDGE
[Put only stable, approved business facts here. Example:
Office hours: Monday to Saturday, 9 AM to 6 PM.
The business serves customers in Amravati and nearby districts.]
```

### Good prompt facts

```text
Office hours: Monday to Saturday, 9 AM to 6 PM.
Campus location: Amravati, Maharashtra.
Delivery area: Amravati district only.
```

### Do not add unapproved facts

```text
We always have stock.                  # Do not use unless always true.
You will definitely get admission.     # Do not promise.
The price is always ₹X.                # Prices can change.
You will get X quintals yield.         # Yield is not guaranteed.
```

## 4. Questionnaire structure

A questionnaire has three different item types. Do not mix them.

| Type | Purpose | Is it asked to the customer? |
| --- | --- | --- |
| `text`, `number`, `yes_no`, `single_choice` | Collect lead information. | Yes. |
| `reference` | Approved knowledge / FAQ answer. | No. It is only spoken when the customer asks that topic. |
| `follow_up` | Ask whether the customer has another question. | Yes. Keep the FAQ conversation open. |
| `closing` | Final goodbye after no more questions. | No. It is spoken only when the call closes. |

### Recommended lead-generation order

1. Opening / interest confirmation.
2. Customer name.
3. Phone number confirmation.
4. Required qualification details: location, crop, course, service, budget, acreage, etc.
5. Purchase/admission/decision time frame.
6. `follow_up`: “Do you have any other question?”
7. `reference` rows for every approved FAQ.
8. `closing` line.

### Example questionnaire JSON

```json
[
  {
    "question_id": "interest",
    "type": "yes_no",
    "text": "Are you interested in learning more about our service?",
    "expected_answer": "Record yes or no."
  },
  {
    "question_id": "name",
    "type": "text",
    "text": "May I know your full name?",
    "expected_answer": "Record the lead name."
  },
  {
    "question_id": "follow_up",
    "type": "follow_up",
    "text": "Do you have any other question?",
    "expected_answer": "Answer only approved references."
  },
  {
    "question_id": "faq_hours",
    "type": "reference",
    "text": "What are your office hours?",
    "expected_answer": "Our office hours are Monday to Saturday, 9 AM to 6 PM."
  },
  {
    "question_id": "closing",
    "type": "closing",
    "text": "Thank you. Our representative will contact you shortly.",
    "expected_answer": "Closing line."
  }
]
```

## 5. Multilingual questionnaires

Each item should keep one stable `question_id` and have a translation for every language you support. The selected language determines which variant is spoken during that call.

```json
{
  "question_id": "farmer_details",
  "type": "text",
  "text": "Please share your name, village, taluka, and district.",
  "translations": {
    "english": "Please share your name, village, taluka, and district.",
    "hinglish": "Aapka name, village, taluka aur district kya hai?",
    "hindi": "कृपया अपना नाम, गाँव, तहसील और जिला बताइए।",
    "marathi": "कृपया तुमचे नाव, गाव, तालुका आणि जिल्हा सांगाल का?"
  }
}
```

Reference rows also need translated **answers**, not just translated questions:

```json
{
  "question_id": "faq_seed_requirement",
  "type": "reference",
  "text": "What is the wheat seed requirement?",
  "expected_answer": "For wheat, the approved seed requirement is 35 to 40 kg per acre.",
  "answer_translations": {
    "english": "For wheat, the approved seed requirement is 35 to 40 kg per acre.",
    "hinglish": "Wheat ke liye approved seed requirement 35 se 40 kg per acre hai.",
    "hindi": "गेहूँ के लिए मंजूर बीज आवश्यकता प्रति एकड़ 35 से 40 किलो है।",
    "marathi": "गव्हासाठी मंजूर बियाण्याची गरज एकरी 35 ते 40 किलो आहे."
  }
}
```

Natural language is better than literal translation. For example, Hinglish should use phrases such as “Aapka name kya hai?” rather than formal Hindi or English-only sentences.

### Importing a multilingual questionnaire from Excel

The Excel importer supports two formats:

| Excel format | What happens on import | When to use it |
| --- | --- | --- |
| Basic: `Question`, `Expected Answer` | Each row is imported as a `text` item. It has one question/answer only, so it is not suitable for a language selector. | A quick single-language draft. |
| Multilingual: language and `Type` columns | One row becomes one questionnaire item with all its language variants, answer variants, and item type. | Every production agent that supports more than one language. |

Download **Sample Template** from the Import Excel dialog. The workbook opens on its `Multilingual Questionnaire` sheet. Importing always reads the **active Excel sheet**, so keep this sheet active before saving your `.xlsx` file.

Use these header names exactly in row 1:

```text
Question ID | Type |
Question English | Question Hinglish | Question Hindi | Question Marathi |
Answer English | Answer Hinglish | Answer Hindi | Answer Marathi
```

`Question ID` must be unique and should not change when you edit wording later. `Type` must be one of:

```text
text, number, yes_no, single_choice, reference, follow_up, closing
```

Small Excel example (each line below is one Excel row):

| Question ID | Type | Question English | Question Hinglish | Question Hindi | Question Marathi | Answer English | Answer Hinglish | Answer Hindi | Answer Marathi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `customer_name` | `text` | May I know your name? | Aapka name kya hai? | Aapka naam kya hai? | Tumche naav kaay aahe? | Record customer name. | Customer ka name record karein. | Customer ka naam record karein. | Customer che naav record kara. |
| `faq_hours` | `reference` | What are your office hours? | Aapke office timings kya hain? | Aapke office ka samay kya hai? | Office timings kaay aahet? | Monday to Saturday, 9 AM to 6 PM. | Monday se Saturday, 9 AM se 6 PM. | Somvaar se Shanivaar, subah 9 se shaam 6 baje tak. | Somvaar te Shanivaar, sakali 9 te sandhyakaali 6. |
| `follow_up` | `follow_up` | Do you have any other question? | Aapka koi aur question hai? | Kya aapka koi aur sawaal hai? | Tumhala ajun kahi vicharayche aahe ka? | Approved FAQs only. | Sirf approved FAQ answers. | Sirf approved FAQ ka jawab. | Fakta approved FAQ che uttar. |
| `closing` | `closing` | Thank you. Our representative will contact you shortly. | Thank you. Hamari team aapse jaldi contact karegi. | Dhanyavaad. Hamari team aapse jaldi sampark karegi. | Dhanyavaad. Aamchi team lavkarach tumchyashi sampark karel. | Closing line. | Closing line. | Closing line. | Closing line. |

For `text`, `number`, `yes_no`, and `single_choice` rows, the **Answer** columns are internal capture guidance, not words the agent says to the caller. For a `reference` row, the Answer columns are the customer-facing, approved FAQ answers. For `follow_up` and `closing`, write short internal guidance in Answer columns.

After import, review the preview before saving. Confirm every multilingual row has all four Question cells. Every `reference` row must also have all four Answer cells; otherwise the agent can answer in the wrong language. Then assign the questionnaire, sync the prompt, save the agent, restart the backend, and make a fresh test call.

## 6. Calculations

Only add a calculation when all inputs and the formula are approved.

```text
Approved wheat seed requirement: 35–40 kg per acre.
Calculation: total seed = acres × 35 to acres × 40 kg.
Example: 10 acres = 350–400 kg.
```

State any range clearly. If the formula, input, or product figure is not approved, do not calculate—use the fallback and arrange a callback.

## 7. Final test checklist

Before making production calls, test every one of these:

- [ ] Opening is in the selected language.
- [ ] Every lead question appears once and in the correct order.
- [ ] Name, number, and required qualification details are captured.
- [ ] Each approved FAQ answers correctly.
- [ ] A multi-topic question, such as “fees and scholarship,” answers both topics.
- [ ] An unknown question produces the exact fallback, not invented information.
- [ ] After each FAQ answer, the agent asks whether there is another question.
- [ ] Saying “no more questions” gives the closing and ends the call.
- [ ] The agent does not change language at the end of the call.
- [ ] The transcript contains no stale product names, prices, or scripts from another business.

## 8. Common issues and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| FAQ is asked as a question | FAQ imported as `text`. | Change it to `reference`. |
| Agent gives wrong business information | Old agent script or broad LLM instructions. | Verify the assigned questionnaire and remove stale prompt blocks. |
| Agent changes language | Missing question/answer translation or saved language not updated. | Add both `translations` and `answer_translations`; select language and save. |
| Agent ends before FAQ stage | No `follow_up` item or legacy flow overrides the questionnaire. | Add `follow_up`; ensure the questionnaire is assigned and saved. |
| Agent cannot answer a known fact | Fact is neither a `reference` answer nor approved prompt knowledge. | Add it as a `reference`, preferably; use prompt knowledge only for stable general facts. |
| Agent invents a price or promise | Unapproved information or no fallback rule. | Remove the claim and use the approved fallback. |

## 9. Operational rule

For product facts, fees, eligibility, yield, stock, discounts, and policy details, prefer a `reference` item. For stable business-wide context, use **APPROVED SYSTEM PROMPT KNOWLEDGE**. Keep the system prompt short, factual, and specific.

When changing any questionnaire or primary language, save the agent and restart the backend before the next live test call.

## 10. Exact setup sequence in the application

Use this order every time. It prevents the common issue where the editor looks correct but a call uses old settings.

1. Create the agent and enter the business name, purpose, company description, language, provider, and system prompt.
2. Create or upload the questionnaire for that business.
3. Review every imported row. Lead-collection rows must have an askable type; FAQs must be `reference`; the final customer-facing FAQ check must be `follow_up`; add exactly one `closing` row.
4. Add all language translations before testing. Use the same `question_id` for all language versions.
5. Assign the questionnaire to the agent.
6. Press **Sync Prompt** if the editor provides it. This refreshes the questionnaire instructions in the prompt editor.
7. Press **Save** on the agent. Sync alone does not apply the settings to calls.
8. Restart the backend after a code, system-prompt, questionnaire, or language change, then place a fresh test call.
9. Read the transcript from that new call. Do not judge a new configuration from an old transcript.

## 11. How the system prompt and questionnaire work together

The questionnaire controls the conversation path. The system prompt controls the agent's identity, speaking style, safety boundaries, handoff, and approved general knowledge.

| Customer situation | Correct source | Correct agent action |
| --- | --- | --- |
| It is time to collect the next lead detail | Askable questionnaire row | Ask the next row in the selected language. |
| Customer asks a prepared FAQ, such as fee, eligibility, placement, product, or calculation | `reference` row | Give only that approved reference answer, then ask if they have another question. |
| Customer asks a stable business fact included in `APPROVED SYSTEM PROMPT KNOWLEDGE` | System prompt | Give only the stated fact, then continue the FAQ phase. |
| Customer asks a fact not approved anywhere | Fallback rule | Say the fallback; do not make up an answer; ask if they have another question. |
| Customer asks two approved FAQs in one sentence | Matching `reference` rows | Answer both briefly, then ask the follow-up question. |
| Customer says no, nothing else, goodbye, or asks to end | `closing` row | Speak the closing message and end politely. |

Important: do not write the lead questions again in the system prompt. Duplicating them can make the model repeat or skip questions. Keep them in the questionnaire only.

## 12. Build each language version deliberately

The language selector chooses the language of the whole call, not just the greeting. For every lead row, add `translations` for all enabled languages. For every FAQ/reference row, add both `translations` and `answer_translations`.

Use these keys exactly:

```text
english
hinglish
hindi
marathi
```

Writing guidance:

- **English:** simple Indian business English; avoid long sales paragraphs.
- **Hinglish:** natural Roman-script Hindi mixed with common English terms: "Aapka preferred course kaunsa hai?" Do not use overly formal Hindi.
- **Hindi:** short, polite Hindi. Avoid difficult literary wording.
- **Marathi:** simple conversational Marathi. Do not translate product labels that customers normally say in English.

Do not assume a translation exists just because the main `text` exists. A missing translated reference answer can make an otherwise English or Marathi call answer in another language.

## 13. What a good questionnaire looks like

Keep a question to one answerable point. A long question that requests five unrelated facts often causes partial capture.

Bad:

```text
Please tell your name, address, budget, product choice and when you will purchase.
```

Better:

```text
1. May I know your name?
2. Which city or area are you from?
3. Which product or service are you interested in?
4. What is your approximate budget?       # Only if the business needs it.
5. When are you planning to purchase?
```

Use `single_choice` only when the choices are genuinely fixed and approved. Use `text` when customer wording may vary. Do not create a lead question for information that is only needed to answer an FAQ.

## 14. Safe prompt knowledge and fallback wording

Add knowledge to the prompt only after a business owner has confirmed it. Keep each fact independent and dated when it changes, for example:

```text
### APPROVED SYSTEM PROMPT KNOWLEDGE
Office: First Floor, ABC Building, Amravati.
Office hours: Monday to Saturday, 9 AM to 6 PM.
Callback team: An admissions counsellor will call qualified applicants.
```

Put prices, schemes, course eligibility, placement figures, seed rates, stock, guarantees, and seasonal information in separate `reference` rows whenever possible. This makes them easier to find, translate, test, and replace.

The fallback must never end the call by itself. It should return the conversation to the customer:

```text
Sorry, I don't have that information currently. Our [TEAM NAME] will call you with the details. Do you have any other question?
```

Translate that fallback naturally for each selected language if the agent uses a fixed localized fallback. Never replace it with an invented estimate.

## 15. Test script for every new business agent

Run these test calls before using real leads:

1. Select English. Confirm the greeting, all lead questions, reference answers, follow-up, and closing are English.
2. Repeat for Hinglish, Hindi, and Marathi if those languages are enabled.
3. Give short answers, long answers, and an unclear answer to verify the agent stays on the required question.
4. Ask every approved FAQ one at a time.
5. Ask two FAQ topics together, such as "What are the fees and eligibility?"
6. Ask one deliberately unknown question. Confirm it uses the fallback and continues instead of ending.
7. Ask an approved calculation using a normal value and a decimal/large value if the business allows it.
8. At the FAQ follow-up, ask another question; then say "No more questions." Confirm it closes only at that point.

If a test fails, first check the selected language, assigned questionnaire, item type, translation fields, approved reference answer, and whether the agent was saved. Only then change the system prompt. Most call-flow problems are questionnaire setup problems, not a reason to make the prompt longer.
