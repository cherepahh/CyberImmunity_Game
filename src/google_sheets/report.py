import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from os import getenv
import logging
import requests
import json

load_dotenv()  # take environment variables from .env.

CREDENTIALS_FILE = getenv("CREDENTIALS_FILE")
SHARE_REPORT_WITH = getenv("SHARE_REPORT_WITH")


class GoogleSheetsIntegration:
    def __init__(self, credentials=CREDENTIALS_FILE) -> None:
        self._creds = ServiceAccountCredentials.from_json_keyfile_name(
            credentials, ['https://www.googleapis.com/auth/spreadsheets',
                          'https://www.googleapis.com/auth/drive'])

        self._auth = self._creds.authorize(
            httplib2.Http())

        self._sheets_service = apiclient.discovery.build(
            'sheets', 'v4', http=self._auth)
        self._drive_service = apiclient.discovery.build(
            'drive', 'v3', http=self._auth)

        self._spreadsheet_id = None
        self._details_sheets = {}
        self._rows_rounds = [0, 0, 0]
        self._max_players = 500

    def set_spreadsheet_id(self, s_id: str) -> None:
        self._spreadsheet_id = s_id

    def get_spreadsheet_id(self) -> str:
        return self._spreadsheet_id

    def create_game_details_sheet(self, game_id):
        result = self._sheets_service.spreadsheets().create(body={
            'properties': {'title': f'Game {game_id}', 'locale': 'ru_RU'},
            'sheets': [{'properties': {'sheetType': 'GRID',
                                       'sheetId': 0,
                                       'title': 'Moves',
                                       'gridProperties': {'rowCount': self._max_players, 'columnCount': 5}}}]
        }).execute()

        self._spreadsheet_id = result["spreadsheetId"]

        # update header row
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": "Moves!A:E",
                 "majorDimension": "ROWS",
                 "values": [
                    ["ChatId", "Role", "Name", "TurnNo", "Choice"],
                 ]}
            ]
        }

        self._sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=self._spreadsheet_id, body=body).execute()

        self._sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=self._spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": "Results",
                                "gridProperties": {
                                    "rowCount": 500,
                                    "columnCount": 500
                                }
                            }
                        }
                    }
                ]
            }).execute()

        admin_emails = SHARE_REPORT_WITH.split(",")
        self._share_spreadsheet(user_emails=admin_emails)

        return self._spreadsheet_id

    def reset_game_data(self):
        range_all = 'Moves!A2:Z'
        body = {}
        self._sheets_service.spreadsheets().values().clear(
            spreadsheetId=self._spreadsheet_id, range=range_all,
            body=body
        ).execute()
        # TODO: also reset results sheet

    def update_game_results(self, game_id, round_num, results):
        logging.debug(
            f"trying to update google sheet with {results} of game with id {game_id}")

        self._rows_rounds[round_num-1] = len(results)
        # update starting from the first empty row, exclude table header, so the first empty row is #2
        offset = 2
        for i in range(0, round_num-1):
            offset += self._rows_rounds[i]
        last_row = offset + self._rows_rounds[round_num-1]

        # skip headers update
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"Moves!A{offset}:E{last_row}",
                 "majorDimension": "ROWS",
                 "values": []}
            ]
        }

        for r in results:
            choice = ', '.join(['{:02d}'.format(i)
                               for i in r['choice']])
            choice = "'" + choice
            body["data"][0]["values"].append(
                [str(r['chat_id']), r['role'], r['player_name'], round_num, choice])

        self._sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=self._spreadsheet_id, body=body).execute()

    def _share_spreadsheet(self, user_emails: list):
        for u in user_emails:
            self._drive_service.permissions().create(
                fileId=self._spreadsheet_id,                
                body={'type': 'user', 'role': 'writer', 'emailAddress': u},
                fields='id'
            ).execute()

    def retrieve_game_results(self, round_num) -> dict:       
        access_token_info = self._creds.get_access_token()
        access_token = access_token_info.access_token

        spreadsheet_id = self._spreadsheet_id
        sheet_name = 'Results'

        query = f'select A,C,D,E,F where B={round_num}'
        url = 'https://docs.google.com/spreadsheets/d/' + spreadsheet_id + \
            '/gviz/tq?sheet=' + sheet_name + '&tqx=out:json&tq=' + query
        try:
            response = requests.get(
                url, headers={'Authorization': 'Bearer ' + access_token}).text
            json_part = "{" + response.split("({")[1].strip(");")
            res = json.loads(json_part)['table']
        except Exception as e:
            logging.error(f"failed to retrieve results: {e}")
            raise
            
        return res
