frappe.ui.form.on('Customer', {
    refresh: function (frm) {
        render_whatsapp_chat_ui(frm);
    }

});


function render_whatsapp_chat_ui(frm) {
    if (frm.fields_dict['custom_customer_chat']) {
        const customerName = frm.doc.customer_name;

        let chat_html = `
            <div id="whatsapp-chat-container" style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; background-color: #e5ddd5;">

                <div id="whatsapp-chat-messages" style="height: 650px; overflow-y: auto; background: #f0f0f0; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
                    <!-- Messages will be dynamically rendered here -->
                </div>

                <div id="whatsapp-chat-input" style="display: flex; gap: 5px;">
                    <input type="text" id="whatsapp-input" placeholder="Message" 
                        style="flex-grow: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                    <button id="whatsapp-send" style="background-color: #25d366; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer;">
                        Send
                    </button>
                </div>
            </div>
        `;

        frm.fields_dict['custom_customer_chat'].$wrapper.html(chat_html);

        const chatMessages = frm.fields_dict['custom_customer_chat'].$wrapper.find('#whatsapp-chat-messages');
        const chatInput = frm.fields_dict['custom_customer_chat'].$wrapper.find('#whatsapp-input');
        const sendButton = frm.fields_dict['custom_customer_chat'].$wrapper.find('#whatsapp-send');

        let lastDate = null;

        frappe.call({
            method: "whatsapp.whatsapp.utils.py.whatsapp.process_message",
            args: {
                doc: frm.doc.name,
                contact: frm.doc.customer_primary_contact
            },
            callback: function (response) {
                if (response.message) {
                    response.message.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

                    response.message.forEach((msg) => {
                        const timestamp = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                        const messageDate = new Date(msg.timestamp).toLocaleDateString();

                        // Group messages by date (if different from last date)
                        if (messageDate !== lastDate) {
                            chatMessages.append(`
                                <div style="text-align: center; margin: 10px 0; font-size: 0.9em; color: #888; font-weight: bold;">
                                    ${messageDate}
                                </div>
                            `);
                            lastDate = messageDate;
                        }

                        const alignment = msg.channel_type === "Incoming" ? "left" : "right";
                        const backgroundColor = msg.channel_type === "Incoming" ? "#ffffff" : "#dcf8c6";

                        let ticks = '';

                        // Show ticks for outgoing messages
                        if (msg.channel_type === "Outgoing") {
                            if (msg.status === "delivered") {
                                ticks = '<span style="color: #888;">✔✔</span>'; // Gray double ticks for "delivered"
                            } else if (msg.status === "read") {
                                ticks = '<span style="color:rgb(0, 179, 255);">✔✔</span>'; // Blue double ticks for "read"
                            } else if (msg.status === "failed") {
                                ticks = '<span style="color: red; font-weight: bold;">✖</span>';
                            } else if (msg.status === "sent") {
                                ticks = '<span style="color: #888; font-weight: bold;">✔</span>';
                            }
                        }

                        const messageElement = `
                            <div style="text-align: ${alignment}; margin: 5px 0; position: relative;">
                                <span class="message" style="background: ${backgroundColor}; padding: 8px 12px; border-radius: 10px; display: inline-block; max-width: 70%; word-wrap: break-word;">
                                    ${msg.message_body}
                                </span>
                                <div style="text-align: ${alignment}; font-size: 0.8em; color: #888; margin-top: 5px;">
                                    ${timestamp}
                                    ${ticks}
                                </div>
                            </div>
                        `;

                        chatMessages.append(messageElement);
                    });
                }
            }
        });

        sendButton.on('click', function () {
            const outgoing_msg = chatInput.val().trim();
            if (outgoing_msg) {
                const currentTime = new Date();
                const timestamp = currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                frappe.call({
                    method: "whatsapp.whatsapp.utils.py.whatsapp.send_chat_message",
                    args: { 
                        docname: frm.doc.name,
                        doctype: frm.doctype,
                        message: outgoing_msg
                    },
                    callback: function (response) {
                        if (response.message) {
                            console.log("Message sent successfully:", response.message);
                        } else {
                            console.error("Failed to send the message.");
                        }
                    },
                    error: function (err) {
                        console.error("Error while sending the message:", err);
                    }
                });

                chatMessages.append(`
                    <div style="text-align: right; margin: 5px 0;">
                        <span style="background: #dcf8c6; padding: 8px 12px; border-radius: 10px; display: inline-block; max-width: 70%; word-wrap: break-word;">
                            ${outgoing_msg}
                        </span>
                        <div style="text-align: right; font-size: 0.8em; color: #888; margin-top: 5px;">
                            ${timestamp}
                        </div>
                    </div>
                `);

                chatInput.val('');
            }
        });

        // Send message on Enter key press
        chatInput.on('keypress', function (e) {
            if (e.which === 13) {
                sendButton.click();
            }
        });
    } else {
        frm.fields_dict['custom_customer_chat'].$wrapper.html('<p>Please set up the chat feature.</p>');
    }
}