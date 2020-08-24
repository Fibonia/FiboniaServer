import json
import os
import stripe
import gunicorn
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# This is your real test secret API key.

stripe.api_key = "sk_test_DMiK1oNbmgPE0SxC69vLO489007v8m0JWJ"

cred = credentials.Certificate('fibonia-83e34-83001bbabd20.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

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
    #intent = stripe.PaymentIntent.create(
     #   amount=data["amount"],
      #  currency='usd',
       # customer=data['customer']
    #)
    payAmount = data["amount"]
    finalAmount = int(float(payAmount * 0.1))

    print("intending")
    intent = stripe.PaymentIntent.create(
        payment_method_types=['card'],
        amount= payAmount,
        currency='usd',
        customer = data['customer'],
        application_fee_amount= finalAmount,
        transfer_data={
            'destination': data['tutorID']
        }
    )
    print("intent, ", intent)

    try:
        # Send publishable key and PaymentIntent details to client
        print("went through")
        return jsonify({'publishableKey': os.getenv('STRIPE_PUBLISHABLE_KEY'), 'clientSecret': intent.client_secret, 'id': intent.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

##Methods added for Stripe Connect


@app.route("/connect/oauth/", methods=["GET"])
def handle_oauth_redirect():
    # Assert the state matches the state you provided in the OAuth link (optional).
    state = request.args.get("state")

    if not state_matches(state):
        return json.dumps({"error": "Incorrect state parameter: " + state}), 403

    # Send the authorization code to Stripe's API.
    code = request.args.get("code")
    try:
        response = stripe.OAuth.token(grant_type="authorization_code", code=code,)
    except stripe.oauth_error.OAuthError as e:
        return json.dumps({"error": "Invalid authorization code: " + code}), 400
    except Exception as e:
        return json.dumps({"error": "An unknown error occurred."}), 500

    connected_account_id = response["stripe_user_id"]

    print("account ID", connected_account_id)
    accntParticulars = stripe.Account.retrieve(connected_account_id)
    print("particulars", accntParticulars)
    email = accntParticulars["email"]
    doc_ref = db.collection("tutors").document(email)
    doc_ref.update({"stripe_id": connected_account_id})
    print("sent to firebase")

    # Render some HTML or redirect to a different page.clear

    return json.dumps({"success": True}), 200

def state_matches(state_parameter):
  # Load the same state value that you randomly generated for your OAuth link.
    saved_state = "234162eb-b627-4899-b123-5dda1859a631"

    return saved_state == state_parameter



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

@app.route("/access-express/<stripe_id>", methods=["GET"])
def openExpress():
    output = stripe.Account.create_login_link(stripe_id)
    print(output)
    return jsonify(output)

#Emails Section (Bcz Heroku is being an ass)
@app.route('/confirm-class', methods=['POST'])
def confirmClass():
    data = request.json
    print(data)
    name = data["name"]
    email = data["email"]
    className = data["class"]

    server = smtplib.SMTP(host='smtp.gmail.com', port=587)
    server.starttls()
    server.login("fibonia.emailclient@gmail.com", "Test!2345")

    msg = MIMEMultipart()

    msg['From'] = "Fibonia Email Server"
    msg['To'] = "info@fibonia.com"
    msg['Subject'] = "New Tutor Class Request"

    msg.attach(MIMEText(name + " has requested to sign up for " + className + ". Their email is " + email + "\nApprove or deny this request"))

    server.send_message(msg)
    server.quit()

    return "success"

@app.route('/tutor-wants-money', methods=['POST'])
def tutorMoney():
    data = request.json
    name = data["name"]
    studentEmail = data["email"]
    paymentCode = data["payCode"]

    server = smtplib.SMTP(host='mail.fibonia.com', port=25)
    server.starttls()
    server.login("appointments@fibonia.com", "GloriousCeiling!#%")
    msg = MIMEMultipart()

    msg['From'] = "appointments@fibonia.com"
    msg['To'] = studentEmail
    msg['Subject'] = "Your Fibonia Appointment"

    body = """Dear {},
    
It is nearly time to learn!
    
Your tutor has requested payment for an upcoming appointment. Please log on to the app or website to start your appointment. You will be billed for the duration of the appointment you have booked. 

Click here to initiate payment https://www.fibonia.com/payment/index.php?code={} 

Best Regards,
Fibonia Team
    
""".format(name, paymentCode)

    print("tutor asked for money")
    msg.attach(MIMEText(body))
    server.send_message(msg)

    server.quit()

    return "success"

@app.route('/tutor-appt-request', methods=['POST'])
def tutorRequest():
    data = request.json
    print(data)

    tutorname = data["name"]
    group = data['group']
    time = data['time']
    classname = data['class']
    email = data['email']
    date = data['date']
    acceptUID = data['acceptUID']
    rejectUID = data['rejectUID']
    classForEmail = classname.replace(" ", "%20")

    print(classForEmail)

    groupString = ""
    if group:
        groupString = "are"
    else:
        groupString = "are not"

    server = smtplib.SMTP(host='mail.fibonia.com', port=587)
    server.starttls()
    server.login("appointments@fibonia.com", "GloriousCeiling!#%")
    msg = MIMEMultipart()

    msg['From'] = "appointments@fibonia.com"
    msg['To'] = email
    msg['Subject'] = "Your Fibonia Appointment"

    body = """Dear {},

You have a new tutoring request for {} at {} GMT on {} and they {} willing to participate in group tutoring.

Login to the app or website to make any changes and see this appointment in your local time.

Click here to accept the appointment: https://www.fibonia.com/response.php?email={}&code={}&class={}
Click here to reject the appointment: https://www.fibonia.com/response.php?email={}&code={}&class={}

Best Regards,
Fibonia Team
    """.format(tutorname, classname, time, date, groupString, email, acceptUID, classForEmail, email, rejectUID, classForEmail)

    msg.attach(MIMEText(body))
    server.send_message(msg)

    server.quit()

    return "success"


if __name__ == '__main__':
    app.run()
