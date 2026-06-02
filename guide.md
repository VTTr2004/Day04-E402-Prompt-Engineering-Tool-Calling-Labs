# Student Guide

## 1. Purpose Of This Lab

This lab is about improving agent behavior, not just making code execute.

You will build an electronics order agent and raise its score by improving:

- the system prompt
- the tool schema
- the guardrails
- the grounded response behavior

## 2. Big Picture

The agent must do this workflow:

1. find candidate products
2. confirm exact product details
3. get a discount
4. calculate totals
5. save the order

The grader checks whether your agent actually behaves this way.

## 3. Code Structure

### `src/`

This is the student implementation area.

Key files:

- `src/agent/graph.py`
- `src/utils/data_store.py`
- `src/core/schemas.py`
- `src/core/llm.py`

### `simple_solution/`

This is the weak baseline.

Use it to understand what poor prompt/tool design looks like:

- vague system prompt
- loose tool interfaces
- weaker control over clarification and guardrails

### `data/`

Important files:

- `products.json`
- `graded_cases.json`
- `expected_orders/`

### `grade/`

- `grade/scoring.py`

This is the grader that compares your outputs against expected behavior.

## 4. What You Need To Improve

### A. System prompt

Your prompt should clearly tell the model:

- when to clarify
- when to refuse
- when not to call tools
- which tool to call next
- what facts must come only from tools
- what the final answer should contain

Weak prompts create most of the failures in this lab.

### B. Tool schema

Tool schema is part of prompt engineering.

Strong schema helps the model understand:

- required fields
- valid argument shapes
- dependencies between tools
- which outputs must be passed to later steps

Weak schema causes:

- wrong arguments
- missing customer data
- skipped validation
- invalid saved orders

### C. Guardrails

The agent should refuse:

- fake invoices
- manual discount overrides
- stock bypasses
- catalog bypasses
- requests to ignore policy

The refusal should happen before tool use.

### D. Clarification

Before any tool call, the model should make sure it has:

- customer name
- phone number
- email
- shipping address
- at least one product request with quantity

If any field is missing, it should ask a short clarification question and stop.

## 5. Step-By-Step Path

### Step 1: Run the baseline first

Before you change `src/`, run:

```bash
python grade/scoring.py --module simple_solution.agent.graph --provider google
```

This gives you the weak baseline score.

You should use that score as your starting point.

### Step 2: Read the cases

Open `data/graded_cases.json`.

Understand:

- normal success cases
- stock failure cases
- clarification cases
- guardrail refusal cases

If you do not understand the case set, your prompt will stay generic.

### Step 3: Write the system prompt

This is the most important part.

Your prompt should explicitly say:

- answer in Vietnamese
- never invent product IDs, prices, discount, totals, or file paths
- clarify before tool use if required customer data is missing
- refuse unsafe requests without calling tools
- follow the expected tool order
- save only after validation succeeds

### Step 4: Strengthen the tool schema

Good tool design should make the model’s next step obvious.

Your tools should use:

- clear names
- clear docstrings
- explicit required arguments
- arguments that reflect workflow dependencies

Good schema reduces model confusion.

### Step 5: Test clarification behavior

The model should not touch the catalog if the request is incomplete.

This is a common failure mode.

If the user forgets email or shipping address, the correct behavior is:

- ask for the missing field
- stop
- use zero tools

### Step 6: Test refusal behavior

The model should reject requests like:

- ignore stock
- apply 90% discount
- create fake invoice
- bypass catalog

Correct behavior:

- short refusal
- no tool calls

### Step 7: Test grounded save behavior

For valid orders, the model should:

- pick correct product IDs
- pass exact validated data through the workflow
- save the correct JSON

### Step 8: Run the grader on `src`

Run:

```bash
python grade/scoring.py --module src.agent.graph --provider google
```

Compare that score against the baseline from `simple_solution/`.

If the score is not clearly better, your prompt, tool schema, or guardrails still need work.

## 6. How To Debug Your Score

When a case fails, inspect:

### Tool trace

Ask:

- did tools start too early?
- did the model skip `get_product_details`?
- did it call `save_order` on a bad request?

### Saved JSON

Ask:

- is customer data present?
- are product IDs correct?
- is the discount correct?
- is the order ID correct?
- was the order saved when it should not have been?

### Final answer

Ask:

- is it grounded in tool output?
- is it concise?
- does it clarify or refuse correctly?

## 7. Recommended Improvement Loop

Use this loop:

1. run the grader on `simple_solution/`
2. run the grader on `src/`
3. inspect failing cases
4. inspect tool trace
5. strengthen prompt
6. tighten tool schema
7. rerun the grader on `src/`

In this lab, score improvement should mostly come from better prompt engineering, not random extra logic.

## 8. What Strong Work Looks Like

A strong submission:

- clarifies before tool use
- refuses unsafe requests without tool calls
- follows the intended workflow
- saves exact expected JSON
- stays grounded in tool output

That is the standard you should aim for.
