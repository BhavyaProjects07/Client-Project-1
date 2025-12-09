    admin_html = f"""
        <h2>📦 New Order Received</h2>

        <p><strong>Order ID:</strong> #{order.id}</p>

        <h3>👤 Customer Details</h3>
        <p>
        <strong>Name:</strong> {order.full_name}<br>
        <strong>Phone:</strong> {order.phone_number}<br>
        <strong>Address:</strong> {order.address}, {order.city}, {order.postal_code}<br>
        <strong>Email:</strong> {order.user.email}
        </p>

        <h3>🛒 Order Items</h3>

        <table border="1" cellspacing="0" cellpadding="8" style="border-collapse: collapse;">
            <tr>
                <th>Product</th>
                <th>Qty</th>
                <th>Price (₹)</th>
            </tr>
            {''.join(admin_rows)}
        </table>

        <h3>💰 Total Amount: ₹{total}</h3>

        <br>
        <a href="{dashboard_link}"
        style="background:#ff8c00;color:white;padding:10px 18px;border-radius:6px;text-decoration:none">
        Open Delivery Dashboard
        </a>

        <p style="margin-top:20px;">This is an automated message from Sona Enterprises.</p>
        """




    customer_items_html = "".join(
        [f"<li>{line}</li>" for line in items_for_email]
    )

    customer_html = f"""
    <div style="font-family:Arial, sans-serif; padding:20px; background:#f7f7f7;">
        <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px;">

            <h2 style="color:#ff8c00;">🎉 Order Confirmed!</h2>
            <p>Hi <strong>{order.full_name}</strong>,</p>

            <p>Thank you for shopping with <strong>Sona Enterprises</strong>!  
            Your order has been successfully placed.</p>

            <h3>📦 Order Details</h3>
            <p><strong>Order ID:</strong> #{order.id}</p>

            <h3>🛒 Items Ordered:</h3>
            <ul style="padding-left:20px; line-height:1.6;">
                {customer_items_html}
            </ul>

            <h3>💰 Total Amount: ₹{total}</h3>

            <h3>📍 Delivery Details:</h3>
            <p>
            <strong>Name:</strong> {order.full_name} <br>
            <strong>Phone:</strong> {order.phone_number} <br>
            <strong>Address:</strong> {order.address}, {order.city}, {order.postal_code}
            </p>

            <p>This is a Cash On Delivery order. You will receive updates as your order progresses.</p>

            <p style="margin-top:30px;">Thank you for choosing us! 😊</p>

            <hr style="border:none; border-top:1px solid #ddd; margin:25px 0;">
            <p style="font-size:12px; color:#555;">This is an automated email from Sona Enterprises.</p>
        </div>
    </div>
    """