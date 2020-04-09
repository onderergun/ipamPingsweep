
import argparse
import json
import requests
from getpass import getpass
from urllib3.exceptions import InsecureRequestWarning
import time

import smtplib
import os.path as op
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders


requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def subnetSweep(cvpServer, session_id, session_token, subnet):
    update_resp = requests.get(
        'https://%s/cvp-ipam-api/subnetsweep?session_id=%s&token=%s&subnet=%s'% (cvpServer, session_id, session_token, subnet),verify=False)
    return update_resp.json()["responses"]

def getAllocations(cvpServer, session_id, session_token, id):
    update_resp = requests.get(
        'https://%s/cvp-ipam-api/allocations?session_id=%s&token=%s&id=%s'% (cvpServer, session_id, session_token, id),verify=False)
    return update_resp.json()["data"]

def getPools(cvpServer, session_id, session_token, id):
    update_resp = requests.get(
        'https://%s/cvp-ipam-api/pools?session_id=%s&token=%s&id=%s'% (cvpServer, session_id, session_token, id),verify=False)
    return update_resp.json()["data"]

def getReservations(cvpServer, session_id, session_token, id):
    update_resp = requests.get(
        'https://%s/cvp-ipam-api/reservations?session_id=%s&token=%s&id=%s'% (cvpServer, session_id, session_token, id),verify=False)
    return update_resp.json()["data"]

def send_mail(send_from, send_to, subject, message, files,
          server, port, username, password, use_tls):

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(message))

    for path in files:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        'attachment; filename="{}"'.format(op.basename(path)))
        msg.attach(part)

    smtp = smtplib.SMTP(server, port)
    if use_tls:
        smtp.starttls()
    smtp.login(username, password)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.quit()

def main():
    d1 = time.strftime("%Y.%m.%d  %H:%M:%S", time.gmtime())

    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--cvpServer', required=True)

    args = parser.parse_args()
    username = args.username
    password = getpass()
    cvpServer=args.cvpServer

    print ('Start Login')
    login_data = {'username': username, 'password': password}
    login_resp = requests.post('https://%s/cvp-ipam-api/login' % cvpServer,
                               data=json.dumps(login_data), verify=False)
    print ('Login Info')
    login_json = login_resp.json()
    print ('\n')

    session_id = login_json['session_id']
    session_token = login_json['token']
    
    id = "network1-ipv4"
    subnets = getPools(cvpServer, session_id, session_token, id)

    for num, net in enumerate(subnets):
       notificationemails= net["notificationemails"].split(",")

       subnetid = net["id"]
       subnet = net["range"]
       octets= subnet.split(".")
       subnetstart = ".".join(octets[0:3]) + ".1"
       subnetend = ".".join(octets[0:3]) + ".253"
       range = subnetid + "-" + subnetstart + "|" + subnetend
       
       percentavailable = net["percentavailable"]
       emailwarning = float(net["emailwarning"])
       emailcritical = float(net["emailcritical"])
       
       allocations=getAllocations(cvpServer, session_id, session_token, range)

       allocIPs = {}
       for address, alloc in enumerate(allocations):
           allocIPs[alloc["address"]] = [alloc["description"]]
       
       print (subnetid)
       response=subnetSweep(cvpServer, session_id, session_token, subnetid)
       aliveIPs=[]
       message = ""
       if (100-percentavailable) > emailcritical:
           message = message + "Available IP addresses in this subnet is below CRITICAL THRESHOLD " + str(emailcritical) + "\n" + "\n"
       else:
           if (100-percentavailable) > emailwarning:
               message = message + "Available IP addresses in this subnet is below WARNING THRESHOLD " + str(emailwarning) + "\n" + "\n" 

       if response is not None:
           for ips, network in enumerate(response):
               aliveIPs.append(network["IP"])
               if (network["Alive"] == True):
                   if (network["IP"] not in allocIPs):
                       print (network["IP"], "is not allocated but ALIVE")
                       message = message + network["IP"] + " is not allocated but ALIVE\n"
                   if network["IP"] in allocIPs:
                       if (allocIPs[network["IP"]] == ['Reserved']):
                           print (network["IP"], "is RESERVED but ALIVE")
                           message = message + network["IP"] + " is RESERVED but ALIVE\n"
       
       for key,value in allocIPs.items():
           if ((key not in aliveIPs) and (value != ['Reserved'])):
               print (key, "is allocated but DEAD")
               message = message + key +  " is allocated but DEAD\n"
       
       send_from = "sender@domain.com"
       send_to = notificationemails
       subject = "Ping Sweep Report for Subnet "+ subnet + "    "+ d1
       files =[]
       server = "smtp.domain.com"
       username = "username"
       password = "password"
       port =587
       use_tls = True
       send_mail(send_from, send_to, subject, message, files, server, port, username, password, use_tls )
    
    print ('\n')
    print ('Start Logout')
    logout_data = {'session_id': session_id, 'token': session_token}
    logout_resp = requests.post('https://%s/cvp-ipam-api/logout' % cvpServer,
                                data=json.dumps(logout_data), verify=False)
    print ('Logout Info')
    logout_json = logout_resp.json()
    print (logout_json)

if __name__ == '__main__':
    main()

