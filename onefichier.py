#!/usr/bin/env python3

import time
import json
import os.path
import re
import requests
from bs4 import BeautifulSoup


class OneFichier():
    base_url = "https://1fichier.com"

    def __init__(self, config_file = "./config.json"):
        """

        :param config_file: Json config file name
        """

        # Debug requests traffic
        # http_client.HTTPConnection.debuglevel = 1
        # logging.basicConfig()
        # logging.getLogger().setLevel(logging.DEBUG)
        # requests_log = logging.getLogger("requests.packages.urllib3")
        # requests_log.setLevel(logging.DEBUG)
        # requests_log.propagate = True


        # Open config file and check mandatory values
        self.config = json.load(open(config_file))
        if "email" not in self.config:
            raise ValueError("email value missing in config file")

        if "password" not in self.config:
            raise ValueError("password value missing in config file")

        if "download_path" not in self.config:
            self.config["download_path"] = "./"

        self.session = requests.Session()
        self.Directories = {}

    def login(self, lt = "on", restrict = "off", purge = "off"):
        """

        :param mail: login
        :param password: password
        :param lt: long session
        :param restrict: Restrict the session to my IP address
        :param purge: purge old sessions
        :return:
        """

        print("Login to 1fichier.com...")

        # Login test
        data ={
            "mail": self.config["email"],
            "pass": self.config["password"],
            "lt": lt,
            "restrict": restrict,
            "purge": purge,
        }

        result = self.session.post(self.base_url + "/login.pl", data)


        # Update directories
        self.getDirectories()

    def logout(self):

        self.session.get(self.base_url + "/logout.pl")
        print("Logout...")
        pass

    def getFilesByDirectoryName(self, name =""):
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

        :param name: Id of the directory to list
        :return: Array of files
        """

        res = self.session.get(self.base_url + "/console/files.pl?dir_id=" + str(dir_id) + "&oby=da")

        # Htmlify the result
        soup = BeautifulSoup("<html><body>" + res.content.decode("utf-8") + "</body></html>", "html.parser")
        lis = soup.findAll("li", {"class": "file"})

        files = {}
        for li in lis:
            ref = li["rel"]
            name = li.find("a").contents[0]

            res = self.session.get(self.base_url + "/console/link.pl?selected[]=" + ref)
            soup = BeautifulSoup("<html><body>" + res.content.decode("utf-8") + "</body></html", "html.parser")
            a = soup.find("a", href=re.compile("^https://1fichier.com/"))

            files[ref] =\
            {
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
            return

        print (data["name"])

        # Disable the download menu
        self.session.get(self.base_url + "/console/params.pl?menu=false")

        # Open the url
        get = self.session.get(data["url"] + "&e=1&auth=1")
        url = get.text.split(";")[0]

        # Enable the download menu
        self.session.get(self.base_url + "/console/params.pl?menu=true")

        response = self.session.get(url, stream = True)
        if not response.ok:
            print("Failed to get stream data !")
            return

        # Download the stream
        headers = response.headers
        file_size = int(headers["content-length"] if 'content-length' in headers else 1)
        print("File size : " + str(file_size) + " bytes (" + str(round(file_size / 1024 / 1024, 2)) + "M)")

        # File already downloaded
        path = path if None else self.config["download_path"]
        filename = os.path.abspath(os.path.join(path, data["name"]))
        if os.path.isfile(filename):

            # Same size ?
            if os.path.getsize(filename) == file_size:
                print("File already downloaded. Skipping !")
                return

            # Delete partially downloaded file
            os.remove(filename)

        done = 0
        chunksize = 4096 * 16
        blocks = 0
        start = time.time()
        with open(filename, 'wb') as handle:
            print(str(round(done / 1024 / 1024, 1)) + "M ", flush=True, end='')
            for block in response.iter_content(chunksize):

                handle.write(block)

                # Space separator
                if blocks % 8 == 0 and blocks > 0:
                    print(" ", end='', flush=True)

                # New line
                if blocks % 48 == 0 and blocks > 0:
                    remain = 0

                    print("{:.2%}".format(done / file_size))
                    print(str(round(done / 1024 / 1024, 1)) + "M ", flush=True, end='')

                blocks += 1
                print('.', end='', flush=True)

                done += chunksize

        end = (time.time() - start) * 1000
        print("Elapsed time : " + str(round(end)) + " seconds")

    def deleteFile(self, file_id):
        """
        Deletes a file

        :param file_id: Id of the file to delete

        """

        print("Deleting file #" + file_id)

        data = {
            "selected[]": file_id,
            "remove": 1,
        }
        result = self.session.post(self.base_url + "/console/remove.pl", data)

        pass

    def moveFile(self, file_id, dir_id):
        """
        Moves a file to a another directory

        :param file_id: File id to move
        :param dir_id: Target directory id

        :return:
        """

        print("Moving file #" + file_id + " to directory #" + dir_id)

        data = {
            "dragged[]": file_id,
            "dragged_type": 2,
            "dropped_dir": dir_id,
        }
        result = self.session.post(self.base_url + "/console/op.pl", data)

        pass

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

        res = self.session.get(self.base_url + "/console/dirs.pl?dir_id=" + str(dir_id))
        # print(res.content.decode("utf-8"))

        # Htmlify the result
        soup = BeautifulSoup("<html><body>" + res.content.decode("utf-8") + "</body></html>", "html.parser")
        lis = soup.findAll("li")

        for li in lis:

            div = li.find("div")
            name = div.get_text().split(u"\xa0")[0]
            hasChildren = div.find("div", {"class": "fcp"}) is not None
            rel = li.attrs["rel"]

            # print("Found directory " + rel + ":\"" + name + "\"")

            self.Directories[rel] = \
            {
                "name": name,
                "parent": dir_id,
            }

            # Find the sub directories
            # if (int(rel) != dir_id and hasChildren):
            if (hasChildren):
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
        result = self.session.post(self.base_url + "/console/mkdir.pl", data)

        # Update directory list
        f = self.getDirectories(dir_id)

        # Find it...
        for ref, data in f.items():
            if data["name"] == name and ref == dir_id:
                return ref

        return None

one = OneFichier()

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

        # Download file
        one.downloadFile(file)

        # Backup the file
        one.moveFile(file_id, done_id)
    # Some delay
    print("Going to sleep...")
    time.sleep(int(one.config["delay"]))