import json
import os
import sys
from unittest import mock

# Ensure the server module can be imported when tests run from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

import gmail_mcp_server

class FakeIMAP:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    def login(self, email, password):
        self.logged_in = True
    def select(self, mailbox):
        return ('OK', [])
    def search(self, charset, query):
        return ('OK', [b'1 2'])
    def fetch(self, email_id, params):
        if email_id == b'1':
            msg = "From: a@example.com\nTo: b@example.com\nSubject: Test 1\nDate: 2023-01-01\n\nBody 1"
        else:
            msg = "From: c@example.com\nTo: d@example.com\nSubject: Test 2\nDate: 2023-01-02\n\nBody 2"
        return ('OK', [(b'RFC822', msg.encode('utf-8'))])

def test_get_unread_emails_success(monkeypatch):
    monkeypatch.setenv('GMAIL_EMAIL', 'user@example.com')
    monkeypatch.setenv('GMAIL_APP_PASSWORD', 'password')
    monkeypatch.setattr(gmail_mcp_server.imaplib, 'IMAP4_SSL', lambda *a, **k: FakeIMAP())

    result = gmail_mcp_server.handle_get_unread_emails(1, {})
    assert result['result']['isError'] is False

    content_text = result['result']['content'][0]['text']
    emails = json.loads(content_text)
    assert len(emails) == 2
    subjects = [e['subject'] for e in emails]
    assert subjects == ['Test 1', 'Test 2']

def test_get_unread_emails_missing_credentials(monkeypatch):
    monkeypatch.delenv('GMAIL_EMAIL', raising=False)
    monkeypatch.delenv('GMAIL_APP_PASSWORD', raising=False)

    result = gmail_mcp_server.handle_get_unread_emails(1, {})

    assert result['result']['isError'] is True
    assert 'Gmail credentials not provided' in result['result']['content'][0]['text']
