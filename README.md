# Welcome To The OrderDesk Lab

This lab teaches you how to improve an LLM agent with prompt engineering.

You will build an order agent for a small electronics retailer. The agent must:

- understand a customer order request
- choose the right tools in the right order
- ask for missing information before doing work
- refuse unsafe or policy-breaking requests
- save the final order as grounded JSON

This is not only a coding lab. It is a prompt-and-tool-design lab.

## What You Will Learn

By the end of the lab, you should be able to:

- write a system prompt that controls agent behavior
- design tool schemas that reduce ambiguity
- build prompt guardrails for unsafe or invalid requests
- force clarification before tool calls
- understand how prompt quality changes evaluation score
- debug an agent by reading saved JSON and tool traces

## Lab Overview

The business scenario is simple:

- OrderDesk sells electronics
- customers ask to create orders
- the agent must look up products, check exact details, get a discount, calculate totals, and save the order

The hard part is behavior quality.

Weak agents usually fail because:

- the prompt is too vague
- tool descriptions are too generic
- schemas do not force required inputs
- guardrails are weak
- the model starts calling tools too early

This lab is designed so those mistakes show up in the score.

## Learning Goal

You are expected to improve:

- prompt clarity
- tool descriptions
- argument schema quality
- clarification behavior
- refusal behavior
- grounding of final answers

The score should improve as your prompt engineering improves.

## Repository Structure

### Student code

- `src/agent/graph.py`
- `src/utils/data_store.py`
- `src/core/`

This is the code students should implement and improve.

### Baseline

- `simple_solution/`

This is an intentionally weak baseline. It exists so you can see what low-quality prompt/tool design looks like in practice.

### Data

- `data/products.json`: product catalog
- `data/graded_cases.json`: evaluation cases
- `data/expected_orders/`: expected saved JSON outputs

### Grading

- `grade/scoring.py`
- `rubric.md`

### Instructions

- `guide.md`
- `task.txt`

## How The Lab Works

You should start by running the weak baseline in `simple_solution/`.

That first run gives you the starting score of the lab.

After that, you will implement the student scaffold in `src/`.

Then you will run the grader against your implementation.

If the score is low, you should improve:

- the system prompt
- the tool docstrings and schema
- the guardrail instructions

This loop is the core of the lab.

## Suggested Order

1. Read `guide.md`
2. Run `simple_solution/` through the grader and record the baseline score
3. Inspect `simple_solution/`
4. Understand `data/graded_cases.json`
5. Implement `src/`
6. Run the grader on `src/`
7. Improve prompt and tool schema until the score becomes strong

## Environment Setup

Create a `.env` file:

```bash
GOOGLE_API_KEY=...
LLM_MODEL=gemini-2.5-flash
```

Optional local model:

```bash
OLLAMA_MODEL=qwen3.5:3b
OLLAMA_BASE_URL=http://localhost:11434
```

## Useful Commands

Run the weak baseline:

```bash
python grade/scoring.py --module simple_solution.agent.graph --provider google
```

This should be your first grading run.

Run your student implementation:

```bash
python grade/scoring.py --module src.agent.graph --provider google
```

Run tests:

```bash
pytest -q
```

## What Success Looks Like

A strong submission will:

- clearly improve over the `simple_solution/` baseline
- avoid early tool calls on incomplete requests
- refuse unsafe requests without touching tools
- follow the expected tool sequence on valid orders
- save the exact expected JSON
- give concise grounded answers in Vietnamese

That is the real target of the lab.
