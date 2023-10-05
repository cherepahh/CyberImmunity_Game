
setupenv:
	pipenv install -r requirements-dev.txt

prepare_db: init_game_data init_game_index init_game_status

init_game_data:
	pipenv run pysondb create ./data/game_data.json

init_game_index:
	pipenv run pysondb create ./data/game_index.json

init_game_status:
	pipenv run pysondb create ./data/game_status.json

prepare: setupenv prepare_db

run-kipr-game-bot:
	python src/kipr_game_bot.py

bot: run-kipr-game-bot

bot-service:
	# requires screen tool to be installed in the system, e.g. via ``sudo apt install screen -y``
	screen -dmS kipr-bot pipenv run python src/kipr_game_bot.py

clean: remove-pipenv

remove-pipenv:
	pipenv -rm
