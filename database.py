import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

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
    
    def record_kid_payment(self, kid_id, amount, payment_date, payment_method, notes):
        """Record a payment for a kid's training"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO kids_payment_history (kid_id, amount, payment_date, payment_method, notes)
            VALUES (?, ?, ?, ?, ?)
            ''', (kid_id, amount, payment_date, payment_method, notes))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def get_last_kid_payment(self, kid_id):
        """Get the last payment record for a kid"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM kids_payment_history 
        WHERE kid_id = ? 
        ORDER BY payment_date DESC 
        LIMIT 1
        ''', (kid_id,))
        
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            result = dict(zip(columns, row))
        else:
            result = None
        
        conn.close()
        return result
    
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
        
        # Consider active if next payment due date is in the future
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
    
    def search_members(self, search_term="", membership_filter="All", sort_by="Name"):
        """Search and filter members"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT * FROM members
        WHERE 1=1
        '''
        params = []
        
        if search_term:
            query += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if membership_filter != "All":
            query += " AND membership_type = ?"
            params.append(membership_filter)
        
        # Add sorting
        if sort_by == "Name":
            query += " ORDER BY name"
        elif sort_by == "Payment Date":
            query += " ORDER BY payment_date DESC"
        elif sort_by == "Amount":
            query += " ORDER BY amount DESC"
        elif sort_by == "Due Date":
            query += " ORDER BY payment_date ASC"
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def update_member(self, member_id, name, phone, email, membership_type, amount, reminder_days, notes):
        """Update member information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE members 
            SET name = ?, phone = ?, email = ?, membership_type = ?, 
                amount = ?, reminder_days = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (name, phone, email, membership_type, amount, reminder_days, notes, member_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def delete_member(self, member_id):
        """Delete a member and their payment history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete payment history first (foreign key constraint)
            cursor.execute('DELETE FROM payment_history WHERE member_id = ?', (member_id,))
            cursor.execute('DELETE FROM reminder_logs WHERE member_id = ?', (member_id,))
            cursor.execute('DELETE FROM members WHERE id = ?', (member_id,))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    # Analytics functions
    def get_revenue_analytics(self):
        """Get comprehensive revenue analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total revenue from all payments
        cursor.execute('SELECT SUM(amount) FROM payment_history')
        total_revenue = cursor.fetchone()[0] or 0
        
        # Monthly revenue for current year
        cursor.execute('''
        SELECT strftime('%Y-%m', payment_date) as month, SUM(amount) as revenue
        FROM payment_history 
        WHERE payment_date >= date('now', 'start of year')
        GROUP BY strftime('%Y-%m', payment_date)
        ORDER BY month
        ''')
        monthly_revenue = [dict(zip(['month', 'revenue'], row)) for row in cursor.fetchall()]
        
        # Revenue by membership type
        cursor.execute('''
        SELECT m.membership_type, SUM(ph.amount) as revenue, COUNT(ph.id) as payments
        FROM payment_history ph
        JOIN members m ON ph.member_id = m.id
        GROUP BY m.membership_type
        ORDER BY revenue DESC
        ''')
        revenue_by_type = [dict(zip(['membership_type', 'revenue', 'payments'], row)) for row in cursor.fetchall()]
        
        # Kids training revenue
        cursor.execute('SELECT SUM(amount) FROM kids_payment_history')
        kids_revenue = cursor.fetchone()[0] or 0
        
        # This month's revenue
        cursor.execute('''
        SELECT SUM(amount) FROM payment_history 
        WHERE payment_date >= date('now', 'start of month')
        ''')
        this_month_revenue = cursor.fetchone()[0] or 0
        
        # Last month's revenue for comparison
        cursor.execute('''
        SELECT SUM(amount) FROM payment_history 
        WHERE payment_date >= date('now', 'start of month', '-1 month')
        AND payment_date < date('now', 'start of month')
        ''')
        last_month_revenue = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'revenue_by_type': revenue_by_type,
            'kids_revenue': kids_revenue,
            'this_month_revenue': this_month_revenue,
            'last_month_revenue': last_month_revenue
        }
    
    def get_membership_analytics(self):
        """Get membership analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Membership type distribution
        cursor.execute('''
        SELECT membership_type, COUNT(*) as count
        FROM members
        GROUP BY membership_type
        ORDER BY count DESC
        ''')
        membership_distribution = [dict(zip(['membership_type', 'count'], row)) for row in cursor.fetchall()]
        
        # New members this month
        cursor.execute('''
        SELECT COUNT(*) FROM members 
        WHERE created_at >= date('now', 'start of month')
        ''')
        new_members_this_month = cursor.fetchone()[0]
        
        # Payment status overview with proper membership type consideration
        today = datetime.now().date()
        
        # Get all members and calculate their individual due dates
        cursor.execute('''
        SELECT id, payment_date, membership_type
        FROM members
        ''')
        
        members = cursor.fetchall()
        overdue_count = 0
        due_soon_count = 0
        active_count = 0
        
        for member in members:
            member_id, payment_date, membership_type = member
            if isinstance(payment_date, str):
                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            
            next_due_date = self.calculate_next_due_date(payment_date, membership_type)
            days_remaining = (next_due_date - today).days
            
            if days_remaining < 0:
                overdue_count += 1
            elif days_remaining <= 7:
                due_soon_count += 1
            else:
                active_count += 1
        
        payment_status_data = {
            'overdue': overdue_count,
            'due_soon': due_soon_count, 
            'active': active_count
        }
        
        conn.close()
        
        return {
            'membership_distribution': membership_distribution,
            'new_members_this_month': new_members_this_month,
            'payment_status': payment_status_data
        }
    
    def get_kids_analytics(self):
        """Get kids training analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Kids by batch time
        cursor.execute('''
        SELECT batch_time, COUNT(*) as count
        FROM kids_training
        WHERE active = TRUE
        GROUP BY batch_time
        ORDER BY count DESC
        ''')
        kids_by_batch = [dict(zip(['batch_time', 'count'], row)) for row in cursor.fetchall()]
        
        # Average age
        cursor.execute('SELECT AVG(age) FROM kids_training WHERE active = TRUE')
        avg_age = cursor.fetchone()[0] or 0
        
        # Age distribution
        cursor.execute('''
        SELECT 
            CASE 
                WHEN age <= 6 THEN '4-6 years'
                WHEN age <= 8 THEN '7-8 years'
                WHEN age <= 10 THEN '9-10 years'
                WHEN age <= 12 THEN '11-12 years'
                ELSE '13+ years'
            END as age_group,
            COUNT(*) as count
        FROM kids_training
        WHERE active = TRUE
        GROUP BY age_group
        ORDER BY age_group
        ''')
        age_distribution = [dict(zip(['age_group', 'count'], row)) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'kids_by_batch': kids_by_batch,
            'average_age': round(avg_age, 1),
            'age_distribution': age_distribution
        }
    
    # Bulk messaging functions
    def get_members_for_bulk_messaging(self, membership_filter="All"):
        """Get members list for bulk messaging with filtering options"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT id, name, phone, email, membership_type
        FROM members
        WHERE 1=1
        '''
        params = []
        
        if membership_filter != "All":
            query += " AND membership_type = ?"
            params.append(membership_filter)
        
        query += " ORDER BY name"
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_kids_parents_for_messaging(self):
        """Get kids parents list for bulk messaging"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT parent_name as name, parent_phone as phone, kid_name
        FROM kids_training
        WHERE active = TRUE
        ORDER BY parent_name
        ''')
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def log_bulk_message(self, message_text, recipient_count, message_type, sent_by="System"):
        """Log bulk message sending for record keeping"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO bulk_messages_log (message_text, recipient_count, message_type, sent_by)
            VALUES (?, ?, ?, ?)
            ''', (message_text, recipient_count, message_type, sent_by))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def get_bulk_message_history(self, limit=10):
        """Get history of bulk messages sent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT message_text, recipient_count, message_type, sent_by, sent_at
        FROM bulk_messages_log
        ORDER BY sent_at DESC
        LIMIT ?
        ''', (limit,))
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    # Check-in functions
    def record_member_checkin(self, member_id, member_name, phone, usage_type="General Play", notes=""):
        """Record a member check-in"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if member already has an active check-in (no check-out)
            cursor.execute('''
            SELECT id FROM member_checkins 
            WHERE member_id = ? AND check_out_time IS NULL
            ORDER BY check_in_time DESC LIMIT 1
            ''', (member_id,))
            
            existing_checkin = cursor.fetchone()
            if existing_checkin:
                conn.close()
                return False, "Member already checked in. Please check out first."
            
            cursor.execute('''
            INSERT INTO member_checkins (member_id, member_name, phone, court_usage_type, notes)
            VALUES (?, ?, ?, ?, ?)
            ''', (member_id, member_name, phone, usage_type, notes))
            
            conn.commit()
            conn.close()
            return True, "Check-in successful"
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False, f"Database error: {e}"
    
    def record_member_checkout(self, member_id):
        """Record a member check-out"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find the active check-in
            cursor.execute('''
            SELECT id, check_in_time FROM member_checkins 
            WHERE member_id = ? AND check_out_time IS NULL
            ORDER BY check_in_time DESC LIMIT 1
            ''', (member_id,))
            
            checkin_record = cursor.fetchone()
            if not checkin_record:
                conn.close()
                return False, "No active check-in found"
            
            checkin_id, check_in_time = checkin_record
            
            # Calculate duration
            check_in_dt = datetime.strptime(check_in_time, '%Y-%m-%d %H:%M:%S')
            check_out_dt = datetime.now()
            duration_minutes = int((check_out_dt - check_in_dt).total_seconds() / 60)
            
            # Update with checkout time and duration
            cursor.execute('''
            UPDATE member_checkins 
            SET check_out_time = CURRENT_TIMESTAMP, duration_minutes = ?
            WHERE id = ?
            ''', (duration_minutes, checkin_id))
            
            conn.commit()
            conn.close()
            return True, f"Check-out successful. Duration: {duration_minutes} minutes"
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False, f"Database error: {e}"
    
    def get_active_checkins(self):
        """Get all currently active check-ins"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, member_id, member_name, phone, check_in_time, court_usage_type, notes
        FROM member_checkins
        WHERE check_out_time IS NULL
        ORDER BY check_in_time DESC
        ''')
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_checkin_history(self, limit=20, member_id=None):
        """Get check-in history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT id, member_id, member_name, phone, check_in_time, check_out_time, 
               duration_minutes, court_usage_type, notes
        FROM member_checkins
        WHERE 1=1
        '''
        params = []
        
        if member_id:
            query += " AND member_id = ?"
            params.append(member_id)
        
        query += " ORDER BY check_in_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_checkin_analytics(self, days_back=30):
        """Get check-in analytics for the specified period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Total visits
        cursor.execute('''
        SELECT COUNT(*) FROM member_checkins
        WHERE check_in_time >= ?
        ''', (cutoff_date,))
        total_visits = cursor.fetchone()[0]
        
        # Unique visitors
        cursor.execute('''
        SELECT COUNT(DISTINCT member_id) FROM member_checkins
        WHERE check_in_time >= ?
        ''', (cutoff_date,))
        unique_visitors = cursor.fetchone()[0]
        
        # Average duration
        cursor.execute('''
        SELECT AVG(duration_minutes) FROM member_checkins
        WHERE check_in_time >= ? AND duration_minutes IS NOT NULL
        ''', (cutoff_date,))
        avg_duration = cursor.fetchone()[0] or 0
        
        # Peak hours
        cursor.execute('''
        SELECT strftime('%H', check_in_time) as hour, COUNT(*) as count
        FROM member_checkins
        WHERE check_in_time >= ?
        GROUP BY hour
        ORDER BY count DESC
        LIMIT 5
        ''', (cutoff_date,))
        peak_hours = [dict(zip(['hour', 'count'], row)) for row in cursor.fetchall()]
        
        # Daily visits
        cursor.execute('''
        SELECT DATE(check_in_time) as date, COUNT(*) as visits
        FROM member_checkins
        WHERE check_in_time >= ?
        GROUP BY DATE(check_in_time)
        ORDER BY date DESC
        LIMIT 7
        ''', (cutoff_date,))
        daily_visits = [dict(zip(['date', 'visits'], row)) for row in cursor.fetchall()]
        
        # Most frequent visitors
        cursor.execute('''
        SELECT member_name, COUNT(*) as visit_count
        FROM member_checkins
        WHERE check_in_time >= ?
        GROUP BY member_id, member_name
        ORDER BY visit_count DESC
        LIMIT 5
        ''', (cutoff_date,))
        frequent_visitors = [dict(zip(['member_name', 'visit_count'], row)) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_visits': total_visits,
            'unique_visitors': unique_visitors,
            'average_duration': round(avg_duration, 1),
            'peak_hours': peak_hours,
            'daily_visits': daily_visits,
            'frequent_visitors': frequent_visitors
        }
    
    def export_members_data(self):
        """Export all members data as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT 
            m.id,
            m.name,
            m.phone,
            m.email,
            m.membership_type,
            m.amount,
            m.payment_date,
            m.reminder_days,
            m.notes,
            m.created_at,
            m.updated_at,
            CASE 
                WHEN DATE('now') > DATE(m.payment_date, '+1 month') THEN 'Overdue'
                WHEN DATE('now') > DATE(m.payment_date, '+' || (30 - m.reminder_days) || ' days') THEN 'Due Soon'
                ELSE 'Active'
            END as status
        FROM members m
        ORDER BY m.name
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def export_payment_history_data(self):
        """Export all payment history data as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT 
            ph.id,
            m.name as member_name,
            m.phone as member_phone,
            ph.amount,
            ph.payment_date,
            ph.payment_method,
            ph.notes,
            ph.created_at
        FROM payment_history ph
        JOIN members m ON ph.member_id = m.id
        ORDER BY ph.payment_date DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def export_kids_training_data(self):
        """Export all kids training data as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT 
            kt.id,
            kt.kid_name,
            kt.parent_name,
            kt.parent_phone,
            kt.age,
            kt.batch_time,
            kt.monthly_fee,
            kt.start_date,
            kt.emergency_contact,
            kt.medical_notes,
            CASE WHEN kt.active = 1 THEN 'Active' ELSE 'Inactive' END as status,
            kt.created_at,
            kt.updated_at
        FROM kids_training kt
        ORDER BY kt.kid_name
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def export_kids_payment_history_data(self):
        """Export all kids payment history data as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT 
            kph.id,
            kt.kid_name,
            kt.parent_name,
            kt.parent_phone,
            kph.amount,
            kph.payment_date,
            kph.payment_method,
            kph.notes,
            kph.created_at
        FROM kids_payment_history kph
        JOIN kids_training kt ON kph.kid_id = kt.id
        ORDER BY kph.payment_date DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def export_checkin_data(self):
        """Export all check-in data as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT 
            mc.id,
            mc.member_name,
            mc.phone,
            mc.check_in_time,
            mc.check_out_time,
            mc.duration_minutes,
            mc.court_usage_type,
            mc.notes,
            CASE 
                WHEN mc.check_out_time IS NULL THEN 'Active'
                ELSE 'Completed'
            END as status
        FROM member_checkins mc
        ORDER BY mc.check_in_time DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def export_reminder_logs_data(self):
        """Export all reminder logs data as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT 
            rl.id,
            m.name as member_name,
            m.phone as member_phone,
            rl.reminder_type,
            rl.sent_date,
            rl.next_due_date,
            rl.message_sent,
            rl.delivery_status,
            rl.notes
        FROM reminder_logs rl
        JOIN members m ON rl.member_id = m.id
        ORDER BY rl.sent_date DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def export_bulk_messages_data(self):
        """Export all bulk messages data as DataFrame"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT 
            bml.id,
            bml.message_content,
            bml.recipient_count,
            bml.sent_date,
            bml.sent_by,
            bml.message_type,
            bml.delivery_status
        FROM bulk_messages_log bml
        ORDER BY bml.sent_date DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_database_summary(self):
        """Get summary statistics for export"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        summary = {}
        
        # Count all tables
        tables = ['members', 'payment_history', 'kids_training', 'kids_payment_history', 
                 'member_checkins', 'reminder_logs', 'bulk_messages_log']
        
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                summary[table] = count
            except sqlite3.OperationalError:
                summary[table] = 0
        
        # Calculate date ranges
        cursor.execute('SELECT MIN(created_at), MAX(created_at) FROM members')
        result = cursor.fetchone()
        if result[0]:
            summary['date_range'] = {'start': result[0], 'end': result[1]}
        else:
            summary['date_range'] = {'start': 'No data', 'end': 'No data'}
        
        conn.close()
        return summary