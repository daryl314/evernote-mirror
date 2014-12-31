# imports
import os
import json
import hashlib
import binascii
import evernote_link
import evernote.edam.error.ttypes as Errors

# return True if a hashed file already exists.  this can happen if a sync
# fails due to API throttling limitations
def hashedFileExists(file, h):
    if not os.path.isfile(file):
        return False
    else:
        return h == hashlib.md5(open(file, 'rb').read()).hexdigest()

# function to convert nested objects in Evernote metadata to dicts that can be
# exported to JSON
def to_dict(x):
    if type(x) is dict:
        for k,v in x.items():
            x[k] = to_dict(v)
    elif type(x) is list:
        x = [ to_dict(a) for a in x ]
    elif type(x) is set:
        x = to_dict(list(x))
    elif type(x) is bytes:
        x = binascii.hexlify(x).decode('ascii')
    elif hasattr(x, '__dict__'):
        x = to_dict( x.__dict__ )
    return x

###############################################################################
# Class to maintain a local archive of Evernote data
###############################################################################

class EvernoteSync(evernote_link.EvernoteLink):

    # initialization
    def __init__(this, token, folder, **kwargs):
        super().__init__(token, **kwargs)
        this.folder = folder
        this.metaFile = os.path.join(folder, 'metadata.js')
        this._makeFolders()
        this._loadMetadata()

    # convert metadata to a dict representation
    def syncMetadata(this):
        super().syncMetadata()
        this.metadata = to_dict(this.metadata)

    # synchronize note data - only fetch dirty notes (in_sync == False)
    def syncNotes(this):
        noteData = this.metadata['notes'].values()
        for guid in [ n['guid'] for n in noteData ]:
            note = this._fetchNoteFile(guid)
            if not note.get('in_sync', False):
                for res in note['resources'] or []:
                    this._fetchResourceFile(res)
            note['in_sync'] = True

    # notify if throttling limit is reached while fetching note
    def fetchNote(this, guid, silent=False):
        try:
            return super().fetchNote(guid, silent)
        except Errors.EDAMSystemException as e:
            if e.errorCode == Errors.EDAMErrorCode.RATE_LIMIT_REACHED:
                print("Rate limit reached")
                print("Retry your request in %d seconds" % e.rateLimitDuration)
                raise

    # notify user if throttling limit is reached while fetching resource
    def fetchResource(this, guid, silent=False):
        try:
            return super().fetchResource(guid, silent)
        except Errors.EDAMSystemException as e:
            if e.errorCode == Errors.EDAMErrorCode.RATE_LIMIT_REACHED:
                print("Rate limit reached")
                print("Retry your request in %d seconds" % e.rateLimitDuration)
                raise

    # purge deleted notes and files
    def purge(this):
        this._purgeNotes()
        this._purgeFiles()

    # synchronize everything
    def sync(this):
        this.syncMetadata()     # synchronize metadata
        this._saveMetadata()    # save metadata in case note sync fails
        this.syncNotes()        # synchronize notes
        this.purge()            # purge deleted notes and resources
        this._saveMetadata()    # save metadata

    # ========== PRIVATE METHODS BELOW ==========

    # create output directory structure (if it doesn't already exist)
    def _makeFolders(this):
        os.makedirs(this.folder, exist_ok=True)
        os.makedirs(os.path.join(this.folder,'notes'), exist_ok=True)
        os.makedirs(os.path.join(this.folder,'files'), exist_ok=True)

    # load metadata file if it exists.  use try block so that corrupted
    # metadata files are re-generated gracefully
    def _loadMetadata(this):
        if os.path.isfile(this.metaFile):
            with open(this.metaFile) as handle:
                try:
                    this.metadata = json.load(handle)
                except:
                    print("Corrupted metadata file - regenerating")

    # save metadata file
    def _saveMetadata(this):
        if this.metaUpdated:
            with open(this.metaFile, 'w') as handle:
                json.dump(this.metadata, handle)

    # fetch a note file if it doesn't already exist in the cache
    def _fetchNoteFile(this, guid):
        outFile = os.path.join(this.folder, 'notes', guid)
        note = this.metadata['notes'][guid]
        if not hashedFileExists(outFile, note['contentHash']):
            noteData = this.fetchNote(guid, silent=True)
            if os.path.isfile(outFile):
                this._report("Updating note: " + outFile)
            else:
                this._report("Saving note: " + outFile)
            with open(outFile, 'w') as handle:
                handle.writelines(noteData.content)
        return note

    # fetch a resource if it doesn't already exist in the cache
    def _fetchResourceFile(this, res):
        outFile = os.path.join(this.folder, 'files', res['guid'])
        if not hashedFileExists(outFile, res['data']['bodyHash']):
            resData = this.fetchResource(res['guid'], silent=True)
            if os.path.isfile(outFile):
                this._report("Updating file: " + outFile)
            else:
                this._report("Saving file: " + outFile)
            with open(outFile, 'wb') as file:
                file.write(resData)

    # remove deleted notes
    def _purgeNotes(this):
        existingNotes = set(os.listdir(os.path.join(this.folder, 'notes')))
        oldNotes = existingNotes - set(this.metadata['notes'].keys())
        for n in list(oldNotes):
            this._report("Deleting note: " + n)
            os.remove(os.path.join(this.folder, 'notes', n))

    # remove deleted resources
    def _purgeFiles(this):
        existingFiles = set(os.listdir(os.path.join(this.folder, 'files')))
        guids = [
                [r['guid'] for r in x['resources']]
                for x in this.metadata['notes'].values()
                if x['resources'] is not None
                ]
        oldFiles = existingFiles - { item for sublist in guids for item in sublist }
        for f in list(oldFiles):
            this._report("Deleting file: " + f)
            os.remove(os.path.join(this.folder, 'files', f))
