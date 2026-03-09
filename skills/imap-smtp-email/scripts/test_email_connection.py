#!/usr/bin/env python3
"""
Email Connection Test Script for Aliyun Enterprise Email
Tests IMAP and SMTP connections using the credentials file.
"""

import json
import ssl
import socket
import sys
from pathlib import Path

def load_credentials():
    """Load email credentials from config file."""
    cred_path = Path("/workspace/projects/.email-credentials.json")
    if not cred_path.exists():
        print(f"❌ Credentials file not found: {cred_path}")
        sys.exit(1)
    
    with open(cred_path, 'r') as f:
        return json.load(f)

def test_imap_connection(creds):
    """Test IMAP connection."""
    print("\n📥 Testing IMAP Connection...")
    print(f"   Server: {creds['imap']['host']}:{creds['imap']['port']}")
    
    try:
        import imaplib
        
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect to IMAP server
        imap = imaplib.IMAP4_SSL(
            creds['imap']['host'],
            creds['imap']['port'],
            ssl_context=context
        )
        
        # Login
        imap.login(creds['imap']['user'], creds['imap']['password'])
        
        # List mailboxes
        status, mailboxes = imap.list()
        
        # Select inbox
        status, messages = imap.select('INBOX')
        
        print(f"   ✅ IMAP connection successful!")
        print(f"   📬 Mailboxes found: {len(mailboxes)}")
        print(f"   📧 Inbox messages: {messages[0].decode() if messages[0] else '0'}")
        
        imap.logout()
        return True
        
    except Exception as e:
        print(f"   ❌ IMAP connection failed: {e}")
        return False

def test_smtp_connection(creds):
    """Test SMTP connection."""
    print("\n📤 Testing SMTP Connection...")
    print(f"   Server: {creds['smtp']['host']}:{creds['smtp']['port']}")
    
    try:
        import smtplib
        
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect to SMTP server
        smtp = smtplib.SMTP_SSL(
            creds['smtp']['host'],
            creds['smtp']['port'],
            context=context
        )
        
        # Login
        smtp.login(creds['smtp']['user'], creds['smtp']['password'])
        
        print(f"   ✅ SMTP connection successful!")
        print(f"   📧 Ready to send emails from: {creds['smtp']['user']}")
        
        smtp.quit()
        return True
        
    except Exception as e:
        print(f"   ❌ SMTP connection failed: {e}")
        return False

def test_pop_connection(creds):
    """Test POP3 connection (optional)."""
    print("\n📬 Testing POP3 Connection...")
    print(f"   Server: {creds['pop']['host']}:{creds['pop']['port']}")
    
    try:
        import poplib
        
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect to POP server
        pop = poplib.POP3_SSL(
            creds['pop']['host'],
            creds['pop']['port'],
            context=context
        )
        
        # Login
        pop.user(creds['pop']['user'])
        pop.pass_(creds['pop']['password'])
        
        # Get mailbox stats
        count, size = pop.stat()
        
        print(f"   ✅ POP3 connection successful!")
        print(f"   📧 Messages: {count}, Size: {size} bytes")
        
        pop.quit()
        return True
        
    except Exception as e:
        print(f"   ❌ POP3 connection failed: {e}")
        return False

def main():
    print("=" * 60)
    print("   📧 Aliyun Enterprise Email Connection Test")
    print("=" * 60)
    
    # Load credentials
    creds = load_credentials()
    print(f"\n📋 Email Account: {creds['email']}")
    print(f"   Provider: {creds['provider']}")
    
    # Test connections
    results = {
        'imap': test_imap_connection(creds),
        'smtp': test_smtp_connection(creds),
        'pop': test_pop_connection(creds)
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("   📊 Connection Test Summary")
    print("=" * 60)
    
    for protocol, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {protocol.upper():6s}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All email connections are working correctly!")
        print(f"   Agent email ready: {creds['email']}")
        return 0
    else:
        print("\n⚠️  Some connections failed. Please check credentials.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
