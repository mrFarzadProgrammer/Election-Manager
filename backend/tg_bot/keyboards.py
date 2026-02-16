import re

from telegram import ReplyKeyboardMarkup, KeyboardButton

from .ui_constants import (
    BTN_ABOUT_BOT,
    BTN_ABOUT_INTRO,
    BTN_ASK_NEW_QUESTION,
    BTN_BACK,
    BTN_BOT_REQUEST,
    BTN_BUILD_BOT,
    BTN_COMMITMENTS,
    BTN_FEEDBACK,
    BTN_HQ_ADDRESSES,
    BTN_OTHER_MENU,
    BTN_PROGRAMS,
    BTN_QUESTION,
    BTN_REGISTER_QUESTION,
    BTN_SEARCH_QUESTION,
    BTN_SELECT_TOPIC,
    BTN_SEND_CONTACT,
    BTN_VOICE_INTRO,
    BTN_VIEW_BY_CATEGORY,
    BTN_VIEW_BY_SEARCH,
    BTN_VIEW_QUESTIONS,
    QUESTION_CATEGORIES,
    ROLE_CANDIDATE,
    ROLE_REPRESENTATIVE,
    ROLE_TEAM,
)


def build_bot_request_cta_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_BOT_REQUEST)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_bot_request_role_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(ROLE_REPRESENTATIVE), KeyboardButton(ROLE_CANDIDATE), KeyboardButton(ROLE_TEAM)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_bot_request_contact_keyboard() -> ReplyKeyboardMarkup:
    # Telegram will only allow the *user themself* to share their contact via this button.
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_SEND_CONTACT, request_contact=True)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_COMMITMENTS), KeyboardButton(BTN_QUESTION)],
            [KeyboardButton(BTN_PROGRAMS), KeyboardButton(BTN_FEEDBACK)],
            [KeyboardButton(BTN_OTHER_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_about_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_PROGRAMS), KeyboardButton(BTN_ABOUT_INTRO)],
            [KeyboardButton(BTN_VOICE_INTRO), KeyboardButton(BTN_HQ_ADDRESSES)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_other_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_BUILD_BOT)],
            [KeyboardButton(BTN_ABOUT_BOT)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True, is_persistent=True)


def build_question_hub_keyboard() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    cat_buttons = [KeyboardButton(f"🗂 {c}") for c in QUESTION_CATEGORIES]
    for i in range(0, len(cat_buttons), 2):
        rows.append(cat_buttons[i : i + 2])
    rows.append([KeyboardButton(BTN_SEARCH_QUESTION), KeyboardButton(BTN_REGISTER_QUESTION)])
    rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def build_question_entry_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_VIEW_QUESTIONS)], [KeyboardButton(BTN_ASK_NEW_QUESTION)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_question_view_method_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_VIEW_BY_CATEGORY), KeyboardButton(BTN_VIEW_BY_SEARCH)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_question_ask_entry_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_SELECT_TOPIC)], [KeyboardButton(BTN_BACK)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def build_question_categories_keyboard(*, prefix_icon: bool, include_back: bool) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    buttons = [KeyboardButton(f"🗂 {c}") for c in QUESTION_CATEGORIES] if prefix_icon else [KeyboardButton(c) for c in QUESTION_CATEGORIES]
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i : i + 2])
    if include_back:
        rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def build_question_list_keyboard(items: list[dict], *, normalize_text) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    buttons: list[KeyboardButton] = []
    for idx, it in enumerate(items, start=1):
        q = normalize_text(it.get("q") or "")
        q = re.sub(r"\s+", " ", q).strip()
        if len(q) > 48:
            q = q[:47] + "…"
        buttons.append(KeyboardButton(f"{idx}) {q}" if q else f"{idx})"))

    for i in range(0, len(buttons), 2):
        rows.append(buttons[i : i + 2])
    rows.append([KeyboardButton(BTN_BACK)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)
