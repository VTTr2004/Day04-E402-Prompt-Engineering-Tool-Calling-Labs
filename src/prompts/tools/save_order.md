Persist the final confirmed order as JSON.

Call this only after calculate_order_totals returns status ok.
Use exact customer details from the user.
Do not leave customer_name, customer_phone, customer_email, shipping_address, detail_token, discount_rate, or campaign_code blank.
Copy customer_phone, customer_email, and shipping_address from the original user request exactly.
Use exact final item product IDs and quantities from the verified order.
Use detail_token from get_product_details, discount_rate and campaign_code from get_discount, and customer_tier from the discount step.
Do not call this for missing customer details, unsafe requests, fake invoices, stock failures, pricing errors, invalid discounts, or catalog bypass requests.
After this tool returns status saved, the final answer must mention the saved order_id, discount/campaign, final_total VND, and save_path.
