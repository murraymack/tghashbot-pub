#!/usr/bin/env python3
import mysql.connector
import time
import json
import requests
import os
from luxor import API
from resolvers import RESOLVERS
from nicehash import private_api
from datetime import datetime

config = {
    'user': 'admin',
    'password': 'xxxxxxxxxxx',
    'host': 'xxxxxxxxxxx-db.xxxxxxxxxxx.us-east-1.rds.amazonaws.com',
    'database': 'hashdata',
    'raise_on_warnings': True
}


def sql_write(data_package, config):

    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    data = {}
    data['date'] = data_package['date']
    data['pool'] = data_package['pool']
    data['algo'] = data_package['algo']
    data['hash_current'] = data_package['hash_current']

    write_hash_data = "INSERT INTO ukalta_ (date, pool, algo, hash_current) VALUES (%s, %s, %s, %s)"
    values = (data['date'], data['pool'], data['algo'], data['hash_current'])

    cursor.execute(write_hash_data, values)
    cnx.commit()
    cursor.close()
    cnx.close()

    print(values)
    print(f"Write of {data['pool']} {data['algo']} successful")

    return None

def sha256_package():

    ###################################################
    # Slushpool MySQL Write Data Packet
    ###################################################

    r = requests.get('https://slushpool.com/accounts/profile/json/btc/',
                     headers={"SlushPool-Auth-Token" : "xxxxxxxxxxx"}).json()

    data = {}
    data['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['pool'] = 'luxor'
    data['algo'] = 'SHA256'
    data['hash_current'] = r['btc']['hash_rate_scoring'] / 1000000

    ###################################################
    # Luxor Hashrate Adder
    ###################################################

    luxAPI = API(host = 'https://api.beta.luxor.tech/graphql', method = 'POST', org = 'luxor', key = 'xxxxxxxxxxx')
    luxRESOLVERS = RESOLVERS(df = False)
    resp = luxAPI.get_subaccount_mining_summary(subaccount='mysubaccount',
                                                mpn='BTC',
                                                inputInterval='_15_MINUTE')
    resolved = luxRESOLVERS.resolve_get_subaccount_mining_summary(resp)

    luxor_hashrate = round(resolved['hashrate'] / 10e14, 2)

    data['hash_current'] = "{:.2f}".format(data['hash_current'] + luxor_hashrate)

    return data

def scrypt_package():

    ###################################################
    # Nicehash MySQL Write Data Packet
    ###################################################

    # Request data
    host="https://api2.nicehash.com"
    organization="xxxxxxxxxxx"
    key="xxxxxxxxxxx"
    secret="xxxxxxxxxxx"
    private = private_api(host, organization, key, secret)
    hashrate = private.get_rig_stats("__DEFAULT__")

    # Write and Package
    data = {}
    data['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['pool'] = 'nicehash'
    data['algo'] = 'scrypt'
    try:
        data['hash_current'] = "{:.2f}".format(float(hashrate['algorithms']['SCRYPT']['speedAccepted']) / 1000000)
    except KeyError:
        data['hash_current'] = "{:.2f}".format(0.00)
    implied_machines = "{:.2f}".format(float(data['hash_current']) / 500)

    return data


while True:
    try:
        sha256_data = sha256_package()
        sql_write(sha256_data, config)
    except:
        print("Error on sha256 write.")
    try:
        scrypt_data = scrypt_package()
        sql_write(scrypt_data, config)
    except:
        print("Error on scrypt write.")
    time.sleep(60)