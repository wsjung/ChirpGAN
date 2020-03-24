from __future__ import print_function
import pickle
import os.path
from os import getcwd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient import errors
from io import FileIO, BytesIO
from googleapiclient.http import MediaIoBaseDownload


# If modifying these scopes, delete the file token.pickle.
# SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def retrieve_all_files(service):
  """Retrieve a list of wav files.

  Args:
    service: Drive API service instance.
  Returns:
    List of File resources.
  """
  result = []
  page_token = None

  while True:
    response = service.files().list(
        #   q="mimeType='audio/x-wav'",
          q="not name contains 'T0' and not name contains 'Blank' and mimeType='audio/x-wav'",
          pageSize=100, 
          fields="nextPageToken, files(id, name)", 
          pageToken=page_token).execute()

    f = response.get('files', [])
    result.extend(f)
    # print(len(result))

    page_token = response.get('nextPageToken', None)
    if page_token is None:
        break

  return result



def download_all_files(service, ids, names, dir):
    """Downloads all files specified by id 

    Args:
        service: Drive API service insetance
        ids: list of ids corresponding to files to download
        dir: directory to download files to
    Returns:
        Downloads all files to specified directory
    """
    
    # check if specified directory exists
    # if not, create it
    path = os.path.join(getcwd(), dir)
    if not os.path.isdir(path):
        print('creating directory %s' % path)
        os.mkdir(path)


    # directory must exist
    assert os.path.isdir(path)

    # length of ids and names is equal
    assert len(ids) == len(names) 
    length = len(ids)
    i = 1

    for id,name in zip(ids,names):
        request = service.files().get_media(fileId=id)

        fh = FileIO(os.path.join(path,name), mode='wb')

        downloader = MediaIoBaseDownload(fh, request)

        print('downloading file %d/%d' % (i,length))

        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))
            i+=1



def main():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    files = retrieve_all_files(service)

    print('### SEARCH COMPLETE ###\nFound %d wav files' % len(files))
    
    print(files)

    ids = [file['id'] for file in files]
    names = [file['name'] for file in files]

    # print(ids)
    # print(names)

    download_all_files(service, ids, names, "dlwavfiles")



if __name__ == '__main__':
    main()