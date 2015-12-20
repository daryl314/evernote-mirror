# Installation

Installing Evernote API:
```
cd evernote
sudo python2 setup.py install
```

Upgrading Evernote API:
```
git submodule update
cd evernote
sudo python2 setup.py install
```

Creating a new configuration file (config.yaml):
```
---
development_mode: false
outFolder: /home/daryl/Documents/Evernote
production:
  authToken: PRODUCTION_TOKEN_GOES_HERE
development:
  authToken: DEVELOPMENT_TOKEN_GOES_HERE
```

# Usage

Install Evernote API, create a configuration file, and run `sync.py`
