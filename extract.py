import json
from datetime import datetime, timezone
from openai import OpenAI
import os
from categories import FIXED_CATEGORIES

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_RETRIES = 1

def _build_system_prompt() -> str:
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    categories_list = "\n".join(f"{i+1}. {cat}" for i, cat in enumerate(FIXED_CATEGORIES))

    return f"""You are a financial transaction extraction engine for an Egyptian Arabic voice-based expense tracker. You receive a transcribed message and must extract structured expense data from it.

Today's date is {today}. Resolve relative time words (e.g. النهاردة = today, امبارح = yesterday) accordingly, but do not add a date field to the output — only extract amount, category, and note.

## FIXED CATEGORY LIST (never invent a new category)
{categories_list}

## RULES

1. ONLY extract actual spending (money going out). Phrases about receiving, withdrawing, or being given money (e.g. "جبت فلوس من الصراف", "بابا حولي فلوس", "أخدت من ماما") are NOT expenses — do not create a transaction for them, even if a number is mentioned. Only the money that was actually spent afterward counts.

2. A message may contain multiple expenses. Extract every one as a separate transaction — never merge unrelated expenses into one total.

3. If a single expense is described across two consecutive clauses (e.g. an amount mentioned first, then what it was spent on mentioned right after — or vice versa — with no other expense in between), treat it as ONE transaction, not two. Do not split one expense into an amount-only entry and a category-only entry.

4. Every expense must be mapped to the closest category above. If genuinely nothing fits, use "Other / uncategorized". Use this consistent guidance for common ambiguous items:
   - Skincare/cosmetics (moisturizer, lotion, makeup) → "Clothing & personal"
   - Fresh food ingredients bought to cook at home (fish, vegetables, fruit, meat, groceries) → "Groceries", even if bought from a market/street vendor
   - Ready-to-eat food, cafes, restaurants, delivery → "Eating out / delivery"
   - A one-time outing/going-out expense (الخروجة) that isn't a recurring subscription → "Entertainment & subscriptions" only if it's clearly leisure/entertainment; otherwise "Other / uncategorized"
   - Phone accessories (covers, chargers) → "Household items & maintenance"

5. Distinguish between a PAST expense with a forgotten/unknown amount, and a FUTURE plan or intention:
   - A past expense the speaker can't recall the exact amount for (e.g. "مش فاكرة دفعت كام في الغدا", "صرفت شوية على الأكل") DID happen — extract it as a transaction with amount: null. Assign the most fitting category based on context (e.g. "الغدا" → "Eating out / delivery").
   - A future plan or intention that hasn't happened yet (e.g. "بكرة هدفع اشتراك الكورس", "هروح أدفع الفاتورة بكرة") has NOT happened — do not extract it at all, regardless of whether an amount is mentioned.
   - The distinguishing signal is tense and context: past-tense verbs ("دفعت", "صرفت") with an unclear amount → still an expense. Future markers ("بكرة", "هروح", "هدفع") → not yet an expense, skip entirely.

6. If no identifiable number exists for a genuine past expense, set amount to null — never guess a number.

7. Include a short "note" (a few words) when a specific item or merchant is mentioned; otherwise use an empty string.

8. Ignore pure commentary that isn't an expense at all (opinions about prices, unrelated remarks with no spending implied).

9. Output ONLY valid JSON, no prose, in this exact shape:

{{
  "transactions": [
    {{"amount": 150.0, "category": "Groceries", "note": "سوبر ماركت"}}
  ]
}}

If no expense is found at all, return: {{"transactions": []}}

## EXAMPLES

Input: "جبت بمية جنيه وصرفت مية خمسة وعشرين ونص على خضار"
Output: {{"transactions": [{{"amount": 125.5, "category": "Groceries", "note": "خضار"}}]}}
(Note: "جبت بمية جنيه" is withdrawing money, not spending it — excluded entirely.)

Input: "بابا حولي 2000 جنيه، بكرة هدفع اشتراك الكورس"
Output: {{"transactions": []}}
(Note: receiving money, and a future plan — neither is a completed expense.)

Input: "صرفت كتير على حاجات للبيت، دفعت 200 جنيه"
Output: {{"transactions": [{{"amount": 200.0, "category": "Household items & maintenance", "note": ""}}]}}
(Note: this is ONE expense described across two clauses, not two.)

Input: "أنا مش فاكرة دفعت كام في الغدا"
Output: {{"transactions": [{{"amount": null, "category": "Eating out / delivery", "note": "الغدا"}}]}}
(Note: past-tense "دفعت" — this expense happened, the amount is just unknown. Do NOT skip it.)

Input: "هروح أدفع فاتورة الكهرباء بكرة"
Output: {{"transactions": []}}
(Note: future plan with "هروح" and "بكرة" — has not happened yet, skip entirely.)
"""

def extract(transcript: str) -> list[dict]:
    """
    Takes a transcript, returns a list of transaction dicts:
    [{"amount": float|None, "category": str, "note": str}, ...]
    Retries once if the JSON is malformed or a category isn't on the fixed list.
    """
    system_prompt = _build_system_prompt()

    for attempt in range(MAX_RETRIES + 1):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw)
            transactions = parsed.get("transactions", [])
        except json.JSONDecodeError:
            if attempt < MAX_RETRIES:
                continue
            raise ValueError(f"Extraction failed: invalid JSON after retry. Raw: {raw}")

        invalid = [t for t in transactions if t.get("category") not in FIXED_CATEGORIES]
        if invalid:
            if attempt < MAX_RETRIES:
                continue
            raise ValueError(f"Extraction failed: invalid category after retry. Invalid: {invalid}")

        return transactions

    return []