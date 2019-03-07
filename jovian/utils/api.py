from requests import get, post
# from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from os.path import basename
from time import sleep
# from tqdm import tqdm, tqdm_notebook
from jovian.utils.credentials import read_or_request_key, write_key, CREDS, request_key
from jovian.utils.logger import log
from jovian.utils.jupyter import in_notebook, save_notebook, get_notebook_name
from jovian.utils.constants import API_URL
from jovian._version import __version__


class ApiError(Exception):
    """Error class for web API related Exceptions"""
    pass


def _u(path):
    """Make a URL from the path"""
    return API_URL + path


def _msg(res):
    try:
        data = res.json()
        if 'errors' in data and len(data['errors'] > 0):
            return data['errors'][0]['message']
        if 'message' in data:
            return data['message']
        if 'msg' in data:
            return data['msg']
    except:
        if res.text:
            return res.text
        return 'Something went wrong'


def _pretty(res):
    """Make a human readable output from an HTML response"""
    return '(HTTP ' + str(res.status_code) + ') ' + _msg(res)


def validate_key(key):
    """Validate the API key by making a request to server"""
    res = get(_u('/user/profile'),
              headers={'Authorization': 'Bearer ' + key})
    if res.status_code == 200:
        return True
    else:
        return False
    raise ApiError(_pretty(res))


def get_key():
    """Retrieve and validate the API Key (from memory, config or user input)"""
    if 'API_KEY' not in CREDS:
        key, source = read_or_request_key()
        if not validate_key(key):
            log('The current API key is invalid or expired.', error=True)
            key, source = request_key(), 'request'
            if not validate_key(key):
                raise ApiError('The API key provided is invalid or expired.')
        write_key(key, source == 'request')
    return CREDS['API_KEY']


def _h():
    """Create authorizaiton header with API key"""
    return {"Authorization": "Bearer " + get_key(),
            "x-jovian-source": "library",
            "x-jovian-library-version": __version__}


# def _create_callback(encoder):
#     """Create a callback to a progress bar for file uploads"""
#     if in_notebook():
#         pbar = tqdm_notebook(total=encoder.len)
#     else:
#         pbar = tqdm(total=encoder.len)

#     def callback(monitor):
#         pbar.update(monitor.bytes_read - pbar.n)
#         if (monitor.bytes_read == pbar.total):
#             pbar.close()

#     return callback

FILENAME_MSG = 'Failed to detect notebook filename. Please provide the notebook filename (including .ipynb extension) as the "filename" argument to "jovian.commit".'


def create_gist_simple(filename=None):
    """Upload the current notebook to create a gist"""
    if not in_notebook():
        log('Failed to detect Juptyer notebook. Skipping..', error=True)
        return
    auth_headers = _h()
    log('Saving notebook..')
    save_notebook()
    sleep(1)
    if filename is None:
        path = get_notebook_name()
        if path is None:
            log(FILENAME_MSG)
            raise ApiError('File upload failed: ' + FILENAME_MSG)
    else:
        path = filename
    nb_file = (basename(path), open(path, 'rb'))
    log('Uploading notebook..')
    res = post(url=_u('/gist/create'),
               data={'public': 1},
               files={'files': nb_file},
               headers=auth_headers)
    if res.status_code == 200:
        return res.json()['data']
    raise ApiError('File upload failed: ' + _pretty(res))


def upload_file(gist_slug, file):
    """Upload an additional file to a gist"""
    if type(file) == str:
        file = (basename(file), open('file', 'rb'))
    res = post(url=_u('/gist/' + gist_slug + '/upload'),
               files={'files': file}, headers=_h())
    if res.status_code == 200:
        return res.json()['data']
    raise ApiError('File upload failed: ' + _pretty(res))
