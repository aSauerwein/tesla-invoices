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

if __name__ == "__main__":
    cur_month = date.today().replace(day=1)
    prev_month = cur_month - timedelta(days=1)

    user_choice_month = input("Bitte gewünschten Monat im Format 'YYYY-MM' bzw. 'cur' oder 'prev' oder 'all' für aktuellen oder vorherigen Monat oder alles eingeben [prev]: ")
    user_choice_month = user_choice_month.strip().lower()
    
    if user_choice_month == "prev" or user_choice_month == "":
        desired_invoice_date = prev_month
        print(f"Using '{desired_invoice_date.strftime('%Y-%m')}'.")
    elif user_choice_month == "cur":
        desired_invoice_date = cur_month
        print(f"Using '{desired_invoice_date.strftime('%Y-%m')}'.")
    elif user_choice_month == "all":
        desired_invoice_date = datetime.strptime("1999-01", '%Y-%m')
        print(f"Using 'all'.")
    else:
        try:
            desired_invoice_date = datetime.strptime(user_choice_month, '%Y-%m') # format: YYYY-MM
            print(f"Using '{desired_invoice_date.strftime('%Y-%m')}'.")
        except:
            print("ERROR - Bitte Eingabe kontrollieren!")
            exit(1)

    bearer_token = open("/opt/tesla-invoices/secrets/access_token.txt").read()
    bearer_token = bearer_token.strip()

    url_products = 'https://owner-api.teslamotors.com/api/1/products?orders=true'
    url_charging_base = 'https://ownership.tesla.com/mobile-app/charging/'
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json',
        'x-tesla-user-agent': 'TeslaApp/4.28.3-2167'
    }

    # get vehicle VINs
    response = requests.get(url_products, headers=headers)
    if response.status_code == 200:
        products = response.json()['response']
        if products:
            for product in products:
                # check if product is vehicle (and therefore has a VIN)
                if 'vin' in product:
                    vehicle_vin = product['vin']
                    if product['display_name']:
                        vehicle_display_name = product['display_name']
                        print(f"Processing vehicle {vehicle_vin} ({vehicle_display_name})...")
                    else:
                        vehicle_display_name = ""
                        print(f"Processing vehicle {vehicle_vin}...")

                    # create API URL for vehicle VIN
                    url_charging_history = f'{url_charging_base}history?deviceLanguage=en&deviceCountry=AT&httpLocale=en_US&vin={vehicle_vin}&operationName=getChargingHistoryV2'

                    # get charging history for VIN
                    response = requests.get(url_charging_history, headers=headers)
                    if response.status_code == 200:
                        charging_history = response.json()['data']
                        if charging_history:
                            # iterate through all charging sessions
                            for charging_session in charging_history:
                                charging_session_datetime = datetime.fromisoformat(charging_session['unlatchDateTime'])
                                charging_session_countrycode = charging_session['countryCode']

                                # check for desired invoice date
                                if (charging_session_datetime.year != desired_invoice_date.year) or (charging_session_datetime.month != desired_invoice_date.month):
                                    if desired_invoice_date.year != 1999:
                                        continue

                                charging_session_invoices = charging_session['invoices']
                                # ignore free supercharging sessions (null)
                                if charging_session_invoices:
                                    for charging_session_invoice in charging_session_invoices:
                                        charging_session_invoice_id = charging_session_invoice['contentId']
                                        charging_session_invoice_filename = charging_session_invoice['fileName']
                                        url_charging_invoice = f'{url_charging_base}invoice/{charging_session_invoice_id}?deviceLanguage=en&deviceCountry=AT&httpLocale=en_US&vin={vehicle_vin}'

                                        response = requests.get(url_charging_invoice, headers=headers)
                                        if response.status_code == 200:
                                            local_file_path = f"invoices/tesla_charging_invoice_{vehicle_vin}_{charging_session_datetime.strftime('%Y-%m-%d')}_{charging_session_countrycode}_{charging_session_invoice_filename}"
                                            # open local file in binary write mode and write the content of the PDF in current dir
                                            with open(local_file_path, 'wb') as file:
                                                file.write(response.content)
                                            print(f"File '{local_file_path}' saved.")
                                        else:
                                            print(f"ERROR - GET {url_charging_invoice} - {response.status_code} - {response.text}")
                        else:
                            print(f"ERROR - There are no charging sessions for vehicle {vehicle_vin}.")
                    else:
                        print(f"ERROR - GET {url_charging_history} - {response.status_code} - {response.text}")
        else:
            print("ERROR - No vehicles found.")
    else:
        print(f"ERROR - GET {url_products} - {response.status_code} - {response.text}")
    
    print("DONE")