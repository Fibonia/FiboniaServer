import json
import os
import stripe
import gunicorn
import smtplib
import pdfplumber
import img2pdf
import random
from PIL import Image
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
from flask_cors import CORS
import pymongo
import ssl
from hashids import Hashids
import pyotp



# This is your real test secret API key.

stripe.api_key = "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"

cred = credentials.Certificate('fibonia-83e34-83001bbabd20.json')
firebase_admin.initialize_app(cred)

# MongoDB Credentials
mongo_url = "mongodb+srv://gurk91:Fibonia!2345@cluster0.a5ggi.mongodb.net/test?retryWrites=true&w=majority"
client = pymongo.MongoClient(mongo_url, ssl=True,ssl_cert_reqs=ssl.CERT_NONE)
mg_db = client.get_database('FibTest')


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
    # Create a PaymentIntent with the order amount and currency
    #intent = stripe.PaymentIntent.create(
     #   amount=data["amount"],
      #  currency='usd',
       # customer=data['customer']
    #)
    payAmount = data["amount"]
    finalAmount = int(float(payAmount * 0.1))
    print("final amount", finalAmount)
    if "tutorID" in data:
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
    else:
    	print("intending")
    	intent = stripe.PaymentIntent.create(
        	payment_method_types=['card'],
        	amount= payAmount,
        	currency='usd',
        	customer = data['customer']
    )
    print("intent, ", intent)

    try:
        # Send publishable key and PaymentIntent details to client
        print("went through")
        return jsonify({'publishableKey': os.getenv('STRIPE_PUBLISHABLE_KEY'), 'clientSecret': intent.client_secret, 'id': intent.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

##Methods added for Stripe Connect

# instantiation of an unique Hashid object
hashids = Hashids(min_length=7, alphabet='abcdefghijklmnopqrstuvwxyz0123456789', salt = 'fibonia')

# Since it takes a String data type rather than the ObjectID(Int) data type, 
# you need to first convert the ObjectID(Int) to String and save it as a 
# variable to pass into this method. 
# i.e. user_id = str(ObjectID.str)
@app.route('/retrieve-referral-code/<uniqueid>', methods=['GET'])
def retrieve_referral(uniqueid):
    #encode
    hashid = hashids.encrypt(str(uniqueid))
    return hashid

@app.route('/decrypt-referral-code/<hashid>', methods=['GET'])
def decrypt_referral(hashid):
    decrypted = hashids.decrypt(str(hashid))
    return str(decrypted[0])

# pyotp instance instantiation
secret = pyotp.random_base32()
totp = pyotp.TOTP(secret, interval=600)

@app.route('/retrieve-otp/', methods=['GET'])
def otp():
    # the generated otp value (6 digits)
    return totp.now()

# Returns a string, not a boolean (i.e. 'True'/'False')
@app.route('/verify-otp/<otp>', methods=['GET'])
def verify(otp):
    return str(totp.verify(otp))

@app.route('/retrieve-discount-code/', methods=['GET'])
def retrieve_discount():
    numbers = {1:'a', 2:'b', 3:'c', 4:'d', 5:'e', 6:'f', 7:'g', 8:'h', 9:'i', 10:'j', 11:'k',
            12:'l', 13:'m', 14:'n', 15:'o', 16:'p', 17:'q', 18:'r', 19:'s', 20:'t', 21:'u',
            22:'v', 23:'w', 24:'x', 25:'y', 26:'z'}
    code = ''
    for _ in range(3):
        code += str(random.randint(10,26))
    for _ in range(4):
        code += numbers[random.randint(1,26)]
    return code

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
def openExpress(stripe_id):
    output = stripe.Account.create_login_link(stripe_id)
    print(output)
    return output["url"]

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
    msg['Subject'] = "New Fibonia Appointment"

    body = """Dear {},

You have a new tutoring request for {} at {} GMT on {} and they {} willing to participate in group tutoring.

Login to the app or website to make any changes and see this appointment in your local time.

Click here to accept the appointment: https://www.fibonia.com/response.php?email={}&code={}&class={}
Click here to reject the appointment: https://www.fibonia.com/response.php?email={}&code={}&class={}

Please note that appointment times on the app and website are in your local timezone.

Best Regards,
Fibonia Team
    """.format(tutorname, classname, time, date, groupString, email, acceptUID, classForEmail, email, rejectUID, classForEmail)

    msg.attach(MIMEText(body))
    server.send_message(msg)

    server.quit()

    return "success"

@app.route('/tutor-appt-reject', methods=['POST'])
def tutorReject():
    data = request.json
    print(data)

    name = data['name']
    timing = data['time']
    classname = data['class']
    studentemail = data['email']
    date = " ".join(timing.split()[0:-1])
    time = timing.split()[-1]

    server = smtplib.SMTP(host='mail.fibonia.com', port=587)
    server.starttls()
    server.login("appointments@fibonia.com", "GloriousCeiling!#%")
    msg = MIMEMultipart()

    msg['From'] = "appointments@fibonia.com"
    msg['To'] = studentemail
    msg['Subject'] = "Fibonia Appointment Request Rejected"

    body = """Dear {},

Your tutor has rejected your request for an appointment on {} at {}hrs for {}. (All times in GMT)

Sorry about this. Please book an appointment with a different tutor, or at a different time. Reach out to us at info@fibonia.com if you need any help.

Best Regards,
Fibonia Team
    """.format(name, date, time, classname)

    msg.attach(MIMEText(body))
    server.send_message(msg)

    server.quit()

    return "success"

@app.route('/tutor-appt-accept', methods=['POST'])
def tutorAccept():
    data = request.json
    print(data)

    name = data['name']
    timing = data['time']
    classname = data['class']
    studentemail = data['email']
    date = " ".join(timing.split()[0:-1])
    time = timing.split()[-1]

    server = smtplib.SMTP(host='mail.fibonia.com', port=587)
    server.starttls()
    server.login("appointments@fibonia.com", "GloriousCeiling!#%")
    msg = MIMEMultipart()

    msg['From'] = "appointments@fibonia.com"
    msg['To'] = studentemail
    msg['Subject'] = "Fibonia Appointment Request Accepted"

    body = """Dear {},

Your tutor has accepted your request for an appointment on {} at {}hrs GMT for {}.

Your tutor will begin the appointment 5-10 mins before the scheduled time in order to allow you to pay them. Please view the appointment on the website or app to click on your tutor's Zoom link to begin.

Please note that appointment times on the app and website are in your local timezone.

Happy Learning!

Best Regards,
Fibonia Team
    """.format(name, date, time, classname)

    msg.attach(MIMEText(body))
    server.send_message(msg)

    server.quit()

    return "success"

@app.route('/tutor-appt-cancel', methods=['POST'])
def tutorCancel():
    data = request.json
    print(data)

    name = data['name']
    timing = data['time']
    classname = data['class']
    studentemail = data['email']
    date = " ".join(timing.split()[0:-1])
    time = timing.split()[-1]

    server = smtplib.SMTP(host='mail.fibonia.com', port=587)
    server.starttls()
    server.login("appointments@fibonia.com", "GloriousCeiling!#%")
    msg = MIMEMultipart()

    msg['From'] = "appointments@fibonia.com"
    msg['To'] = studentemail
    msg['Subject'] = "Fibonia Appointment Cancelled"

    body = """Dear {},

Your tutor has cancelled your appointment on {} at {}hrs GMT for {}.

Sorry about this. Please book an appointment with a different tutor, or at a different time. Reach out to us at info@fibonia.com if you need any help.

Best Regards,
Fibonia Team
    """.format(name, date, time, classname)

    msg.attach(MIMEText(body))
    server.send_message(msg)

    server.quit()

    return "success"

@app.route('/student-appt-cancel', methods=['POST'])
def studentCancel():
    data = request.json
    print(data)

    name = data['name']
    timing = data['time']
    classname = data['class']
    tutoremail = data['email']
    date = " ".join(timing.split()[0:-1])
    time = timing.split()[-1]

    server = smtplib.SMTP(host='mail.fibonia.com', port=587)
    server.starttls()
    server.login("appointments@fibonia.com", "GloriousCeiling!#%")
    msg = MIMEMultipart()

    msg['From'] = "appointments@fibonia.com"
    msg['To'] = tutoremail
    msg['Subject'] = "Fibonia Appointment Cancelled"

    body = """Dear {},

Your student has cancelled the appointment on {} at {}hrs GMT for {}.

Sorry about this. Reach out to us at info@fibonia.com if you need any help.

Best Regards,
Fibonia Team
    """.format(name, date, time, classname)

    msg.attach(MIMEText(body))
    server.send_message(msg)

    server.quit()

    return "success"


@app.route('/venmo-payout', methods=['POST'])
def venmoPayout():
    data = request.json
    print(data)
    name = data["name"]
    email = data["email"]
    venmo = data["venmo"]

    server = smtplib.SMTP(host='smtp.gmail.com', port=587)
    server.starttls()
    server.login("fibonia.emailclient@gmail.com", "Test!2345")

    msg = MIMEMultipart()

    msg['From'] = "Fibonia Email Server"
    msg['To'] = "requests@fibonia.com"
    msg['Subject'] = "Venmo Payout"

    msg.attach(MIMEText("{} wants to receive venmo payout for id {} and email {}".format(name, venmo, email)))

    server.send_message(msg)
    server.quit()

    return "success"

def transcript_call(url1,req,ourclass=0):
  def download_file(url):
      local_filename = url.split('/')[-1]
      headers = {'User-Agent': 'XY', 'Content-type': 'application/json'}
      with requests.get(url,headers=headers) as r:
          assert r.status_code == 200, f'error, status code is {r.status_code}'
          with open(local_filename, 'wb') as f:
              f.write(r.content)
      return local_filename
  if url1[len(url1)-3:len(url1)] != "pdf":
    invoice_pdf = "tstoutput.pdf"
    if url1.split('.')[-1] == "JPG":
      ourfile = "tstyes.JPG"
      urllib.request.urlretrieve(url1, "tstyes.JPG")
    else:
      ourfile = "tstyes.PNG"
      urllib.request.urlretrieve(url1, "tstyes.PNG")
    image = Image.open(ourfile)
    pdf_bytes = img2pdf.convert(image.filename)
    file = open(invoice_pdf, "wb")
    file.write(pdf_bytes)
    image.close()
    file.close()
    os.remove(ourfile)
  if url1[len(url1)-3:len(url1)] == "pdf":
    invoice = url1
    invoice_pdf = download_file(invoice)
  url1 = invoice_pdf
  try:
    with pdfplumber.open(invoice_pdf) as pdf:
        os.remove(invoice_pdf)
        page = pdf.pages[0]
        text = page.extract_text(x_tolerance=2)
        lines = text.split('\n')
        firstname = ""
        secondname = ""
        lvl = ""
        grade=""
        for i in range(0,len(pdf.pages)):
          page = pdf.pages[0]
          text = page.extract_text(x_tolerance=2)
          lines = text.split('\n')
          for line in lines:
            if "My Academics" in line:
              ourbool = True
              break;
            else:
              ourbool = False
        if req == "grade":
          for i in range(0,len(pdf.pages)):
            page = pdf.pages[i]
            text = page.extract_text(x_tolerance=2)
            lines = text.split('\n')
            for line in lines:
              if ourclass in line and ourbool == False:
                grade = line.split(' ')[-2]
              elif ourclass in line and ourbool:
                grade = line.split(' ')[-1]
          if grade == "":
            return None
          else:
            return json.dumps({"grade":grade})
        elif req == "signup":
          for i in range(0,len(pdf.pages)):
            page = pdf.pages[i]
            text = page.extract_text(x_tolerance=2)
            lines = text.split('\n')
            for line in lines:
              if ourbool == False:
                if "Name " in line:
                  firstname = line.split(' ')[1]
                  lastname = line.split(' ')[-1]
                if "Level " in line:
                  lvl = line.split(' ')[-1]
              elif ourbool:
                firstname = lines[3].split(' ')[0]
                lastname = lines[3].split(' ')[-1]
                lvl = [lines[x].split(' ')[-1] for x in range(0,len(lines)) if  "Level " in lines[x]]
                break;
            break;
          if firstname == "" or lastname=="" or lvl == "":
            return None
          else:
            return json.dumps({"firstname":firstname,"lastname":lastname,"lvl":lvl})
        else:
          return None
  except Exception as e:
    return None

@app.route('/transcript', methods=['GET'])
def transcript_check():
    data = request.json
    input_url = data['url1']
    input_req = data['req']
    input_ourclass = data['ourclass']
    return transcript_call(input_url, input_req, input_ourclass)

@app.route('/schools', methods=['GET'])
def schools():
    colleges = ["--Select School--", "UC Berkeley", "Other"]
    return json.dumps({"schools": colleges})

@app.route('/get_classes', methods=['POST'])
def berk_classes():
    data = request.json
    print(data)
    school = data['school']
    with open('classes.json', 'r') as f:
        ret_val = json.load(f)
    classes_dict = json.loads(ret_val)
    out_dict = classes_dict[school]
    return json.dumps(out_dict)

@app.route('/add_data', methods=['POST'])
def addData():
    data = request.json["value"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    table.insert_one(data)
    return "Data Inserted"

@app.route('/delete_data', methods=['POST'])
def deleteData():
    ourid = request.json["id"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    myquery = {"_id":ObjectId(ourid)}
    table.delete_one(myquery)
    return "Data Deleted"

@app.route('/select_data', methods=['POST'])
def selectData():
    ourid = request.json["id"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    myquery = {"_id":ObjectId(ourid)}
    mydoc = table.find(myquery)
    list_cur = list(mydoc)
    mydoc = dumps(list_cur)
    return mydoc

@app.route('/update_data', methods=['POST'])
def updateData():
    ourid = request.json["id"]
    value = request.json["value"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    myquery = {"_id":ObjectId(ourid)}
    newvalues = { "$set": value }
    table.update_one(myquery,newvalues)
    return "Data Updated"

if __name__ == '__main__':
    app.run()
