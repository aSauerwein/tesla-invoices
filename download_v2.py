#!/usr/bin/env python3

"""
Author: Dominik Steiner (dominik.steiner@nts.eu)
Description: This script downloads all Tesla charging invoices for a given month.
Usage: python3 dsteiner_tesla_invoices_download.py
Version: 2.0
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

REFRESH_TOKEN_PATH = Path(
    os.environ.get("REFRESH_TOKEN", "/opt/tesla-invoices/secrets/refresh_token.txt")
)
REFRESH_TOKEN = REFRESH_TOKEN_PATH.read_text().strip()
ACCESS_TOKEN_PATH = Path(
    os.environ.get("ACCESS_TOKEN", "/opt/tesla-invoices/secrets/access_token.txt")
)
ACCESS_TOKEN = ACCESS_TOKEN_PATH.read_text().strip()
# path to save invoices
INVOICE_PATH = Path(os.environ.get("INVOICE_PATH", "/opt/tesla-invoices/invoices/"))


def main():
    pass


def base_req(url: str, method="get", json={}):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        # "x-tesla-user-agent": "TeslaApp/4.28.3-2167",
    }
    result = requests.request(method=method, url=url, headers=headers, json=json)
    result.raise_for_status()
    try:
        return result.json()
    except Exception as e:
        # not json, could be text or binary(PDF)
        return result


def jwt_decode(token: str):
    # get the second part of the jwt token
    payload = token.split(".")[1]
    # add padding
    payload += "=" * ((4 - len(payload) % 4) % 4)
    payload_json = json.loads(base64.b64decode(payload))
    return payload_json


def refresh_token():
    # check if current token expires in less than 2 hours
    jwt_json = jwt_decode(ACCESS_TOKEN)
    if jwt_json["exp"] - time.time() < 7200:
        # expire in less than 2 hours
        # continue renewal
        url = "https://auth.tesla.com/oauth2/v3/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": "ownerapi",
            "refresh_token": REFRESH_TOKEN,
            "scope": "openid email offline_access",
        }
        result = base_req(url, method="post", json=payload)
        ACCESS_TOKEN_PATH.write_text(result["access_token"])
    else:
        # token is valid for mor then 2 hours
        # skip renewal
        return True


def interactive():
    # interactive user input mode
    cur_month = date.today().replace(day=1)
    prev_month = cur_month - timedelta(days=1)

    user_choice_month = input(
        "Bitte gewünschten Monat im Format 'YYYY-MM' bzw. 'cur' oder 'prev' oder 'all' für aktuellen oder vorherigen Monat oder alles eingeben [prev]: "
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
        print(f"Using 'all'.")
    else:
        try:
            desired_invoice_date = datetime.strptime(
                user_choice_month, "%Y-%m"
            )  # format: YYYY-MM
            print(f"Using '{desired_invoice_date.strftime('%Y-%m')}'.")
        except:
            print("ERROR - Bitte Eingabe kontrollieren!")
            exit(1)

    download_invoice(desired_invoice_date)


def daemon():
    # non interactive daemon mode, download current only current month
    cur_month = date.today().replace(day=1)
    download_invoice(cur_month)
    pass


def download_invoice(desired_invoice_date):
    # refresh token befor any api request
    refresh_token()

    vehicles = get_vehicles()
    url_charging_base = "https://ownership.tesla.com/mobile-app/charging/"
    for vin, vehicle in vehicles.items():
        if "display_name" in vehicle:
            print(f"Processing vehicle {vehicle['vin']} - {vehicle['display_name']}...")
        else:
            print(f"Processing vehicle {vehicle['vin']}...")

        # create API URL for vehicle VIN
        url_charging_history = f"{url_charging_base}history?deviceLanguage=en&deviceCountry=AT&httpLocale=en_US&vin={vehicle['vin']}&operationName=getChargingHistoryV2"
        charging_sessions = base_req(url_charging_history)
        save_invoice(charging_sessions["data"], desired_invoice_date)


def get_charging_invoice(charging_session_invoice_id, vin):
    url_charging_base = "https://ownership.tesla.com/mobile-app/charging/"
    url_charging_invoice = f"{url_charging_base}invoice/{charging_session_invoice_id}?deviceLanguage=en&deviceCountry=AT&httpLocale=en_US&vin={vin}"

    return base_req(url_charging_invoice)


def save_invoice(charging_sessions, desired_invoice_date):
    # make sure folder exists
    INVOICE_PATH.mkdir(parents=True, exist_ok=True)

    for charging_session in charging_sessions:
        charging_session_datetime = datetime.fromisoformat(
            charging_session["unlatchDateTime"]
        )
        charging_session_countrycode = charging_session["countryCode"]

        # check for desired invoice date
        if desired_invoice_date == 1990:
            # 1990 means all invoices, if it is not 1990 skip this invoice
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
                charging_invoice = get_charging_invoice(
                    charging_session_invoice_id, charging_session["vin"]
                )

                local_file_path = (
                    INVOICE_PATH
                    / f"tesla_charging_invoice_{charging_session['vin']}_{charging_session_datetime.strftime('%Y-%m-%d')}_{charging_session_countrycode}_{charging_session_invoice_filename}"
                )
                local_file_path.write_bytes(charging_invoice.content)
                print(f"File '{local_file_path}' saved.")


def get_vehicles():
    url_products = "https://owner-api.teslamotors.com/api/1/products?orders=true"
    vehicles = {}
    products = base_req(url=url_products)
    for product in products["response"]:
        # check if product is vehicle (and therefore has a VIN)
        if "vin" in product:
            vehicles[product["vin"]] = product
    return vehicles


if __name__ == "__main__":
    if len(argv) > 1:
        if argv[1] == "daemon":
            daemon()
    else:
        interactive()
