#!/usr/bin/python3
# -*- coding: utf-8 -*-


import time
import json
import os.path
import re
import requests
from bs4 import BeautifulSoup
import getopt
import sys
import getpass


class OneFichier():
    BASE_URL = "https://1fichier.com"
    CONFIG_PATH = ".config/onefichier/"
    CONFIG_FILE = "config.json"

    def __init__(self, config_file=None):
        """

        :param config_file: Json config file name
        """

        path = os.path.join(os.path.expanduser("~"), OneFichier.CONFIG_PATH)
        if config_file is None:
            config_file = os.path.join(os.path.join(path, self.CONFIG_FILE))

        # Config file exists ?
        if not os.path.isfile(config_file):
            print("Config file not found in " + config_file)
            sys.exit("Please run with --init parameter")

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

    @staticmethod
    def makeconf():
        print("make config file...")

        # Create the path in home directory
        path = os.path.join(os.path.expanduser("~"), OneFichier.CONFIG_PATH)
        if not os.path.exists(path):
            os.makedirs(path)
            os.chmod(path, 0o700)

        data = dict()
        data["email"] = input("What is your login: ")
        data["password"] = getpass.getpass("Whate is your password: ")
        data["download_path"] = input("What is the local absolute where to download files: ")
        data["directory"] = input("What is the name of the folder on 1fichier to watch: ")
        data["done"] = input("What is the name of the folder where to move downloaded files: ")
        data["delay"] = input("Seconds to sleep before looking for new file to download [300]: ")

        if data["delay"] == "":
            data["delay"] = 300

        # Save the file
        file = os.path.join(path, OneFichier.CONFIG_FILE)
        with open(file, "w") as outfile:
            json.dump(data, outfile, sort_keys=True, indent=3, separators=(',', ': '))

        # Protect the file
        os.chmod(file, 0o600)

        sys.exit()

    def login(self, lt="on", restrict="off", purge="off"):
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

        result = self.session.post(self.BASE_URL + "/login.pl", data)


        # Update directories
        self.getDirectories()

    def logout(self):

        self.session.get(self.BASE_URL + "/logout.pl")
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

        print(data["name"])

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
            print("Resuming download...")
            headers = {'Range': 'bytes=%d-' % os.path.getsize(filename)}

        # Requesting the file
        response = self.session.get(url, headers=headers, stream=True)
        if not response.ok:

            # File fully downloaded
            if response.status_code == 416:
                print("File already downloaded, skipping...")

            # Global error...
            else:
                print("Global error (HTTP status code: " + str(response.status_code) + ") !")

            return

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
        print("File size : " + str(file_size) + " bytes (" + str(round(file_size / 1024 / 1024, 2)) + "M)")

        done = openpos          # bytes already downloaded
        chunksize = 4096 * 16   # size of the stream
        blocks = 0              # number of blocks already downloaded
        start = time.time()     # Total elapsed time
        with open(filename, openmode) as handle:

            # resume mode ?
            if openpos > 0:
                handle.seek(openpos)

            print(str(round(done / 1024 / 1024, 1)) + "M ", flush=True, end='')
            for block in response.iter_content(chunksize):

                handle.write(block)

                # Space separator
                if blocks % 8 == 0 and blocks > 0:
                    print(" ", end='', flush=True)

                # New line
                if blocks % 80 == 0 and blocks > 0:
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
        result = self.session.post(self.BASE_URL + "/console/remove.pl", data)

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
        result = self.session.post(self.BASE_URL + "/console/op.pl", data)

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

        res = self.session.get(self.BASE_URL + "/console/dirs.pl?dir_id=" + str(dir_id))
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
        result = self.session.post(self.BASE_URL + "/console/mkdir.pl", data)

        # Update directory list
        f = self.getDirectories(dir_id)

        # Find it...
        for ref, data in f.items():
            if data["name"] == name and ref == dir_id:
                return ref

        return None


def main(argv):

    # Read arguments
    try:
        opts, args = getopt.getopt(argv, "i", ["init"])
    except getopt.GetoptError:
        print("onefichier --help")
        sys.exit(2)

    for opt, args in opts:
        if opt in ('-i', '--init'):
            OneFichier.makeconf()

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
            # Then make it
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

if __name__ == "__main__":
    main(sys.argv[1:])
