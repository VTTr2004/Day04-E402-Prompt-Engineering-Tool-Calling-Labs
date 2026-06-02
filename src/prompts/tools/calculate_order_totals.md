Validate product IDs, detail_token, quantities, and discount rate, then calculate the order total.

Call this after get_discount and before save_order.
Use exact product IDs and quantities from the final order.
If this tool returns an error, stop and explain the issue to the user.
Never save an order after a pricing or stock validation error.
