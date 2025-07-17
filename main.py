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

def extract_sender_from_message(message_data):
    """Extract sender email from message data."""
    try:
        headers = message_data['payload'].get('headers', [])
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
        print(f"Error extracting sender: {error}")
        return None

def get_senders_batch(service, message_ids):
    """Get senders from messages using batch API with 2 requests per batch."""
    sender_counts = defaultdict(int)
    batch_results = {}
    batch_size = 10

    def callback(request_id, response, exception):
        if exception:
            print(f"Error in batch request {request_id}: {exception}")
        else:
            batch_results[request_id] = response

    total_batches = (len(message_ids) + batch_size - 1) // batch_size
    print(f"Processing {len(message_ids)} messages in {total_batches} batches of {batch_size}...")

    # Process messages in batches
    for i in range(0, len(message_ids), batch_size):
        batch_ids = message_ids[i:i + batch_size]
        batch = service.new_batch_http_request(callback=callback)

        # Add requests to batch
        for msg_id in batch_ids:
            batch.add(
                service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='metadata',
                    metadataHeaders=['From']
                ),
                request_id=msg_id
            )

        # Execute batch
        batch_num = i // batch_size + 1
        if batch_num % 25 == 0:
            print(f"Processing batch {batch_num}/{total_batches}...")

        batch.execute()

        # Process results
        for msg_id, message_data in batch_results.items():
            sender = extract_sender_from_message(message_data)
            if sender:
                sender_counts[sender] += 1

        batch_results.clear()

        # Rate limiting between batches - conservative
        time.sleep(0.1)

    return dict(sender_counts)

def get_all_message_ids(service, max_messages=None):
    """Get message IDs with pagination support."""
    print(f"Fetching message IDs...")
    message_ids = []
    page_token = None
    page_count = 0

    while True:
        # Gmail API max is 500 per request
        page_size = min(500, max_messages - len(message_ids) if max_messages else 500)

        result = service.users().messages().list(
            userId='me',
            maxResults=page_size,
            pageToken=page_token,
            q='-in:spam -in:trash'
        ).execute()

        messages = result.get('messages', [])
        if not messages:
            break

        batch_ids = [msg['id'] for msg in messages]
        message_ids.extend(batch_ids)
        page_count += 1

        print(f"Page {page_count}: fetched {len(batch_ids)} IDs (total: {len(message_ids)})")

        # Check if we've reached our limit
        if max_messages and len(message_ids) >= max_messages:
            message_ids = message_ids[:max_messages]
            break

        # Check for next page
        page_token = result.get('nextPageToken')
        if not page_token:
            break

        # Small delay between pages
        time.sleep(0.2)

    print(f"Total message IDs collected: {len(message_ids)}")
    return message_ids

def fetch_senders(service, limit=None):
    """Fetch sender info from messages using individual API calls."""
    print(f"Fetching senders from {limit if limit else 'all'} messages...")

    start_time = time.time()

    # Get all message IDs with pagination
    message_ids = get_all_message_ids(service, limit)

    if not message_ids:
        print("No messages found")
        return {}

    # Use batch API calls to get senders
    sender_counts = get_senders_batch(service, message_ids)

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"\nProcessing completed in {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")

    print(f"\nTop 20 senders:")
    top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    for sender, count in top_senders:
        print(f"{sender}: {count} messages")

    return sender_counts

if __name__ == '__main__':
    service = authenticate_gmail()
    if service:
        profile = service.users().getProfile(userId='me').execute()
        print(f"Authenticated as: {profile['emailAddress']}")
        print(f"Total messages: {profile['messagesTotal']}")
        print("="*50)
        fetch_senders(service, limit=5000)
