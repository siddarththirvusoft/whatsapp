import frappe
import requests
from frappe.utils import now
import json


@frappe.whitelist()
def send_chat_message(docname,doctype, message):

    enable = frappe.db.get_single_value('Whatsapp Settings', 'enable')
    token = frappe.db.get_single_value('Whatsapp Settings', 'access_token')
    url = frappe.db.get_single_value('Whatsapp Settings', 'url')

    API_URL = f"{url}"

    if enable:

        recipient_number = frappe.db.get_value('Customer', {'name': docname}, 'mobile_no')

        if not recipient_number:
            return

        headers = {
            "Authorization": f"Bearer {token}"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_number,
            "type": "text",
            "text": {
                "body": message
            }
        }

        message_response = requests.post(API_URL, headers=headers, json=payload)

        if message_response.status_code == 200:
            response_data = json.loads(message_response.text)
            messages = response_data.get("messages", [])

            if messages and isinstance(messages, list) and "id" in messages[0]:
                msg_id = messages[0]["id"]

                whatsapp_comm = frappe.get_doc({
                    "doctype": "Whatsapp Communication",
                    "customer": docname,
                    "message_to":recipient_number,
                    "recipient_number": recipient_number,
                    "message_body": message,
                    "message_id": msg_id,
                    "status": "Success",
                    "party_type": doctype,
                    "party_id": docname,
                    "channel_type":"Outgoing"
                })

                whatsapp_comm.insert(ignore_permissions=True)
                frappe.db.commit()

                frappe.log_error(message=f"New Whatsapp Communication created with ID: {msg_id}", title="NEW WHATSAPP COMMUNICATION CREATED")
            else:
                frappe.log_error(message=f"Message ID not found in response: {response_data}", title="MESSAGE ID MISSING")
        else:
            frappe.log_error(message=f"Failed to send WhatsApp message. Response: {message_response.text}", title="WHATSAPP MESSAGE FAILED")




@frappe.whitelist()
def process_message(contact):
    contact_details = frappe.db.get_all(
        'Contact',
        filters={'name': contact},
        fields=['name', 'mobile_no']
    )

    if not contact_details:
        frappe.log_error(f"No contact found for {contact}", "Whatsapp Communication Error")
        return []

    contact_mobiles = {c['mobile_no'].replace(" ", "").lstrip("+") for c in contact_details}

    messages = frappe.db.get_all(
        'Whatsapp Communication',
        filters={'channel_type': ['in', ['Incoming', 'Outgoing']]},
        fields=['status', 'from', 'message_to', 'message_body', 'timestamp', 'status', 'delivery_time', 'read_time','channel_type']
    )

    result = []

    for msg in messages:
        if msg['channel_type'] == 'Incoming':
            msg_mobile = msg['from'].replace(" ", "").lstrip("+")
        else:
            msg_mobile = msg['message_to'].replace(" ", "").lstrip("+")

        if msg_mobile in contact_mobiles:
            result.append({
                'timestamp': msg['timestamp'],
                'channel_type': msg['channel_type'],
                'message_body': msg['message_body'],
                'contact_name': contact,
                'status': msg['status'],
                'delivery_time':msg['delivery_time'],
                'read_time': msg['read_time']
            })

    return result
