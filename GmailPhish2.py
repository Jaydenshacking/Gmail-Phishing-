#!/usr/bin/python

import smtplib
import base64
import os
import sys
import getopt
import urllib.request
import urllib.parse
import re
import socket
import time
import itertools
import urllib.parse
from datetime import datetime
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("No BeautifulSoup installed")
    print("See: http://www.crummy.com/software/BeautifulSoup/#Download")
    sys.exit()
try:
    import DNS
except ImportError:
    print("No pyDNS installed")

from optparse import OptionParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

version = 0.13

class SendEmails:
    def __init__(self):
        self.FROM_ADDRESS = None
        self.MAIL_FROM_ADDRESS = None
        self.REPLY_TO_ADDRESS = None
        self.SUBJECT = 'Test'
        self.filemail = 'emails.txt'
        self.filebody = 'body.txt'
        self.delay = 3
        self.limit = 50
        self.Discovered = {}
        self.emailSent = []
        self.emailFail = []
        self.google = False
        self.guser = 'test'
        self.gpass = 'test'
        self.MAIL_SERVER = None
        self.Beef = False
        self.verbose = False
        self.output = False
        self.socEngWebsite = ''

    def getWebServer(self):
        webserver = self.socEngWebsite
        return webserver

    def discoverSMTP(self, domain):
        DNS.DiscoverNameServers()
        mx_hosts = DNS.mxlookup(domain)
        return mx_hosts

    def checkEmail(self, emails):
        for email in emails:
            if not re.match(r"([a-zA-Z\.\-_0-9]+)@([a-zA-Z\.\-_0-9]+)\.([a-z]+)", email):
                print(f"Error: not a valid email {email}")
                print(f"Check {self.filemail}")
                sys.exit()

    def discoveredDomain(self, emails):
        for email in emails:
            domain = email.split('@')[1]
            if domain not in self.Discovered:
                self.Discovered[domain] = self.discoverSMTP(domain)
        return self.Discovered

    def writeLog(self):
        emailSent = self.emailSent
        emailFail = self.emailFail
        now = datetime.now().strftime("%d-%m-%Y_%H-%M")
        with open(f"phemail-log-{now}.txt", "w") as f:
            emailSent = sorted(set(emailSent))
            emailFail = sorted(set(emailFail))
            command = ' '.join(sys.argv)
            f.write(command)
            f.write("\n\nSuccessful Emails Sent:\n")
            f.write("-------------------------\n")
            for email in emailSent:
                f.write(f"{email}\n")
            f.write("\nFailed Emails Sent:\n")
            f.write("-------------------------\n")
            for email in emailFail:
                f.write(f"{email}\n")
        print(f"Phemail.py log file saved: phemail-log-{now}.txt")

    def removePictures(self, pict):
        for i, _ in enumerate(pict):
            os.remove(f'image{i}.jpg')

    def createMail(self, email):
        FROM_ADDRESS = self.FROM_ADDRESS
        MAIL_FROM_ADDRESS = self.MAIL_FROM_ADDRESS
        SUBJECT = self.SUBJECT
        REPLY_TO_ADDRESS = self.REPLY_TO_ADDRESS
        webserverLog = datetime.now().strftime("%d_%m_%Y_%H:%M")
        try:
            with open(self.filebody, 'rb') as fb:
                body = fb.read().decode('utf-8')
        except IOError:
            print(f"File not found: {self.filebody}")
            sys.exit()
        webserver = self.getWebServer()
        msg = MIMEMultipart('related')
        msg['mail from'] = FROM_ADDRESS
        msg['from'] = MAIL_FROM_ADDRESS
        msg['subject'] = SUBJECT
        msg['reply-to'] = REPLY_TO_ADDRESS
        msg['to'] = email
        msg.preamble = 'This is a multi-part message in MIME format.'
        msgAlt = MIMEMultipart('alternative')
        msg.attach(msgAlt)
        msgText = MIMEText('This is the alternative plain text message.')
        msgAlt.attach(msgText)
        html = BeautifulSoup(body, "lxml")
        pict = []
        for i, x in enumerate(html.findAll('img')):
            picname = f'image{i}.jpg'
            try:
                with open(picname, 'rb') as ft:
                    pict.append(MIMEImage(ft.read()))
            except IOError:
                print(f"Downloaded {picname}")
                with open(picname, 'rb') as ft:
                    pict.append(MIMEImage(ft.read()))
            body = body.replace(x['src'], f'cid:image{i}')

        if self.Beef:
            url = f"{webserver}/index.php?e={base64.b64encode(email.encode()).rstrip(b'=')}&b=1"
        else:
            url = f"{webserver}/index.php?e={base64.b64encode(email.encode()).rstrip(b'=')}&b=0"

        url = f"{url}&l={base64.b64encode(webserverLog.encode()).rstrip(b'=')}"
        msgAlt.attach(MIMEText(body.format(url), 'html'))
        for i, pic in enumerate(pict):
            pic.add_header('Content-ID', f'<image{i}>')
            msg.attach(pic)
        return FROM_ADDRESS, msg['to'], msg.as_string(), pict

    def sendMail(self):
        delay = self.delay
        verbose = self.verbose
        MAIL_SERVER = self.MAIL_SERVER
        numLimit = int(self.limit)
        limit = 0
        webserver = self.getWebServer()
        Emails = [line.strip() for line in open(self.filemail)]
        Emails = sorted(set(Emails))
        self.checkEmail(Emails)
        emailSent = self.emailSent
        emailFail = self.emailFail
        Discovered = self.discoveredDomain(Emails)

        for domain in Discovered:
            print(f"Domain: {domain}")
            if MAIL_SERVER:
                print(f"SMTP server: {MAIL_SERVER}")
                server = smtplib.SMTP(MAIL_SERVER)
                mx = itertools.cycle([(10, MAIL_SERVER)])
                mx_current = next(mx)[1]
            else:
                if Discovered[domain]:
                    mx = itertools.cycle(Discovered[domain])
                    mx_current = next(mx)[1]
                    print(f"SMTP server: {mx_current}")
                    server = smtplib.SMTP(mx_current)

            for email in Emails:
                if domain == email.split('@')[1]:
                    FROM, TO, MSG, pict = self.createMail(email)
                    try:
                        if verbose:
                            server.set_debuglevel(1)
                        server.sendmail(FROM, TO, MSG)
                        print(f"Sent to {email}")
                        time.sleep(delay)
                        emailSent.append(email)
                    except Exception as e:
                        print(f"Error: sending to {email}")
                        emailFail.append(email)
                        if verbose:
                            print(e)
                    limit += 1
                    if numLimit == limit:
                        print(f"Connection closed to SMTP server: {mx_current}")
                        server.close()
                        time.sleep(delay)
                        mx_current = next(mx)[1]
                        print(f"Domain: {domain}")
                        print(f"SMTP server: {mx_current}")
                        server = smtplib.SMTP(mx_current)
                        limit = 0

        if self.output:
            self.writeLog()
        print(f"PHishing URLs point to {webserver}")

    def sendGMail(self):
        guser = self.guser
        gpass = self.gpass
        delay = self.delay
        numLimit = int(self.limit)
        limit = 0
        verbose = self.verbose
        MAIL_SERVER = self.MAIL_SERVER or 'smtp.sendgrid.net'
        webserver = self.getWebServer()
        Emails = [line.strip() for line in open(self.filemail)]
        Emails = sorted(set(Emails))
        self.checkEmail(Emails)
        emailSent = self.emailSent
        emailFail = self.emailFail

        print(f"SMTP server: {MAIL_SERVER}")
        server = smtplib.SMTP(MAIL_SERVER, 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(guser, gpass)

        for email in Emails:
            if email not in emailSent:
                FROM, TO, MSG, pict = self.createMail(email)
                try:
                    if verbose:
                        server.set_debuglevel(1)
                    server.sendmail(FROM, TO, MSG)
                    print(f"Sent to {email}")
                    time.sleep(delay)
                    emailSent.append(email)
                except Exception as e:
                    print(f"Error: sending to {email}")
                    emailFail.append(email)
                    if verbose:
                        print(e)
                limit += 1
                if numLimit == limit:
                    print(f"Connection closed to SMTP server: {MAIL_SERVER}")
                    server.close()
                    time.sleep(delay)
                    print(f"SMTP server: {MAIL_SERVER}")
                    server = smtplib.SMTP(MAIL_SERVER, 587)
                    limit = 0

        if self.output:
            self.writeLog()
        print(f"PHishing URLs point to {webserver}")
        server.close()

class HarvestEmails:
    def __init__(self):
        self.agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
        self.headers = {'User-Agent': self.agent}
        self.format = 0
        self.pages = 10
        self.search = "example"
        self.domain = "example.com"
        self.verbose = False
        self.run = False

    def gatherEmails(self):
        pages = self.pages
        search = self.search.replace(" ", "+")
        domain = self.domain
        format_type = self.format
        verbose = self.verbose
        emails = []
        print(f"Gathering emails for domain: {domain}")
        print(f"Google Query: {search}")
        for page in range(0, pages):
            url = f"http://www.google.co.uk/search?hl=en&safe=off&q=site:linkedin.com/pub+{re.sub(r'\..*', '', search)}&start={page}0"
            if verbose:
                print(f"Google Query {url}")
            request = urllib.request.Request(url, None, self.headers)
            response = urllib.request.urlopen(request)
            data = response.read()
            html = BeautifulSoup(data, "lxml")
            regex = re.compile(r"linkedin\.com/pub/([a-zA-Z'\-]+)\-([\-a-zA-Z']+)")
            usernames = regex.findall(str(html))
            if verbose:
                print(usernames)
            sys.stdout.write(f"\r{((100 * (page + 1)) // pages)}%")
            sys.stdout.flush()
            for email in usernames:
                if format_type == '0':
                    emails.append(f"{email[0]} {email[1]}@{domain}")
                elif format_type == '1':
                    emails.append(f"{email[0]}.{email[1]}@{domain}")
                elif format_type == '2':
                    emails.append(f"{email[0]}{email[1]}@{domain}")
                elif format_type == '3':
                    emails.append(f"{email[0][0:1]}.{email[1]}@{domain}")
                elif format_type == '4':
                    emails.append(f"{email[0]}.{email[1][0:1]}@{domain}")
                elif format_type == '5':
                    emails.append(f"{email[1]}.{email[0]}@{domain}")
                elif format_type == '6':
                    emails.append(f"{email[1][0:1]}.{email[0]}@{domain}")
                elif format_type == '7':
                    emails.append(f"{email[0][0:1]}@{domain}")
                elif format_type == '8':
                    emails.append(f"{email[1]}{email[0]}@{domain}")
                elif format_type == '9':
                    emails.append(f"{email[0]}_{email[1]}@{domain}")
        emails = sorted(set(emails))
        with open("emails.txt", "w") as f:
            print("")
            for email in emails:
                f.write(f"{email}\n")
                print(email)
        print("\nemails.txt updated")
        sys.exit()

class CloneWebsite:
    def __init__(self):
        self.URL = ""
        self.run = False
        self.scheme = ""
        self.netloc = ""
        self.verbose = False

    def Page(self):
        print(self.URL)
        process = os.system(f"wget --no-check-certificate -c -k -O clone.html {self.URL}")
        if process == 0:
            print("Cloned web page saved: clone.html")
        else:
            print("[!] Cloning could not be completed. Please install wget: https://www.gnu.org/software/wget/")

def usage(version):
    print(f"PHishing EMAIL tool v{version}\nUsage: {os.path.basename(sys.argv[0])} [-e <emails>] [-m <mail_server>] [-f <from_address>] [-r <replay_address>] [-s <subject>] [-b <body>]")
    print("""          -e    emails: File containing list of emails (Default: emails.txt)
          -F    mail from: SMTP email address header (Default: Name Surname <name_surname@example.com>)
          -f    from: Source email address displayed in FROM field of the email (Default: Name Surname <name_surname@example.com>)
          -r    reply_address: Actual email address used to send the emails in case that people reply to the email
          -s    subject: Subject of the email (Default: Newsletter)
          -b    body: Body of the email (Default: body.txt)
          -p    pages: Specifies number of results pages searched (Default: 10 pages)
          -v    verbose: Verbose Mode (Default: false)
          -l    layout: Send email with no embedded pictures
          -B    BeEF: Add the hook for BeEF
          -m    mail_server: SMTP mail server to connect to
          -g    Google: Use a google account username:password
          -t    Time delay: Add delay between each email (Default: 3 sec)
          -L    webserverLog: Customise the name of the webserver log file (Default: Date time in format "%d_%m_%Y_%H_%M")
          -S    Search: query on Google
          -d    domain: of email addresses
          -n    number: of emails per connection (Default: 10 emails)
          -c    clone: Clone a web page
          -w    website: where the phishing email link points to
          -o    save output in a file
          -T    Type Format (Default: 0):
                0- firstname surname
                1- firstname.surname@example.com
                2- firstnamesurname@example.com
                3- f.surname@example.com
                4- firstname.s@example.com
                5- surname.firstname@example.com
                6- s.firstname@example.com
                7- surname.f@example.com
                8- surnamefirstname@example.com
                9- firstname_surname@example.com
          """)
    print(f"Examples: {os.path.basename(sys.argv[0])} -e emails.txt -f \"Name Surname <name_surname@example.com>\" -r \"Name Surname <name_surname@example.com>\" -s \"Subject\" -b body.txt")
    print(f"          {os.path.basename(sys.argv[0])} -S example -d example.com -T 1 -p 12")
    print(f"          {os.path.basename(sys.argv[0])} -c https://example.com")

if __name__ == "__main__":
    sender = SendEmails()
    harvester = HarvestEmails()
    cloner = CloneWebsite()

    if sys.argv[1:]:
        optlist, args = getopt.getopt(sys.argv[1:], 'he:f:F:r:s:b:p:g:w:lBm:vL:T:S:d:t:n:c:R:o')
        NoPict = False
        webserverLog = None

        for o, a in optlist:
            if o == "-h":
                usage(version)
                sys.exit()
            elif o == "-e":
                sender.filemail = a
            elif o == "-F":
                sender.MAIL_FROM_ADDRESS = a
            elif o == "-f":
                sender.FROM_ADDRESS = a
            elif o == "-r":
                sender.REPLY_TO_ADDRESS = a
            elif o == "-s":
                sender.SUBJECT = a
            elif o == "-b":
                sender.filebody = a
            elif o == "-S":
                harvester.run = True
                harvester.search = a
            elif o == "-d":
                harvester.domain = a
            elif o == "-T":
                harvester.format = a
            elif o == "-p":
                harvester.pages = int(a)
            elif o == "-l":
                NoPict = True
            elif o == "-m":
                sender.MAIL_SERVER = a
            elif o == "-B":
                sender.Beef = True
            elif o == "-w":
                sender.socEngWebsite = a
            elif o == "-o":
                sender.output = True
            elif o == "-c":
                pUrl = urllib.parse.urlparse(a)
                cloner.URL = a
                cloner.scheme = pUrl.scheme.lower()
                cloner.netloc = pUrl.netloc.lower()
                if not cloner.scheme:
                    print('ERROR: http(s):// prefix required')
                    sys.exit(1)
                cloner.run = True
            elif o == "-v":
                harvester.verbose = True
                sender.verbose = True
                cloner.verbose = True
            elif o == "-g":
                sender.google = True
                sender.guser, sender.gpass = a.split(":")
            elif o == "-t":
                sender.delay = int(a)
            elif o == "-n":
                sender.limit = int(a)
            elif o == "-L":
                webserverLog = "".join([c for c in a if re.match(r'\w', c)])
            else:
                usage(version)
                sys.exit()
    else:
        usage(version)
        sys.exit()

    if harvester.run:
        harvester.gatherEmails()
    if cloner.run:
        cloner.Page()
        sys.exit()

    if sender.google:
        sender.sendGMail()
    else:
        if sender.FROM_ADDRESS is None:
            print("Error: from_address not specified")
            sys.exit()
        sender.sendMail()