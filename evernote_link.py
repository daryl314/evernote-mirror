# imports
import requests

# confirm that Evernote SDK is installed properly
try:
    from evernote.api.client import EvernoteClient
    import evernote
except:
    raise ImportError('Evernote not installed - please read README.md')

###############################################################################
# Class for connecting to Evernote
###############################################################################

class EvernoteLink:

    # initialization
    def __init__(this, token, blockSize=100, verbose=True, devMode=True):
        this.token = token
        this.blockSize = blockSize
        this.verbose = verbose
        this.devMode = devMode
        this.chunkFilter = this._defaultChunkFilter()
        this.reset()
        this.metaUpdated = False

    # connection method
    def connect(this):
        this.client = EvernoteClient(token=this.token, sandbox=this.devMode)
        this.userStore = this.client.get_user_store()
        this.noteStore = this.client.get_note_store()
        this.user = this.userStore.getUser()
        this.userInfo = this.userStore.getPublicUserInfo(this.user.username)

    # method to reset metadata
    def reset(this):
        this.metadata = {
            'notes':          {},
            'notebooks':      {},
            'tags':           {},
            'lastSyncCount':  0,
            'lastSyncTime':   0
        }

    # method to synchronize metadata
    def syncMetadata(this):

        # check synchronization state
        syncState = this.noteStore.getSyncState(this.token)
        if syncState.fullSyncBefore > this.metadata['lastSyncTime']:
            this.reset()

        # perform synchronization
        if syncState.updateCount == this.metadata['lastSyncCount']:
            this._report("No new data")
        else:
            this._fetchData()
            this.metadata['lastSyncTime'] = syncState.currentTime

    # method to fetch a note
    def fetchNote(this, guid):
        return this.noteStore.getNote(
              this.token, # authorization token
              guid,       # note guid
              True,       # include note contents
              False,      # exclude resource binary contents
              False,      # exclude resource recognition data
              False       # exclude resource alternate binary contents
        )

    # method to fetch a resource
    def fetchResource(this, guid):
        this._report("Fetching resource: " + guid)
        url = "%s/res/%s" % (this.userInfo.webApiUrlPrefix, guid)
        req = requests.post(url, {'auth':this.token})
        return req.content

    # ========== PRIVATE METHODS BELOW ==========

    # send text to console
    def _report(this, message):
        if this.verbose:
            print(message)

    # method to return a default chunk filter:
    # FullMap data isn't included in settings, and note content class is unset
    # to return all types of notes.  Everything else is explicitly set below.
    def _defaultChunkFilter(this):
        cf = evernote.edam.notestore.ttypes.SyncChunkFilter()
        cf.includeNotes           = True    # include note data (w/ resources)
        cf.includeNoteResources   = True    # include note resource data
        cf.includeNotebooks       = True    # include notebook data
        cf.includeTags            = True    # include tag data
        cf.includeNoteAttributes  = False   # exclude note attribute data
        cf.includeSearches        = False   # exclude saved search data
        cf.includeResources       = False   # don't download resource data
        cf.includeLinkedNotebooks = False   # exclude linked notebooks
        cf.includeExpunged        = False   # exclude expunged data
        return cf

    # method to fetch sync data starting from a given USN and update metadata
    def _fetchData(this, afterUSN=0):
        this._report("Fetching data starting from afterUSN=" + str(afterUSN))
        s = this.noteStore.getFilteredSyncChunk(
            this.token, afterUSN, this.blockSize, this.chunkFilter)

        # update metadata for notebooks, tags, and notes
        for n in s.notebooks or []:
            this.metadata['notebooks'][n.guid] = n.name
        for t in s.tags or []:
            this.metadata['tags'][t.guid] = t
        for n in s.notes or []:
            if n.active:
                this.metadata['notes'][n.guid] = n
            elif n.guid in this.metadata['notes']:
                del this.metadata['notes'][n.guid]

        # advance sync counter and fetch more data if required
        this.metadata['lastSyncCount'] = s.updateCount
        this.metaUpdated = True
        if s.chunkHighUSN < s.updateCount:
            this._fetchData(s.chunkHighUSN)
