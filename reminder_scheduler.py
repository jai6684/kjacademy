from datetime import datetime, timedelta
import sqlite3

class ReminderScheduler:
    def __init__(self):
        pass
    
    def get_pending_reminders(self, db_manager):
        """Get list of members who need payment reminders"""
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        pending_reminders = []
        
        # Get all members
        cursor.execute('''
        SELECT id, name, phone, email, membership_type, amount, payment_date, reminder_days
        FROM members
        ORDER BY name
        ''')
        
        members = cursor.fetchall()
        
        for member in members:
            member_id, name, phone, email, membership_type, amount, payment_date, reminder_days = member
            
            # Convert payment_date string to date object
            if isinstance(payment_date, str):
                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
            
            # Calculate next due date
            next_due_date = db_manager.calculate_next_due_date(payment_date, membership_type)
            
            # Calculate days until due date
            days_remaining = (next_due_date - today).days
            
            # Check if reminder should be sent
            should_remind = False
            reminder_type = "payment_reminder"
            
            if days_remaining < 0:
                # Overdue
                should_remind = True
                reminder_type = "overdue_reminder"
            elif days_remaining <= reminder_days:
                # Within reminder window
                should_remind = True
                reminder_type = "payment_reminder"
            
            # Check if reminder was already sent recently (within last 3 days)
            if should_remind:
                recent_reminder = self._check_recent_reminder(cursor, member_id, reminder_type)
                if not recent_reminder:
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
    
    def _check_recent_reminder(self, cursor, member_id, reminder_type, days_back=3):
        """Check if a reminder was sent recently"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        cursor.execute('''
        SELECT COUNT(*) FROM reminder_logs
        WHERE member_id = ? AND reminder_type = ? AND sent_at >= ? AND success = 1
        ''', (member_id, reminder_type, cutoff_date))
        
        count = cursor.fetchone()[0]
        return count > 0
    
    def get_overdue_members(self, db_manager):
        """Get members with overdue payments"""
        pending = self.get_pending_reminders(db_manager)
        return [r for r in pending if r['days_remaining'] < 0]
    
    def get_due_soon_members(self, db_manager, days_ahead=7):
        """Get members with payments due within specified days"""
        pending = self.get_pending_reminders(db_manager)
        return [r for r in pending if 0 <= r['days_remaining'] <= days_ahead]
    
    def get_kids_pending_reminders(self, db_manager):
        """Get kids training payments that need reminders"""
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date()
        pending_reminders = []
        
        # Get all active kids
        cursor.execute('''
        SELECT id, kid_name, parent_name, parent_phone, monthly_fee, start_date
        FROM kids_training
        WHERE active = TRUE
        ORDER BY kid_name
        ''')
        
        kids = cursor.fetchall()
        
        for kid in kids:
            kid_id, kid_name, parent_name, parent_phone, monthly_fee, start_date = kid
            
            # Get last payment date
            cursor.execute('''
            SELECT payment_date FROM kids_payment_history
            WHERE kid_id = ?
            ORDER BY payment_date DESC
            LIMIT 1
            ''', (kid_id,))
            
            last_payment = cursor.fetchone()
            
            if last_payment:
                last_payment_date = datetime.strptime(last_payment[0], '%Y-%m-%d').date()
                next_due_date = last_payment_date + timedelta(days=30)  # Monthly payment
            else:
                # No payments yet, use start date + 30 days
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                next_due_date = start_date + timedelta(days=30)
            
            # Calculate days remaining
            days_remaining = (next_due_date - today).days
            
            # Check if reminder needed (within 15 days or overdue)
            if days_remaining <= 15:
                # Check for recent reminders
                recent_reminder = self._check_recent_reminder(cursor, kid_id, "kids_payment_reminder")
                if not recent_reminder:
                    pending_reminders.append({
                        'kid_id': kid_id,
                        'kid_name': kid_name,
                        'parent_name': parent_name,
                        'phone': parent_phone,
                        'amount': monthly_fee,
                        'next_due_date': next_due_date,
                        'days_remaining': days_remaining,
                        'reminder_type': "kids_payment_reminder"
                    })
        
        conn.close()
        return pending_reminders
    
    def schedule_automatic_reminders(self, db_manager, message_manager):
        """Schedule and send automatic reminders (can be called by a cron job)"""
        # Get pending reminders
        pending_member_reminders = self.get_pending_reminders(db_manager)
        pending_kids_reminders = self.get_kids_pending_reminders(db_manager)
        
        sent_count = 0
        
        # Send member reminders
        for reminder in pending_member_reminders:
            template_type = reminder['reminder_type']
            message_template = db_manager.get_message_template(template_type)
            
            if message_template:
                formatted_message = message_manager.format_message(message_template, reminder)
                success = message_manager.send_message(
                    phone=reminder['phone'],
                    message=formatted_message,
                    method="SMS"
                )
                
                if success:
                    db_manager.log_reminder(reminder['member_id'], template_type, formatted_message)
                    sent_count += 1
        
        # Send kids reminders
        for reminder in pending_kids_reminders:
            # Use parent reminder template or create a custom one
            message_template = f"""Hi {reminder['parent_name']}! 🏸

Your child {reminder['kid_name']}'s badminton training fee of ₹{reminder['amount']} is due on {reminder['next_due_date'].strftime('%d-%m-%Y')}.

Please make the payment to continue the training sessions.

Thank you!
Contact: +91-9876543210"""
            
            success = message_manager.send_message(
                phone=reminder['phone'],
                message=message_template,
                method="SMS"
            )
            
            if success:
                # Log reminder for kids (using kid_id as member_id)
                db_manager.log_reminder(reminder['kid_id'], "kids_payment_reminder", message_template)
                sent_count += 1
        
        return sent_count
    
    def get_reminder_statistics(self, db_manager, days_back=30):
        """Get statistics about sent reminders"""
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Get reminder stats
        cursor.execute('''
        SELECT reminder_type, COUNT(*) as count, SUM(success) as successful
        FROM reminder_logs
        WHERE sent_at >= ?
        GROUP BY reminder_type
        ''', (cutoff_date,))
        
        stats = {}
        for row in cursor.fetchall():
            reminder_type, count, successful = row
            stats[reminder_type] = {
                'total_sent': count,
                'successful': successful,
                'failed': count - successful,
                'success_rate': (successful / count * 100) if count > 0 else 0
            }
        
        conn.close()
        return stats
