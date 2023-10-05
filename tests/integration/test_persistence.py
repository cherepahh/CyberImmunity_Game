from pytest import fixture
from uuid import uuid4
from src.persistence.stub import read_all_data


@fixture
def game_id():
    return uuid4().__str__()


def test_read_games_data():
    data = read_all_data()
    assert data is not None