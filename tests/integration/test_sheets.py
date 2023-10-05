from pytest import fixture
from oauth2client.service_account import ServiceAccountCredentials
import requests


TEST_SHEET_ID = "1n5yFNS60aVnkpOYnvUcY7GOW4LOmm8AqFh6dXqHqNXQ"
TEST_SHEET_ID_Q = '160yKvcQ-muiFLNrJUiA-u3v-uqjlBEyJi6Z0RDdgKUM'
TEST_EXTERNAL_SHEET_ID = "1m3TX7IwUKOoscnCJi6TwliEbyG4qwBUdpxpDqoI9h3A"
TEST_EXTERNAL_SHEET_RESULTS_NAME = "TG-RESULTS"


@fixture(scope="module")
def credentials():
    CREDENTIALS_FILE = 'credentials_sa.json'

    result = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE,
        ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive']
    )
    return result


def test_sheet_query(credentials):
    access_token_info = credentials.get_access_token()
    access_token = access_token_info.access_token

    spreadsheet_id = TEST_SHEET_ID_Q
    sheet_name = 'Results'

    query = 'select A,E where D=2'
    url = 'https://docs.google.com/spreadsheets/d/' + spreadsheet_id + \
        '/gviz/tq?sheet=' + sheet_name + '&tqx=out:csv&tq=' + query
    res = requests.get(
        url, headers={'Authorization': 'Bearer ' + access_token})
    print("round 2 results: \n" + res.text)


def test_external_sheet_query(credentials):
    access_token_info = credentials.get_access_token()
    access_token = access_token_info.access_token

    spreadsheet_id = TEST_EXTERNAL_SHEET_ID
    sheet_name = TEST_EXTERNAL_SHEET_RESULTS_NAME

    query = 'select A,C,D,E,F where B=1'
    url = 'https://docs.google.com/spreadsheets/d/' + spreadsheet_id + \
        '/gviz/tq?sheet=' + sheet_name + '&tqx=out:csv&tq=' + query
    res = requests.get(
        url, headers={'Authorization': 'Bearer ' + access_token})
    print("round 2 results: \n" + res.text)