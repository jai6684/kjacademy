import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import time
import os
import re
from twilio.rest import Client

# =============================================================================
# DATABASE MANAGER CLASS
# =============================================================================

class DatabaseManager:
    def __init__(self, db_path=None):
        # Use environment variable for deployment, fallback to local for development
        self.db_path = db_path or os.getenv("DB_PATH", "badminton_court.db")
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Members table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            email TEXT,
            membership_type TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date DATE NOT NULL,
            reminder_days INTEGER DEFAULT 30,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Payment history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date DATE NOT NULL,
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members (id)
        )
        ''')
        
        # Kids training table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS kids_training (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kid_name TEXT NOT NULL,
            parent_name TEXT NOT NULL,
            parent_phone TEXT NOT NULL,
            age INTEGER NOT NULL,
            batch_time TEXT NOT NULL,
            monthly_fee REAL NOT NULL,
            start_date DATE NOT NULL,
            emergency_contact TEXT,
            medical_notes TEXT,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Kids payment history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS kids_payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kid_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date DATE NOT NULL,
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kid_id) REFERENCES kids_training (id)
        )
        ''')
        
        # Message templates table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_type TEXT NOT NULL UNIQUE,
            message_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Reminder logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminder_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN NOT NULL,
            FOREIGN KEY (member_id) REFERENCES members (id)
        )
        ''')
        
        # Member checkins table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS member_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            check_out_time TIMESTAMP NULL,
            duration_minutes INTEGER NULL,
            court_usage_type TEXT DEFAULT 'General Play',
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members (id)
        )
        ''')
        
        # Bulk messages log table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bulk_messages_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_text TEXT NOT NULL,
            recipient_count INTEGER NOT NULL,
            message_type TEXT NOT NULL,
            sent_by TEXT DEFAULT 'System',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Insert default message templates if they don't exist
        self._insert_default_templates(cursor)
        
        conn.commit()
        conn.close()
    
    def _insert_default_templates(self, cursor):
        """Insert default message templates"""
        default_templates = [
            ("payment_reminder", """Hi {member_name}! 🏸

Your badminton court membership payment of ₹{amount} is due on {due_date}. 

Please make the payment at your earliest convenience.

Thank you for being a valued member!

Contact us: {phone}"""),
            ("overdue_reminder", """Dear {member_name},

Your badminton court membership payment of ₹{amount} is overdue by {overdue_days} days.

Please make the payment immediately to continue enjoying our facilities.

For any queries, contact us: {phone}

Thank you!""")
        ]
        
        for template_type, message_text in default_templates:
            cursor.execute('''
            INSERT OR IGNORE INTO message_templates (template_type, message_text)
            VALUES (?, ?)
            ''', (template_type, message_text))
    
    def add_member(self, name, phone, email, membership_type, amount, payment_date, reminder_days, notes):
        """Add a new member to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO members (name, phone, email, membership_type, amount, payment_date, reminder_days, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, phone, email, membership_type, amount, payment_date, reminder_days, notes))
            
            member_id = cursor.lastrowid
            
            # Add initial payment to payment history
            cursor.execute('''
            INSERT INTO payment_history (member_id, amount, payment_date, payment_method, notes)
            VALUES (?, ?, ?, ?, ?)
            ''', (member_id, amount, payment_date, "Initial Payment", "Membership registration"))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def get_all_payments(self, search_term="", membership_filter="All", status_filter="All"):
        """Get all payment records with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT m.id, m.name as member_name, m.phone, m.email, m.membership_type, 
               m.amount, m.payment_date, m.reminder_days, m.notes
        FROM members m
        WHERE 1=1
        '''
        params = []
        
        if search_term:
            query += " AND (m.name LIKE ? OR m.phone LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        if membership_filter != "All":
            query += " AND m.membership_type = ?"
            params.append(membership_filter)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def record_payment(self, member_id, amount, payment_date, payment_method, notes):
        """Record a new payment for a member"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Add payment to history
            cursor.execute('''
            INSERT INTO payment_history (member_id, amount, payment_date, payment_method, notes)
            VALUES (?, ?, ?, ?, ?)
            ''', (member_id, amount, payment_date, payment_method, notes))
            
            # Update member's last payment date and amount
            cursor.execute('''
            UPDATE members 
            SET payment_date = ?, amount = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (payment_date, amount, member_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def calculate_next_due_date(self, payment_date, membership_type):
        """Calculate the next due date based on membership type"""
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        
        if membership_type == "Monthly Subscriber":
            return payment_date + timedelta(days=30)
        elif membership_type == "Quarterly":
            return payment_date + timedelta(days=90)
        elif membership_type == "Half Yearly":
            return payment_date + timedelta(days=180)
        elif membership_type == "Annual":
            return payment_date + timedelta(days=365)
        else:
            return payment_date + timedelta(days=30)  # Default to monthly
    
    def get_total_members(self):
        """Get total number of members"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM members')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_active_subscriptions(self):
        """Get number of active subscriptions (not overdue)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = datetime.now().date()
        cursor.execute('''
        SELECT COUNT(*) FROM members m
        WHERE date(m.payment_date, '+30 days') >= date(?)
        ''', (today,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_total_kids(self):
        """Get total number of kids in training"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM kids_training WHERE active = TRUE')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_recent_payments(self, limit=5):
        """Get recent payments"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT m.name as member_name, ph.amount, ph.payment_date
        FROM payment_history ph
        JOIN members m ON ph.member_id = m.id
        ORDER BY ph.created_at DESC
        LIMIT ?
        ''', (limit,))
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def add_kid(self, kid_name, parent_name, parent_phone, age, batch_time, monthly_fee, start_date, emergency_contact, medical_notes):
        """Add a new kid to the training program"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO kids_training (kid_name, parent_name, parent_phone, age, batch_time, 
                                     monthly_fee, start_date, emergency_contact, medical_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (kid_name, parent_name, parent_phone, age, batch_time, monthly_fee, 
                  start_date, emergency_contact, medical_notes))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def get_all_kids(self):
        """Get all kids in the training program"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM kids_training WHERE active = TRUE ORDER BY kid_name
        ''')
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def search_members(self, search_term="", membership_filter="All", sort_by="Name"):
        """Search and filter members"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM members WHERE 1=1'
        params = []
        
        if search_term:
            query += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if membership_filter != "All":
            query += " AND membership_type = ?"
            params.append(membership_filter)
        
        if sort_by == "Name":
            query += " ORDER BY name"
        elif sort_by == "Payment Date":
            query += " ORDER BY payment_date DESC"
        elif sort_by == "Amount":
            query += " ORDER BY amount DESC"
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_message_template(self, template_type):
        """Get a message template by type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT message_text FROM message_templates WHERE template_type = ?
        ''', (template_type,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""
    
    def update_message_template(self, template_type, message_text):
        """Update a message template"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE message_templates 
            SET message_text = ?, updated_at = CURRENT_TIMESTAMP
            WHERE template_type = ?
            ''', (message_text, template_type))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def log_reminder(self, member_id, reminder_type, message):
        """Log a sent reminder"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO reminder_logs (member_id, reminder_type, message, success)
            VALUES (?, ?, ?, ?)
            ''', (member_id, reminder_type, message, True))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def delete_member(self, member_id):
        """Delete a member and all related records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete related payment history first
            cursor.execute('DELETE FROM payment_history WHERE member_id = ?', (member_id,))
            
            # Delete related reminder logs
            cursor.execute('DELETE FROM reminder_logs WHERE member_id = ?', (member_id,))
            
            # Delete related checkin records
            cursor.execute('DELETE FROM member_checkins WHERE member_id = ?', (member_id,))
            
            # Finally delete the member
            cursor.execute('DELETE FROM members WHERE id = ?', (member_id,))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def delete_kid(self, kid_id):
        """Delete a kid and all related records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete related payment history first
            cursor.execute('DELETE FROM kids_payment_history WHERE kid_id = ?', (kid_id,))
            
            # Finally delete the kid
            cursor.execute('DELETE FROM kids_training WHERE id = ?', (kid_id,))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False

# =============================================================================
# MESSAGE MANAGER CLASS
# =============================================================================

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
    
    def send_whatsapp_url(self, phone, message):
        """Generate WhatsApp URL for manual sending"""
        # Format phone number for WhatsApp URL
        formatted_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        # URL encode the message
        import urllib.parse
        encoded_message = urllib.parse.quote(message)
        whatsapp_url = f"https://wa.me/{formatted_phone}?text={encoded_message}"
        return whatsapp_url
    
    def format_message(self, template, member_data):
        """Format message template with member data"""
        court_name = "KJ Badminton Academy"
        contact_phone = "+91-9876543210"
        
        payment_date = member_data.get('payment_date', datetime.now().date())
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        
        # Calculate due date
        membership_type = member_data.get('membership_type', 'Monthly Subscriber')
        if membership_type == "Monthly Subscriber":
            due_date = payment_date + timedelta(days=30)
        elif membership_type == "Quarterly":
            due_date = payment_date + timedelta(days=90)
        elif membership_type == "Half Yearly":
            due_date = payment_date + timedelta(days=180)
        elif membership_type == "Annual":
            due_date = payment_date + timedelta(days=365)
        else:
            due_date = payment_date + timedelta(days=30)
        
        today = datetime.now().date()
        overdue_days = (today - due_date).days if today > due_date else 0
        
        formatted_message = template.format(
            member_name=member_data.get('member_name', 'Member'),
            amount=member_data.get('amount', 0),
            due_date=due_date.strftime('%d-%m-%Y'),
            membership_type=membership_type,
            overdue_days=overdue_days,
            court_name=court_name,
            phone=contact_phone
        )
        
        return formatted_message

# =============================================================================
# REMINDER SCHEDULER CLASS
# =============================================================================

class ReminderScheduler:
    def __init__(self):
        pass
    
    def get_pending_reminders(self, db_manager):
        """Get list of members who need payment reminders"""
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        pending_reminders = []
        
        cursor.execute('''
        SELECT id, name, phone, email, membership_type, amount, payment_date, reminder_days
        FROM members
        ORDER BY name
        ''')
        
        members = cursor.fetchall()
        
        for member in members:
            member_id, name, phone, email, membership_type, amount, payment_date, reminder_days = member
            
            if isinstance(payment_date, str):
                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            
            next_due_date = db_manager.calculate_next_due_date(payment_date, membership_type)
            days_remaining = (next_due_date - today).days
            
            should_remind = False
            reminder_type = "payment_reminder"
            
            if days_remaining < 0:
                should_remind = True
                reminder_type = "overdue_reminder"
            elif days_remaining <= reminder_days:
                should_remind = True
                reminder_type = "payment_reminder"
            
            if should_remind:
                pending_reminders.append({
                    'member_id': member_id,
                    'member_name': name,
                    'phone': phone,
                    'email': email,
                    'membership_type': membership_type,
                    'amount': amount,
                    'payment_date': payment_date,
                    'next_due_date': next_due_date,
                    'days_remaining': days_remaining,
                    'reminder_type': reminder_type,
                    'reminder_days': reminder_days
                })
        
        conn.close()
        return pending_reminders

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_phone_number(phone):
    """Format phone number to international format"""
    phone = re.sub(r'\D', '', phone)
    
    if phone.startswith('91') and len(phone) == 12:
        return f"+{phone}"
    
    if len(phone) == 10:
        return f"+91{phone}"
    
    if len(phone) > 10:
        return f"+{phone}"
    
    return phone

def validate_phone_number(phone):
    """Validate phone number format"""
    digits_only = re.sub(r'\D', '', phone)
    
    if len(digits_only) == 10:
        return True
    elif len(digits_only) == 12 and digits_only.startswith('91'):
        return True
    elif len(digits_only) == 13 and phone.startswith('+91'):
        return True
    
    return False

# =============================================================================
# STREAMLIT APP FUNCTIONS
# =============================================================================

# Initialize database manager
@st.cache_resource
def init_database():
    return DatabaseManager()

# Initialize message manager
@st.cache_resource
def init_message_manager():
    return MessageManager()

# Initialize reminder scheduler
@st.cache_resource
def init_reminder_scheduler():
    return ReminderScheduler()

def show_dashboard(db_manager, reminder_scheduler):
    st.header("📊 Dashboard")
    
    # PWA Install Button
    st.markdown("""
    <div style="text-align: center; margin: 1rem 0;">
        <button id="install-btn" style="display: none; background: #1f77b4; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
            📱 Install App on Home Screen
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    # Get statistics
    total_members = db_manager.get_total_members()
    active_subscriptions = db_manager.get_active_subscriptions()
    pending_reminders = reminder_scheduler.get_pending_reminders(db_manager)
    total_kids = db_manager.get_total_kids()
    
    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Members", total_members)
    with col2:
        st.metric("Active Subscriptions", active_subscriptions)
    with col3:
        st.metric("Pending Reminders", len(pending_reminders))
    with col4:
        st.metric("Kids Enrolled", total_kids)
    
    st.markdown("---")
    
    # Recent activities
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔔 Upcoming Payment Reminders")
        if pending_reminders:
            for reminder in pending_reminders[:5]:
                member_name = reminder.get('member_name', 'Unknown')
                days_remaining = reminder.get('days_remaining', 0)
                amount = reminder.get('amount', 0)
                
                reminder_type = "🔴 Due Soon" if days_remaining <= 3 else "🟡 Reminder Due"
                st.write(f"{reminder_type} **{member_name}** - ₹{amount} ({days_remaining} days)")
        else:
            st.info("No pending reminders")
    
    with col2:
        st.subheader("💰 Recent Payments")
        recent_payments = db_manager.get_recent_payments(5)
        if recent_payments:
            for payment in recent_payments:
                st.write(f"✅ **{payment['member_name']}** - ₹{payment['amount']} ({payment['payment_date']})")
        else:
            st.info("No recent payments")

def show_member_registration(db_manager):
    st.header("👤 Member Registration")
    
    with st.form("member_registration"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name *", placeholder="Enter member's full name")
            phone = st.text_input("Phone Number *", placeholder="+91XXXXXXXXXX")
            email = st.text_input("Email", placeholder="member@email.com")
            
        with col2:
            membership_type = st.selectbox(
                "Membership Type *",
                ["Monthly Subscriber", "Quarterly", "Half Yearly", "Annual"]
            )
            amount = st.number_input("Amount (₹) *", min_value=0.0, value=0.0)
            payment_date = st.date_input("Payment Date *", value=datetime.now().date())
        
        reminder_days = st.selectbox(
            "Reminder Before (days)",
            [15, 30],
            index=1
        )
        
        notes = st.text_area("Notes", placeholder="Any additional notes about the member")
        
        submitted = st.form_submit_button("Register Member", use_container_width=True)
        
        if submitted:
            if not name or not phone or not amount:
                st.error("Please fill in all required fields (*)")
            elif not validate_phone_number(phone):
                st.error("Please enter a valid phone number (format: +91XXXXXXXXXX)")
            else:
                formatted_phone = format_phone_number(phone)
                
                success = db_manager.add_member(
                    name=name,
                    phone=formatted_phone,
                    email=email,
                    membership_type=membership_type,
                    amount=amount,
                    payment_date=payment_date,
                    reminder_days=reminder_days,
                    notes=notes
                )
                
                if success:
                    st.success(f"✅ Member {name} registered successfully!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to register member. Please try again.")

def show_payment_tracking(db_manager):
    st.header("💳 Payment Tracking")
    
    # Search and filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search Member", placeholder="Enter name or phone")
    with col2:
        membership_filter = st.selectbox("Filter by Membership", 
                                       ["All", "Monthly Subscriber", "Quarterly", "Half Yearly", "Annual"])
    with col3:
        status_filter = st.selectbox("Payment Status", ["All", "Due Soon", "Overdue", "Paid"])
    
    # Get payments data
    payments = db_manager.get_all_payments(search_term, membership_filter, status_filter)
    
    if payments:
        # Display payments
        for payment in payments:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{payment['member_name']}**")
                    st.caption(f"📞 {payment['phone']} | {payment['membership_type']}")
                
                with col2:
                    st.write(f"₹{payment['amount']}")
                    st.caption(f"Paid: {payment['payment_date']}")
                
                with col3:
                    # Calculate next due date
                    next_due = db_manager.calculate_next_due_date(payment['payment_date'], payment['membership_type'])
                    days_remaining = (next_due - datetime.now().date()).days
                    
                    if days_remaining < 0:
                        st.error(f"Overdue by {abs(days_remaining)} days")
                    elif days_remaining <= 7:
                        st.warning(f"Due in {days_remaining} days")
                    else:
                        st.success(f"Due in {days_remaining} days")
                
                with col4:
                    if st.button("💰", key=f"pay_{payment['id']}", help="Record Payment"):
                        st.session_state[f"show_payment_modal_{payment['id']}"] = True
                
                st.markdown("---")
                
                # Show payment modal if requested
                if st.session_state.get(f"show_payment_modal_{payment['id']}", False):
                    show_payment_modal(db_manager, payment)
    else:
        st.info("No payment records found")

def show_payment_modal(db_manager, member):
    """Show payment recording modal"""
    with st.expander(f"Record Payment for {member['member_name']}", expanded=True):
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("✖", key=f"close_modal_{member['id']}", help="Close"):
                st.session_state[f"show_payment_modal_{member['id']}"] = False
                st.rerun()
        
        with st.form(f"payment_{member['id']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                amount = st.number_input("Amount (₹)", min_value=0.0, value=float(member['amount']) if member['amount'] is not None else 0.0)
                payment_date = st.date_input("Payment Date", value=datetime.now().date())
            
            with col2:
                payment_method = st.selectbox("Payment Method", ["Cash", "UPI", "Card", "Bank Transfer"])
                notes = st.text_input("Notes", placeholder="Payment reference or notes")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Record Payment", use_container_width=True):
                    success = db_manager.record_payment(
                        member_id=member['id'],
                        amount=amount,
                        payment_date=payment_date,
                        payment_method=payment_method,
                        notes=notes
                    )
                    
                    if success:
                        st.success("✅ Payment recorded successfully!")
                        # Clear modal state
                        st.session_state[f"show_payment_modal_{member['id']}"] = False
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Failed to record payment")
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state[f"show_payment_modal_{member['id']}"] = False
                    st.rerun()

def show_kids_training(db_manager):
    st.header("🧒 Kids Training Program")
    
    tab1, tab2 = st.tabs(["Add New Kid", "Manage Kids"])
    
    with tab1:
        with st.form("kids_registration"):
            col1, col2 = st.columns(2)
            
            with col1:
                kid_name = st.text_input("Kid's Name *", placeholder="Enter kid's name")
                parent_name = st.text_input("Parent's Name *", placeholder="Enter parent's name")
                parent_phone = st.text_input("Parent's Phone *", placeholder="+91XXXXXXXXXX")
                
            with col2:
                age = st.number_input("Age", min_value=4, max_value=18, value=8)
                batch_time = st.selectbox("Batch Time", 
                                        ["Morning (6:00-7:00 AM)", "Evening (5:00-6:00 PM)", "Evening (6:00-7:00 PM)"])
                monthly_fee = st.number_input("Monthly Fee (₹) *", min_value=0.0, value=1000.0)
            
            start_date = st.date_input("Training Start Date", value=datetime.now().date())
            emergency_contact = st.text_input("Emergency Contact", placeholder="Alternative phone number")
            medical_notes = st.text_area("Medical Notes", placeholder="Any medical conditions or allergies")
            
            submitted = st.form_submit_button("Register Kid", use_container_width=True)
            
            if submitted:
                if not kid_name or not parent_name or not parent_phone or not monthly_fee:
                    st.error("Please fill in all required fields (*)")
                elif not validate_phone_number(parent_phone):
                    st.error("Please enter a valid phone number")
                else:
                    success = db_manager.add_kid(
                        kid_name=kid_name,
                        parent_name=parent_name,
                        parent_phone=format_phone_number(parent_phone),
                        age=age,
                        batch_time=batch_time,
                        monthly_fee=monthly_fee,
                        start_date=start_date,
                        emergency_contact=emergency_contact,
                        medical_notes=medical_notes
                    )
                    
                    if success:
                        st.success(f"✅ {kid_name} registered successfully!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to register kid")
    
    with tab2:
        kids_data = db_manager.get_all_kids()
        
        if kids_data:
            search_kid = st.text_input("🔍 Search Kids", placeholder="Enter kid's name or parent's name")
            
            if search_kid:
                kids_data = [kid for kid in kids_data if 
                           search_kid.lower() in kid['kid_name'].lower() or 
                           search_kid.lower() in kid['parent_name'].lower()]
            
            for kid in kids_data:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                    
                    with col1:
                        st.write(f"**{kid['kid_name']}** (Age: {kid['age']})")
                        st.caption(f"Parent: {kid['parent_name']}")
                    
                    with col2:
                        st.write(f"📞 {kid['parent_phone']}")
                        st.caption(f"Batch: {kid['batch_time']}")
                    
                    with col3:
                        st.write(f"₹{kid['monthly_fee']}/month")
                        st.caption(f"Started: {kid['start_date']}")
                    
                    with col4:
                        st.write("🟢 Active")
                    
                    with col5:
                        if st.button("🗑️", key=f"delete_kid_{kid['id']}", help="Delete Kid"):
                            st.session_state[f"confirm_delete_kid_{kid['id']}"] = True
                    
                    # Show confirmation dialog if delete was clicked
                    if st.session_state.get(f"confirm_delete_kid_{kid['id']}", False):
                        st.error(f"⚠️ **Confirm Deletion of {kid['kid_name']}**")
                        st.warning("This will permanently delete the kid and all their payment history. This action cannot be undone.")
                        
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_yes_kid_{kid['id']}", type="primary"):
                                if db_manager.delete_kid(kid['id']):
                                    st.success(f"✅ {kid['kid_name']} deleted successfully!")
                                    # Clear confirmation state
                                    st.session_state[f"confirm_delete_kid_{kid['id']}"] = False
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete kid")
                        
                        with col2:
                            if st.button("❌ Cancel", key=f"confirm_no_kid_{kid['id']}"):
                                st.session_state[f"confirm_delete_kid_{kid['id']}"] = False
                                st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No kids registered yet")

def show_send_reminders(db_manager, message_manager):
    st.header("📱 Send Payment Reminders")
    
    pending_reminders = ReminderScheduler().get_pending_reminders(db_manager)
    
    if not pending_reminders:
        st.success("🎉 All members are up to date with their payments!")
        return
    
    st.write(f"**{len(pending_reminders)} members** need payment reminders:")
    
    # Categorize reminders
    overdue = [r for r in pending_reminders if r['days_remaining'] < 0]
    due_soon = [r for r in pending_reminders if r['days_remaining'] >= 0]
    
    tab1, tab2 = st.tabs([f"🔴 Overdue ({len(overdue)})", f"🟡 Due Soon ({len(due_soon)})"])
    
    with tab1:
        if overdue:
            st.error(f"**{len(overdue)} members have overdue payments**")
            
            for reminder in overdue:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        st.write(f"**{reminder['member_name']}**")
                        st.caption(f"📞 {reminder['phone']}")
                    
                    with col2:
                        st.write(f"₹{reminder['amount']}")
                        st.caption(f"Overdue by {abs(reminder['days_remaining'])} days")
                    
                    with col3:
                        template = db_manager.get_message_template("overdue_reminder")
                        message = message_manager.format_message(template, reminder)
                        whatsapp_url = message_manager.send_whatsapp_url(reminder['phone'], message)
                        
                        st.markdown(f"[📱 Send WhatsApp]({whatsapp_url})", unsafe_allow_html=True)
                    
                    st.markdown("---")
        else:
            st.info("No overdue payments")
    
    with tab2:
        if due_soon:
            st.warning(f"**{len(due_soon)} members have payments due soon**")
            
            for reminder in due_soon:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        st.write(f"**{reminder['member_name']}**")
                        st.caption(f"📞 {reminder['phone']}")
                    
                    with col2:
                        st.write(f"₹{reminder['amount']}")
                        st.caption(f"Due in {reminder['days_remaining']} days")
                    
                    with col3:
                        template = db_manager.get_message_template("payment_reminder")
                        message = message_manager.format_message(template, reminder)
                        whatsapp_url = message_manager.send_whatsapp_url(reminder['phone'], message)
                        
                        st.markdown(f"[📱 Send WhatsApp]({whatsapp_url})", unsafe_allow_html=True)
                    
                    st.markdown("---")
        else:
            st.info("No payments due soon")

def show_bulk_messaging(db_manager, message_manager):
    st.header("📢 Bulk Messaging")
    st.info("Send announcements to all members via WhatsApp")
    
    with st.form("bulk_message"):
        message_text = st.text_area(
            "Message *", 
            placeholder="Write your announcement here...\n\nExample:\nDear members,\n\nWe're excited to announce new court timings from next week.\n\nMorning slots: 6:00 AM - 10:00 AM\nEvening slots: 4:00 PM - 10:00 PM\n\nThank you!",
            height=200
        )
        
        include_signature = st.checkbox("Include Academy Signature", value=True)
        
        if st.form_submit_button("Generate WhatsApp Links", use_container_width=True):
            if message_text:
                final_message = message_text
                if include_signature:
                    final_message += "\n\n---\nKJ Badminton Academy\nContact: +91-9876543210"
                
                members = db_manager.search_members()
                
                if members:
                    st.success(f"Generated WhatsApp links for {len(members)} members:")
                    
                    for member in members:
                        whatsapp_url = message_manager.send_whatsapp_url(member['phone'], final_message)
                        st.markdown(f"**{member['name']}**: [📱 Send WhatsApp]({whatsapp_url})")
                else:
                    st.error("No members found")
            else:
                st.error("Please enter a message")

def show_member_database(db_manager):
    st.header("👥 Member Database")
    
    # Search and filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search", placeholder="Name, phone, or email")
    with col2:
        membership_filter = st.selectbox("Membership Type", 
                                       ["All", "Monthly Subscriber", "Quarterly", "Half Yearly", "Annual"])
    with col3:
        sort_by = st.selectbox("Sort By", ["Name", "Payment Date", "Amount", "Due Date"])
    
    # Get filtered members
    members = db_manager.search_members(search_term, membership_filter, sort_by)
    
    if members:
        st.write(f"**{len(members)} members found**")
        
        # Display members in a table-like format
        for member in members:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                
                with col1:
                    st.write(f"**{member['name']}**")
                    st.caption(f"📞 {member['phone']}")
                    if member['email']:
                        st.caption(f"✉️ {member['email']}")
                
                with col2:
                    st.write(f"**{member['membership_type']}**")
                    st.caption(f"₹{member['amount']}")
                
                with col3:
                    next_due = db_manager.calculate_next_due_date(member['payment_date'], member['membership_type'])
                    days_remaining = (next_due - datetime.now().date()).days
                    
                    if days_remaining < 0:
                        st.error(f"Overdue by {abs(days_remaining)} days")
                    elif days_remaining <= 7:
                        st.warning(f"Due in {days_remaining} days")
                    else:
                        st.success(f"Due in {days_remaining} days")
                    
                    st.caption(f"Last paid: {member['payment_date']}")
                
                with col4:
                    st.write("🟢 Active")
                
                with col5:
                    if st.button("🗑️", key=f"delete_btn_{member['id']}", help="Delete Member"):
                        st.session_state[f"confirm_delete_{member['id']}"] = True
                
                # Show confirmation dialog if delete was clicked
                if st.session_state.get(f"confirm_delete_{member['id']}", False):
                    st.error(f"⚠️ **Confirm Deletion of {member['name']}**")
                    st.warning("This will permanently delete the member and all their payment history. This action cannot be undone.")
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("✅ Yes, Delete", key=f"confirm_yes_{member['id']}", type="primary"):
                            if db_manager.delete_member(member['id']):
                                st.success(f"✅ {member['name']} deleted successfully!")
                                # Clear confirmation state
                                st.session_state[f"confirm_delete_{member['id']}"] = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete member")
                    
                    with col2:
                        if st.button("❌ Cancel", key=f"confirm_no_{member['id']}"):
                            st.session_state[f"confirm_delete_{member['id']}"] = False
                            st.rerun()
                
                if member['notes']:
                    st.caption(f"📝 {member['notes']}")
                
                st.markdown("---")
    else:
        st.info("No members found matching your search criteria")

def show_message_settings(db_manager):
    st.header("⚙️ Message Settings")
    st.write("Customize reminder message templates")
    
    tab1, tab2 = st.tabs(["Payment Reminder", "Overdue Reminder"])
    
    with tab1:
        st.subheader("💬 Payment Reminder Message")
        current_template = db_manager.get_message_template("payment_reminder")
        
        updated_template = st.text_area(
            "Payment Reminder Template",
            value=current_template,
            height=200,
            help="Available variables: {member_name}, {amount}, {due_date}, {phone}"
        )
        
        if st.button("Update Payment Reminder", use_container_width=True):
            if db_manager.update_message_template("payment_reminder", updated_template):
                st.success("✅ Payment reminder template updated!")
                st.rerun()
            else:
                st.error("❌ Failed to update template")
    
    with tab2:
        st.subheader("🚨 Overdue Reminder Message")
        current_template = db_manager.get_message_template("overdue_reminder")
        
        updated_template = st.text_area(
            "Overdue Reminder Template",
            value=current_template,
            height=200,
            help="Available variables: {member_name}, {amount}, {overdue_days}, {phone}"
        )
        
        if st.button("Update Overdue Reminder", use_container_width=True):
            if db_manager.update_message_template("overdue_reminder", updated_template):
                st.success("✅ Overdue reminder template updated!")
                st.rerun()
            else:
                st.error("❌ Failed to update template")

def show_data_export(db_manager):
    st.header("📊 Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Members Data", use_container_width=True):
            members = db_manager.search_members()
            if members:
                df = pd.DataFrame(members)
                csv = df.to_csv(index=False)
                st.download_button(
                    "📁 Download Members CSV",
                    csv,
                    f"members_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.error("No members data to export")
    
    with col2:
        if st.button("📥 Export Kids Data", use_container_width=True):
            kids = db_manager.get_all_kids()
            if kids:
                df = pd.DataFrame(kids)
                csv = df.to_csv(index=False)
                st.download_button(
                    "📁 Download Kids CSV",
                    csv,
                    f"kids_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.error("No kids data to export")

# =============================================================================
# AUTHENTICATION FUNCTIONS
# =============================================================================

def show_login():
    """Show login page"""
    
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="login-header">', unsafe_allow_html=True)
    st.title("🏸 KJ Badminton Academy")
    st.subheader("Admin Login")
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        submitted = st.form_submit_button("🔐 Login", use_container_width=True)
        
        if submitted:
            # Get credentials from environment variables for security
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "kjbadminton2024")
            
            if username == admin_username and password == admin_password:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.login_time = datetime.now()
                st.success("✅ Login successful! Redirecting...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("💡 **Setup Instructions**)

def check_authentication():
    """Check if user is authenticated with session timeout"""
    # For testing: Add URL parameter to force logout
    logout_param = st.query_params.get("logout", [""])[0].lower()
    if logout_param == "true":
        st.session_state.clear()  # Clear entire session state
        st.query_params.clear()
        st.rerun()  # Force immediate rerun with cleared session
        return False
    
    authenticated = st.session_state.get("authenticated", False)
    
    if not authenticated:
        return False
    
    # Check session timeout (4 hours)
    login_time = st.session_state.get("login_time")
    if login_time:
        time_elapsed = datetime.now() - login_time
        if time_elapsed.total_seconds() > 14400:  # 4 hours in seconds
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.login_time = None
            return False
    
    return True

def logout():
    """Logout user and clear all session data"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.login_time = None
    st.rerun()

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    # Configure page ONCE at the very start - Streamlit requirement
    st.set_page_config(
        page_title="KJ Badminton Academy",
        page_icon="🏸",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state defaults to ensure fresh sessions start unauthenticated
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("login_time", None)
    st.session_state.setdefault("username", None)
    
    # Check authentication after page config
    if not check_authentication():
        show_login()
        return
    
    # Initialize managers
    db_manager = init_database()
    message_manager = init_message_manager()
    reminder_scheduler = init_reminder_scheduler()
    
    # PWA Configuration and Meta Tags
    st.markdown("""
    <script>
    // Create manifest dynamically
    const manifest = {
        "name": "KJ Badminton Academy",
        "short_name": "KJ Academy",
        "description": "Badminton court management system for KJ Badminton Academy",
        "start_url": window.location.origin,
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1f77b4",
        "orientation": "portrait-primary",
        "scope": "/",
        "icons": [
            {
                "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAADl0RVh0U29mdHdhcmUAbWF0cGxvdGxpYiB2ZXJzaW9uIDMuMC4zLCBodHRwOi8vbWF0cGxvdGxpYi5vcmcvnQurowAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAABmJLR0QA/wD/AP+gvaeTAAAT9dToZjPc9YOhu3VmF9uZvn9/diesdAI0v8iBFmY2o2NGmCuhfxqmT3OHT2ttMjLaMCONXQGg9H4UVFlePXlQ/GSInc0FtUAibuP0LbixcMDTil0IHELI9QjSu1CqqmSke7hBAixm8+l8DW9BSXnOFajB3mdm0TlOfStwiJNL+d6owdNsiy74mKDNOY2vcmO0fmdMlE+ni0qpSNDoZhyZax7uHEWhLGtXwOj9+k+6Zh6clBsRZJP9UwLtRAVM7l44SjT2smvbnptS2JI482zn5zcyrmcZ6oXbDVYzWy+XbhMjV975XZlL7COZR9d2xUJPdeM5hJlI1KKnlD5nJVnKD1YwZ+f6bQIeel4WEJlV7H0H0TtgWRxD8w+fws2j3x8hVR3k5VJlEioai9jqC2OeCdbFFSaJmrCZ6aT20vVZE6gJk69UUd39cugkUaTVxG5I3AK/8WsxbUdkBsPhyPMxPBOD4YANU0cghvnh9XZP1rRUbSH2Td/YkbPQLOqkivoXkD26iFxLGoZJ0HXcBfO8I9hl0U5Qk15oRpuYDszJ6ZeRwFx9fWLFG8nP5gMOX6yvnQxinG40y36Cj5Uh/dfSb+TCsLZN9ddaXdZWhSfbMc1Mm5AcOPIrFtJG35hTYWJy9Ua5cac+yw6tWSdLN2IQhuzsXMMeCUKdarKnirA3VDox6jm9SFs/p0LB9Y0g7Eufyfj3oatEUcCWwppn1qIeJAo4MU9M0EN8Z/7CzFoRE0xCM2idauLw6IJbqEOxjyDcR6kvOkRAhAk3Qp33WHQqcaomKJkynbKp7WXJYuEUprCwssyq9pJcpbRAHqgaUWVn9vFpwRnFX1Ykh1lymXjiNFTiE2KjJlP8FmQkVbeY/VzpBm0vuA41AGyMBkBBdTMGRH5mI16m8zdS0Xd1aExfZbzKs0SHM0LP2l9fPDmkYdYNxmFjwzwCNRPJEQSB4FHr1GcAq847gn5IZgoQb1/aG775+7/5iz95+/on4DcDeMG++Izv/vC3//DCl5Mvsy8kkL3EnuxU9c/B89UZ39vbmyIaFQFIMG+PUFLKVUSP48+K6SxGlnxZo3nzbRy6hYdoKmsWxVsX9+mNILNscQGAITAOJuhtDneVotZecKZjWBwWdvgBPBc8MosOCAc8VzENtllhRWGjity3nREH8ErrkrrWVldLLrdHcgLhbIJ3n6T+QG1iU3FGtvOr3Q9dbYZhIPyRcEYpdpkV7c07WNuUfpfoi5LW1pq5YHKvXVkLZABJe9D3pZYWPZpK43FWjnsXwPWza0I+1Zaus7bgwestS4nEu4hye0uhuj6PMcoVVK17PM/JFuTnnBvrrF3PyEa/UEL1ptT2+TRxKH3i4MPx13JvjzHkD8thD41tg//DGzthY/tYmJMvDixdd62ksxDGSqTsCk2Pe6Bt0NIOPM46DSIMTXDDumPyhRVSwvQVGu33BR6xyuJ0C3VbS8f62aAhFW2xXH1vtnWfKEUWt6nqr1N010aILjHN/dETCR5JAEAU66CMZIQQzU4jtV0bKPLrgl56KBd4mQz2uHaA+P0GvXZhOMLjWe4wmfc1Rp+YMJBpjfBOsh0yLI4bLgZG/u46EtE7p2oGAHadPtEZR/xhzvneUXpo6NTBUlv8HvqRnJfEiZNUZ42s0xXDmW1/Y1oV4dzxqb+INeYulfoBkc...",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAADl0RVh0U29mdHdhcmUAbWF0cGxvdGxpYiB2ZXJzaW9uIDMuMC4zLCBodHRwOi8vbWF0cGxvdGxpYi5vcmcvnQurowAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAABmJLR0QA/wD/AP+gvaeTAAAT9dToZjPc9YOhu3VmF9uZvn9/diesdAI0v8iBFmY2o2NGmCuhfxqmT3OHT2ttMjLaMCONXQGg9H4UVFlePXlQ/GSInc0FtUAibuP0LbixcMDTil0IHELI9QjSu1CqqmSke7hBAixm8+l8DW9BSXnOFajB3mdm0TlOfStwiJNL+d6owdNsiy74mKDNOY2vcmO0fmdMlE+ni0qpSNDoZhyZax7uHEWhLGtXwOj9+k+6Zh6clBsRZJP9UwLtRAVM7l44SjT2smvbnptS2JI482zn5zcyrmcZ6oXbDVYzWy+XbhMjV975XZlL7COZR9d2xUJPdeM5hJlI1KKnlD5nJVnKD1YwZ+f6bQIeel4WEJlV7H0H0TtgWRxD8w+fws2j3x8hVR3k5VJlEioai9jqC2OeCdbFFSaJmrCZ6aT20vVZE6gJk69UUd39cugkUaTVxG5I3AK/8WsxbUdkBsPhyPMxPBOD4YANU0cghvnh9XZP1rRUbSH2Td/YkbPQLOqkivoXkD26iFxLGoZJ0HXcBfO8I9hl0U5Qk15oRpuYDszJ6ZeRwFx9fWLFG8nP5gMOX6yvnQxinG40y36Cj5Uh/dfSb+TCsLZN9ddaXdZWhSfbMc1Mm5AcOPIrFtJG35hTYWJy9Ua5cac+yw6tWSdLN2IQhuzsXMMeCUKdarKnirA3VDox6jm9SFs/p0LB9Y0g7Eufyfj3oatEUcCWwppn1qIeJAo4MU9M0EN8Z/7CzFoRE0xCM2idauLw6IJbqEOxjyDcR6kvOkRAhAk3Qp33WHQqcaomKJkynbKp7WXJYuEUprCwssyq9pJcpbRAHqgaUWVn9vFpwRnFX1Ykh1lymXjiNFTiE2KjJlP8FmQkVbeY/VzpBm0vuA41AGyMBkBBdTMGRH5mI16m8zdS0Xd1aExfZbzKs0SHM0LP2l9fPDmkYdYNxmFjwzwCNRPJEQSB4FHr1GcAq847gn5IZgoQb1/aG775",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    };
    
    // Create and append manifest link
    const manifestBlob = new Blob([JSON.stringify(manifest)], {type: 'application/json'});
    const manifestURL = URL.createObjectURL(manifestBlob);
    
    // Remove existing manifest links
    const existingManifest = document.querySelector('link[rel="manifest"]');
    if (existingManifest) {
        existingManifest.remove();
    }
    
    const manifestLink = document.createElement('link');
    manifestLink.rel = 'manifest';
    manifestLink.href = manifestURL;
    document.head.appendChild(manifestLink);
    
    // Add PWA meta tags
    const metaTags = [
        {name: 'viewport', content: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'},
        {name: 'apple-mobile-web-app-capable', content: 'yes'},
        {name: 'apple-mobile-web-app-status-bar-style', content: 'default'},
        {name: 'apple-mobile-web-app-title', content: 'KJ Academy'},
        {name: 'mobile-web-app-capable', content: 'yes'},
        {name: 'theme-color', content: '#1f77b4'},
        {name: 'apple-touch-icon', content: manifest.icons[0].src}
    ];
    
    metaTags.forEach(tag => {
        const existingTag = document.querySelector(`meta[name="${tag.name}"]`);
        if (existingTag) {
            existingTag.remove();
        }
        const meta = document.createElement('meta');
        meta.name = tag.name;
        meta.content = tag.content;
        document.head.appendChild(meta);
    });
    
    // Register Service Worker
    if ('serviceWorker' in navigator) {
        const swCode = `
            const CACHE_NAME = 'kj-badminton-v1';
            const urlsToCache = [
                '/',
                window.location.href
            ];
            
            self.addEventListener('install', function(event) {
                event.waitUntil(
                    caches.open(CACHE_NAME)
                        .then(function(cache) {
                            return cache.addAll(urlsToCache);
                        })
                );
            });
            
            self.addEventListener('fetch', function(event) {
                event.respondWith(
                    caches.match(event.request)
                        .then(function(response) {
                            return response || fetch(event.request);
                        }
                    )
                );
            });
            
            self.addEventListener('activate', function(event) {
                event.waitUntil(
                    caches.keys().then(function(cacheNames) {
                        return Promise.all(
                            cacheNames.map(function(cacheName) {
                                if (cacheName !== CACHE_NAME) {
                                    return caches.delete(cacheName);
                                }
                            })
                        );
                    })
                );
            });
        `;
        
        const swBlob = new Blob([swCode], {type: 'application/javascript'});
        const swURL = URL.createObjectURL(swBlob);
        
        navigator.serviceWorker.register(swURL)
            .then(function(registration) {
                console.log('Service Worker registered successfully');
            })
            .catch(function(error) {
                console.log('Service Worker registration failed');
            });
    }
    
    // Add install prompt functionality
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        
        // Show install button if it exists
        const installBtn = document.getElementById('install-btn');
        if (installBtn) {
            installBtn.style.display = 'block';
            installBtn.addEventListener('click', () => {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    deferredPrompt = null;
                    installBtn.style.display = 'none';
                });
            });
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Custom CSS for mobile responsiveness
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    
    .stButton > button {
        width: 100%;
        margin: 0.25rem 0;
    }
    
    .payment-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🏸 KJ Badminton Academy")
    st.markdown("---")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        
        # User info and logout
        if st.session_state.get("username"):
            st.success(f"👤 Logged in as: **{st.session_state.username}**")
            if st.button("🚪 Logout", use_container_width=True):
                logout()
        
        st.markdown("---")
        
        page = st.selectbox(
            "Select Page",
            ["Dashboard", "Member Registration", "Payment Tracking", "Kids Training", 
             "Send Reminders", "Bulk Messaging", "Member Database", "Message Settings", "Data Export"]
        )
    
    # Main content based on selected page
    if page == "Dashboard":
        show_dashboard(db_manager, reminder_scheduler)
    elif page == "Member Registration":
        show_member_registration(db_manager)
    elif page == "Payment Tracking":
        show_payment_tracking(db_manager)
    elif page == "Kids Training":
        show_kids_training(db_manager)
    elif page == "Send Reminders":
        show_send_reminders(db_manager, message_manager)
    elif page == "Bulk Messaging":
        show_bulk_messaging(db_manager, message_manager)
    elif page == "Member Database":
        show_member_database(db_manager)
    elif page == "Message Settings":
        show_message_settings(db_manager)
    elif page == "Data Export":
        show_data_export(db_manager)

if __name__ == "__main__":
    main()