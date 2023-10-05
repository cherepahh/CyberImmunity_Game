from os import getenv
from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.

GAME_ADMINS_TG_USERNAMES = getenv("GAME_ADMINS_TG_USERNAMES")


_admins_usernames = GAME_ADMINS_TG_USERNAMES.replace(" ","").split(",")


def check_authorization(user):
    if user in _admins_usernames:
        return True
    return False


def _force_admin_usernames(usernames: str):
    '''
    mainly used for test purposes
    '''    
    global GAME_ADMINS_TG_USERNAMES
    global _admins_usernames
    GAME_ADMINS_TG_USERNAMES = usernames
    _admins_usernames = GAME_ADMINS_TG_USERNAMES.replace(" ","").split(",")
    return _admins_usernames
