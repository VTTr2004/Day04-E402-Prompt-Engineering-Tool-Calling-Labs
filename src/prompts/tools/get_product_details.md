Return exact product details for chosen catalog product IDs.

Use only product IDs returned by list_products.
This verifies price, stock, SKU, warranty, and returns a detail_token.
If stock is insufficient for the requested quantity, stop and tell the user instead of calculating or saving.
Pass the returned detail_token to calculate_order_totals and save_order.
