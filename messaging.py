import os
from twilio.rest import Client
from datetime import datetime

class MessageManager:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        
        # Initialize Twilio client if credentials are available
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
    
    def send_message(self, phone, message, method="SMS"):
        """Send SMS or WhatsApp message using Twilio"""
        if not self.client:
            print("Twilio client not initialized. Please check your credentials.")
            return False
        
        try:
            # Format phone number for WhatsApp if needed
            if method == "WhatsApp":
                if not phone.startswith("whatsapp:"):
                    phone = f"whatsapp:{phone}"
                from_number = f"whatsapp:{self.phone_number}"
            else:
                from_number = self.phone_number
            
            # Send the message
            message_obj = self.client.messages.create(
                body=message,
                from_=from_number,
                to=phone
            )
            
            print(f"Message sent successfully! SID: {message_obj.sid}")
            return True
            
        except Exception as e:
            print(f"Failed to send message: {str(e)}")
            return False
    
    def format_message(self, template, member_data):
        """Format message template with member data"""
        # Default values for message formatting
        court_name = "KJ Badminton Academy"
        contact_phone = "+91-9876543210"
        
        # Calculate due date
        payment_date = member_data.get('payment_date', datetime.now().date())
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        
        # Calculate next due date based on membership type
        from database import DatabaseManager
        db = DatabaseManager()
        due_date = db.calculate_next_due_date(payment_date, member_data.get('membership_type', 'Monthly Subscriber'))
        
        # Calculate overdue days
        today = datetime.now().date()
        overdue_days = (today - due_date).days if today > due_date else 0
        
        # Format template with member data
        formatted_message = template.format(
            member_name=member_data.get('member_name', 'Member'),
            amount=member_data.get('amount', 0),
            due_date=due_date.strftime('%d-%m-%Y'),
            membership_type=member_data.get('membership_type', 'Monthly Subscriber'),
            overdue_days=overdue_days,
            court_name=court_name,
            phone=contact_phone
        )
        
        return formatted_message
    
    def send_bulk_messages(self, recipients, message_template, method="SMS"):
        """Send bulk messages to multiple recipients"""
        results = []
        
        for recipient in recipients:
            formatted_message = self.format_message(message_template, recipient)
            success = self.send_message(recipient['phone'], formatted_message, method)
            
            results.append({
                'member_id': recipient.get('member_id'),
                'member_name': recipient.get('member_name'),
                'phone': recipient.get('phone'),
                'success': success
            })
        
        return results
    
    def test_connection(self):
        """Test Twilio connection"""
        if not self.client:
            return False, "Twilio credentials not configured"
        
        try:
            # Try to fetch account information
            account = self.client.api.accounts(self.account_sid).fetch()
            return True, f"Connected to Twilio account: {account.friendly_name}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def get_message_cost_estimate(self, recipients_count, method="SMS"):
        """Estimate cost for bulk messages"""
        # Approximate costs (may vary by region)
        cost_per_sms = 0.0075  # $0.0075 per SMS
        cost_per_whatsapp = 0.005  # $0.005 per WhatsApp message
        
        if method == "WhatsApp":
            total_cost = recipients_count * cost_per_whatsapp
        else:
            total_cost = recipients_count * cost_per_sms
        
        return {
            'recipients': recipients_count,
            'method': method,
            'cost_per_message': cost_per_whatsapp if method == "WhatsApp" else cost_per_sms,
            'total_cost': total_cost,
            'currency': 'USD'
        }
