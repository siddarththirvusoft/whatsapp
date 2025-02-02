import frappe
import json
from werkzeug.wrappers import Response
import pytz
from datetime import datetime, timezone

@frappe.whitelist(allow_guest=True)
def whatsapp_webhook():

    if frappe.request.method == "GET":

        expected_verify_token = frappe.db.get_single_value('Whatsapp Settings', 'meta_verify_token')

        challenge = frappe.form_dict.get("hub.challenge")
        verify_token = frappe.form_dict.get("hub.verify_token")

        if verify_token == expected_verify_token:
            return Response(challenge, content_type="text/plain", status=200)

        else:

            frappe.local.response = "Verification failed"
            frappe.local.response.status_code = 400

    elif frappe.request.method == "POST":

        payload = frappe.request.get_data(as_text=True)
        frappe.log_error(message=f"Received WhatsApp Communication Payload: {payload}", title="PAYLOAD")
        try:
            data = json.loads(payload)
            entry = data.get("entry", [])
            if not entry:
                return Response("Invalid Payload: Missing 'entry'", content_type="text/plain", status=400)

            changes = entry[0].get("changes", [])
            if not changes:
                return Response("Invalid Payload: Missing 'changes'", content_type="text/plain", status=400)

            field = changes[0].get("field")
            value = changes[0].get("value")

            if not field:
                return Response("Field is missing", content_type="text/plain", status=400)

            if field == "messages":

                statuses = value.get("statuses", [])
                messages = value.get("messages", [])

                for status in statuses:
                    message_id = status.get("id")
                    status = status.get("status")
                    timestamp = status.get("timestamp")

                    try:
                        whatsapp_communication = frappe.get_all(
                            "Whatsapp Communication",
                            filters={"message_id": message_id},
                            fields=["name", "status", "delivery_time", "read_time"]
                        )

                        frappe.log_error(
                                    message=f"Updated timestamp for status {whatsapp_communication}",
                                    title="whatsapp_communication"
                                )
                        if whatsapp_communication:
                            whatsapp_doc = frappe.get_doc("Whatsapp Communication", whatsapp_communication[0].get("name"))

                            # Replace the existing status with the new status
                            whatsapp_doc.status = status

                            # Convert the timestamp to local time
                            if timestamp:
                                epoch_timestamp = int(timestamp)
                                utc_time = datetime.utcfromtimestamp(epoch_timestamp)
                                utc_time = pytz.utc.localize(utc_time)
                                local_time = utc_time.astimezone(pytz.timezone("Asia/Kolkata"))
                                formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S")

                                if status == "delivered":
                                    whatsapp_doc.delivery_time = formatted_time
                                elif status == "read":
                                    whatsapp_doc.read_time = formatted_time

                                frappe.log_error(
                                    message=f"Updated timestamp for status {status}: {formatted_time}",
                                    title="Timestamp Update"
                                )

                            whatsapp_doc.save(ignore_permissions=True)
                            frappe.db.commit()

                            frappe.log_error(
                                message=f"Updated WhatsApp Communication: {whatsapp_doc.name} with status {status}",
                                title="Status Update Success"
                            )
                        else:
                            frappe.log_error(
                                message=f"Message ID {message_id} not found in Whatsapp Communication",
                                title="Message Not Found"
                            )

                    except Exception as e:
                        frappe.log_error(
                            message=f"Error updating message status: {str(e)}",
                            title="Update Error"
                        )

                for message in messages:
                    try:
                        epoch_timestamp = message.get("timestamp")
                        timezone_str = 'Asia/Kolkata'

                        epoch_timestamp_int = int(epoch_timestamp)
                        utc_time = datetime.utcfromtimestamp(epoch_timestamp_int)
                        utc_time = pytz.utc.localize(utc_time)
                        local_time = utc_time.astimezone(pytz.timezone(timezone_str))

                        raw_number = message.get("from")  # "919999999999"
                        processed_number = raw_number[2:]  # Remove country code if necessary

                        customer_id = frappe.db.get_value('Customer', {'mobile_no': processed_number}, 'name')
                        frappe.log_error(message=f"CUSTOMER: {customer_id}", title="CUSTOMER")
                        data_to_insert = {
                            "doctype": "Whatsapp Communication",
                            "phone_number_id": value.get("metadata", {}).get("phone_number_id"),
                            "display_phone_number": value.get("metadata", {}).get("display_phone_number"),
                            "from": message.get("from")[2:],
                            "message_id": message.get("id"),
                            "timestamp": local_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "message_type": message.get("type"),
                            "message_body": message.get("text", {}).get("body"),
                            "contact_name": customer_id,
                            "contact_wa_id": value.get("contacts", [])[0].get("wa_id"),
                            "status": 'Incoming',
                            'payload': payload,
                        }

                        whatsapp_communication = frappe.get_doc(data_to_insert)
                        whatsapp_communication.insert(ignore_permissions=True)

                        frappe.db.commit()

                        frappe.log_error(message=f"Inserted WhatsApp Communication: {whatsapp_communication.name}", title="Insert Success")
                    except Exception as e:
                        frappe.log_error(message=f"Error inserting document: {str(e)}", title="Insert Error")

            return Response("Event Received", content_type="text/plain", status=200)

        except json.JSONDecodeError:
            frappe.log_error(message="Invalid JSON payload", title="WhatsApp Webhook Error")
            return Response("Invalid JSON", content_type="text/plain", status=400)
