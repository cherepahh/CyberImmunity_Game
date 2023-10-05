import logging
from persistence.stub import get_game_data, store_update_score, get_round_summary, ROLE_ARCHITECT, ROLE_HACKER, get_round_details


class KiprGameOgneborec:
    security_objectives_and_assumptions = "<b>Цели безопасности</b>\n\n" + \
        "1. Тушение возможно только в авторизованном районе\n" + \
        "2. Тушение возможно только авторизованным способом\n" + \
        "\n<b>Предположения безопасности</b>\n\n" + \
        "* Источник полётного задания благонадёжен\n" + \
        "* В авторизованных районах действия нет людей, животных и объектов инфраструктуры, которым можно нанести урон\n"

    components_full = [
        {
            "id": 1,
            "name": "1. Связь",
            "cost": 2,
            "available_from_round": 1,
            "in_tcb": True,
            "attack_text": "Подмена полётного задания, изменение района и способа тушения."
        },
        {
            "id": 2,
            "name": "2. Центральная система управления",
            "cost": 2,
            "available_from_round": 1,
            "in_tcb": True,
            "attack_text": "Дрон улетает в неавторизованный район и использует неавторизованный способ борьбы с пожаром."
        },
        {
            "id": 3,
            "name": "3. Тушение водой",
            "cost": 1,
            "available_from_round": 1,
            "in_tcb": True,
            "attack_text": "Произвольное опустошение резервуара по таймеру происходит вне заданного района тушения."
        },
        {
            "id": 4,
            "name": "4. Поджигание",
            "cost": 1,
            "available_from_round": 1,
            "in_tcb": True,
            "attack_text": "Произвольное поджигание по таймеру приводит к поджогу до прибытия в заданный район или после окончания тушения."
        },
        {
            "id": 5,
            "name": "5. Контроль обстановки",
            "cost": 2,
            "available_from_round": 1,
            "in_tcb": False,
            "attack_text": "Дрон досрочно прекращает тушение, т.к. получил оценку, что всё уже потушено."
        },
        {
            "id": 6,
            "name": "6. Управление перемещением",
            "cost": 2,
            "available_from_round": 1,
            "in_tcb": True,
            "attack_text": "Дрон улетает в неавторизованный район (или не долетает до авторизованного), сообщает об успешном прибытии, система управления начинает тушение в неавторизованном районе."
        },
        {
            "id": 7,
            "name": "7. Контроль уровня заряда батареи",
            "cost": 1,
            "available_from_round": 1,
            "in_tcb": True,
            "attack_text": "Центральная система управления не получила вовремя информацию о критическом разряде батареи, дрон упал и разбился."
        },
        {
            "id": 8,
            "name": "8. Навигация (спутник)",
            "cost": 2,
            "available_from_round": 1,
            "in_tcb": True,
            "attack_text": "Выдаёт некорректные координаты, имитирует достижение заданного района. Если повезёт, дрон улетит в неавторизованный район и начнёт тушить там."
        },
        {
            "id": 9,
            "name": "9. Навигация (ИНС)",
            "cost": 1,
            "available_from_round": 3,
            "in_tcb": True,
            "attack_text": "Выдаёт некорректные координаты, имитирует достижение заданного района. Если повезёт, дрон улетит в неавторизованный район и начнёт тушить там."
        },
        {
            "id": 10,
            "name": "10. Комплексирование",
            "cost": 1,
            "available_from_round": 3,
            "in_tcb": True,
            "attack_text": "Выдаёт некорректные координаты, имитирует достижение заданного района. Если повезёт, дрон улетит в неавторизованный район и начнёт тушить там."
        },
        {
            "id": 11,
            "name": "11. Контроль аутентичности полётного задания",
            "cost": 1,
            "available_from_round": 3,
            "in_tcb": True,
            "attack_text": "Подмена полётного задания, дрон улетает тушит не там и не так, как спланировал оператор и источник полетного задания."
        },
        {
            "id": 12,
            "name": "12. Контроль цепей поджига",
            "cost": 1,
            "available_from_round": 3,
            "in_tcb": True,
            "attack_text": "Отключение или активация цепей в произвольный момент, приводящих к невозможности или возможности активации произвольного типа борьбы с пожаром."
        }
    ]

    @staticmethod
    def get_attacks_text(round: int = 1) -> list:
        attacks = []
        for c in KiprGameOgneborec.components_full:
            if c["available_from_round"] <= round:
                attacks.append(f'{c["name"]}: {c["attack_text"]}')
        return attacks

    @staticmethod
    def get_attacks_ids(round: int = 1) -> list:
        attacks = []
        for c in KiprGameOgneborec.components_full:
            if c["available_from_round"] <= round:
                attacks.append(c["id"])
        return attacks

    @staticmethod
    def message_round_2_architects() -> str:
        return "На втором шаге бюджет защиты увеличен до 8 млн рублей. \n" \
         "Архитектура не меняется."
    
    @staticmethod
    def message_round_2_hackers() -> str:
        return "На втором шаге бюджет атаки увеличен до 5 сценариев. \n" \
         "Архитектура и сами атаки не меняются."

    @staticmethod
    def message_round_3_architects() -> str:
        return "На третьем шаге бюджет защиты снижен до 5 млн рублей. \n" \
         "Архитектура изменилась, внимательно изучите описание "\
         "добавленных или изменившихся компонент и их взаимодействие."
    
    @staticmethod
    def message_round_3_hackers() -> str:
        return "На третьем шаге бюджет атаки увеличен до 6 сценариев. \n" \
         "Архитектура и атаки изменились, внимательно изучите добавленные " \
         "или изменившиеся компоненты, а также новые сценарии атак"

    architecture_round_1 = ["./resources/ogneborec-arch-1.jpg", "./resources/ogneborec-sd-arch-1.jpg"]
    architecture_round_2 = architecture_round_1
    architecture_round_3 = ["./resources/ogneborec-arch-3.jpg", "./resources/ogneborec-sd-arch-3.jpg"]

    round_1_security_budget_limit = 6
    round_1_attack_budget_limit = 3
    round_2_security_budget_limit = 8
    round_2_attack_budget_limit = 5
    round_3_security_budget_limit = 5
    round_3_attack_budget_limit = 6
    security_budget = [round_1_security_budget_limit, round_2_security_budget_limit, round_3_security_budget_limit]
    attack_budget = [round_1_attack_budget_limit, round_2_attack_budget_limit, round_3_attack_budget_limit]

    @staticmethod
    def get_component_by_id(component_id: int) -> dict or None:
        for c in KiprGameOgneborec.components_full:
            if c["id"] == component_id:
                return c
        return None

    @staticmethod
    def calculate_security_costs(choice: str, round_num: int) -> int:
        components = choice.split(",")
        security_budget = 0
        for c in components:
            try:
                c_index = int(c)
            except Exception as e:
                logging.error(f"user input validation failed: {e}")
                raise e
            component = KiprGameOgneborec.get_component_by_id(c_index)
            if component is None or component["available_from_round"] > round_num:
                logging.error("user input validation failed: invalid choice")
                raise ValueError("invalid choice")
            security_budget += component["cost"]
        return security_budget

    @staticmethod
    def is_security_choice_valid(choice: str, round_num: int):
        validation_result = False
        try:
            security_budget = KiprGameOgneborec.calculate_security_costs(
                choice, round_num)
        except Exception as _:
            return False

        if security_budget <= KiprGameOgneborec.security_budget[round_num-1]:
            validation_result = True
            logging.debug(
                f"user input validation successful: chosen {choice}, calculated budget: {security_budget}")
        else:
            logging.info(
                f"user input validation unsuccessful: chosen {choice}, calculated budget: {security_budget}")
        return validation_result

    @staticmethod
    def is_attacking_choice_valid(choice: str, round_num: int):
        attacks = choice.split(",")
        if len(attacks) > KiprGameOgneborec.attack_budget[round_num-1]:
            return False
        for a in attacks:
            try:
                a_index = int(a)
            except Exception as _:
                # not a number
                return False
            allowed_attacks = KiprGameOgneborec.get_attacks_ids(round=round_num)
            if a_index not in allowed_attacks:
                # no such attack
                return False
        return True


    @staticmethod
    def calculate_game_round_results(game_id: str, round: int = 1):
        choice_architects = get_game_data(
            game_id=game_id, round=round, role=ROLE_ARCHITECT)
        choice_hackers = get_game_data(
            game_id=game_id, round=round, role=ROLE_HACKER)
        for a in choice_architects:
            protected = a["choice"]
            a[f"protected_score_round_{round}"] = 0
            a[f"compromised_score_round_{round}"] = 0
            for h in choice_hackers:
                hacked = h["choice"]
                for c in hacked:
                    component = KiprGameOgneborec.get_component_by_id(c)
                    if component["in_tcb"] is False:
                        # not interested in components outside of trusted code base
                        if h[f"irrelevant_attacks_score_round_{round}"] == -1:
                            h[f"irrelevant_attacks_score_round_{round}"] = 1
                        else:
                            h[f"irrelevant_attacks_score_round_{round}"] += 1
                        continue

                    if c in protected:
                        # attack blocked, score to the architects
                        a[f"protected_score_round_{round}"] += 1
                        # update unsuccessful attacks score for hackers
                        key = f"unsuccessful_attacks_score_round_{round}"
                    else:
                        a[f"compromised_score_round_{round}"] += 1
                        try:
                            a[f"compromised_tcb_components_round_{round}"].append(c)
                        except Exception as _:
                            a[f"compromised_tcb_components_round_{round}"] = [c]
                        key = f"successful_attacks_score_round_{round}"
                    if h[key] == -1:
                            h[key] = 1
                    else:
                        h[key] += 1
                store_update_score(h)
            store_update_score(a)

        round_results = get_game_data(game_id=game_id, round=round, role=None)
        logging.debug(round_results)


    @staticmethod
    def get_round_summary(game_id: str, round: int = 1):
        return get_round_summary(game_id=game_id, round=round)

    @staticmethod
    def get_round_details(game_id: str, round: int = 1):
        return get_round_details(game_id=game_id, round=round)