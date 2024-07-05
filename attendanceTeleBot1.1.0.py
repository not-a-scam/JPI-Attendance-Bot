from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
import logging
import json
import datetime
from pytz import timezone
import os.path
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
global GROUPCHAT_ID
GROUPCHAT_ID = os.getenv("GROUP_CHAT_ID")


with open('list.json') as f:
    NLIST = json.load(f)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def update_list():
    with open('list.json', 'w') as f:
        json.dump(NLIST, f)


def get_cell_from_server(server):
    for cell in NLIST.keys():
        if server in NLIST[cell]:
            return cell
    return None


async def poll_attendance(context: ContextTypes.DEFAULT_TYPE):
    attendance_string = write_attendance(nums=[0 for i in range(len(NLIST.keys()))], nc_nums=[0 for i in range(len(NLIST.keys()))])
    reply_markup = build_keyboard()
    await context.bot.send_message(GROUPCHAT_ID, attendance_string, reply_markup=reply_markup)

async def manual_poll_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = None
    if context.args and len(context.args) == 3 and len(context.args[0]) <= 2 and len(context.args[1]) <= 2 and len(context.args[2]) == 4:
        date = datetime.datetime(int(context.args[2]), int(context.args[1]), int(context.args[0]))
    attendance_string = write_attendance(nums=[0 for i in range(len(NLIST.keys()))], date=date, nc_nums=[0 for i in range(len(NLIST.keys()))])
    reply_markup = build_keyboard()
    await context.bot.send_message(GROUPCHAT_ID, attendance_string, reply_markup=reply_markup)

def build_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=1),
            InlineKeyboardButton("2", callback_data=2),
            InlineKeyboardButton("3", callback_data=3),
        ],
        [
            InlineKeyboardButton("4", callback_data=4),
            InlineKeyboardButton("5", callback_data=5),
            InlineKeyboardButton("6", callback_data=6),
        ],
        [
            InlineKeyboardButton("7", callback_data=7),
            InlineKeyboardButton("8", callback_data=8),
            InlineKeyboardButton("9", callback_data=9),
        ],
        [
            InlineKeyboardButton("Clear", callback_data='clear')
        ],
        [
            InlineKeyboardButton("+NC", callback_data='add_nc'),
            InlineKeyboardButton("-NC", callback_data='sub_nc')
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def write_attendance(nums=[], date=None, nc_nums=[]):
    if not date:
        date = datetime.date.today()

    attendance_string = 'Attendance for ' + str(date.day) + "/" + str(date.month) + "/" + str(date.year) + "\n\n"

    for i, cell in enumerate(NLIST.keys()):
        attendance_string += cell + ': ' + str(nums[i])
        if nc_nums[i] != 0:
            attendance_string += " + " + str(nc_nums[i])
        attendance_string += "\n"
    attendance_string += '\ntotal -> ' + str(sum(nums))
    if sum(nc_nums) > 0:
        attendance_string += " + " + str(sum(nc_nums))

    return attendance_string


async def set_group_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'group':
        global GROUPCHAT_ID
        GROUPCHAT_ID = update.effective_chat.id
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Group has been updated to id ' + str(update.effective_chat.id))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Invalid chat type used')


def get_nums(message):
    nums = []
    nc_nums = []
    for x in message.text.split('\n')[2:-2]:
        cell, raw_num = x.split(": ")
        num, *nc_num = raw_num.split(" + ")
        nums.append(int(num))
        if nc_num:
            nc_nums.append(int(nc_num[0]))
        else:
            nc_nums.append(0)

    return nums, nc_nums


def get_date_from_message(message):
    datedata = message.text.split('\n')[0].split(' ')[-1].split('/')
    day = int(datedata[0])
    month = int(datedata[1])
    year = int(datedata[2])
    return datetime.date(year, month, day)


def get_index_from_cell(cellname):
    if cellname in list(NLIST):
        return list(NLIST).index(cellname)
    else:
        return None


async def attendance_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    await query.answer()

    server = query.from_user.first_name
    cellname = get_cell_from_server(server)
    date = get_date_from_message(query.message)
    index = get_index_from_cell(cellname)
    nums, nc_nums = get_nums(query.message)

    if query.data.isdigit():

        nums[index] = ((nums[index]) * 10) + int(query.data)

    else:
        if query.data == 'clear':
            nums[index] = 0
            nc_nums[index] = 0

        elif query.data == 'add_nc':
            nc_nums[index] += 1

        elif query.data == 'sub_nc':
            if nc_nums[index] > 0:
                nc_nums[index] -= 1

    attendance_string = write_attendance(nums=nums, date=date, nc_nums=nc_nums)
    reply_markup = build_keyboard()
    if attendance_string == query.message.text:
        return

    await query.edit_message_text(attendance_string, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.effective_chat.id)


def get_value_from_day_name(day):
    days = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
    if day in days:
        return days.index(day)
    else:
        return None


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def set_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 2 and len(context.args[0]) == 3 and len(context.args[1]) == 4:
        day = get_value_from_day_name(context.args[0])
        if day is not None:
            chat_id = update.effective_message.chat_id
            settime = datetime.time(hour=int(context.args[1][:2]), minute=int(context.args[1][2:]),
                                    tzinfo=timezone('Asia/Singapore'))
            job_removed = remove_job_if_exists(context.args[0] + settime.isoformat(timespec='minutes'), context)
            context.job_queue.run_daily(poll_attendance, settime, days=(int(day),), chat_id=chat_id,
                                        name=context.args[0] + settime.isoformat(timespec='minutes'))
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Attendance scheduled for " + settime.isoformat(timespec='minutes'))
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="check date")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /set <mon/tues/wed/thu/fri/sat/sun> <time in 24h>\n\n e.g /set fri 2359")


async def unset_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    job_removed = remove_job_if_exists(context.args[0], context)
    text = "Poll successfully cancelled!" if job_removed else "No poll set for that time."
    await update.message.reply_text(text)


async def add_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) == 1:
            cell = context.args[0]
            name = update.message.from_user.first_name
            check = get_cell_from_server(name)
            if name not in NLIST[cell]:
                if not check:
                    NLIST[cell].append(name)
                    update_list()
                    await context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text="You've been added to " + cell)
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text="You are already in " + check)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text="You've already been added to " + cell)

        elif len(context.args) == 2:
            cell = context.args[0]
            name = context.args[1]
            check = get_cell_from_server(name)
            if not check:
                if name not in NLIST[cell]:
                    NLIST[cell].append(name)
                    update_list()
                    await context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text=name + " has been added to " + cell)
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text=name + " has already been added to " + cell)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=name + " is already in " + check)

        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Usage: /addserver <cell name> [server name]. If server's name is not "
                                                "provided, messenger's name will be used")
    except (IndexError, ValueError):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /addserver <cell name> [server "
                                                                              "name]. If server's name is not "
                                                                              "provided, messenger's name will be used")


async def del_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            name = update.message.from_user.first_name
            cell = get_cell_from_server(name)
            if name in NLIST[cell]:
                NLIST[cell].remove(name)
                update_list()
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text="You've been removed from " + cell)

        elif len(context.args) == 1:
            name = context.args[0]
            cell = get_cell_from_server(name)
            if cell:
                NLIST[cell].remove(name)
                update_list()
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=name + " has been removed from " + cell)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=name + " does not exist in data")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Usage: /delserver [server name]. If server's name is not provided, "
                                                "messenger's name will be used")

    except (IndexError, ValueError):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Usage: /delserver [server name]. If server's name is not provided, "
                                            "messenger's name will be used")


async def add_cell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 1:
        cell_name = context.args[0]
        NLIST[cell_name] = []
        update_list()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=cell_name + " has been added!")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /addcell <cell name>")


async def del_cell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 1 and context.args[0] in list(NLIST.keys()):
        cell = context.args[0]
        del NLIST[cell]
        update_list()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=cell + " has been removed")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /delcell <cell name>")


async def cells(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if NLIST:
        cell_string = ''
        for cell in list(NLIST.keys()):
            cell_string = cell_string + cell + " :\n" + '\n'.join(NLIST[cell]) + "\n\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=cell_string)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No cells")


async def show_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.jobs()
    if len(jobs) > 0:
        pollstring = 'Schedule:\n\n'
        for job in jobs:
            pollstring += str(job.name) + '\n'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=pollstring)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No polls queued")


if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).read_timeout(30).write_timeout(30).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('addserver', add_server))
    application.add_handler(CommandHandler('delserver', del_server))
    application.add_handler(CommandHandler('addcell', add_cell))
    application.add_handler(CommandHandler('delcell', del_cell))
    application.add_handler(CommandHandler('cells', cells))
    application.add_handler(CommandHandler('set', set_attendance))
    application.add_handler(CommandHandler('unset', unset_attendance))
    application.add_handler(CommandHandler('showsched', show_jobs))
    application.add_handler(CommandHandler('setgroup', set_group_chat))
    application.add_handler(CommandHandler('manualPoll', manual_poll_attendance))
    application.add_handler(CallbackQueryHandler(attendance_button))
    application.run_polling()
