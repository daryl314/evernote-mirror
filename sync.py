#!/usr/bin/env python

# imports
import evernote_sync
import yaml

# load configuration data from yaml configuration file
with open('config.yaml') as handle:
    config = yaml.load(handle)

# authorization token and user store URL (based on dev/prod mode)
if config['development_mode']:
    token = config['development']['authToken']
else:
    token = config['production']['authToken']

# connect to Evernote
e = evernote_sync.EvernoteSync(
    token, config['outFolder'], devMode=config['development_mode'])
e.connect()

# synchronize data
e.sync()
