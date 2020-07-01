import json
import os
import stripe
# This is your real test secret API key.

stripe.api_key = "sk_test_DMiK1oNbmgPE0SxC69vLO489007v8m0JWJ"

from flask import Flask, render_template, jsonify, request

app = Flask(__name__, static_folder=".",
            static_url_path="", template_folder=".")


def calculate_order_amount(items):
    # Replace this constant with a calculation of the order's amount
    # Calculate the order total on the server to prevent
    # people from directly manipulating the amount on the client
    return 1400

@app.route('/')
def intro():
    return "Hello there"

@app.route('/create_customer', methods=['POST'])
def creatCustomer():
    cust = stripe.Customer.create(description="created for user")
    custID = cust['id']
    return custID


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
        currency='usd'
    )

    try:
        # Send publishable key and PaymentIntent details to client
        return jsonify({'publishableKey': os.getenv('STRIPE_PUBLISHABLE_KEY'), 'clientSecret': intent.client_secret})
    except Exception as e:
        return jsonify(error=str(e)), 403

if __name__ == '__main__':
    app.run()
