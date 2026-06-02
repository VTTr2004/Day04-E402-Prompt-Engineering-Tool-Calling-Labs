# Rubric

## What The Grader Actually Checks

This lab is graded mainly from two things:

1. saved JSON correctness
2. tool usage correctness

The goal is to help students understand that prompt engineering affects real measurable behavior.

## 1. Saved JSON Scoring

For normal save cases, the grader compares your saved order JSON against the expected fixture in `data/expected_orders/`.

It checks fields like:

- customer name
- phone
- email
- shipping address
- exact product IDs
- quantities
- prices
- discount rate
- final total
- deterministic order ID
- save path

The grader also checks that the saved file actually exists on disk.

If your JSON is wrong, it usually means:

- the prompt allowed guessing
- the tool schema was too weak
- the model skipped or misused a validation step

## 2. Non-Save Case Scoring

For clarification and guardrail cases, the grader checks that the agent does **not** save an order.

Examples:

- missing email
- missing shipping address
- fake invoice request
- “ignore stock” request

If an order is saved in those cases, the score should drop heavily.

## 3. Tool Usage Scoring

For normal successful cases, the grader expects this workflow:

1. `list_products`
2. `get_product_details`
3. `get_discount`
4. `calculate_order_totals`
5. `save_order`

For clarification and refusal cases, the expected tool usage is usually:

- no tool calls

If your model starts searching too early or saves too early, that is treated as a prompt/schema/guardrail failure.

## 4. What The Current Grader Does Not Strongly Score

The current grader does **not** heavily score response wording anymore.

That was intentional.

We removed brittle keyword-based answer scoring because it overfit wording instead of measuring actual agent behavior.

So the main score now comes from:

- the saved artifact
- the tool trace

There is optional LLM judging support, but the main rubric is mostly deterministic.

## 5. How Students Usually Lose Points

### Weak prompt

Common result:

- tool calls begin before required customer fields exist
- refusal cases still call tools
- the model saves invalid orders

### Weak tool schema

Common result:

- arguments are vague or incomplete
- required fields are omitted
- the model skips intermediate validation

### Weak guardrails

Common result:

- the model accepts stock bypass
- the model accepts fake discounts
- the model accepts fake invoice behavior

### Weak grounding

Common result:

- wrong order ID
- wrong discount
- wrong save path
- missing customer information
- wrong saved JSON

## 6. Performance Bands

### `90-100`

Strong work.

The agent behaves correctly, saves the expected JSON, avoids invalid saves, and follows the intended workflow.

### `80-89`

Mostly correct.

Usually there is one smaller tool-trace or payload issue.

### `65-79`

Partially working.

The workflow exists, but the agent is still too loose or inconsistent.

### `0-64`

Weak result.

This usually means the prompt, schema, or guardrails are not controlling the agent well enough.

## 7. Important Note For Students

A low score in this lab is often not a “business logic bug.”

It is usually a prompt engineering problem:

- instructions are unclear
- tools are underspecified
- validation order is weak
- refusal behavior is underspecified

That is exactly what this lab is meant to teach.
