import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from database import DatabaseManager
from messaging import MessageManager
from reminder_scheduler import ReminderScheduler
from utils import format_phone_number, validate_phone_number
import time

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

def main():
    st.set_page_config(
        page_title="KJ Badminton Academy",
        page_icon="🏸",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
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
                "src": "data:image/png;base64,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",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAADl0RVh0U29mdHdhcmUAbWF0cGxvdGxpYiB2ZXJzaW9uIDMuMC4zLCBodHRwOi8vbWF0cGxvdGxpYi5vcmcvnQurowAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAABmJLR0QA/wD/AP+gvaeTAAAT9dToZjPc9YOhu3VmF9uZvn9/diesdAI0v8iBFmY2o2NGmCuhfxqmT3OHT2ttMjLaMCONXQGg9H4UVFlePXlQ/GSInc0FtUAibuP0LbixcMDTil0IHULI9QjSu1CqqmSke7hBAixm8+l8DW9BSXnOFajB3mdm0TlOfStwiJNL+d6owdNsiy74mKDNOY2vcmO0fmdMlE+ni0qpSNDoZhyZax7uHEWhLGtXwOj9+k+6Zh6clBsRZJP9UwLtRAVM7l44SjT2smvbnptS2JI482zn5zcyrmcZ6oXbDVYzWy+XbhMjV975XZlL7COZR9d2xUJPdeM5hJlI1KKnlD5nJVnKD1YwZ+f6bQIeel4WEJlV7H0H0TtgWRxD8w+fws2j3x8hVR3k5VJlEioai9jqC2OeCdbFFSaJmrCZ6aT20vVZE6gJk69UUd39cugkUaTVxG5I3AK/8WsxbUdkBsPhyPMxPBOD4YANU0cghvnh9XZP1rRUbSH2Td/YkbPQLOqkivoXkD26iFxLGoZJ0HXcBfO8I9hl0U5Qk15oRpuYDszJ6ZeRwFx9fWLFG8nP5gMOX6yvnQxinG40y36Cj5Uh/dfSb+TCsLZN9ddaXdZWhSfbMc1Mm5AcOPIrFtJG35hTYWJy9Ua5cac+yw6tWSdLN2IQhuzsXMMeCUKdarKnirA3VDox6jm9SFs/p0LB9Y0g7Eufyfj3oatEUcCWwppn1qIeJAo4MU9M0EN8Z/7CzFoRE0xCM2idauLw6IJbqEOxjyDcR6kvOkRAhAk3Qp33WHQqcaomKJkynbKp7WXJYuEUprCwssyq9pJcpbRAHqgaUWVn9vFpwRnFX1Ykh1lymXjiNFTiE2KjJlP8FmQkVbeY/VzpBm0vuA41AGyMBkBBdTMGRH5mI16m8zdS0Xd1aExfZbzKs0SHM0LP2l9fPDmkYdYNxmFjwzwCNRPJEQSB4FHr1GcAq847gn5IZgoQb1/aG775",
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
        page = st.selectbox(
            "Select Page",
            ["Dashboard", "Analytics", "Member Registration", "Payment Tracking", "Kids Training", 
             "Send Reminders", "Bulk Messaging", "Member Check-in", "Message Settings", "Member Database", "Data Export"]
        )
    
    # Main content based on selected page
    if page == "Dashboard":
        show_dashboard(db_manager, reminder_scheduler)
    elif page == "Analytics":
        show_analytics(db_manager)
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
    elif page == "Member Check-in":
        show_member_checkin(db_manager)
    elif page == "Message Settings":
        show_message_settings(db_manager)
    elif page == "Member Database":
        show_member_database(db_manager)
    elif page == "Data Export":
        show_data_export(db_manager)

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
            for reminder in pending_reminders[:5]:  # Show only first 5
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
                # Format phone number
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
            # Search functionality
            search_kid = st.text_input("🔍 Search Kids", placeholder="Enter kid's name or parent's name")
            
            # Filter kids based on search
            if search_kid:
                kids_data = [kid for kid in kids_data if 
                           search_kid.lower() in kid['kid_name'].lower() or 
                           search_kid.lower() in kid['parent_name'].lower()]
            
            # Display kids data
            for kid in kids_data:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{kid['kid_name']}** (Age: {kid['age']})")
                        st.caption(f"Parent: {kid['parent_name']} | 📞 {kid['parent_phone']}")
                    
                    with col2:
                        st.write(f"₹{kid['monthly_fee']}/month")
                        st.caption(f"Batch: {kid['batch_time']}")
                    
                    with col3:
                        # Calculate next payment due
                        last_payment = db_manager.get_last_kid_payment(kid['id'])
                        if last_payment:
                            next_due = datetime.strptime(last_payment['payment_date'], '%Y-%m-%d').date() + timedelta(days=30)
                            days_remaining = (next_due - datetime.now().date()).days
                            
                            if days_remaining < 0:
                                st.error(f"Overdue by {abs(days_remaining)} days")
                            elif days_remaining <= 7:
                                st.warning(f"Due in {days_remaining} days")
                            else:
                                st.success(f"Due in {days_remaining} days")
                        else:
                            st.info("No payments recorded")
                    
                    with col4:
                        if st.button("💰", key=f"kid_pay_{kid['id']}", help="Record Payment"):
                            show_kid_payment_modal(db_manager, kid)
                    
                    st.markdown("---")
        else:
            st.info("No kids registered yet")

def show_kid_payment_modal(db_manager, kid):
    """Show kid payment recording modal"""
    with st.expander(f"Record Payment for {kid['kid_name']}", expanded=True):
        with st.form(f"kid_payment_{kid['id']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                amount = st.number_input("Amount (₹)", min_value=0.0, value=float(kid['monthly_fee']) if kid['monthly_fee'] is not None else 0.0)
                payment_date = st.date_input("Payment Date", value=datetime.now().date())
            
            with col2:
                payment_method = st.selectbox("Payment Method", ["Cash", "UPI", "Card", "Bank Transfer"])
                notes = st.text_input("Notes", placeholder="Payment reference or notes")
            
            if st.form_submit_button("Record Payment", use_container_width=True):
                success = db_manager.record_kid_payment(
                    kid_id=kid['id'],
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    notes=notes
                )
                
                if success:
                    st.success("✅ Payment recorded successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to record payment")

def show_send_reminders(db_manager, message_manager):
    st.header("📱 Send Payment Reminders")
    
    # Get pending reminders
    reminder_scheduler = init_reminder_scheduler()
    pending_reminders = reminder_scheduler.get_pending_reminders(db_manager)
    
    if not pending_reminders:
        st.info("🎉 No pending reminders at this time!")
        return
    
    st.write(f"Found {len(pending_reminders)} members who need payment reminders:")
    
    # Display pending reminders
    selected_reminders = []
    
    for reminder in pending_reminders:
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            
            with col1:
                selected = st.checkbox("", key=f"select_{reminder['member_id']}")
                if selected:
                    selected_reminders.append(reminder)
            
            with col2:
                st.write(f"**{reminder['member_name']}**")
                st.caption(f"📞 {reminder['phone']}")
            
            with col3:
                st.write(f"₹{reminder['amount']}")
                st.caption(f"{reminder['membership_type']}")
            
            with col4:
                days = reminder['days_remaining']
                if days < 0:
                    st.error(f"Overdue by {abs(days)} days")
                elif days <= 3:
                    st.warning(f"Due in {days} days")
                else:
                    st.info(f"Due in {days} days")
            
            st.markdown("---")
    
    # Send reminders section
    if selected_reminders:
        st.subheader(f"Send Reminders to {len(selected_reminders)} Selected Members")
        
        # Message preview
        sample_reminder = selected_reminders[0]
        message_template = db_manager.get_message_template("payment_reminder")
        preview_message = message_manager.format_message(message_template, sample_reminder)
        
        st.text_area("Message Preview:", value=preview_message, height=100, disabled=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            send_method = st.selectbox("Send via", ["SMS", "WhatsApp"])
        
        with col2:
            if st.button("🚀 Send Reminders", use_container_width=True, type="primary"):
                send_bulk_reminders(message_manager, selected_reminders, send_method, db_manager)

def send_bulk_reminders(message_manager, reminders, send_method, db_manager):
    """Generate WhatsApp links for sending reminders"""
    import urllib.parse
    
    st.subheader("📱 WhatsApp Reminder Links")
    st.info("Click each link below to open WhatsApp with the message pre-filled. You can then send it manually.")
    
    total_count = len(reminders)
    
    for i, reminder in enumerate(reminders):
        message_template = db_manager.get_message_template("payment_reminder")
        message = message_manager.format_message(message_template, reminder)
        
        # Format phone number for WhatsApp URL (remove spaces, ensure country code)
        phone = reminder['phone'].replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Add country code if not present (assuming Indian numbers start with +91)
        if not phone.startswith('+'):
            if phone.startswith('91'):
                phone = '+' + phone
            elif len(phone) == 10:  # Indian mobile number without country code
                phone = '+91' + phone
            else:
                phone = '+91' + phone  # Default to India
        
        # URL encode the message
        encoded_message = urllib.parse.quote(message)
        
        # Create WhatsApp URL
        whatsapp_url = f"https://wa.me/{phone.replace('+', '')}?text={encoded_message}"
        
        # Display the reminder card
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{reminder['member_name']}** - {reminder['phone']}")
                st.caption(f"₹{reminder['amount']} | {reminder['membership_type']}")
                
                # Show a preview of the message (truncated)
                preview = message[:100] + "..." if len(message) > 100 else message
                st.text(f"Message: {preview}")
            
            with col2:
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color: #25D366; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">📱 Open WhatsApp</button></a>', unsafe_allow_html=True)
                
                # Log the reminder when link is generated
                db_manager.log_reminder(reminder['member_id'], "WhatsApp_Link", message)
        
        st.markdown("---")
    
    st.success(f"✅ Generated WhatsApp links for {total_count} members!")
    st.info("💡 **How to use:** Click each 'Open WhatsApp' button to open WhatsApp with the message ready. Review and send manually.")
    
    # Option to mark all as sent
    if st.button("✅ Mark All as Sent", type="secondary", use_container_width=True):
        for reminder in reminders:
            message_template = db_manager.get_message_template("payment_reminder")
            message = message_manager.format_message(message_template, reminder)
            db_manager.log_reminder(reminder['member_id'], "WhatsApp_Manual", message)
        st.success("All reminders marked as sent!")
        st.rerun()

def show_message_settings(db_manager):
    st.header("⚙️ Message Settings")
    
    st.subheader("Custom Message Templates")
    
    # Get current templates
    payment_template = db_manager.get_message_template("payment_reminder")
    overdue_template = db_manager.get_message_template("overdue_reminder")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Payment Reminder", "Overdue Reminder", "Available Variables", "Twilio Configuration"])
    
    with tab1:
        st.write("**Payment Reminder Template** (sent 15-30 days before due date)")
        
        new_payment_template = st.text_area(
            "Message Template:",
            value=payment_template,
            height=150,
            help="Use variables like {member_name}, {amount}, {due_date}, etc."
        )
        
        if st.button("Update Payment Template", key="update_payment"):
            if db_manager.update_message_template("payment_reminder", new_payment_template):
                st.success("✅ Payment reminder template updated!")
            else:
                st.error("❌ Failed to update template")
    
    with tab2:
        st.write("**Overdue Reminder Template** (sent after due date)")
        
        new_overdue_template = st.text_area(
            "Message Template:",
            value=overdue_template,
            height=150,
            help="Use variables like {member_name}, {amount}, {overdue_days}, etc."
        )
        
        if st.button("Update Overdue Template", key="update_overdue"):
            if db_manager.update_message_template("overdue_reminder", new_overdue_template):
                st.success("✅ Overdue reminder template updated!")
            else:
                st.error("❌ Failed to update template")
    
    with tab3:
        st.write("**Available Variables for Message Templates:**")
        
        variables = [
            "{member_name} - Member's full name",
            "{amount} - Payment amount",
            "{due_date} - Next payment due date",
            "{membership_type} - Type of membership",
            "{overdue_days} - Number of days overdue",
            "{court_name} - Your badminton court name",
            "{phone} - Your contact phone number"
        ]
        
        for var in variables:
            st.code(var)
        
        st.info("💡 You can customize these templates with your own message style and include any of these variables.")
    
    with tab4:
        st.write("**Twilio Configuration & Testing**")
        
        # Get message manager for testing
        message_manager = init_message_manager()
        
        # Show current configuration status
        st.subheader("📋 Current Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if message_manager.account_sid:
                st.success("✅ Account SID: Configured")
                st.text(f"SID: {message_manager.account_sid[:8]}...")
            else:
                st.error("❌ Account SID: Not configured")
            
            if message_manager.auth_token:
                st.success("✅ Auth Token: Configured")
            else:
                st.error("❌ Auth Token: Not configured")
        
        with col2:
            if message_manager.phone_number:
                st.success("✅ Phone Number: Configured")
                st.text(f"Number: {message_manager.phone_number}")
                
                # Check phone number format
                if not message_manager.phone_number.startswith('+'):
                    st.warning("⚠️ Phone number should start with '+' (country code)")
                    st.info("💡 Example: +19042202855 for US numbers")
            else:
                st.error("❌ Phone Number: Not configured")
        
        st.markdown("---")
        
        # Test connection button
        st.subheader("🧪 Test Connection")
        
        if st.button("🔗 Test Twilio Connection", use_container_width=True, type="primary"):
            with st.spinner("Testing Twilio connection..."):
                success, message = message_manager.test_connection()
                
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                else:
                    st.error(f"❌ {message}")
                    
                    # Provide helpful troubleshooting
                    st.markdown("**🔧 Troubleshooting:**")
                    
                    if "Invalid From Number" in message or "21212" in message:
                        st.warning("**Phone Number Format Issue:**")
                        st.markdown("""
                        - Your phone number needs to include the country code
                        - Format: `+1XXXXXXXXXX` for US numbers
                        - Example: `+19042202855` instead of `9042202855`
                        - Go to Secrets and update `TWILIO_PHONE_NUMBER`
                        """)
                    
                    elif "Authentication" in message or "20003" in message:
                        st.warning("**Credential Issue:**")
                        st.markdown("""
                        - Check your Account SID and Auth Token
                        - Make sure they're copied correctly from Twilio Console
                        - No extra spaces or characters
                        """)
                    
                    elif "Channel" in message or "63007" in message:
                        st.warning("**Phone Number Verification Issue:**")
                        st.markdown("""
                        - Make sure the phone number is verified in your Twilio account
                        - Check that it's an active number in your Twilio console
                        - For WhatsApp, ensure WhatsApp is enabled for this number
                        """)
                    
                    else:
                        st.info("**General Steps:**")
                        st.markdown("""
                        1. Check your Twilio Console for any account issues
                        2. Verify your phone number is active and verified
                        3. Make sure your account has sufficient balance
                        4. Check that your phone number format includes country code (+1...)
                        """)
        
        # Configuration guide
        st.markdown("---")
        st.subheader("⚙️ Configuration Guide")
        
        with st.expander("🔧 How to Configure Twilio", expanded=False):
            st.markdown("""
            **Step 1: Get Twilio Credentials**
            1. Sign up/login to [Twilio Console](https://console.twilio.com)
            2. Go to Account Dashboard
            3. Copy your Account SID and Auth Token
            
            **Step 2: Get a Phone Number**
            1. Go to Phone Numbers → Manage → Buy a number
            2. Choose a number that supports SMS (and WhatsApp if needed)
            3. Note the full number with country code
            
            **Step 3: Set Environment Variables**
            1. In your Replit project, go to the Secrets tab
            2. Add these three secrets:
               - `TWILIO_ACCOUNT_SID`: Your Account SID
               - `TWILIO_AUTH_TOKEN`: Your Auth Token  
               - `TWILIO_PHONE_NUMBER`: Your phone number with country code (e.g., +19042202855)
            
            **Step 4: Test**
            1. Use the test button above to verify connection
            2. Try sending a test reminder to yourself
            """)
        
        # Quick fix for common issues
        st.markdown("---")
        st.subheader("🚨 Quick Fixes")
        
        if message_manager.phone_number and not message_manager.phone_number.startswith('+'):
            st.error("**Most Common Issue: Missing Country Code**")
            st.markdown(f"""
            Your current phone number: `{message_manager.phone_number}`
            
            **Fix:** Update your `TWILIO_PHONE_NUMBER` secret to: `+1{message_manager.phone_number}`
            (assuming it's a US number)
            """)
            
            if st.button("🔗 Open Secrets Tab", use_container_width=True):
                st.markdown("**Go to your Replit project → Secrets tab → Edit TWILIO_PHONE_NUMBER**")
        
        st.markdown("---")
        st.info("💡 After updating any configuration, restart the app to apply changes.")

def show_member_database(db_manager):
    st.header("🗄️ Member Database")
    
    # Search and filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search", placeholder="Name, phone, or email")
    with col2:
        membership_filter = st.selectbox("Membership Type", 
                                       ["All", "Monthly Subscriber", "Quarterly", "Half Yearly", "Annual"])
    with col3:
        sort_by = st.selectbox("Sort By", ["Name", "Payment Date", "Amount", "Due Date"])
    
    # Get all members
    members = db_manager.search_members(search_term, membership_filter, sort_by)
    
    if members:
        st.write(f"Found {len(members)} members")
        
        # Display members in a more detailed format
        for member in members:
            with st.expander(f"{member['name']} - {member['membership_type']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Contact Information:**")
                    st.write(f"📞 Phone: {member['phone']}")
                    if member['email']:
                        st.write(f"✉️ Email: {member['email']}")
                    
                    st.write(f"**Membership:** {member['membership_type']}")
                    st.write(f"**Amount:** ₹{member['amount']}")
                    st.write(f"**Payment Date:** {member['payment_date']}")
                
                with col2:
                    # Calculate next due date
                    next_due = db_manager.calculate_next_due_date(member['payment_date'], member['membership_type'])
                    days_remaining = (next_due - datetime.now().date()).days
                    
                    st.write("**Payment Status:**")
                    if days_remaining < 0:
                        st.error(f"❌ Overdue by {abs(days_remaining)} days")
                    elif days_remaining <= 7:
                        st.warning(f"⚠️ Due in {days_remaining} days")
                    else:
                        st.success(f"✅ Due in {days_remaining} days")
                    
                    if member['notes']:
                        st.write("**Notes:**")
                        st.write(member['notes'])
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("💰 Record Payment", key=f"pay_db_{member['id']}"):
                        show_payment_modal(db_manager, member)
                with col2:
                    if st.button("📝 Edit Member", key=f"edit_db_{member['id']}"):
                        show_edit_member_modal(db_manager, member)
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_db_{member['id']}", type="secondary"):
                        if st.button("Confirm Delete", key=f"confirm_delete_{member['id']}", type="primary"):
                            if db_manager.delete_member(member['id']):
                                st.success("Member deleted successfully!")
                                st.rerun()
    else:
        st.info("No members found matching your search criteria")

def show_analytics(db_manager):
    """Show analytics dashboard"""
    st.header("📈 Analytics Dashboard")
    
    # Get analytics data
    revenue_analytics = db_manager.get_revenue_analytics()
    membership_analytics = db_manager.get_membership_analytics()
    kids_analytics = db_manager.get_kids_analytics()
    
    # Revenue Overview Section
    st.subheader("💰 Revenue Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Revenue", 
            f"₹{revenue_analytics['total_revenue']:,.0f}",
            help="Total revenue from all payments"
        )
    
    with col2:
        st.metric(
            "This Month", 
            f"₹{revenue_analytics['this_month_revenue']:,.0f}",
            delta=f"₹{revenue_analytics['this_month_revenue'] - revenue_analytics['last_month_revenue']:,.0f}",
            help="Revenue for current month vs last month"
        )
    
    with col3:
        st.metric(
            "Kids Training", 
            f"₹{revenue_analytics['kids_revenue']:,.0f}",
            help="Total revenue from kids training"
        )
    
    with col4:
        # Calculate average monthly revenue properly using only monthly_revenue data
        if revenue_analytics['monthly_revenue']:
            avg_monthly = sum(item['revenue'] for item in revenue_analytics['monthly_revenue']) / len(revenue_analytics['monthly_revenue'])
        else:
            avg_monthly = 0
        st.metric(
            "Avg Monthly", 
            f"₹{avg_monthly:,.0f}",
            help="Average monthly revenue (current year)"
        )
    
    st.markdown("---")
    
    # Revenue Charts Section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Monthly Revenue Trend")
        if revenue_analytics['monthly_revenue']:
            import pandas as pd
            df = pd.DataFrame(revenue_analytics['monthly_revenue'])
            df['month'] = pd.to_datetime(df['month']).dt.strftime('%b %Y')
            st.bar_chart(df.set_index('month')['revenue'])
        else:
            st.info("No revenue data available yet")
    
    with col2:
        st.subheader("💼 Revenue by Membership Type")
        if revenue_analytics['revenue_by_type']:
            import pandas as pd
            df = pd.DataFrame(revenue_analytics['revenue_by_type'])
            st.bar_chart(df.set_index('membership_type')['revenue'])
        else:
            st.info("No membership revenue data available")
    
    st.markdown("---")
    
    # Membership Analytics Section
    st.subheader("👥 Membership Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "New Members This Month", 
            membership_analytics['new_members_this_month'],
            help="Members who joined this month"
        )
    
    with col2:
        st.metric(
            "Active Members", 
            membership_analytics['payment_status']['active'],
            help="Members with current payments"
        )
    
    with col3:
        st.metric(
            "Overdue Payments", 
            membership_analytics['payment_status']['overdue'],
            help="Members with overdue payments"
        )
    
    # Membership Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Membership Type Distribution")
        if membership_analytics['membership_distribution']:
            import pandas as pd
            df = pd.DataFrame(membership_analytics['membership_distribution'])
            st.bar_chart(df.set_index('membership_type')['count'])
        else:
            st.info("No membership data available")
    
    with col2:
        st.subheader("⚠️ Payment Status Overview")
        status_data = membership_analytics['payment_status']
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("🟢 Active", status_data['active'])
        with col_b:
            st.metric("🟡 Due Soon", status_data['due_soon'])
        with col_c:
            st.metric("🔴 Overdue", status_data['overdue'])
    
    st.markdown("---")
    
    # Kids Training Analytics
    st.subheader("🧒 Kids Training Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Kids Enrolled", 
            sum(item['count'] for item in kids_analytics['kids_by_batch']),
            help="Total number of kids in training"
        )
    
    with col2:
        st.metric(
            "Average Age", 
            f"{kids_analytics['average_age']} years",
            help="Average age of kids in training"
        )
    
    with col3:
        most_popular_batch = max(kids_analytics['kids_by_batch'], key=lambda x: x['count'])['batch_time'] if kids_analytics['kids_by_batch'] else "N/A"
        st.metric(
            "Most Popular Batch", 
            most_popular_batch.split('(')[0].strip() if most_popular_batch != "N/A" else "N/A",
            help="Batch time with most enrollments"
        )
    
    # Kids Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏰ Kids by Batch Time")
        if kids_analytics['kids_by_batch']:
            import pandas as pd
            # Simplify batch time for display
            simplified_data = []
            for item in kids_analytics['kids_by_batch']:
                simplified_batch = item['batch_time'].split('(')[0].strip()
                simplified_data.append({'batch_time': simplified_batch, 'count': item['count']})
            df = pd.DataFrame(simplified_data)
            st.bar_chart(df.set_index('batch_time')['count'])
        else:
            st.info("No kids enrollment data available")
    
    with col2:
        st.subheader("🎂 Age Distribution")
        if kids_analytics['age_distribution']:
            import pandas as pd
            df = pd.DataFrame(kids_analytics['age_distribution'])
            st.bar_chart(df.set_index('age_group')['count'])
        else:
            st.info("No age distribution data available")

def show_bulk_messaging(db_manager, message_manager):
    """Show bulk messaging interface"""
    st.header("📢 Bulk Messaging")
    
    # Message composition section
    st.subheader("✉️ Compose Message")
    
    # Recipient selection
    col1, col2 = st.columns(2)
    
    with col1:
        recipient_type = st.selectbox(
            "Send To:",
            ["All Members", "Members by Type", "Kids Parents", "Custom Selection"]
        )
    
    with col2:
        if recipient_type == "Members by Type":
            membership_filter = st.selectbox(
                "Membership Type:",
                ["Monthly Subscriber", "Quarterly", "Half Yearly", "Annual"]
            )
        else:
            membership_filter = "All"
    
    # Get recipients based on selection
    if recipient_type == "All Members":
        recipients = db_manager.get_members_for_bulk_messaging()
        kids_parents = db_manager.get_kids_parents_for_messaging()
        all_recipients = recipients + [{"id": f"parent_{i}", "name": p["name"], "phone": p["phone"], "membership_type": "Kids Parent"} for i, p in enumerate(kids_parents)]
    elif recipient_type == "Members by Type":
        recipients = db_manager.get_members_for_bulk_messaging(membership_filter)
        all_recipients = recipients
    elif recipient_type == "Kids Parents":
        kids_parents = db_manager.get_kids_parents_for_messaging()
        all_recipients = [{"id": f"parent_{i}", "name": p["name"], "phone": p["phone"], "membership_type": "Kids Parent"} for i, p in enumerate(kids_parents)]
    else:  # Custom Selection
        all_members = db_manager.get_members_for_bulk_messaging()
        kids_parents = db_manager.get_kids_parents_for_messaging()
        all_possible = all_members + [{"id": f"parent_{i}", "name": p["name"], "phone": p["phone"], "membership_type": "Kids Parent"} for i, p in enumerate(kids_parents)]
        
        st.write("**Select Recipients:**")
        selected_recipients = []
        for person in all_possible:
            if st.checkbox(f"{person['name']} ({person.get('membership_type', 'Member')}) - {person['phone']}", key=f"select_{person['id']}"):
                selected_recipients.append(person)
        all_recipients = selected_recipients
    
    # Show recipient count
    st.info(f"📊 **{len(all_recipients)} recipients** will receive this message")
    
    # Message composition
    col1, col2 = st.columns([2, 1])
    
    with col1:
        message_subject = st.text_input("Subject (optional)", placeholder="Court Announcement")
        message_text = st.text_area(
            "Message *", 
            placeholder="Write your announcement here...\n\nExample:\nDear members,\n\nWe're excited to announce new court timings from next week.\n\nMorning slots: 6:00 AM - 10:00 AM\nEvening slots: 4:00 PM - 10:00 PM\n\nThank you!",
            height=200
        )
    
    with col2:
        st.write("**Message Templates:**")
        
        template_options = {
            "Court Maintenance": "Dear members,\n\nCourt maintenance is scheduled for {date}. The court will be closed from {time}.\n\nWe apologize for any inconvenience.\n\nThank you!",
            "New Timings": "Dear members,\n\nWe're updating our court timings starting {date}:\n\nMorning: 6:00 AM - 10:00 AM\nEvening: 4:00 PM - 10:00 PM\n\nThank you!",
            "Tournament": "Exciting news! 🏸\n\nWe're organizing a badminton tournament on {date}.\n\nRegistration: {details}\nPrize: {prize}\n\nJoin us!",
            "Holiday Notice": "Dear members,\n\nThe court will remain closed on {date} due to {reason}.\n\nRegular timings will resume from {resume_date}.\n\nThank you!"
        }
        
        selected_template = st.selectbox("Quick Templates:", ["Custom"] + list(template_options.keys()))
        
        if selected_template != "Custom":
            if st.button("Use Template", use_container_width=True):
                st.session_state['bulk_message_text'] = template_options[selected_template]
                st.rerun()
        
        # Use session state value if available
        if 'bulk_message_text' in st.session_state and not message_text:
            message_text = st.session_state['bulk_message_text']
    
    # Sending options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        send_method = st.selectbox("Send via:", ["SMS", "WhatsApp"])
    
    with col2:
        include_court_info = st.checkbox("Include Court Contact", value=True)
    
    with col3:
        send_test = st.checkbox("Send Test First")
    
    # Build final message (always build it when message_text exists)
    final_message = ""
    if message_text:
        if message_subject:
            final_message += f"Subject: {message_subject}\n\n"
        
        final_message += message_text
        
        if include_court_info:
            final_message += "\n\n---\nKJ Badminton Academy\nContact: +91-9876543210"
    
    # Preview message
    if message_text:
        st.subheader("📝 Message Preview")
        st.text_area("Final message that will be sent:", value=final_message, height=150, disabled=True)
        
        # Cost estimation
        if all_recipients:
            cost_estimate = message_manager.get_message_cost_estimate(len(all_recipients), send_method)
            st.write(f"**Estimated Cost:** ${cost_estimate['total_cost']:.3f} USD ({cost_estimate['recipients']} {cost_estimate['method']} messages)")
    
    # Send buttons
    if message_text and all_recipients and final_message:
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if send_test and st.button("🧪 Send Test Message", use_container_width=True):
                # Send to first recipient only
                test_recipient = all_recipients[0]
                success = message_manager.send_message(
                    phone=test_recipient['phone'],
                    message=f"[TEST MESSAGE]\n\n{final_message}",
                    method=send_method
                )
                
                if success:
                    st.success(f"✅ Test message sent to {test_recipient['name']}")
                else:
                    st.error("❌ Failed to send test message")
        
        with col2:
            if st.button("🚀 Send to All", use_container_width=True, type="primary"):
                send_bulk_announcement(db_manager, message_manager, all_recipients, final_message, send_method, recipient_type)
        
        with col3:
            if st.button("💾 Save as Template", use_container_width=True):
                # This would save the message as a custom template
                st.info("Template saving feature coming soon!")
    
    st.markdown("---")
    
    # Message history
    st.subheader("📜 Recent Bulk Messages")
    message_history = db_manager.get_bulk_message_history(5)
    
    if message_history:
        for msg in message_history:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Truncate long messages
                    display_text = msg['message_text'][:100] + "..." if len(msg['message_text']) > 100 else msg['message_text']
                    st.write(f"**{display_text}**")
                    st.caption(f"Sent by: {msg['sent_by']} | {msg['sent_at']}")
                
                with col2:
                    st.metric("Recipients", msg['recipient_count'])
                
                with col3:
                    st.write(f"**{msg['message_type']}**")
                
                st.markdown("---")
    else:
        st.info("No bulk messages sent yet")

def show_member_checkin(db_manager):
    """Show member check-in system"""
    st.header("🏸 Member Check-in System")
    
    tab1, tab2, tab3 = st.tabs(["Check-in/Check-out", "Currently in Court", "Analytics"])
    
    with tab1:
        st.subheader("⏱️ Check-in / Check-out")
        
        # Member selection for check-in
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Check-in Member**")
            
            # Get all members for selection
            all_members = db_manager.search_members()
            
            if all_members:
                member_options = {f"{member['name']} ({member['phone']})": member for member in all_members}
                selected_member_key = st.selectbox(
                    "Select Member:",
                    options=list(member_options.keys()),
                    help="Choose a member to check in"
                )
                
                if selected_member_key:
                    selected_member = member_options[selected_member_key]
                    
                    usage_type = st.selectbox(
                        "Court Usage Type:",
                        ["General Play", "Training Session", "Tournament", "Private Coaching", "Practice Match"]
                    )
                    
                    notes = st.text_input("Notes (optional)", placeholder="Additional notes about the visit")
                    
                    if st.button("✅ Check In", use_container_width=True, type="primary"):
                        success, message = db_manager.record_member_checkin(
                            member_id=selected_member['id'],
                            member_name=selected_member['name'],
                            phone=selected_member['phone'],
                            usage_type=usage_type,
                            notes=notes
                        )
                        
                        if success:
                            st.success(f"✅ {selected_member['name']} checked in successfully!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            else:
                st.info("No members found. Please register members first.")
        
        with col2:
            st.write("**Check-out Member**")
            
            # Get active check-ins for checkout
            active_checkins = db_manager.get_active_checkins()
            
            if active_checkins:
                checkout_options = {f"{checkin['member_name']} (In: {checkin['check_in_time']})": checkin for checkin in active_checkins}
                selected_checkout_key = st.selectbox(
                    "Select Member to Check-out:",
                    options=list(checkout_options.keys()),
                    help="Choose a member to check out"
                )
                
                if selected_checkout_key:
                    selected_checkout = checkout_options[selected_checkout_key]
                    
                    # Show check-in details
                    checkin_time = datetime.strptime(selected_checkout['check_in_time'], '%Y-%m-%d %H:%M:%S')
                    current_duration = int((datetime.now() - checkin_time).total_seconds() / 60)
                    
                    st.info(f"**Usage Type:** {selected_checkout['court_usage_type']}")
                    st.info(f"**Current Duration:** {current_duration} minutes")
                    if selected_checkout['notes']:
                        st.info(f"**Notes:** {selected_checkout['notes']}")
                    
                    if st.button("🚪 Check Out", use_container_width=True, type="secondary"):
                        success, message = db_manager.record_member_checkout(selected_checkout['member_id'])
                        
                        if success:
                            st.success(f"✅ {selected_checkout['member_name']} checked out successfully!")
                            st.success(message)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
            else:
                st.info("No members currently checked in.")
    
    with tab2:
        st.subheader("🏸 Currently in Court")
        
        active_checkins = db_manager.get_active_checkins()
        
        if active_checkins:
            st.write(f"**{len(active_checkins)} members currently in the court:**")
            
            for checkin in active_checkins:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{checkin['member_name']}**")
                        st.caption(f"📞 {checkin['phone']}")
                    
                    with col2:
                        st.write(f"**{checkin['court_usage_type']}**")
                        if checkin['notes']:
                            st.caption(f"Notes: {checkin['notes']}")
                    
                    with col3:
                        checkin_time = datetime.strptime(checkin['check_in_time'], '%Y-%m-%d %H:%M:%S')
                        current_duration = int((datetime.now() - checkin_time).total_seconds() / 60)
                        st.write(f"**{current_duration} minutes**")
                        st.caption(f"Since: {checkin_time.strftime('%I:%M %p')}")
                    
                    with col4:
                        if st.button("🚪", key=f"checkout_{checkin['id']}", help="Check out"):
                            success, message = db_manager.record_member_checkout(checkin['member_id'])
                            if success:
                                st.success("Checked out!")
                                st.rerun()
                            else:
                                st.error(message)
                    
                    st.markdown("---")
        else:
            st.info("🏸 No members currently in the court")
            st.write("The court is empty right now.")
    
    with tab3:
        st.subheader("📊 Check-in Analytics")
        
        # Time period selection
        col1, col2 = st.columns(2)
        with col1:
            days_back = st.selectbox("Analytics Period:", [7, 14, 30, 60], index=2)
        with col2:
            st.metric("Period", f"Last {days_back} days")
        
        # Get analytics data
        analytics = db_manager.get_checkin_analytics(days_back)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Visits", analytics['total_visits'])
        
        with col2:
            st.metric("Unique Visitors", analytics['unique_visitors'])
        
        with col3:
            st.metric("Avg Duration", f"{analytics['average_duration']} min")
        
        with col4:
            avg_daily = analytics['total_visits'] / days_back if days_back > 0 else 0
            st.metric("Avg Daily Visits", f"{avg_daily:.1f}")
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 Daily Visits")
            if analytics['daily_visits']:
                import pandas as pd
                df = pd.DataFrame(analytics['daily_visits'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                st.bar_chart(df.set_index('date')['visits'])
            else:
                st.info("No visit data available for this period")
        
        with col2:
            st.subheader("⏰ Peak Hours")
            if analytics['peak_hours']:
                import pandas as pd
                peak_data = []
                for item in analytics['peak_hours']:
                    hour = int(item['hour'])
                    time_label = f"{hour:02d}:00"
                    peak_data.append({'hour': time_label, 'visits': item['count']})
                df = pd.DataFrame(peak_data)
                st.bar_chart(df.set_index('hour')['visits'])
            else:
                st.info("No peak hour data available")
        
        # Frequent visitors
        st.subheader("🏆 Most Frequent Visitors")
        if analytics['frequent_visitors']:
            for i, visitor in enumerate(analytics['frequent_visitors'], 1):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{i}. **{visitor['member_name']}**")
                with col2:
                    st.metric("Visits", visitor['visit_count'])
        else:
            st.info("No frequent visitor data available")

def send_bulk_announcement(db_manager, message_manager, recipients, message, send_method, message_type):
    """Generate WhatsApp links for bulk announcements"""
    import urllib.parse
    
    st.subheader("📱 WhatsApp Bulk Message Links")
    st.info("Click each link below to open WhatsApp with the announcement pre-filled. You can then send it manually.")
    
    total_count = len(recipients)
    
    for i, recipient in enumerate(recipients):
        # Format phone number for WhatsApp URL (remove spaces, ensure country code)
        phone = recipient['phone'].replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Add country code if not present (assuming Indian numbers start with +91)
        if not phone.startswith('+'):
            if phone.startswith('91'):
                phone = '+' + phone
            elif len(phone) == 10:  # Indian mobile number without country code
                phone = '+91' + phone
            else:
                phone = '+91' + phone  # Default to India
        
        # URL encode the message
        encoded_message = urllib.parse.quote(message)
        
        # Create WhatsApp URL
        whatsapp_url = f"https://wa.me/{phone.replace('+', '')}?text={encoded_message}"
        
        # Display the recipient card
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{recipient['name']}** - {recipient['phone']}")
                membership_type = recipient.get('membership_type', 'Member')
                st.caption(f"Type: {membership_type}")
                
                # Show a preview of the message (truncated)
                preview = message[:80] + "..." if len(message) > 80 else message
                st.text(f"Message: {preview}")
            
            with col2:
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color: #25D366; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold;">📱 Open WhatsApp</button></a>', unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Log the bulk message
    db_manager.log_bulk_message(
        message_text=message,
        recipient_count=total_count,
        message_type=f"{message_type} (WhatsApp_Links)",
        sent_by="Admin"
    )
    
    st.success(f"✅ Generated WhatsApp links for {total_count} recipients!")
    st.info("💡 **How to use:** Click each 'Open WhatsApp' button to open WhatsApp with the message ready. Review and send manually.")
    
    # Option to mark all as sent
    if st.button("✅ Mark All as Sent", type="secondary", use_container_width=True):
        st.success("All bulk messages marked as sent!")
        st.balloons()

def show_edit_member_modal(db_manager, member):
    """Show member editing modal"""
    st.subheader(f"Edit Member: {member['name']}")
    
    with st.form(f"edit_member_{member['id']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name", value=member['name'])
            phone = st.text_input("Phone Number", value=member['phone'])
            email = st.text_input("Email", value=member.get('email', ''))
            
        with col2:
            membership_type = st.selectbox(
                "Membership Type",
                ["Monthly Subscriber", "Quarterly", "Half Yearly", "Annual"],
                index=["Monthly Subscriber", "Quarterly", "Half Yearly", "Annual"].index(member['membership_type'])
            )
            amount = st.number_input("Amount (₹)", min_value=0.0, value=float(member['amount']) if member['amount'] is not None else 0.0)
            reminder_days = st.selectbox(
                "Reminder Before (days)",
                [15, 30],
                index=0 if member.get('reminder_days', 30) == 15 else 1
            )
        
        notes = st.text_area("Notes", value=member.get('notes', ''))
        
        if st.form_submit_button("Update Member", use_container_width=True):
            success = db_manager.update_member(
                member_id=member['id'],
                name=name,
                phone=phone,
                email=email,
                membership_type=membership_type,
                amount=amount,
                reminder_days=reminder_days,
                notes=notes
            )
            
            if success:
                st.success("✅ Member updated successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to update member")

def show_data_export(db_manager):
    """Show data export page"""
    st.header("📁 Data Export & Backup")
    st.markdown("Export your badminton court management data for backup or analysis purposes.")
    
    # Show database summary
    summary = db_manager.get_database_summary()
    
    st.subheader("📊 Database Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Members", summary.get('members', 0))
    with col2:
        st.metric("Payment Records", summary.get('payment_history', 0))
    with col3:
        st.metric("Kids Enrolled", summary.get('kids_training', 0))
    with col4:
        st.metric("Check-ins", summary.get('member_checkins', 0))
    
    st.markdown("---")
    
    # Export options
    st.subheader("🔄 Export Options")
    
    # Individual exports
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Member Data")
        if st.button("📥 Export Members", use_container_width=True):
            try:
                df = db_manager.export_members_data()
                if not df.empty:
                    csv = df.to_csv(index=False)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 Download Members CSV",
                        data=csv,
                        file_name=f"members_export_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ {len(df)} member records ready for download")
                else:
                    st.warning("⚠️ No member data to export")
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
        
        st.markdown("### Payment History")
        if st.button("📥 Export Payment History", use_container_width=True):
            try:
                df = db_manager.export_payment_history_data()
                if not df.empty:
                    csv = df.to_csv(index=False)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 Download Payment History CSV",
                        data=csv,
                        file_name=f"payment_history_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ {len(df)} payment records ready for download")
                else:
                    st.warning("⚠️ No payment history to export")
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
        
        st.markdown("### Kids Training Data")
        if st.button("📥 Export Kids Training", use_container_width=True):
            try:
                df = db_manager.export_kids_training_data()
                if not df.empty:
                    csv = df.to_csv(index=False)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 Download Kids Training CSV",
                        data=csv,
                        file_name=f"kids_training_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ {len(df)} kids training records ready for download")
                else:
                    st.warning("⚠️ No kids training data to export")
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
    
    with col2:
        st.markdown("### Check-in Data")
        if st.button("📥 Export Check-ins", use_container_width=True):
            try:
                df = db_manager.export_checkin_data()
                if not df.empty:
                    csv = df.to_csv(index=False)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 Download Check-ins CSV",
                        data=csv,
                        file_name=f"checkins_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ {len(df)} check-in records ready for download")
                else:
                    st.warning("⚠️ No check-in data to export")
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
        
        st.markdown("### Kids Payment History")
        if st.button("📥 Export Kids Payments", use_container_width=True):
            try:
                df = db_manager.export_kids_payment_history_data()
                if not df.empty:
                    csv = df.to_csv(index=False)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 Download Kids Payments CSV",
                        data=csv,
                        file_name=f"kids_payments_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ {len(df)} kids payment records ready for download")
                else:
                    st.warning("⚠️ No kids payment data to export")
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
        
        st.markdown("### Reminder Logs")
        if st.button("📥 Export Reminder Logs", use_container_width=True):
            try:
                df = db_manager.export_reminder_logs_data()
                if not df.empty:
                    csv = df.to_csv(index=False)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 Download Reminder Logs CSV",
                        data=csv,
                        file_name=f"reminder_logs_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.success(f"✅ {len(df)} reminder log records ready for download")
                else:
                    st.warning("⚠️ No reminder logs to export")
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
    
    # Bulk export
    st.markdown("---")
    st.subheader("📦 Complete Backup")
    st.markdown("Export all data in a single ZIP file for complete backup")
    
    if st.button("📦 Create Complete Backup", use_container_width=True, type="primary"):
        try:
            import zipfile
            import io
            
            # Create a zip buffer
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Export all data types
                export_functions = [
                    ("members", db_manager.export_members_data),
                    ("payment_history", db_manager.export_payment_history_data),
                    ("kids_training", db_manager.export_kids_training_data),
                    ("kids_payment_history", db_manager.export_kids_payment_history_data),
                    ("checkins", db_manager.export_checkin_data),
                    ("reminder_logs", db_manager.export_reminder_logs_data),
                    ("bulk_messages", db_manager.export_bulk_messages_data)
                ]
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, (name, func) in enumerate(export_functions):
                    status_text.text(f"Exporting {name}...")
                    try:
                        df = func()
                        if not df.empty:
                            csv_data = df.to_csv(index=False)
                            zip_file.writestr(f"{name}_{timestamp}.csv", csv_data)
                    except Exception as e:
                        st.warning(f"⚠️ Could not export {name}: {str(e)}")
                    
                    progress_bar.progress((i + 1) / len(export_functions))
                
                # Add database summary
                summary_text = f"""KJ Badminton Academy - Database Backup
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Database Summary:
- Total Members: {summary.get('members', 0)}
- Payment History Records: {summary.get('payment_history', 0)}
- Kids Training Records: {summary.get('kids_training', 0)}
- Kids Payment Records: {summary.get('kids_payment_history', 0)}
- Check-in Records: {summary.get('member_checkins', 0)}
- Reminder Log Records: {summary.get('reminder_logs', 0)}
- Bulk Message Records: {summary.get('bulk_messages_log', 0)}

Data Range: {summary['date_range']['start']} to {summary['date_range']['end']}
"""
                zip_file.writestr(f"backup_summary_{timestamp}.txt", summary_text)
                
                status_text.empty()
                progress_bar.empty()
            
            zip_buffer.seek(0)
            
            st.download_button(
                label="📥 Download Complete Backup (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"badminton_court_backup_{timestamp}.zip",
                mime="application/zip",
                use_container_width=True
            )
            
            st.success("✅ Complete backup created successfully!")
            st.info("💡 The ZIP file contains all your data in CSV format plus a summary report.")
            
        except Exception as e:
            st.error(f"❌ Backup creation failed: {str(e)}")
    
    # Data range information
    st.markdown("---")
    st.subheader("ℹ️ Data Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Data Range**: {summary['date_range']['start']} to {summary['date_range']['end']}")
    
    with col2:
        st.info(f"**Total Records**: {sum(summary.get(table, 0) for table in ['members', 'payment_history', 'kids_training', 'kids_payment_history', 'member_checkins', 'reminder_logs', 'bulk_messages_log'])}")

if __name__ == "__main__":
    main()
