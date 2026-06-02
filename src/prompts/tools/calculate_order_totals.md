Validate product IDs, detail_token, quantities, and discount rate, then calculate totals.

Call this only after get_discount returns status ok.
Use exact product IDs and quantities from the final order, preserving all requested bundle lines.
Use the detail_token from get_product_details and the discount_rate from get_discount.
If this tool returns status error, stop and explain the issue in Vietnamese.
Never call save_order after a pricing, detail_token, product, discount, or stock validation error.
If this tool returns status ok, do not recalculate or re-check product details. Call save_order next.
