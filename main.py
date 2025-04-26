import asyncio
import datetime
import json
from copy import deepcopy
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler


def get_data():
    with open('data.json', 'r') as file:
        data = json.load(file)

    return data


def update_file(data: dict):
    with open('data.json', 'w') as file:
        file.write(
            json.dumps(data, indent=4)
        )


# user_id: {
#   'reminders': [
#       {
#           'text': 'reminder 1',
#           'time': '26.04.2025 18:00'
#       },
#       {
#           'text': 'reminder 2',
#           'time': '3.05.2025 22:00'
#       }
#   ],
#   'state': 'start',
# }
data = get_data()

REMINDERS_LIMIT = 5

router = Router()
scheduler = AsyncIOScheduler()

# 1. Добавить поле времени в объект напоминания
# 2. Добавить планировщик для уведомлений


@router.message(Command('start'))
async def start_handler(message: Message):
    user_id = message.from_user.id

    if user_id not in data:
        data[str(user_id)] = {
            'reminders': [],
            'new_reminder': {},
            'state': 'start',
        }

        update_file(data)

    await message.answer(
        'Привет, я бот-напоминалка \n'
        'Чтобы узнать о моих возможностях напиши команду /help'
    )


@router.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(
        'Вот что я умею:\n'
        '/add - добавить напоминание \n'
        '/delete - удалить напоминание \n'
        '/show - показать все мои напоминания \n'
    )


@router.message(Command('add'))
async def add_handler(message: Message):
    user_id = message.from_user.id

    # проверка на лимит
    user_reminders = data[str(user_id)]['reminders']
    if len(user_reminders) >= REMINDERS_LIMIT:
        await message.answer('Вы исчерпали лимит напоминаний. Удалите предыдущие для добавления новых')
        return

    data[str(user_id)]['state'] = 'add_text'
    update_file(data)

    await message.answer('Отправь мне свое напоминание')


@router.message(Command('show'))
async def show_handler(message: Message):
    user_id = message.from_user.id
    user_reminders = data[str(user_id)]['reminders']

    if not user_reminders:
        await message.answer('У тебя нет напоминаний')
        return

    answer_text = 'Вот список твоих напоминаний: \n\n'
    for i in range(len(user_reminders)):
        answer_text += f'{i + 1}. {user_reminders[i]} \n\n'

    await message.answer(answer_text)


@router.message(Command('delete'))
async def delete_handler(message: Message):
    user_id = message.from_user.id
    data[str(user_id)]['state'] = 'delete'
    update_file(data)

    await show_handler(message)
    await message.answer('Пришли мне номер напоминания для удаления')


@router.message()
async def message_handler(message: Message):
    user_id = message.from_user.id
    user_state = data[str(user_id)]['state']

    if user_state == 'add_text':
        data[str(user_id)]['new_reminder'] = {
            'text': message.text
        }

        await message.answer('Хорошо, пришли мне время напоминания в формате: ДД.ММ.ГГГГ ЧЧ:ММ')
        data[str(user_id)]['state'] = 'add_time'

        update_file(data)

    elif user_state == 'add_time':
        new_reminder = data[str(user_id)]['new_reminder']
        remind_dt = datetime.strptime(message.text, '%d.%m.%Y %H:%M')

        new_reminder['time'] = remind_dt.strftime("%Y-%m-%d %H:%M:%S")

        data[str(user_id)]['reminders'].append(new_reminder)
        await message.answer('Напоминание добавлено')

        data[str(user_id)]['state'] = 'start'
        data[str(user_id)]['new_reminder'] = {}

        update_file(data)

    elif user_state == 'delete':
        try:
            user_reminders = data[str(user_id)]['reminders']

            reminder_index = int(message.text)

            if 0 > reminder_index > len(user_reminders):
                await message.answer('Похоже, ты ошибся. Попробуй снова')
                return

            user_reminders.pop(reminder_index - 1)
            data[str(user_id)]['reminders'] = user_reminders

            await message.answer('Напоминание удалено')
            data[str(user_id)]['state'] = 'start'

            update_file(data)

        except:
            await message.answer('Похоже, ты ошибся. Попробуй снова')

    else:
        await message.answer('Извини, я не понимаю')

async def send_reminders(bot):
    data_copy = deepcopy(data)

    for user_id, user_data in data_copy.items():
        for reminder in user_data['reminders']:
            remind_dt = datetime.strptime(reminder['time'], '%Y-%m-%d %H:%M:%S')
            now_dt = datetime.now()

            if (
                    remind_dt.year == now_dt.year and
                    remind_dt.month == now_dt.month and
                    remind_dt.day == now_dt.day and
                    remind_dt.hour == now_dt.hour and
                    remind_dt.minute == now_dt.minute
            ):
                await bot.send_message(
                    user_id,
                    f'🔔 Напоминаю: \n\n{reminder["text"]}'
                )

async def main():
    bot = Bot(token='7874118763:AAEOiyw2T8bECxXDXzR801Cl_xnH4-LNANw')
    dp = Dispatcher()

    dp.include_router(router)

    scheduler.add_job(send_reminders, 'interval', minutes = 1, args = [bot])
    scheduler.start()

    await dp.start_polling(bot)


asyncio.run(main())
