# OneDownloader

Automatic file downloader on 1fichier.com

## Requirements

* *Python3*:
 `sudo apt-get install python3`

* *pip*:
 `wget https://bootstrap.pypa.io/get-pip.py`
 `sudo python3 get-pip.py`

* *Requests*:
 `sudo pip install requests`

* *Beautiful Soup*:
 `sudo pip install beautifulsoup4`

## Usage

####Installation :
This will install onefichier.py to /usr/share/ and make a symbolic link to /usr/bin/
```
sudo make install
```

####Init :
This will create `~/.onefichier/config.json` file which contains all needed parameters
```
onefichier --init
```

####Run :

```
onefichier
```

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
