import re
from datetime import datetime, timedelta

def format_phone_number(phone):
    """Format phone number to international format"""
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # If it starts with 91, assume it's already formatted
    if phone.startswith('91') and len(phone) == 12:
        return f"+{phone}"
    
    # If it's a 10-digit number, add +91
    if len(phone) == 10:
        return f"+91{phone}"
    
    # If it already has country code without +
    if len(phone) > 10:
        return f"+{phone}"
    
    return phone

def validate_phone_number(phone):
    """Validate phone number format"""
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid Indian mobile number
    if len(digits_only) == 10:
        return True
    elif len(digits_only) == 12 and digits_only.startswith('91'):
        return True
    elif len(digits_only) == 13 and phone.startswith('+91'):
        return True
    
    return False

def calculate_membership_duration(membership_type):
    """Calculate duration in days for different membership types"""
    duration_map = {
        "Monthly Subscriber": 30,
        "Quarterly": 90,
        "Half Yearly": 180,
        "Annual": 365
    }
    return duration_map.get(membership_type, 30)

def format_currency(amount):
    """Format amount in Indian Rupees"""
    return f"₹{amount:,.2f}"

def format_date(date_obj):
    """Format date in DD-MM-YYYY format"""
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
    return date_obj.strftime('%d-%m-%Y')

def calculate_age_from_dob(date_of_birth):
    """Calculate age from date of birth"""
    if isinstance(date_of_birth, str):
        date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
    
    today = datetime.now().date()
    age = today.year - date_of_birth.year
    
    # Adjust if birthday hasn't occurred this year
    if today < date_of_birth.replace(year=today.year):
        age -= 1
    
    return age

def generate_member_id(name, phone):
    """Generate a unique member ID"""
    # Take first 3 letters of name and last 4 digits of phone
    name_part = re.sub(r'[^a-zA-Z]', '', name)[:3].upper()
    phone_part = phone[-4:] if len(phone) >= 4 else phone
    timestamp = datetime.now().strftime('%m%d')
    
    return f"{name_part}{phone_part}{timestamp}"

def validate_email(email):
    """Validate email address format"""
    if not email:
        return True  # Email is optional
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def get_next_business_day(date_obj=None):
    """Get next business day (Monday-Friday)"""
    if date_obj is None:
        date_obj = datetime.now().date()
    
    # If it's Friday (4), Saturday (5), or Sunday (6), move to Monday
    if date_obj.weekday() >= 4:
        days_to_add = 7 - date_obj.weekday()
        return date_obj + timedelta(days=days_to_add)
    else:
        return date_obj + timedelta(days=1)

def sanitize_input(text):
    """Sanitize user input to prevent basic security issues"""
    if not text:
        return ""
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', str(text))
    return sanitized.strip()

def format_batch_time(batch_time):
    """Format batch time for display"""
    time_map = {
        "Morning (6:00-7:00 AM)": "🌅 Morning 6-7 AM",
        "Evening (5:00-6:00 PM)": "🌇 Evening 5-6 PM", 
        "Evening (6:00-7:00 PM)": "🌆 Evening 6-7 PM"
    }
    return time_map.get(batch_time, batch_time)

def get_payment_status_color(days_remaining):
    """Get color code for payment status"""
    if days_remaining < 0:
        return "🔴"  # Overdue - Red
    elif days_remaining <= 3:
        return "🟠"  # Due soon - Orange
    elif days_remaining <= 7:
        return "🟡"  # Warning - Yellow
    else:
        return "🟢"  # Good - Green

def calculate_late_fee(days_overdue, base_amount, late_fee_percentage=5):
    """Calculate late fee based on days overdue"""
    if days_overdue <= 0:
        return 0
    
    late_fee = (base_amount * late_fee_percentage / 100)
    return min(late_fee, base_amount * 0.20)  # Cap at 20% of base amount

def export_data_summary(members_data, kids_data):
    """Generate a summary of all data for export"""
    summary = {
        'total_members': len(members_data),
        'total_kids': len(kids_data),
        'total_monthly_revenue': 0,
        'overdue_members': 0,
        'active_members': 0
    }
    
    today = datetime.now().date()
    
    for member in members_data:
        summary['total_monthly_revenue'] += member.get('amount', 0)
        
        # Calculate if overdue
        payment_date = member.get('payment_date')
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        
        next_due = payment_date + timedelta(days=calculate_membership_duration(member.get('membership_type', 'Monthly Subscriber')))
        
        if next_due < today:
            summary['overdue_members'] += 1
        else:
            summary['active_members'] += 1
    
    return summary
