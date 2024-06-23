#!/usr/bin/env python3

"""
Author: Dominik Steiner (dominik.steiner@nts.eu), Andreas Sauerwein-Schlosser (andreas@sauerwein.se)
Description: This script downloads all Tesla charging invoices for a given month.
Usage: python3 dsteiner_tesla_invoices_download.py
Version: 0.6.0
Date Created: 2024-02-05
Changed: Changed Owner-API Endpoint to /products instead of /vehicles.
Python Version: 3.11.7
Dependencies: requests, datetime
Notice: This software is provided "as is" and without any warranty. Use at your own risk.
"""

import requests
from datetime import date, datetime, timedelta
from pathlib import Path
import base64
import json
import time
from sys import argv
import os
import smtplib
from email.message import EmailMessage
import logging
from time import sleep

# setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)

if Path("/data/options.json").exists():
    # running as HA Addon, parse all options from /data/options.json
    HOMEASSISTANT = True
    options = json.load(Path("/data/options.json").open())
    REFRESH_TOKEN_PATH = Path("/data/refresh_token.txt")
    REFRESH_TOKEN = options["refresh_token"]  # refresh token from options, might be expired
    ACCESS_TOKEN_PATH = Path("/data/access_token.txt")
    ACCESS_TOKEN = options["access_token"]  # access token from options, might be expired
    INVOICE_PATH = Path("/data/invoices/")
    if options.get("enable_email_export", False):
        ENABLE_EMAIL_EXPORT = True
        EMAIL_FROM = options["email"]["from"]
        EMAIL_TO = options["email"]["to"]
        EMAIL_SERVER = options["email"]["mailserver"]
        EMAIL_SERVER_PORT = options["email"]["port"]
        EMAIL_USER = options["email"]["user"]
        EMAIL_PASS = options["email"]["password"]
    else:
        ENABLE_EMAIL_EXPORT = False
    ENABLE_SUBSCRIPTION_INVOICE = options.get("enable_subscription_invoice", True)
else:
    HOMEASSISTANT = False
    # get everything from environment variables
    REFRESH_TOKEN_PATH = Path(os.environ.get("REFRESH_TOKEN", "/opt/tesla-invoices/secrets/refresh_token.txt"))
    REFRESH_TOKEN = REFRESH_TOKEN_PATH.read_text().strip()
    ACCESS_TOKEN_PATH = Path(os.environ.get("ACCESS_TOKEN", "/opt/tesla-invoices/secrets/access_token.txt"))
    ACCESS_TOKEN = ACCESS_TOKEN_PATH.read_text().strip()
    # path to save invoices
    INVOICE_PATH = Path(os.environ.get("INVOICE_PATH", "/opt/tesla-invoices/invoices/"))

    ENABLE_EMAIL_EXPORT = os.environ.get("ENABLE_EMAIL_EXPORT", "False").lower() == "true"
    ENABLE_SUBSCRIPTION_INVOICE = os.environ.get("ENABLE_SUBSCRIPTION_INVOICE", "True").lower() == "true"
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
    EMAIL_TO = os.environ.get("EMAIL_TO", "")
    EMAIL_SERVER = os.environ.get("EMAIL_SERVER", "")
    EMAIL_SERVER_PORT = os.environ.get("EMAIL_SERVER_PORT", "587")
    EMAIL_USER = os.environ.get("EMAIL_USER", "")
    EMAIL_PASS = os.environ.get("EMAIL_PASS", "")

# if not REFRESH_TOKEN:
#     logger.error("Refresh Token not set")
#     exit(1)

# if not ACCESS_TOKEN:
#     logger.error("Access Token not set")
#     exit(1)

sess = requests.session()


def main():
    pass


def base_req(url: str, method="get", json={}, *args, **kwargs):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        # "x-tesla-user-agent": "TeslaApp/4.28.3-2167",
    }
    logging.info(f"{method} Request to url: {url}")
    for attempt in range(3):
        try:
            result = sess.request(method=method, url=url, headers=headers, json=json, *args, **kwargs)
            break
        except requests.exceptions.ChunkedEncodingError:
            logger.warning(f"incomplete read occured, attempt {attempt} of 3")
            sleep(attempt * 3 + 1)  # sleep for 1, 4, 7 seconds
    else:
        logger.error("giving up after 3 tries")
        exit(1)
    result.raise_for_status()
    if "application/json" in result.headers.get("Content-Type"):
        return result.json()
    elif "application/pdf" in result.headers.get("Content-Type"):
        return result.content
    else:
        return result


def jwt_decode(token: str):
    # get the second part of the jwt token
    payload = token.split(".")[1]
    # add padding
    payload += "=" * ((4 - len(payload) % 4) % 4)
    payload_json = json.loads(base64.b64decode(payload))
    return payload_json


def compare_token():
    # NOTE to myself
    # it's a little bit difficult to keep track of the tokens in HA
    # USER sets it access and refresh token in the GUI
    # this token gets written to /data/options.json
    # there are some difficulties
    # 1. token set by user can be empty ( somehow.. )
    # 2. user set token can be older than already saved token
    # 3. saved token can be empty
    # 4. saved token can invalid/impossible to parse
    compare_access_token()
    compare_refresh_token()


def compare_access_token():
    global ACCESS_TOKEN
    file_access_token_json = ""
    options_access_token_json = ""
    if ACCESS_TOKEN_PATH.exists():
        file_access_token = ACCESS_TOKEN_PATH.read_text().strip()
        try:
            # see if token is valid
            file_access_token_json = jwt_decode(file_access_token)
        except Exception as e:
            logging.warning(f"Could not Parse Access Token from file {ACCESS_TOKEN_PATH}, {e}")

    # try to get access token from options
    try:
        options_access_token_json = jwt_decode(ACCESS_TOKEN)
    except Exception as e:
        logging.warning(f"Could not Parse Access Token from Options, {e}")

    if not file_access_token_json and not options_access_token_json:
        logging.error("Could not find any valid access token from file or options, exiting")
        exit(1)
    elif file_access_token_json and options_access_token_json:
        # compare both tokens
        if file_access_token_json.get("iat", 0) > options_access_token_json.get("iat", 0):
            ACCESS_TOKEN = file_access_token
        else:
            # nothing to do, ACCESS_TOKEN already set to options
            pass
    elif file_access_token_json and not options_access_token_json:
        ACCESS_TOKEN = file_access_token
    elif not file_access_token_json and options_access_token_json:
        # file does not exist an access token set in options
        # write access token to file
        ACCESS_TOKEN_PATH.write_text(ACCESS_TOKEN)
    else:
        logging.warning("Unhandled Case when comparing access tokens")


def compare_refresh_token():
    global REFRESH_TOKEN
    file_refresh_token_json = ""
    options_refresh_token_json = ""
    if REFRESH_TOKEN_PATH.exists():
        file_refresh_token = REFRESH_TOKEN_PATH.read_text().strip()
        try:
            # see if token is valid
            file_refresh_token_json = jwt_decode(file_refresh_token)
        except Exception as e:
            logging.warning(f"Could not Parse Refresh Token from file {REFRESH_TOKEN_PATH}, {e}")

    # try to get access token from options
    try:
        options_refresh_token_json = jwt_decode(REFRESH_TOKEN)
    except Exception as e:
        logging.warning(f"Could not Parse Refresh Token from Options, {e}")

    if not file_refresh_token_json and not options_refresh_token_json:
        logging.error("Could not find any valid refresh token from file or options, exiting")
        exit(1)
    elif file_refresh_token_json and options_refresh_token_json:
        # compare both tokens
        if file_refresh_token_json.get("iat", 0) > options_refresh_token_json.get("iat", 0):
            REFRESH_TOKEN = file_refresh_token
        else:
            # nothing to do, REFRESH_TOKEN already set to options
            pass
    elif file_refresh_token_json and not options_refresh_token_json:
        # file exists and nothing in options
        REFRESH_TOKEN = file_refresh_token
    elif not file_refresh_token_json and options_refresh_token_json:
        # file does not exist and refresh token set in options
        # write refresh token to file
        REFRESH_TOKEN_PATH.write_text(REFRESH_TOKEN)
    else:
        logging.warning("Unhandled Case when comparing refresh tokens")


def refresh_token():
    global ACCESS_TOKEN
    if HOMEASSISTANT:
        compare_token()
    # check if current token expires in less than 2 hours
    jwt_json = jwt_decode(ACCESS_TOKEN)
    if jwt_json["exp"] - time.time() < 7200:
        # expire in less than 2 hours
        # continue renewal
        logger.info("Refreshing token")
        url = "https://auth.tesla.com/oauth2/v3/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": "ownerapi",
            "refresh_token": REFRESH_TOKEN,
            "scope": "openid email offline_access",
        }
        result = base_req(url, method="post", json=payload)
        ACCESS_TOKEN_PATH.write_text(result["access_token"])
        ACCESS_TOKEN = result["access_token"]
        logger.info("Sucesfully refreshed token")
    else:
        # token is valid for mor then 2 hours
        # skip renewal
        logger.debug("Token still valid for more then 2 hours")
        return True


def interactive():
    # interactive user input mode
    cur_month = date.today().replace(day=1)
    prev_month = cur_month - timedelta(days=1)

    user_choice_month = input(
        "Bitte gewünschten Monat im Format 'YYYY-MM' bzw. 'cur' oder 'prev' oder 'all' für aktuellen oder vorherigen Monat oder alles eingeben [prev]: "  # noqa
    )
    user_choice_month = user_choice_month.strip().lower()

    if user_choice_month == "prev" or user_choice_month == "":
        desired_invoice_date = prev_month
        print(f"Using '{desired_invoice_date.strftime('%Y-%m')}'.")
    elif user_choice_month == "cur":
        desired_invoice_date = cur_month
        print(f"Using '{desired_invoice_date.strftime('%Y-%m')}'.")
    elif user_choice_month == "all":
        desired_invoice_date = datetime.strptime("1999-01", "%Y-%m")
        print("Using 'all'.")
    else:
        try:
            desired_invoice_date = datetime.strptime(user_choice_month, "%Y-%m")  # format: YYYY-MM
            print(f"Using '{desired_invoice_date.strftime('%Y-%m')}'.")
        except:  # noqa
            print("ERROR - Bitte Eingabe kontrollieren!")
            exit(1)

    download_invoice(desired_invoice_date)


def daemon():
    # non interactive daemon mode, download current only current month
    logger.debug("Starting in Daemon mode")
    cur_month = date.today().replace(day=1)
    logger.debug("Downloading invoice of current month only")
    download_invoice(cur_month)


def download_invoice(desired_invoice_date):
    # refresh token befor any api request
    logger.info(f"Desired Invoice Date: {desired_invoice_date} ")
    refresh_token()

    vehicles = get_vehicles()
    url_charging_base = "https://ownership.tesla.com/mobile-app/charging/"
    for vin, vehicle in vehicles.items():
        if "display_name" in vehicle:
            logger.info(f"Processing vehicle {vehicle['vin']} - {vehicle['display_name']}...")
        else:
            logger.info(f"Processing vehicle {vehicle['vin']}...")

        # create API URL for vehicle VIN
        url_charging_history = f"{url_charging_base}history?deviceLanguage=en&deviceCountry=AT&httpLocale=en_US&vin={vehicle['vin']}&operationName=getChargingHistoryV2"  # noqa
        charging_sessions = base_req(url_charging_history)
        save_charging_invoice(charging_sessions["data"], desired_invoice_date)

        if ENABLE_SUBSCRIPTION_INVOICE:
            logger.info("Subscription Invoice Enabled -> starting to download subscription invoices")
            url_subcription_invoices = "https://ownership.tesla.com/mobile-app/subscriptions/invoices"
            params_subscription_invoices = {
                "deviceLanguage": "en",
                "deviceCountry": "AT",
                "httpLocale": "en_US",
                "vin": vehicle["vin"],
                "optionCode": "$CPF1",
            }
            subscription_invoices = base_req(url_subcription_invoices, params=params_subscription_invoices)
            save_subscription_invoice(subscription_invoices["data"], desired_invoice_date, vehicle["vin"])

        if ENABLE_EMAIL_EXPORT:
            send_mails()

        logger.info("DONE")


def get_charging_invoice(charging_session_invoice_id, vin):
    url_charging_base = "https://ownership.tesla.com/mobile-app/charging/"
    url_charging_invoice = f"{url_charging_base}invoice/{charging_session_invoice_id}?deviceLanguage=en&deviceCountry=AT&httpLocale=en_US&vin={vin}"  # noqa

    return base_req(url_charging_invoice)


def get_subscription_invoice(subscription_invoice_id, vin):
    url_documents_invoice = f"https://ownership.tesla.com/mobile-app/documents/invoices/{subscription_invoice_id}"
    params = {
        "deviceLanguage": "en",
        "deviceCountry": "AT",
        "httpLocale": "en_US",
        "vin": vin,
    }
    return base_req(url_documents_invoice, params=params)


def save_charging_invoice(charging_sessions, desired_invoice_date):
    # make sure folder exists
    INVOICE_PATH.mkdir(parents=True, exist_ok=True)

    for charging_session in charging_sessions:
        charging_session_datetime = datetime.fromisoformat(charging_session["unlatchDateTime"])
        charging_session_countrycode = charging_session["countryCode"]

        # check for desired invoice date
        if desired_invoice_date.year == 1999:
            # 1999 means all invoices
            pass
        elif charging_session_datetime.year != desired_invoice_date.year:
            # wrong year -> skip
            continue
        elif charging_session_datetime.month != desired_invoice_date.month:
            # correct year but bad month -> skip
            continue

        charging_session_invoices = charging_session["invoices"]
        # ignore free supercharging sessions (null)
        if charging_session_invoices:
            for charging_session_invoice in charging_session_invoices:
                charging_session_invoice_id = charging_session_invoice["contentId"]
                charging_session_invoice_filename = charging_session_invoice["fileName"]

                local_file_path = (
                    INVOICE_PATH
                    / f"tesla_charging_invoice_{charging_session['vin']}_{charging_session_datetime.strftime('%Y-%m-%d')}_{charging_session_countrycode}_{charging_session_invoice_filename}"  # noqa
                )
                if local_file_path.exists():
                    # file already downloaded, skip
                    logger.info(f"Invoice {charging_session_invoice_filename} already saved")
                    continue

                logger.info(f"Downloading {charging_session_invoice_filename}")
                charging_invoice = get_charging_invoice(charging_session_invoice_id, charging_session["vin"])
                local_file_path.write_bytes(charging_invoice)
                logger.info(f"File '{local_file_path}' saved.")


def save_subscription_invoice(subscription_invoices, desired_invoice_date, vin):
    # make sure folder exists
    INVOICE_PATH.mkdir(parents=True, exist_ok=True)

    for invoice in subscription_invoices:
        invoice_datetime = datetime.fromisoformat(invoice["InvoiceDate"])

        # check for desired invoice date
        if desired_invoice_date.year == 1999:
            # 1999 means all invoices
            pass
        elif invoice_datetime.year != desired_invoice_date.year:
            # wrong year -> skip
            continue
        elif invoice_datetime.month != desired_invoice_date.month:
            # correct year but bad month -> skip
            continue

        local_file_path = (
            INVOICE_PATH / f"tesla_subscription_invoice_{vin}_{invoice_datetime.strftime('%Y-%m-%d')}.pdf"
        )
        if local_file_path.exists():
            # file already downloaded, skip
            logger.info(f"Invoice - {invoice['InvoiceFileName']} already saved to {local_file_path}")
            continue

        logger.info(f"Downloading {invoice['InvoiceFileName']}")
        subscription_invoice = get_subscription_invoice(invoice["InvoiceId"], vin)
        local_file_path.write_bytes(subscription_invoice)
        logger.info(f"File '{local_file_path}' saved.")


def get_vehicles():
    url_products = "https://owner-api.teslamotors.com/api/1/products?orders=true"
    vehicles = {}
    products = base_req(url=url_products)
    for product in products["response"]:
        # check if product is vehicle (and therefore has a VIN)
        if "vin" in product:
            vehicles[product["vin"]] = product
    return vehicles


def send_mails():
    try:
        s = smtplib.SMTP(EMAIL_SERVER, EMAIL_SERVER_PORT, timeout=20)
        s.ehlo()
        s.starttls()
        s.login(EMAIL_USER, EMAIL_PASS)
    except Exception as e:
        logger.error(f"Failed to connect to mailserver: {e}")
        return False

    for invoice in INVOICE_PATH.glob("*.pdf"):
        # look for a .json with the exact same name and path of the pdf
        metadata_file = Path(str(invoice).replace(".pdf", ".json"))
        if metadata_file.exists():
            metadata = json.load(metadata_file.open())
        else:
            metadata_file.touch()
            metadata = {}

        if "email_sent" in metadata:
            # email already sent, skip this invoice
            continue

        email = EmailMessage()

        email["From"] = EMAIL_FROM
        email["To"] = EMAIL_TO
        email["Subject"] = "Tesla Invoice Export"
        email.add_attachment(
            invoice.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=invoice.name,
        )
        try:
            s.send_message(email)
            logger.info(f"Sent Mail to {EMAIL_TO} for invoice {invoice.name}")
            metadata["email_sent"] = int(time.time())
            json.dump(metadata, metadata_file.open("w"), sort_keys=True, indent=4)
        except smtplib.SMTPException as e:
            logger.error(f" Failed to send mail: {e}")


if __name__ == "__main__":
    if len(argv) > 1:
        if argv[1] == "daemon":
            daemon()
    else:
        interactive()
