""" functions for storing and reading player choices, simplest implementation
"""
from pysondb import db
import logging

GAME_DATA_FILE_NAME = "./data/game_data.json"
GAME_INDEX_FILE_NAME = "./data/game_index.json"
GAME_STATUS_FILE_NAME = "./data/game_status.json"
ROLE_ARCHITECT = "архитектор"
ROLE_HACKER = "хакер"
GAME_STATUS_IN_PROGRESS = 'in progress'
GAME_STATUS_COMPLETED = 'completed'

def store_data(data: dict) -> None:
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    game_db.add(data)

def read_all_data():
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    data = game_db.getAll()
    return data

def _convert_choices_string_to_list(choice: str) -> list:
    choices = choice.split(",")
    choices_list = []
    for c in choices:
        choices_list.append(int(c.strip()))
    return choices_list

def preserve_entry_schema(entry: dict):
    extra_fields = [
       "compromised_score_round_1",
       "compromised_score_round_2",
       "compromised_score_round_3",
       "protected_score_round_1",
       "protected_score_round_2",
       "protected_score_round_3",
       "compromised_tcb_components_round_1",
       "compromised_tcb_components_round_2",
       "compromised_tcb_components_round_3",
       "successful_attacks_score_round_1",
       "successful_attacks_score_round_2",
       "successful_attacks_score_round_3",
       "unsuccessful_attacks_score_round_1",
       "unsuccessful_attacks_score_round_2",
       "unsuccessful_attacks_score_round_3",
       "irrelevant_attacks_score_round_1",
       "irrelevant_attacks_score_round_2",
       "irrelevant_attacks_score_round_3",

    ]
    for f in extra_fields:
        if f not in entry:
            entry[f] = -1
    return entry

def store_update_choice(choice : dict, round: int = 1) -> None:
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    choices_str = choice["choice"]
    choice = preserve_entry_schema(choice)
    choice["round"] = round    
    choice["choice"] = _convert_choices_string_to_list(choices_str)
    try:
        # if choice already present, update it
        data = game_db.getByQuery({
            "game_id": choice["game_id"],
            "player_username": choice["player_username"],
            "round": round
        })[0]
        data["choice"] = choice["choice"]
        # just in case the player has changed the team name
        data["player_name"] = choice["player_name"]
        game_db.updateById(data["id"], data)
    except Exception as _:
        # if it's a new choice, add it to the db        
        data = choice        
        data["choice"] = choice["choice"]        
        game_db.add(data)

def store_update_score(player_info):
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    game_db.updateById(player_info["id"], player_info)

def get_game_status(game_id: str) -> dict or None:
    game_status_db = db.getDb(GAME_STATUS_FILE_NAME)
    try:
        game_status = game_status_db.getByQuery(query={"game_id": game_id})[0]
    except Exception as _:
        game_status = None
    return game_status


def set_game_status(game_id: str, round: int, status: str) -> None:
    game_status_db = db.getDb(GAME_STATUS_FILE_NAME)    
    games = game_status_db.getByQuery(query={"game_id": game_id})
    if len(games) == 0:
        game_status = None    
    else:
        game_status = games[0]
    if game_status is None:
        game_status = {}
    game_status["game_id"] = game_id
    game_status["round"] = round
    game_status["status"] = status
    game_id = game_status.get("id", None)
    if game_id is not None:
        game_status_db.updateById(pk=game_id, new_data=game_status)
    else:
        game_status_db.add(game_status)


def get_game_data(game_id: str, round: int or None, role: str or None) -> dict:
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    query={"game_id": game_id}

    if round is not None:
        # if game round is defined then query results only of
        # this particular round
        query["round"] = round

    if role is not None:
        query["role"] = role

    data = game_db.getByQuery(query=query)
    return data

def reset_game_data() -> None:
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    game_db.deleteAll()
    game_status_db = db.getDb(GAME_STATUS_FILE_NAME)
    game_status_db.deleteAll()


def get_score(game_id: str, player_info: dict, round: int = 1) -> dict or None:
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    query={"game_id": game_id, "player_username": player_info["username"], "round": round}

    data = game_db.getByQuery(query=query)[0]
    return data

def get_round_summary(game_id: str, round: int = 1) -> dict or None:
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    query={"game_id": game_id}
    data = game_db.getByQuery(query=query)
    architects_score = 0
    hackers_score = 0

    for e in data:
        if e["role"] == ROLE_ARCHITECT:
            if e["protected_score_round_"+str(round)] > 0:
                architects_score += e["protected_score_round_"+str(round)]
        elif e["role"] == ROLE_HACKER:
            if e["successful_attacks_score_round_"+str(round)] > 0:
                hackers_score += e["successful_attacks_score_round_"+str(round)]
    result = {
        "architects": architects_score,
        "hackers": hackers_score
    }
    return result

def get_round_details(game_id: str, round: int = 1) -> dict or None:
    game_db = db.getDb(GAME_DATA_FILE_NAME)
    query={"game_id": game_id, "round": round}
    data = game_db.getByQuery(query=query)
    return data

def get_last_game_id() -> str or None:
    game_index = db.getDb(GAME_INDEX_FILE_NAME)
    try:
        data = game_index.getByQuery({"type": "last_game_id"})[0]
        last_game_id = data["last_game_id"]
        return last_game_id
    except Exception as _:
        # not found
        return None

def set_last_game_id(game_id: str) -> None:
    game_index = db.getDb(GAME_INDEX_FILE_NAME)
    try:
        data = game_index.getByQuery({"type": "last_game_id"})[0]
        data["last_game_id"] = game_id
        game_index.updateById(data["id"], data)
    except Exception as _:
        # not found
        data = {
            "type": "last_game_id",
            "last_game_id": game_id
        }
        game_index.add(data)
