# KJ Badminton Academy

## Overview

This is a Streamlit-based web application for managing a badminton court facility. The system handles member management, payment tracking, and automated reminder functionality. It provides a user-friendly interface for court administrators to manage memberships, track payments, send notifications, and schedule reminders for upcoming dues.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit for rapid web application development
- **Responsive Design**: Custom CSS media queries for mobile compatibility
- **Caching Strategy**: Uses Streamlit's `@st.cache_resource` decorator for singleton resource management
- **Configuration**: Wide layout with expandable sidebar for optimal screen real estate usage

### Backend Architecture
- **Data Layer**: SQLite database with dedicated DatabaseManager class
- **Business Logic**: Modular design with separate managers for different concerns:
  - `DatabaseManager`: Handles all database operations and schema management
  - `MessageManager`: Manages SMS/WhatsApp communications via Twilio
  - `ReminderScheduler`: Handles payment reminder logic and scheduling
- **Utility Functions**: Centralized utilities for phone number formatting, validation, and currency display

### Data Storage
- **Database**: SQLite for lightweight, serverless data storage
- **Schema Design**: Normalized structure with three main tables:
  - `members`: Core member information and membership details
  - `payment_history`: Transaction records with foreign key relationships
  - `kids_training`: Specialized table for youth programs
- **Data Integrity**: Foreign key constraints and automatic timestamp tracking

### Authentication & Security
- **Environment Variables**: Sensitive credentials stored as environment variables
- **Input Validation**: Phone number validation and formatting utilities
- **Error Handling**: Try-catch blocks for external service integration failures

### Communication System
- **Multi-channel Messaging**: Support for both SMS and WhatsApp via Twilio API
- **Template System**: Dynamic message formatting with member-specific data
- **Fallback Handling**: Graceful degradation when Twilio credentials are unavailable

## External Dependencies

### Third-party Services
- **Twilio API**: SMS and WhatsApp messaging service
  - Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER environment variables
  - Handles message delivery and status tracking

### Python Packages
- **Streamlit**: Web application framework for the user interface
- **Pandas**: Data manipulation and analysis for member/payment data
- **Twilio**: Official Python SDK for Twilio API integration
- **SQLite3**: Built-in Python database interface (no external installation required)

### Database Dependencies
- **SQLite**: Embedded database engine (no separate server required)
- **File-based Storage**: Database stored as local `.db` file for portability

### Development Environment
- **Python 3.x**: Core runtime requirement
- **Environment Configuration**: Uses `os.getenv()` for configuration management
- **Date/Time Handling**: Built-in `datetime` module for scheduling and calculations