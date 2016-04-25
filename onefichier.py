#!/usr/bin/env python3


# import time
from time import sleep
import json
import os.path
import re
import requests
from bs4 import BeautifulSoup

from pprint import pprint

class OneFichier():
    base_url = "https://1fichier.com"


    def __init__(self, config_file = "./config.json"):
        """

        :param config_file: Json config file name
        """

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
        # print(result.content.decode("utf-8"))

        print("Getting Directories list")
        self.getDirectories()


        print("Done !")
        pass


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

        :param data:
        :param path:
        :return:
        """

        # Oops, some infos are missing !!
        if data is None or data["name"] is None or data["url"] is None:
            return

        # File already downloaded
        path = path if None else self.config["download_path"]
        filename = os.path.abspath(os.path.join(path, data["name"]))
        # print(filename)
        if os.path.isfile(filename):
            print("File \"" + data["name"] + "\" already downloaded. Skipping !")
            return

        # Open the url
        print("Processing file \"" + data["name"] + "\"...")
        response = self.session.post(data["url"])
        if not response.ok:
            print("Failed to get http data !")
            return

        # Download the stream
        headers = response.headers
        done = 0
        chunksize = 4096 * 16
        start = time.time()
        with open(filename, 'wb') as handle:
            # print("File opened")
            for block in response.iter_content(chunksize):
                # done += chunksize
                # self.printProgress(done, headers["content-length"], "Progress:", "Complete", 100)
                # percent = int(round(done / float(headers["content-length"]) * 100))
                # print(str(done) + " / " + headers["content-length"] + " : "+ str(percent) + "%", flush=True)
                # sys.stdout.flush()
                handle.write(block)

        end = (time.time() - start) * 1000
        print("Elapsed time : " + str(round(end)) + " seconds")

        pass


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
    sleep(int(one.config["delay"]))