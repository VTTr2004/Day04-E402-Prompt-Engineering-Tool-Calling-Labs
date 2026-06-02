Return exact product details for chosen catalog product IDs.

Use only product IDs returned by list_products.
Call this before get_discount and before any pricing or saving.
The result verifies SKU, exact name, category, unit_price, stock, warranty, and detail_token.
If this tool returns status error or any item status not_found, stop and ask the user to clarify the product. Do not price or save.
After this tool returns, compare each requested quantity against the returned stock.
If any requested quantity exceeds stock, stop and answer in Vietnamese. Do not call get_discount, calculate_order_totals, or save_order.
If every item is in stock, pass the returned detail_token to calculate_order_totals and save_order.
