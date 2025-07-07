#!/usr/bin/env python3

import sys
import json
import os
import imaplib
import ssl
import email
import traceback

def handle_initialize(request):
    # Handle the initialize request from the client
    print("Handling initialize request.", file=sys.stderr)
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": {
            "protocolVersion": "2025-03-26", # Specify the protocol version
            "serverInfo": {
                "name": "gmail-mcp-server", # Name of the server
                "version": "0.1.0" # Version of the server
            },
            "capabilities": {
                "tools": {} # Declare that the server supports tools
                # TODO: Add other capabilities if implemented (e.g., resources)
            }
        }
    }

def handle_list_resources(request):
    # Handle resources/list request
    print("Handling resources/list request.", file=sys.stderr)
    return {"jsonrpc": "2.0", "id": request.get("id"), "result": {"resources": []}} # Return empty list as no resources are provided

def handle_list_resource_templates(request):
    # Handle resources/templates/list request
    print("Handling resources/templates/list request.", file=sys.stderr)
    return {"jsonrpc": "2.0", "id": request.get("id"), "result": {"resourceTemplates": []}} # Return empty list as no resource templates are provided


def handle_list_tools(request):
    tools = [
        {
            "name": "get_unread_emails",
            "description": "Fetches unread emails from Gmail",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "max_emails": {
                        "type": "number",
                        "description": "Maximum number of unread emails to fetch",
                        "optional": True
                    }
                }
            }
        }
    ]
    return {"jsonrpc": "2.0", "id": request.get("id"), "result": {"tools": tools}}

def handle_call_tool(request):
    print("Entering handle_call_tool.", file=sys.stderr)
    # Call the requested tool if it is recognized
    tool_name = request.get("params", {}).get("name")
    arguments = request.get("params", {}).get("arguments", {})

    if tool_name == "get_unread_emails":
        return handle_get_unread_emails(request.get("id"), arguments)
    else:
        return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32601, "message": "Method not found"}}

def handle_get_unread_emails(request_id, arguments):
    print("Entering handle_get_unread_emails.", file=sys.stderr)
    gmail_email = os.environ.get('GMAIL_EMAIL')
    gmail_app_password = os.environ.get('GMAIL_APP_PASSWORD')
    max_emails = arguments.get('max_emails')
    if max_emails is not None:
        try:
            max_emails = int(max_emails)
            if max_emails < 0:
                raise ValueError
        except (ValueError, TypeError):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": "Invalid 'max_emails' value."}],
                    "isError": True
                }
            }

    if not gmail_email or not gmail_app_password:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": "Gmail credentials not provided in environment variables."}],
                "isError": True
            }
        }

    try:
        print("Connecting to Gmail IMAP server...", file=sys.stderr)
        # Connect to the server
        # Use SSL for secure connection
        context = ssl.create_default_context()
        with imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=context, timeout=120) as mail:
            print("Attempting login...", file=sys.stderr)
            mail.login(gmail_email, gmail_app_password)
            print("Login successful.", file=sys.stderr)

            print("Attempting to select inbox...", file=sys.stderr)
            # Select the mailbox you want to work with
            mail.select("inbox")
            print("Inbox selected successfully.", file=sys.stderr)

            print("Attempting to search for unread emails...", file=sys.stderr)
            status, email_ids = mail.search(None, '(UNSEEN)')
            print(f"Search status: {status}", file=sys.stderr)
            if status != 'OK':
                raise Exception("Failed to search for emails.")

            email_id_list = email_ids[0].split()
            print(f"Found {len(email_id_list)} unread emails.", file=sys.stderr)

            emails_to_fetch = email_id_list
            if max_emails is not None and len(email_id_list) > max_emails:
                emails_to_fetch = email_id_list[-max_emails:] # Fetch the most recent unread emails

            fetched_emails_data = []
            for email_id in emails_to_fetch:
                print(f"Attempting to fetch email ID {email_id.decode()}...", file=sys.stderr)
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                print(f"Fetch status for ID {email_id.decode()}: {status}", file=sys.stderr)
                if status != 'OK':
                    print(f"Failed to fetch email ID {email_id.decode()}", file=sys.stderr)
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                email_info = {
                    "id": email_id.decode(),
                    "from": msg.get("From"),
                    "to": msg.get("To"),
                    "subject": msg.get("Subject"),
                    "date": msg.get("Date"),
                    "body_preview": "" # Placeholder for body preview
                }

                # Extract plain text body
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdispo = part.get('Content-Disposition')

                        # look for plain text parts, but skip attachments
                        if ctype == 'text/plain' and cdispo is None:
                            try:
                                # Attempt to decode with common encodings
                                body = part.get_payload(decode=True).decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    body = part.get_payload(decode=True).decode('latin-1')
                                except UnicodeDecodeError:
                                    try:
                                        body = part.get_payload(decode=True).decode('cp1252')
                                    except Exception as decode_error:
                                        print(f"Error decoding email part with multiple codecs: {decode_error}", file=sys.stderr)
                                        body = "Could not decode email body."

                            email_info["body_preview"] = body[:200] + "..." if len(body) > 200 else body # Get first 200 chars
                            break
                else:
                     try:
                        body = msg.get_payload(decode=True).decode('utf-8')
                     except UnicodeDecodeError:
                        try:
                            body = msg.get_payload(decode=True).decode('latin-1')
                        except UnicodeDecodeError:
                            try:
                                body = msg.get_payload(decode=True).decode('cp1252')
                            except Exception as decode_error:
                                print(f"Error decoding email body with multiple codecs: {decode_error}", file=sys.stderr)
                                body = "Could not decode email body."

                     email_info["body_preview"] = body[:200] + "..." if len(body) > 200 else body


                fetched_emails_data.append(email_info)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(fetched_emails_data, indent=2)
                        }
                    ],
                    "isError": False
                }
            }

    except Exception as e:
        error_message = f"Error fetching emails: {e}"
        print(error_message, file=sys.stderr)
        with open("gmail_mcp_error.log", "a") as f:
            f.write("Error fetching emails:\n")
            traceback.print_exc(file=f)
            f.write("-" * 20 + "\n")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": error_message}],
                "isError": True
            }
        }


def main():
    # Set up basic logging to stderr
    print("Gmail MCP server started.", file=sys.stderr)
    print("Entering main request loop.", file=sys.stderr)

    while True:
        print("Waiting for request...", file=sys.stderr)
        line = sys.stdin.readline()
        if not line:
            print("Received empty line, exiting loop.", file=sys.stderr)
            break # End of input

        # Add a very early log to see the raw received line
        print(f"Raw line received: {line.strip()}", file=sys.stderr)
        print(f"Read line: {line.strip()}", file=sys.stderr)

        try:
            request = json.loads(line)
            print(f"Successfully parsed JSON request: {request}", file=sys.stderr)
        except json.JSONDecodeError:
            print("Error decoding JSON from stdin.", file=sys.stderr)
            error_response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            json.dump(error_response, sys.stdout)
            sys.stdout.write('\n')
            sys.stdout.flush()
            print("Parse error response sent.", file=sys.stderr)
            continue # Continue to the next iteration of the loop
        except Exception as e:
             print(f"An unexpected error occurred during JSON parsing: {e}", file=sys.stderr)
             error_response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": f"Unexpected error during JSON parsing: {e}"}}
             json.dump(error_response, sys.stdout)
             sys.stdout.write('\n')
             sys.stdout.flush()
             print("Unexpected JSON parsing error response sent.", file=sys.stderr)
             continue # Continue to the next iteration of the loop


        response = None
        method = request.get("method")

        try:
            if method == "initialize":
                response = handle_initialize(request)
            elif method == "tools/list":
                print("Handling tools/list request.", file=sys.stderr)
                response = handle_list_tools(request)
            elif method == "tools/call":
                print("Handling tools/call request.", file=sys.stderr)
                response = handle_call_tool(request)
            elif method == "resources/list":
                 response = handle_list_resources(request)
            elif method == "resources/templates/list":
                 response = handle_list_resource_templates(request)
            elif method == "notifications/initialized":
                 print("Received notifications/initialized notification.", file=sys.stderr)
                 # Notifications do not require a response
                 continue # Skip response generation for notifications
            # TODO: Add handlers for other methods if needed (e.g., resources/read)
            else:
                print(f"Unknown method: {method}", file=sys.stderr)
                response = {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32601, "message": "Method not found"}}

        except Exception as e:
            error_message = f"An error occurred during request handling for method {method}: {e}"
            print(error_message, file=sys.stderr)
            # Log the full traceback to a file
            with open("gmail_mcp_error.log", "a") as f:
                f.write(f"Error handling method {method}:\n")
                traceback.print_exc(file=f)
                f.write("-" * 20 + "\n")

            # Send an internal error response
            error_response = {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32603, "message": error_message}}
            json.dump(error_response, sys.stdout)
            sys.stdout.write('\n')
            sys.stdout.flush()
            print(f"Error handling method {method} response sent.", file=sys.stderr)
            continue # Continue to the next iteration of the loop


        if response:
            print(f"Sending response: {response}", file=sys.stderr)
            # Write response to stdout
            json.dump(response, sys.stdout)
            sys.stdout.write('\n')
            sys.stdout.flush()
            print("Response sent and flushed.", file=sys.stderr)
        else:
             print("No response generated.", file=sys.stderr)


    print("Gmail MCP server stopped.", file=sys.stderr)

if __name__ == "__main__":
    main()
