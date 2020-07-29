import json
import os
import stripe
import gunicorn
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import webbrowser

# This is your real test secret API key.

stripe.api_key = "sk_test_DMiK1oNbmgPE0SxC69vLO489007v8m0JWJ"

from flask import Flask, render_template, jsonify, request

app = Flask(__name__, static_folder=".",
            static_url_path="", template_folder=".")

@app.route('/')
def intro():
    return "Hello there"

@app.route('/create_customer', methods=['GET'])
def createCustomer():
    cust = stripe.Customer.create(description="created for user")
    return cust


@app.route('/ephemeral_keys', methods=['POST'])
def getEphemeral():
    data = request.json
    customerID = data["customerID"]
    key = stripe.EphemeralKey.create(customer=customerID, stripe_version="2020-03-02")
    return key
#cus_HYmWfqLKkaAonF

@app.route('/retrieve-customer/<id>', methods=['GET'])
def retrieveCustomer(id):
    return stripe.Customer.retrieve(id)

@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    data = request.json
    print(data["amount"])
    # Create a PaymentIntent with the order amount and currency
    intent = stripe.PaymentIntent.create(
        amount=data["amount"],
        currency='usd',
        customer=data['customer']
    )

    try:
        # Send publishable key and PaymentIntent details to client
        return jsonify({'publishableKey': os.getenv('STRIPE_PUBLISHABLE_KEY'), 'clientSecret': intent.client_secret})
    except Exception as e:
        return jsonify(error=str(e)), 403

##Methods added for Stripe Connect


@app.route("/connect/oauth", methods=["GET"])
def handle_oauth_redirect():
    # Assert the state matches the state you provided in the OAuth link (optional).
    state = request.args.get("state")

    if not state_matches(state):
        send_email("bad state")
        return json.dumps({"error": "Incorrect state parameter: " + state}), 403

    # Send the authorization code to Stripe's API.
    code = request.args.get("code")
    try:
        response = stripe.OAuth.token(grant_type="authorization_code", code=code,)
    except stripe.oauth_error.OAuthError as e:
        send_email("bad auth code")
        return json.dumps({"error": "Invalid authorization code: " + code}), 400
    except Exception as e:
        send_email("other error")
        return json.dumps({"error": "An unknown error occurred."}), 500

    connected_account_id = response["stripe_user_id"]
    send_email(connected_account_id)
    save_account_id(connected_account_id)
    print("account ID", connected_account_id)

    # Render some HTML or redirect to a different page.
    webbrowser.open("myFibonia://")
    return json.dumps({"success": True}), 200

def state_matches(state_parameter):
  # Load the same state value that you randomly generated for your OAuth link.
    saved_state = "{{ STATE }}"

    return saved_state == state_parameter

def save_account_id(id):
  # Save the connected account ID from the response to your database.
    print("Connected account ID: ", id)


def send_email(content):

    server = smtplib.SMTP(host='smtp.gmail.com', port=587)
    server.starttls()
    server.login("fibonia.emailclient@gmail.com", "Test!2345")

    msg = MIMEMultipart()

    msg['From'] = "Fibonia Email Server"
    msg['To'] = "gurkarn.goindi@berkeley.edu"
    msg['Subject'] = "New Tutor Class Request"

    msg.attach(MIMEText(content))

    server.send_message(msg)
    server.quit()

@app.route("/webhook", methods=["POST"])
def webhook_received():
    request_data = json.loads(request.data)
    signature = request.headers.get("stripe-signature")

# Verify webhook signature and extract the event.
# See https://stripe.com/docs/webhooks/signatures for more information.
    try:
        event = stripe.Webhook.construct_event(
            payload=request.data, sig_header=signature, secret=webhook_secret
        )
    except ValueError as e:
        # Invalid payload.
        return Response(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid Signature.
        return Response(status=400)
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        handle_successful_payment_intent(payment_intent)

    return json.dumps({"success": True}), 200

def handle_successful_payment_intent(payment_intent):
    print(str( payment_intent))
    ##MARK: Fill this space

if __name__ == '__main__':
    app.run()
