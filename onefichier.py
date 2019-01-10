#!/usr/bin/python3
# -*- coding: utf-8 -*-


import getopt
import getpass
import json
import logging
import os.path
import re
import sys
import time
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime import multipart, text


class OneFichier:
    BASE_URL = "https://1fichier.com"
    CONFIG_PATH = ".onefichier/"
    CONFIG_FILE = "config.json"
    LOG_FILE = "trace.log"

    VERSION = "OneFichier v0.1"

    def __init__(self, config_file=None):
        """

        :param config_file: Json config file name
        """

        # Config file exists ?
        path = os.path.join(os.path.expanduser("~"), OneFichier.CONFIG_PATH)
        if config_file is None:
            config_file = os.path.join(os.path.join(path, self.CONFIG_FILE))

        if not os.path.isfile(config_file):
            logging.critical("Config file not found in " + config_file)
            logging.critical("Please run with --init parameter")
            print("Failed to load config file ! ('{}')".format(config_file))
            sys.exit(2)

        # Open config file and check mandatory values
        self.config = json.load(open(config_file))
        if "email" not in self.config:
            raise ValueError("email value missing in config file")

        if "password" not in self.config:
            raise ValueError("password value missing in config file")

        if "download_path" not in self.config:
            self.config["download_path"] = "./"

        logging.getLogger("requests").setLevel(logging.WARNING)
        self.session = requests.Session()
        self.Directories = {}

    @staticmethod
    def makeconf():
        """
        Create a config file in home directory
        :return: None
        """
        print("make config file...")

        # Create the path in home directory
        path = os.path.join(os.path.expanduser("~"), OneFichier.CONFIG_PATH)
        if not os.path.exists(path):
            os.makedirs(path)
            os.chmod(path, 0o700)

        data = dict()
        data["email"] = input("Insert your email address: ")
        data["password"] = getpass.getpass("Insert your password: ")
        data["download_path"] = input("What is the local absolute where to download files: ")
        data["directory"] = input("What is the name of the folder on 1fichier to watch: ")
        data["done"] = input("What is the name of the folder where to move downloaded files: ")
        data["delay"] = input("Seconds to sleep before looking for new file to download [300]: ")

        if data["delay"] == "":
            data["delay"] = 300

        data["smtp"] = {}
        data["smtp"]["host"] = input("Smtp host: ")
        data["smtp"]["port"] = input("Smtp port: ")
        data["smtp"]["user"] = input("Smtp user: ")
        data["smtp"]["password"] = getpass.getpass("Smtp password: ")
        data["smtp"]["from"] = input("Smtp from: ")
        data["smtp"]["to"] = input("Smtp to: ")
        data["smtp"]["subject"] = "OneFichier reporting"
        data["smtp"]["tls"] = True

        # Save the file
        file = os.path.join(path, OneFichier.CONFIG_FILE)
        with open(file, "w") as outfile:
            json.dump(data, outfile, sort_keys=True, indent=3, separators=(',', ': '))

        # Protect the file
        os.chmod(file, 0o600)

        sys.exit()

    def login(self, lt="on", purge="off", valider="Send"):
        """

        :param lt: long session
        :param restrict: Restrict the session to my IP address
        :param purge: purge old sessions
        :return:
        """

        logging.info(self.VERSION)
        logging.info("Login to 1fichier.com...")

        # Login test
        data ={
            "mail": self.config["email"],
            "pass": self.config["password"],
            "lt": lt,
            "purge": purge,
            "valider": valider,
        }

        result = self.session.post(self.BASE_URL + "/login.pl", data)
        content = result.content.decode("utf-8")

        if "Invalid username." in content:
            logging.info("Wrong username")
            print ("Wrong username")
            exit()

        if "Invalid username or Password." in content:
            logging.info("Wrong password")
            print ("Wrong password")
            exit()

            if "222" in content:
                    logging.info("Your IP has (probably) been banned")
                    print ("Your IP has (probably) been banned")
            exit()

        logging.info("Login successful.")
        print ("Login successful.")

        # Update directories
        self.getDirectories()

    def logout(self):

        self.session.get(self.BASE_URL + "/logout.pl")
        logging.debug("Logout...")
        pass

    def getFilesByDirectoryName(self, name=""):
        """
        Get a listing of file in a directory by its name
        :param name: Name of the directory
        :return: Array of files
        """
        dir_id = self.getDirectoryId(name)

        return self.getFilesByDirectoryId(dir_id)

    def getFilesByDirectoryId(self, dir_id):
        """
        Get a listing of file in a directory by its id

        :param dir_id: Id of the directory to list
        :return: Array of files
        """

        res = self.session.get(self.BASE_URL + "/console/files.pl?dir_id=" + str(dir_id) + "&oby=da")

        # Htmlify the result
        soup = BeautifulSoup("<html><body>" + res.content.decode("utf-8") + "</body></html>", "html.parser")
        lis = soup.findAll("li", {"class": "file"})

        files = {}
        for li in lis:
            ref = li["rel"]
            name = li.find("a").contents[0]

            res = self.session.get(self.BASE_URL + "/console/link.pl?selected[]=" + ref)
            soup = BeautifulSoup("<html><body>" + res.content.decode("utf-8") + "</body></html", "html.parser")
            a = soup.find("a", href=re.compile("^https://1fichier.com/"))

            files[ref] ={
                "name": name,
                "url": a.attrs["href"]
            }

        return files

    def getFilesToDownload(self):
        """
        Returns the list of file to downloadFile

        :return:
        """
        return self.getFilesByDirectoryName(self.config["directory"])

        pass

    def downloadFile(self, data, path=None):
        """
        Download a file

        :param data: File information data
        :param path: Local download path
        """

        # Oops, some infos are missing !!
        if data is None or data["name"] is None or data["url"] is None:
            return False

        logging.info("Downloading file \"" + data["name"] + "\"")

        # Disable the download menu
        self.session.get(self.BASE_URL + "/console/params.pl?menu=false")

        # Open the url
        get = self.session.get(data["url"] + "&e=1&auth=1")
        url = get.text.split(";")[0]

        # Enable back the download menu
        self.session.get(self.BASE_URL + "/console/params.pl?menu=true")

        # File already downloaded
        headers = {}
        path = path if None else self.config["download_path"]
        filename = os.path.abspath(os.path.join(path, data["name"]))
        if os.path.isfile(filename):
            logging.info("Resuming download...")
            headers = {'Range': 'bytes=%d-' % os.path.getsize(filename)}

        # Requesting the file
        try:
            response = self.session.get(url, headers=headers, stream=True)
        except requests.Exception.MissingSchema:
            return False

        if not response.ok:

            # File fully downloaded
            if response.status_code == 416:
                logging.info("File already downloaded, skipping...")

            # Global error...
            else:
                logging.error("Global error (HTTP status code: " + str(response.status_code) + ") !")

            return False

        # Download the stream
        headers = response.headers

        # Resume mode ?
        if 'Content-Range' not in headers:
            openmode = "wb"             # open file mode
            openpos = 0                 # seek position in resume mode
        else:
            openmode = "ab"
            m = re.match("bytes (\d+)-(\d+)\/(\d+)", headers["Content-Range"])
            openpos = int(m.group(1))

        file_size = int(headers["content-length"]) if 'content-length' in headers else 1
        logging.info("File size : " + "{0:,}".format(file_size).replace(',', ' ') + " bytes (" +
                     "{0:,}".format(round(file_size / 1024 / 1024, 2)).replace(',', ' ') + "M)")

        done = openpos          # bytes already downloaded
        chunksize = 4096 * 16   # size of the stream
        start = time.time()     # Total elapsed time
        with open(filename, openmode) as handle:

            # resume mode ?
            if openpos > 0:
                handle.seek(openpos)

            for block in response.iter_content(chunksize):

                handle.write(block)
                done += chunksize

        elapsed = (time.time() - start)  # * 1000
        m, s = divmod(elapsed, 60)
        h, m = divmod(m, 60)
        logging.info("Elapsed time : %d:%02d:%02d" % (h, m, s))

        return True

    def deleteFile(self, file_id):
        """
        Deletes a file

        :param file_id: Id of the file to delete

        """

        logging.debug("Deleting file #" + file_id)

        data = {
            "selected[]": file_id,
            "remove": 1,
        }
        result = self.session.post(self.BASE_URL + "/console/remove.pl", data)

    def moveFile(self, file_id, dir_id):
        """
        Moves a file to a another directory

        :param file_id: File id to move
        :param dir_id: Target directory id

        :return:
        """

        logging.debug("Moving file #" + file_id + " to directory #" + dir_id)

        data = {
            "dragged[]": file_id,
            "dragged_type": 2,
            "dropped_dir": dir_id,
        }
        result = self.session.post(self.BASE_URL + "/console/op.pl", data)

    def addFileToDirectory(self, file_name, dir_id):
        """
        Add a file to a directory

        :param file_name:
        :param dir_id:
        :return:
        """
        # POST : https://1fichier.com/?<file_id>
        # data with POST : did = <directory_id>


        pass

    def getDirectoryId(self, name):
        """
        Returns the id of a directory given by its name
        :param name:
        :return:
        """

        for ref, data in self.Directories.items():
            if data["name"] == name:
                return ref

        return None

    def getDirectories(self, dir_id = 0):
        """
        Collects the list of Directories

        :param dir_id: Id of the base directory

        """

        res = self.session.get(self.BASE_URL + "/console/dirs.pl?dir_id=" + str(dir_id))

        logging.info("Parsing directories. This might take some time...")
        print ("Parsing directories. This might take some time...")

        # Htmlify the result
        soup = BeautifulSoup("<html><body>" + res.content.decode("utf-8") + "</body></html>", "html.parser")
        lis = soup.findAll("li")

        for li in lis:

            div = li.find("div")
            name = div.get_text().split(u"\xa0")[0]
            haschildren = div.find("div", {"class": "fcp"}) is not None
            rel = li.attrs["rel"]

            self.Directories[rel] = \
            {
                "name": name,
                "parent": dir_id,
            }

            # Find the sub directories
            # if (int(rel) != dir_id and hasChildren):
            if haschildren:
                self.getDirectories(rel)

        return self.Directories

    def getDirectory(self, dir_id, name):
        """
        Checks if a directory is present


        :param dir_id: Parent directory
        :param name: Directory name
        :return:
        """

        for ref, data in self.Directories.items():
            if data["name"] == name and data["parent"] == dir_id:
                return ref

        return None

    def makeDirectory(self, dir_id, name):
        """

        :param dir_id: Base directory id
        :param name: Name of the new directory

        :return:
        """

        data ={
            "dir_id": dir_id,
            "mkdir": name
        }
        result = self.session.post(self.BASE_URL + "/console/mkdir.pl", data)

        # Update directory list
        f = self.getDirectories(dir_id)

        # Find it...
        for ref, data in f.items():
            if data["name"] == name and ref == dir_id:
                return ref

        return None

    def sendreport(self, body):
        """
        Send a notification by email

        :param body:    Body of the mail
        :return:
        """
        smtp = self.config['smtp']

        msg = multipart.MIMEMultipart()
        msg['From'] = smtp['from']
        msg['To'] = smtp['to']
        msg['Subject'] = smtp['subject']

        msg.attach(text.MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp['host'], smtp['port'])
        server.starttls()
        server.login(smtp['user'], smtp['password'])

        server.sendmail(smtp['from'], smtp['to'], msg.as_string())
        server.quit()


def main(argv):

    # Init log
    path = os.path.join(os.path.expanduser("~"), OneFichier.CONFIG_PATH)
    if os.path.exists(path) is False:
        os.mkdir(path, 0o700)

    log = os.path.join(path, OneFichier.LOG_FILE)
    logging.basicConfig(filename=log,
                        level=logging.INFO,
                        format='%(asctime)s - %(levelname)s: %(message)s')

    # Read arguments
    try:
        opts, args = getopt.getopt(argv[1:], "ic:", ["init", "config="])
    except getopt.GetoptError as e:
        logging.warning("onefichier --help")
        sys.exit(2)

    config = None       # Config file name
    for opt, arg in opts:
        # Init ?
        if opt in ('-i', '--init'):
            OneFichier.makeconf()

        # Config filename to use
        if opt in ('-c', '--config'):
            config = arg

    one = OneFichier(config)

    while True:
        # Login
        one.login()

        # Files to downloadFile
        files = one.getFilesToDownload()

        # Download directory id
        dir_id = one.getDirectoryId(one.config["directory"])

        # Backup directory present ?
        done_id = one.getDirectory(dir_id, one.config["done"])
        if not done_id:
            done_id = one.makeDirectory(dir_id, one.config["done"])

        # Let's go !!!
        for file_id, file in files.items():

            # Send an email
            one.sendreport('Downloading ' + file['name'])

            # Download file
            if one.downloadFile(file):

                # Backup the file
                one.moveFile(file_id, done_id)

                # Send an email
                one.sendreport(file['name'] + ' downloaded !')

        # Some delay
        # logging.debug("Going to sleep...")
        time.sleep(int(one.config["delay"]))

if __name__ == "__main__":
    main(sys.argv)
