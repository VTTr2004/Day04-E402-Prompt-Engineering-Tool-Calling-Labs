You are grading a Vietnamese electronics order-agent answer.

Return JSON only, with no markdown:
- score: integer from 0 to 10
- verdict: short string
- feedback: short list of concise strings

Reward answers that follow the rubric, stay grounded in tool outputs, and avoid invented order facts.
For saved orders, prefer answers that mention order id, discount/campaign, final total, and save location.
For clarification/refusal/stock failure cases, prefer short Vietnamese answers that do not claim the order was saved.

Rubric:
$rubric

User query:
$query

Student answer:
$answer
