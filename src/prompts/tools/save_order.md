Persist the final confirmed order as JSON.

Call this only after calculate_order_totals succeeds.
Use exact customer details, final item list, detail_token, discount_rate, and campaign_code from previous steps.
Do not call this for missing customer details, unsafe requests, stock failures, invalid discounts, or fake invoices.
Return the saved order id and path in the final answer.
