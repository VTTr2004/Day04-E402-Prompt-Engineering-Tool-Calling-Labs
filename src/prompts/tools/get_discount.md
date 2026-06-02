Return the simulated campaign discount for the order.

Call this only after get_product_details confirms every requested item is in stock.
For valid orders, email is required; use the customer email exactly as seed_hint.
Fallback to phone only if a future workflow explicitly allows orders without email.
Use customer_tier "standard" unless the user clearly says VIP.
Never invent, override, round, or manually force a discount rate or campaign_code.
Remember the returned campaign_code. It is required by save_order and must not be blank.
Next step: pass discount_rate to calculate_order_totals and campaign_code to save_order.
