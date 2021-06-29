# import _thread
import eventlet
from eventlet import tpool
import socketio
from python.libs import iEEG
from python.libs.iEEG import ReadError, WriteError, metadata as metadata_fields
from python.libs.Modifier import Modifier
from python.libs import BIDS
from python.libs.loris_api import LorisAPI
import csv
import datetime

# EEG2BIDS Wizard version
appVersion = '1.0.1'

# LORIS credentials of user
lorisCredentials = {
    'lorisURL': '',
    'lorisUsername': '',
    'lorisPassword': '',
}

# Create socket listener.
sio = socketio.Server(async_mode='eventlet', cors_allowed_origins=[])
app = socketio.WSGIApp(sio)

# Create Loris API handler.
loris_api = LorisAPI()


@sio.event
def connect(sid, environ):
    print('connect: ', sid)
    if environ['REMOTE_ADDR'] != '127.0.0.1':
        return False  # extra precaution.


def tarfile_bids_thread(data):
    iEEG.TarFile(data)
    response = {
        'compression_time': 'example_5mins'
    }
    return eventlet.tpool.Proxy(response)


@sio.event
def tarfile_bids(sid, data):
    # data = { bids_directory: '../path/to/bids/output', output_time: 'bids output time' }
    response = eventlet.tpool.execute(tarfile_bids_thread, data)
    send = {
        'compression_time': response['compression_time']
    }
    sio.emit('response', send)


@sio.event
def set_loris_credentials(sid, data):
    loris_credentials = data
    if 'lorisURL' not in loris_credentials:
        print('error with credentials:', data)
        return

    if loris_credentials['lorisURL'].endswith('/'):
        loris_credentials['lorisURL'] = loris_credentials['lorisURL'][:-1]
    loris_api.url = loris_credentials['lorisURL'] + '/api/v0.0.4-dev/'
    loris_api.username = loris_credentials['lorisUsername']
    loris_api.password = loris_credentials['lorisPassword']
    loris_api.login()

    if loris_api.token:
        sio.emit('loris_login_response', {
            'success': 200,
            'lorisUsername': loris_api.username
        })
    else:
        sio.emit('loris_login_response', {'error': "Can't login to the LORIS instance."})

    sio.emit('loris_sites', loris_api.get_sites())
    sio.emit('loris_projects', loris_api.get_projects())


def get_loris_sites(sid):
    sio.emit('loris_sites', loris_api.get_sites())


@sio.event
def get_loris_projects(sid):
    sio.emit('loris_projects', loris_api.get_projects())


@sio.event
def get_loris_subprojects(sid, project):
    sio.emit('loris_subprojects', loris_api.get_subprojects(project))


@sio.event
def get_loris_visits(sid, subproject):
    sio.emit('loris_visits', loris_api.get_visits(subproject))


@sio.event
def create_candidate_and_visit(sid, data):
    new_candidate = loris_api.create_candidate(
        data['project'],
        data['dob'],
        data['sex'],
        data['site'],
    )

    if new_candidate['CandID']:
        loris_api.create_visit(new_candidate['CandID'], data['visit'], data['site'], data['project'],
                               data['subproject'])
        loris_api.start_next_stage(new_candidate['CandID'], data['visit'], data['site'], data['subproject'],
                                   data['project'], data['date'])
        print('new_candidate_created')
        sio.emit('new_candidate_created', {'PSCID': new_candidate['PSCID']})


@sio.event
def get_edf_data(sid, data):
    # data = { files: 'EDF files (array of {path, name})' }
    print('get_edf_data:', data)

    if 'files' not in data or not data['files']:
        msg = 'No EDF file selected.'
        print(msg)
        response = {'error': msg}
        sio.emit('edf_data', response)
        return

    headers = []
    try:
        for file in data['files']:
            anonymize = iEEG.Anonymize(file['path'])
            metadata = anonymize.get_header()
            year = '20' + str(metadata[0]['year']) if metadata[0]['year'] < 85 else '19' + str(metadata[0]['year'])
            date = datetime.datetime(int(year), metadata[0]['month'], metadata[0]['day'], metadata[0]['hour'],
                                     metadata[0]['minute'], metadata[0]['second'])

            headers.append({
                'file': file,
                'metadata': metadata,
                'date': str(date)
            })

        for i in range(1, len(headers)):
            if set(headers[i - 1]['metadata'][1]['ch_names']) != set(headers[i]['metadata'][1]['ch_names']):
                msg = 'The files selected contain more than one recording.'
                print(msg)
                response = {
                    'error': msg,
                }
                sio.emit('edf_data', response)
                return

        # sort the recording per date
        headers = sorted(headers, key=lambda k: k['date'])

        # return the first split metadata and date
        response = {
            'files': [header['file'] for header in headers],
            'subjectID': headers[0]['metadata'][0]['subject_id'],
            'recordingID': headers[0]['metadata'][0]['recording_id'],
            'date': headers[0]['date']
        }

    except ReadError as e:
        print(e)
        response = {
            'error': 'Cannot read file - ' + str(e)
        }
    except Exception as e:
        print(e)
        response = {
            'error': 'Failed to retrieve EDF header information',
        }
    sio.emit('edf_data', response)


@sio.event
def get_bids_metadata(sid, data):
    # data = { file_path: 'path to metadata file' }
    print('data:', data)

    if 'file_path' not in data or not data['file_path']:
        msg = 'No metadata file selected.'
        print(msg)
        response = {'error': msg}
    elif 'modality' not in data or data['modality'] not in ['ieeg', 'eeg']:
        msg = 'No valid modality found.'
        print(msg)
        response = {'error': msg}
    else:
        try:
            with open(data['file_path']) as fd:
                reader = csv.DictReader(fd, delimiter="\t", quotechar='"')
                try:
                    metadata = {rows['Field']: rows['Value'] for rows in reader}
                    diff = list(set(metadata.keys()) - set(metadata_fields[data['modality']].keys()))
                    response = {
                        'metadata': metadata,
                        'invalid_keys': diff,
                    }
                except KeyError:
                    metadata = {}
                    response = {
                        'error': 'Metadata file format is not valid.',
                    }
        except IOError:
            msg = "Could not read the metadata file."
            print(msg)
            response = {
                'error': msg,
            }

    sio.emit('bids_metadata', response)


def edf_to_bids_thread(data):
    print('data is ')
    print(data)
    error_messages = []
    if 'edfData' not in data or 'files' not in data['edfData'] or not data['edfData']['files']:
        error_messages.append('No .edf file(s) to convert.')
    if 'bids_directory' not in data or not data['bids_directory']:
        error_messages.append('The BIDS output directory is missing.')
    if not data['session']:
        error_messages.append('The LORIS Visit Label is missing.')

    if not error_messages:
        time = iEEG.Time()
        data['output_time'] = 'output-' + time.latest_output

        try:
            iEEG.Converter(data)  # EDF to BIDS format.

            # store subject_id for Modifier
            data['subject_id'] = iEEG.Converter.m_info['subject_id']
            data['appVersion'] = appVersion
            Modifier(data)  # Modifies data of BIDS format
            response = {
                'output_time': data['output_time']
            }
            return eventlet.tpool.Proxy(response)
        except ReadError as e:
            error_messages.append('Cannot read file - ' + str(e))
        except WriteError as e:
            error_messages.append('Cannot write file - ' + str(e))
    else:
        response = {
            'error': error_messages
        }
    return eventlet.tpool.Proxy(response)


@sio.event
def edf_to_bids(sid, data):
    # data = { file_paths: [], bids_directory: '', read_only: false,
    # events_tsv: '', line_freq: '', site_id: '', project_id: '',
    # sub_project_id: '', session: '', subject_id: ''}
    print('edf_to_bids: ', data)
    response = eventlet.tpool.execute(edf_to_bids_thread, data)
    print(response)
    print('Response received!')
    sio.emit('bids', response.copy())


@sio.event
def validate_bids(sid, data):
    # data = { bids_directory: '../path/to/bids/output', output_time: 'bids output time' }
    print('validate_bids: ', data)
    error_messages = []
    if 'bids_directory' not in data or not data['bids_directory']:
        error_messages.append('The BIDS output directory is missing.')
    if 'output_time' not in data or not data['output_time']:
        error_messages.append('The BIDS format is missing.')
    if not error_messages:
        BIDS.Validate(data)
        response = {
            'file_paths': BIDS.Validate.file_paths,
            'result': BIDS.Validate.result
        }
    else:
        response = {
            'error': error_messages
        }
    sio.emit('response', response)


@sio.event
def disconnect(sid):
    print('disconnect: ', sid)


if __name__ == '__main__':
    eventlet.wsgi.server(
        eventlet.listen(('127.0.0.1', 7301)),
        app,
        log_output=True
    )