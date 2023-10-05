import asyncio
import logging
import sys
from os import getenv
from typing import Any, Dict
from uuid import uuid4

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    # InlineKeyboardMarkup,
    # InlineKeyboardButton,
    CallbackQuery,
    FSInputFile
)

from dotenv import load_dotenv

from games.ogneborec import KiprGameOgneborec
from google_sheets.report import GoogleSheetsIntegration
from persistence.stub import store_update_choice, get_score, \
    get_last_game_id, set_last_game_id, \
    reset_game_data, get_game_status, set_game_status, get_game_data, \
    ROLE_HACKER, ROLE_ARCHITECT, \
    GAME_STATUS_IN_PROGRESS, GAME_STATUS_COMPLETED
from admins import check_authorization

load_dotenv()  # take environment variables from .env.

KIPR_BOT_VERSION = "1.01"


TOKEN = getenv("BOT_TOKEN")
MAX_ROUNDS = 3

selected_game = KiprGameOgneborec
report = GoogleSheetsIntegration()

# restore the last game context, if no last game present, start new one
game_id = get_last_game_id()
if game_id is None:
    game_id = uuid4().__str__()
    set_last_game_id(game_id)
else:
    report.set_spreadsheet_id(game_id)

form_router = Router()


class Form(StatesGroup):
    name = State()
    role = State()
    # << play_mode = State() # играть против других игроков или бота >>
    choice = State()
    choice_round_1 = State()
    results_round_1 = State()
    choice_round_2 = State()
    results_round_2 = State()
    choice_round_3 = State()
    results_round_3 = State()
    current_state = name
    choices = [choice_round_1, choice_round_2, choice_round_3]


@form_router.message(CommandStart())
async def command_start(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.name)
    await message.answer(
        "Привет! Как зовут вас или вашу команду?",
        reply_markup=ReplyKeyboardRemove(),
    )

@form_router.message(Command("version"))
@form_router.message(F.text.casefold() == "version")
async def cancel_handler(message: Message) -> None:
    """
    Allow user to request bot version
    """
    
    await message.answer(
        f"КИПР бот, версия {KIPR_BOT_VERSION}",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("cancel"))
@form_router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Галя, у нас отмена!",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("reset"))
async def reset_handler(message: Message, state: FSMContext) -> None:
    """
    Allow admins to reset game state
    """
    if not check_authorization(message.chat.username):
        logging.info(
            f"Unauthorized request for game reset! Request from {message.chat.username}")
        await message.answer(
            "Только администраторы могут сбрасывать состояние игры!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    reset_game_data()
    report.reset_game_data()
    await message.answer(
            "Игровые данные удалены успешно",
            reply_markup=ReplyKeyboardRemove(),
        )
    set_game_status(game_id=game_id, round=1, status=GAME_STATUS_IN_PROGRESS)


@form_router.message(Command("newgame"))
@form_router.message(F.text.casefold() == "newgame")
async def new_game_handler(message: Message, state: FSMContext) -> None:
    """
    Allow authorized user to start new game.
    """
    if not check_authorization(message.chat.username):
        logging.info(
            f"Unauthorized request for new game start! Request from {message.chat.username}")
        await message.answer(
            "Только администраторы могут начинать новую игру!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    global game_id
    global report

    # check if existing game id has been provided
    game_details = message.text.strip("/newgame").strip().split(";")
    if game_details != ['']:
        # game details provided, use it
        game_id = game_details[0]
        # reuse already created sheet for game results
        if len(game_details) >= 1:
            report.set_spreadsheet_id(game_id)
        else:
            report.create_game_details_sheet(game_id)
    else:
        # uuid will only be used in the title, for communication will be used Google spreadsheet id 
        game_id = uuid4().__str__()
        report.create_game_details_sheet(game_id)
        game_id = report.get_spreadsheet_id()

    set_last_game_id(game_id=game_id)
    set_game_status(game_id=game_id, round=1, status=GAME_STATUS_IN_PROGRESS)



    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    logging.info("New game started!")

    await message.answer(
        "Начата новая игра! Таблица с результатами: " +
        f"https://docs.google.com/spreadsheets/d/{report.get_spreadsheet_id()}",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("endround"))
@form_router.message(F.text.casefold() == "endround")
async def end_round(message: Message, state: FSMContext) -> None:
    """
    Allow authorized user to end round and summarize results
    """
    if not check_authorization(message.chat.username):
        logging.info(
            f"Unauthorized request for round end! Request from {message.chat.username}")
        await message.answer(
            "Только администраторы могут завершать шаг игры!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    data = await state.get_data()
    """ get round id """
    game_round = message.text.strip("/endround").strip()
    try:
        round_num = int(game_round)
    except Exception as _:
        try:
            round_num = data['round']
            s = await state.get_state()
            logging.debug(f"ending round in state {s} with data {data}")
        except Exception as _:
            round_num = 1

    logging.info(f"round {round_num} is over!")
    selected_game.calculate_game_round_results(game_id=game_id, round=round_num)

    # calculate round results
    await message.answer(
        f"Шаг {round_num} игры завершён!",
        reply_markup=ReplyKeyboardRemove(),
    )

    results = selected_game.get_round_details(game_id=game_id, round=round_num)

    global report
    report.update_game_results(game_id, round_num, results=results)


@form_router.message(Command("roundresults"))
@form_router.message(F.text.casefold() == "roundresults")
async def start_round(message: Message, state: FSMContext) -> None:
    logging.info("getting round results")
    data = await state.get_data()
    round_num = data['round']    
    bot = message.bot
    await broadcast_round_results(bot, round_num)


@form_router.message(Command("startround"))
@form_router.message(F.text.casefold() == "startround")
async def start_round(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    round_num = data['round']
    await set_next_round_state(bot=message.bot, state=state, finished_round_num=round_num)
    logging.info("starting results")


async def set_next_round_state(bot, state: FSMContext, finished_round_num: int):
    if finished_round_num < MAX_ROUNDS:
        round_num = finished_round_num + 1
        status = GAME_STATUS_IN_PROGRESS
        try:
            await state.set_state(Form.choice)
            set_game_status(game_id, round_num, status)
            await broadcast_next_round(bot, game_id, round_num)
        except Exception as e:
            logging.error(f"failed to set next round state: {e}")
    else:
        round_num = MAX_ROUNDS
        status = GAME_STATUS_COMPLETED
        set_game_status(game_id, round_num, status)
        await broadcast_final_results(bot, game_id)

async def broadcast_round_results(bot, round_num):
    try:
        results = report.retrieve_game_results(round_num=round_num)
        logging.debug(f"round {round_num} results: {results}")
        for r in results['rows']:
            chat_id = int(r['c'][0]['v'])
            # score = int(r['c'][1]['v'])
            # total_score = int(r['c'][1]['v'])
            # rating = int(r['c'][3]['v'])
            # comment = r['c'][4]['v']
            feedback = r['c'][4]['v']
            # summary = f"* за этот ход вы получаете {score} очков\n" + \
            #           f"* общее количество очков {total_score}\n" +\
            #           f"ваша позиция в рейтинге №{rating}.\n\n" + \
            #           f"Подробная информация: {comment}"
            await bot.send_message(chat_id, feedback)
    except Exception as e:
        logging.error(f"failed to handle round results: {e}")


async def broadcast_next_round(bot, game_id: str, round_num: int) -> None:
    data = get_game_data(game_id, round=round_num-1 if round_num > 0 else 0, role=None)
    for player in data:
        await bot.send_message(player["chat_id"], f"Начинаем шаг {round_num}!")
        await intro_round(bot=bot, chat_id=player['chat_id'], round=round_num, role=player['role'])


async def broadcast_final_results(bot, game_id: str) -> None:
    data = get_game_data(game_id, round=MAX_ROUNDS, role=None)
    for player in data:
        await bot.send_message(player["chat_id"], "Игра завершена! Проверьте свои результаты")


@form_router.message(Form.name)
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(Form.role)
    await message.answer(
        f"Приветствуем, {html.quote(message.text)}!\nВ какой роли вы хотите играть?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Архитектор"),
                    KeyboardButton(text="Хакер"),
                ]
            ],
            resize_keyboard=True,
        ),
    )


async def intro_round(bot, chat_id, round, role):
    arch = [selected_game.architecture_round_1, selected_game.architecture_round_2, selected_game.architecture_round_3]
    security_budget = [selected_game.round_1_security_budget_limit,selected_game.round_2_security_budget_limit,selected_game.round_3_security_budget_limit]
    attacks_budget = [selected_game.round_1_attack_budget_limit, selected_game.round_2_attack_budget_limit, selected_game.round_3_attack_budget_limit]
    await bot.send_photo(chat_id, photo=FSInputFile(path=arch[round-1][0]),
                               caption="Архитектура системы и стоимость защиты компонентов:\n"
                               "<b>₽</b> - один миллион рублей, <b>₽₽</b> - два миллиона"
                               )
    if round != 2:
        # on round 2 this diagram is the same, no need to spam players
        await bot.send_photo(chat_id, photo=FSInputFile(path=arch[round-1][1]),
                               caption="Логика взаимодействия компонентов"                               
                               )
    if (role == ROLE_HACKER):
        if round == 1:
            await bot.send_message(chat_id, "Вы получите очки, если в ходе атаки будет нарушена хотя бы одна из целей безопасности:\n" +
                                selected_game.security_objectives_and_assumptions
                                )
        max_attacks = attacks_budget[round-1]
        if round == 2:
            await bot.send_message(chat_id, "Атаки и последствия не изменились, но увеличилось количество вариантов.\n\n" +
                                f"Какие атаки вы выбираете? (максимум {max_attacks}, каждая атака работает независимо от других)\n" +
                                "В ответном сообщении пришлите список с номерами атак через запятую (например, 1,2)",
                                )
        else:            
            await bot.send_message(chat_id, "Вы можете атаковать следующими способами:\n"
                                """{}""".format("\n".join(selected_game.get_attacks_text(round=round))) +
                                f"\n\nКакие атаки вы выбираете? (максимум {max_attacks}, каждая атака работает независимо от других)\n" +
                                "В ответном сообщении пришлите список с номерами атак через запятую (например, 1,2)",
                                )
    elif role == ROLE_ARCHITECT:
        max_secure = security_budget[round-1]
        await bot.send_message(chat_id, f"Бюджет защиты <b>{max_secure}</b> млн руб.\n"
                         "Какие компоненты вы будете защищать за эти деньги?\n"
                         "В ответном сообщении пришлите список с номерами через запятую (например, 1,2)",
                         )


@form_router.message(Form.role, F.text.casefold() == ROLE_ARCHITECT)
async def process_system_architect(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    name = data["name"]
    await state.update_data(role=message.text.casefold())
    await state.clear()
    await message.answer("Отлично, вы защищаете нашу систему!",
                         reply_markup=ReplyKeyboardRemove(),
                         )
    await message.answer("Как архитектор вы согласовали с бизнесом такие цели и предположения безопасности:\n\n" +
                         selected_game.security_objectives_and_assumptions
                         )
    await intro_round(bot=message.bot, chat_id=message.chat.id, round=1, role=ROLE_ARCHITECT)
    await state.set_state(Form.choice)
    await state.update_data(message=message, name=name, role=ROLE_ARCHITECT)


@form_router.message(Form.role, F.text.casefold() == ROLE_HACKER)
async def process_hacker(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    name = data["name"]
    await state.update_data(role=message.text.casefold())
    await message.answer("Отлично, вы решили проверить поведение системы под атакой!\n",
                         reply_markup=ReplyKeyboardRemove(),
                         )
    await intro_round(bot=message.bot, chat_id=message.chat.id, round=1, role= ROLE_HACKER)
    await state.set_state(Form.choice)
    await state.update_data(message=message, name=name, role=message.text.casefold())


async def extract_choice_from_state_and_store(state: FSMContext, chat_id: str, username: str, round: int = 1):
    data = await state.get_data()
    choice = {
        "game_id": game_id,
        "chat_id": chat_id,
        "player_username": username,
        "player_name": data["name"],
        "role": data["role"],
        "choice": data[f"choice_round_{round}"]
    }
    store_update_choice(choice=choice, round=round)


async def show_input_common_summary(message: Message, data: Dict[str, Any], choice, round_num) -> None:
    name=data["name"]
    role=data.get("role", "<роль не определена>")
    if round_num == 1:
        text=f"Итак, {html.quote(name)}, "
        text += (
            f"вы играете в роли {html.quote(role)}а, ваш выбор {choice}."
        )
    else:
        text = f"Отлично, ваш выбор {choice} принят"
    await message.answer(text=text, reply_markup=ReplyKeyboardRemove())


async def show_input_error_message(message: Message, text: str) -> None:
    await message.answer(text , reply_markup=ReplyKeyboardRemove())


@ form_router.callback_query()
async def show_round_results(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.bot.answer_callback_query(callback.id)
    await show_round_results_summary(callback=callback, state=state)


async def show_round_results_summary(callback: CallbackQuery, state: FSMContext) -> None:
    # await message.answer(text=text, reply_markup=ReplyKeyboardRemove())
    player_info = await state.get_data()
    bot = callback.bot
    if player_info == {}:
        await bot.send_message(callback.from_user.id, "нет данных о текущем шаге")
        return
    game_round = player_info["round"]
    results = get_score(game_id=game_id, player_info=player_info, round=game_round)

    text = f"Результаты игры для шага {game_round}\n"

    if player_info["role"] == ROLE_ARCHITECT:
        text += f"Успешная защита: {results['protected_score_round_'+str(game_round)]}\n" \
               f"Пропущенные критические атаки: {results['compromised_score_round_'+str(game_round)]}"
        if results['compromised_score_round_'+str(game_round)] > 0:
            text += "\n\nУспешные атаки:\n"
            for a_id in results['compromised_tcb_components_round_'+str(game_round)]:
                component = selected_game.components_full[a_id-1]
                text += component["name"] + ": " + component["attack_text"] + "\n"
    elif player_info["role"] == ROLE_HACKER:
        text += f"Успешный взлом: {results['successful_attacks_score_round_'+str(game_round)]}\n" \
               f"Заблокированный взлом: {results['unsuccessful_attacks_score_round_'+str(game_round)]}"
    else:
        text = "неопределённая роль, нельзя интерпретировать результаты"

    await bot.send_message(callback.from_user.id, text)


async def process_choice(message: Message, state: FSMContext, round_num: int, data, budget) -> None:
    choice = message.text
    name = data.get("name", "Anonymous")
    role = data.get("role", "<роль не определена>")
    need_to_reset_state = False

    await state.update_data(round=round_num, username=message.chat.username, message=message, name=name)

    if role == ROLE_ARCHITECT:
        if selected_game.is_security_choice_valid(message.text, round_num):
            await show_input_common_summary(message=message, data=data, choice=message.text.casefold(), round_num=round_num)
            costs = selected_game.calculate_security_costs(
                choice=choice, round_num=round_num)
            await extract_choice_from_state_and_store(state, message.chat.id, message.chat.username, round=round_num)
            await message.answer(f"Вы потратили {costs} млн. руб. "
                                 f"из общего бюджета {budget} млн. руб.\n",
                                #  reply_markup = InlineKeyboardMarkup(
                                #         inline_keyboard=[[InlineKeyboardButton(
                                #             text="Узнать результат хода", callback_data="*")]],
                                #         resize_keyboard=True,
                                #     )
                                 )

        else:
            err_message = "Выбранный способ защиты недопустим, попробуйте ещё раз:\n" + \
                          "В ответном сообщении с учётом бюджета пришлите список " + \
                          "с номерами защищаемых компонент через запятую (например, 1,2).\n" +\
                          "Обратите внимание, что суммарная стоимость защиты не может превышать лимит!"
            await show_input_error_message(message=message, text=err_message)
            need_to_reset_state = True
    elif role == ROLE_HACKER:
        if selected_game.is_attacking_choice_valid(message.text, round_num):
            await extract_choice_from_state_and_store(
                state, message.chat.id, message.chat.username, round=round_num
            )
            await show_input_common_summary(message=message, data=data, choice=message.text.casefold(),  round_num=round_num)
            await message.answer("Команда сделала свой выбор, теперь дождитесь окончания текущего "
                                 "шага игры и посмотрите результаты.\n",
                                #  reply_markup = InlineKeyboardMarkup(
                                #         inline_keyboard=[[InlineKeyboardButton(
                                #             text="Узнать результат хода", callback_data="*")]],
                                #         resize_keyboard=True,
                                #     )
                                 )
        else:
            err_message = "Выбранный способ атаки недопустим, попробуйте ещё раз:\n" + \
                          "В ответном сообщении с учётом ограничения числа атак пришлите список " + \
                          "с номерами атакуемых компонент через запятую (например, 1,2)"
            await show_input_error_message(message=message, text=err_message)
            need_to_reset_state = True

    if need_to_reset_state:
        await state.update_data(message=message, name=name, role=role)


@form_router.message(Form.choice)
async def process_choice_input(message: Message, state: FSMContext) -> None:
    """ 
    handle user choices for all rounds here, 
    sync current round through the game status stored in local file 
    """
    choice = message.text
    status = get_game_status(game_id=game_id)
    if status is not None:
        round_num = status["round"]
    else:
        round_num = 1

    if round_num == MAX_ROUNDS and status["status"] == GAME_STATUS_COMPLETED:
        await message.answer("Игра завершена, ставок больше нет")
        return

    if round_num == 1:
        data = await state.update_data(choice_round_1=choice)
        budget = selected_game.round_1_security_budget_limit
    elif round_num == 2:
        data = await state.update_data(choice_round_2=choice)
        budget = selected_game.round_2_security_budget_limit
    else: # round 3
        data = await state.update_data(choice_round_3=choice)
        budget = selected_game.round_3_security_budget_limit

    await process_choice(
        message=message, state=state, round_num=round_num, data=data, budget=budget
    )


async def main():
    bot=Bot(token=TOKEN, parse_mode=ParseMode.HTML)
    dp=Dispatcher()
    dp.include_router(form_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
        raise
