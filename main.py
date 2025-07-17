#!/usr/bin/env python3
"""
Gmail Authentication Script
Authenticates with Gmail API using readonly scope to access email metadata.
"""

import os
import pickle
import time
from collections import defaultdict
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope for readonly access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Rate limiting settings
REQUESTS_PER_SECOND = 20
BATCH_SIZE = 100

def authenticate_gmail():
    """Authenticate with Gmail API and return service object."""
    creds = None
    token_file = 'token.pickle'
    
    # Load existing token if available
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    # Build Gmail service
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_sender_from_message(service, message_id):
    """Get the sender email from a specific message."""
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='metadata',
            metadataHeaders=['From']
        ).execute()
        
        headers = message['payload'].get('headers', [])
        for header in headers:
            if header['name'] == 'From':
                # Extract email from "Name <email@domain.com>" format
                from_header = header['value']
                if '<' in from_header and '>' in from_header:
                    email = from_header.split('<')[1].split('>')[0]
                else:
                    email = from_header
                return email.strip()
        return None
    except Exception as error:
        print(f"Error getting sender for message {message_id}: {error}")
        return None

def fetch_senders(service, limit=None):
    """Fetch sender info from messages."""
    print(f"Fetching senders from {limit if limit else 'all'} messages...")
    
    # Get list of message IDs
    result = service.users().messages().list(userId='me', maxResults=limit).execute()
    messages = result.get('messages', [])
    
    sender_counts = defaultdict(int)
    
    for i, msg in enumerate(messages):
        sender = get_sender_from_message(service, msg['id'])
        if sender:
            sender_counts[sender] += 1
            print(f"[{i+1}/{len(messages)}] {sender}")
        
        # Rate limiting - 20 requests per second
        time.sleep(0.05)
    
    print(f"\nTop senders:")
    for sender, count in sorted(sender_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{sender}: {count} messages")
    
    return sender_counts

if __name__ == '__main__':
    service = authenticate_gmail()
    if service:
        profile = service.users().getProfile(userId='me').execute()
        print(f"Authenticated as: {profile['emailAddress']}")
        print(f"Total messages: {profile['messagesTotal']}")
        print("="*50)
        fetch_senders(service, limit=100)