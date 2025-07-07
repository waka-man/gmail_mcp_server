# Gmail MCP Server

This is a Model Context Protocol (MCP) server that provides a tool to fetch unread emails from a Gmail account using the IMAP protocol.

## Requirements

*   Python 3
*   A Gmail account with IMAP enabled.
*   A Gmail App Password. You will need to generate an App Password for your Gmail account to allow the server to log in securely. See the Google Account Help for instructions on how to generate an App Password: [https://support.google.com/accounts/answer/185833#zippy=%2Cwhy-you-may-need-an-app-password](https://support.google.com/accounts/answer/185833#zippy=%2Cwhy-you-may-need-an-app-password)

## Installation

1.  Clone this repository to your local machine:
    ```bash
    git clone https://github.com/waka-man/gmail-mcp-server.git ~/Documents/Cline/MCP/gmail-mcp-server
    ```
    (Note: Replace `<repository_url>` with the actual URL of the repository if it's hosted remotely. If the server is already at the specified path, you can skip this step.)

2.  Navigate to the server directory:
    ```bash
    cd ~/Documents/Cline/MCP/gmail-mcp-server
    ```

3.  Set the following environment variables with your Gmail credentials:
    ```bash
    export GMAIL_EMAIL="your_gmail_address@gmail.com"
    export GMAIL_APP_PASSWORD="your_gmail_app_password"
    ```
    Replace `"your_gmail_address@gmail.com"` and `"your_gmail_app_password"` with your actual Gmail address and the generated App Password.

## Usage

To run the server, execute the Python script:

```bash
python3 /home/waka/Documents/Cline/MCP/gmail-mcp-server/gmail_mcp_server.py
```

This server is designed to be used with an MCP client. It communicates over standard input/output using the MCP JSON-RPC protocol.

## Available Tools

### `get_unread_emails`

**Description:** Fetches unread emails from the configured Gmail account's inbox.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "max_emails": {
      "type": "number",
      "description": "Maximum number of unread emails to fetch. Must be a non-negative integer.",
      "optional": true
    }
  }
}
```

**Example Usage (via MCP Client):**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_unread_emails",
    "arguments": {
      "max_emails": 10
    }
  }
}
```

This will return a JSON array of unread email objects, each containing `id`, `from`, `to`, `subject`, `date`, and a `body_preview`.
