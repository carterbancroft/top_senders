# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Top Senders is a Python utility that analyzes Gmail accounts to identify the top email senders by frequency. It uses the Gmail API with read-only permissions to fetch email metadata and rank senders by message count.

## Key Commands

### Setup and Environment
```bash
# Activate virtual environment (required for all operations)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Prerequisites
- Requires `credentials.json` from Google Cloud Console with Gmail API enabled
- First run triggers OAuth flow to generate `token.pickle` for subsequent runs

## Architecture

**Single-file application**: All logic is contained in `main.py` with a script-based architecture.

**Core components**:
- `authenticate_gmail()`: OAuth2 flow with token persistence using pickle
- `get_sender_from_message()`: Extracts sender email from message headers  
- `fetch_senders()`: Main processing loop with rate limiting

**API Integration**: Uses Gmail API v1 with `gmail.readonly` scope for security. Only fetches message metadata (headers), never content.

**Rate Limiting**: Built-in 20 requests/second limit (0.05s delay) to respect Gmail API quotas.

## Code Patterns

- OAuth tokens are persisted in `token.pickle` and auto-refreshed
- Error handling uses try-catch blocks for API calls
- Sender emails extracted from "From" headers with support for "Name <email>" format
- Progress tracking shows `[current/total]` during processing
- Results sorted by message count in descending order

## Important Files

- `main.py`: Complete application logic
- `credentials.json`: Google API credentials (not in repo)
- `token.pickle`: OAuth token storage (auto-generated)
- `requirements.txt`: Python dependencies for Google API libraries

## Development Notes

The project processes emails in batches with configurable limits. Default is 100 messages for testing; can be set to `None` for full mailbox analysis (30k+ messages takes ~25-30 minutes).

Authentication flow only needs to run once per machine - subsequent runs use cached tokens automatically.