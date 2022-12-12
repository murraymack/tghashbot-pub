#!/usr/bin/env python3
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, InlineQueryHandler, Job, JobQueue, CallbackContext
import logging
import sys
import os
import glob
import re
import mysql.connector
import time
import json

# SQL Config
config = {
    'user': 'admin',
    'password': 'xxxxxxxx',
    'host': 'xxxxxxxx-db.xxxxxxxx.us-east-1.rds.amazonaws.com',
    'database': 'hashdata',
    'raise_on_warnings': True
}

# HELPER FUNCTION: Returns type=list of user_ids for iterating
def user_id_list(user_list_db):
    user_list = []
    file = open(user_list_db, "r")
    for user in file:
        try:
            if not user.split(',')[0] == "\n":
                user_list.append(user.split(',')[0])
        except IndexError as error:
            None #put some logging here later if needed
    return user_list

def hash_callback(returned_rows=None):

    assert type(returned_rows) == list

    substring = ""
    datestr = ""

    for item in returned_rows:
        for element in item:
            date, pool, algo, hashrate = element
            datestr = date.strftime("%y/%m/%d %H:%M:%S")
            if algo == "SHA256":
                #datestring = date.strftime("%y/%m/%d %H:%M:%S")
                substring += f"SHA256: {hashrate} PH/s\n"
            if algo == "scrypt":
                #datestring = date.strftime("%y/%m/%d %H:%M:%S")
                substring += f"Scrypt: {hashrate} MH/s\n"
    substring += datestr


    return substring

def latest_hash(update, context):

    data_read = ["SHA256", "scrypt"]
    returned_rows = sql_read(data_read, config)
    payload = hash_callback(returned_rows)

    context.bot.send_message(chat_id=update.effective_chat.id, text=payload)



def start_alerts(update, context: CallbackContext):

    chat_id=update.effective_chat.id

    try:
        if int(context.args[0]) > 0:
            interval = int(context.args[0])
            message=str(f"Alerts started with interval of {interval} seconds!\nTo cancel, type /stop hash_alert\n")
            context.bot.send_message(chat_id=chat_id, text=message)
            context.job_queue.run_repeating(hash_alert, context=chat_id, interval=interval, first=1.0)
        else:
            message=str(f"Please enter a duration for the alert scan!\nExample: /alert 60")
            context.bot.send_message(chat_id=chat_id, text=message)
    except:
        context.bot.send_message(chat_id=chat_id, text="Please enter a duration for the alert scan!\nExample: /alert 60")



def stop_alerts(update, context: CallbackContext):
    """Remove the job"""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Alerts successfully cancelled!' if job_removed else 'You have no active alerts.'
    update.message.reply_text(text)



def show_alerts(update, context: CallbackContext):
    """Show names of existing alerts"""
    current_jobs = [job.name for job in context.job_queue.jobs()]
    if not current_jobs:
        update.message.reply_text("No active alerts.")
    else:
        show_jobs = ""
        for job in current_jobs:
            show_jobs += str(job)
            show_jobs += "\n"
        update.message.reply_text("Active alerts:\n" + show_jobs[:-1])



def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.jobs()
    if not current_jobs:
        return False
    for job in current_jobs:
        job.remove()
    return True

def sql_read(data_read, config):

    #Connect and set base query
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    q0 = "SELECT u.date, u.pool, u.algo, u.hash_current"
    query = []
    returned_rows = []

    #Parse data_read values here
    #data_read in form of ["SHA256","scrypt","etc"]
    for data in data_read:
        substring = f"{q0} FROM ukalta_ AS u WHERE u.date = (SELECT MAX(date) FROM u WHERE algo = '{data}') AND u.algo = '{data}';"
        query.append(substring)

    #Execute query and return results
    for item in query:
        cursor.execute(item)
        record = cursor.fetchall()
        returned_rows.append(record)

    #Close MySQL Connection
    cursor.close()
    cnx.close()

    return returned_rows

def hash_alert(context: CallbackContext):

    job = context.job

    substring = ""

    returned_rows = sql_read(["SHA256","scrypt"], config)

    for item in returned_rows:
        for element in item:
            date, pool, algo, hashrate = element
            datestr = date.strftime("%y/%m/%d %H:%M:%S")
            if algo == "SHA256" and hashrate <= 2.25:
                #datestring = date.strftime("%y/%m/%d %H:%M:%S")
                substring += f"Low SHA256: {hashrate} PH/s\n"
            if algo == "scrypt" and hashrate <= 10000:
                #datestring = date.strftime("%y/%m/%d %H:%M:%S")
                substring += f"Low Scrypt: {hashrate} MH/s\n"
    if len(substring) <= 1:
        substring += datestr
    else:
        context.bot.send_message(job.context, text=substring)
        

# writting functionality of the command
def start(update, context):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.name
    users_raw = str(os.getcwd()) + "/users/user_list.txt"
    user_list = user_id_list(users_raw)
    print(f"{user_id},{user_name}\n", file=open(users_raw, "a"))

    message = 'Welcome to the bot'
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def main():

    # set classes
    token = 'xxxxxxxx:xxxxxxxx'
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue
    job_queue.set_dispatcher(dispatcher)

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    # give a name to the command and add it to the dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('hash', latest_hash))
    dispatcher.add_handler(CommandHandler('alert', start_alerts))
    dispatcher.add_handler(CommandHandler('show', show_alerts))
    dispatcher.add_handler(CommandHandler('stop', stop_alerts))

    updater.start_polling() # enable bot to get updates
    updater.idle()
    job_queue.start()

if __name__ == "__main__":
    main()