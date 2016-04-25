# OneDownloader

Automatic file downloader on 1fichier.com

## Installation

Python3 => sudo apt-get install python3

pip =>
 wget https://bootstrap.pypa.io/get-pip.py
 sudo python3 get-pip.py

Requests => sudo pip install requests

Beautiful Soup => sudo pip install beautifulsoup4

## Usage

Configure config.json file :
```javascript
{
    "email": "email@example.com",		  // email login
    "password": "MySuperPassword",		 // Ultra secret password
    "download_path": "./",			       	// Where to store downloaded file on your computer
    "directory": "autodownload",		   // Directory to watch on 1fichier.com
    "done": "done",				            		// Directory name in the watch directory where to move downloaded files
    "delay": 300					               	// Time to sleep before next looking for new file to download
}```

Run the script :
`python3 onefichier.py`

## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D


## Credits

any comment to iliak@mimicprod.net

## License

GNU GENERAL PUBLIC LICENSE V3
