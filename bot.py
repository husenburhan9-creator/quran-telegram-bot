
import os, json, datetime, re
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# -------- Settings --------
TZ = ZoneInfo("Asia/Baghdad")          # کاتی هەولێر
DATA_FILE = Path("data.json")          # پاشەکەوتی داتا
MIDNIGHT_HOUR = 0                      # 00:00
POST_DAYS = {5, 6, 0, 1, 2}            # شەم(5) یەک(6) دوو(0) سێ(1) چوار(2)
# Thu(3), Fri(4) — باڵا نەكەوێت

# -------- Persistence --------
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {},          # uid -> {name, number, friend_name, friend_number}
        "done": {},           # "YYYY-MM-DD" -> [uid, ...]
        "makeups": {},        # "YYYY-MM-DD" -> [uid, ...]  (قەرەبوون)
        "group_ids": []       # chats کاراکراو بۆ ڕاپۆرتی خۆکار
    }

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=2)

DATA = load_data()

def today_str():
    return datetime.datetime.now(TZ).date().isoformat()

def label_user(uid: str):
    u = DATA["users"].get(uid)
    if not u: return uid
    base = u.get("name") or uid
    num  = u.get("number")
    return f"{base} ({num})" if num else base

# -------- Conversation states --------
NAME, NUMBER, FRIEND_NAME, FRIEND_NUMBER, TODAY_DONE = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    # تۆمارکردنی گرووپ بۆ ڕاپۆرتی خۆکار
    if chat.type in ("group", "supergroup"):
        if chat.id not in DATA["group_ids"]:
            DATA["group_ids"].append(chat.id)
            save_data()
    await update.message.reply_text("بەخێر بێیت بۆ بۆتی پڕۆژەی تەمەن 🌙")
    await update.message.reply_text("٢) ناوی خۆت بنووسە:")
    return NAME

async def name_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = (update.message.text or "").strip()
    DATA["users"].setdefault(uid, {})
    DATA["users"][uid]["name"] = name
    save_data()
    await update.message.reply_text("٣) ژمارەکەت هەڵبژێرە (١–١٠٠) وەک تێکست بنووسە:")
    return NUMBER

def valid_num(txt: str):
    if not re.fullmatch(r"\d{1,3}", txt or ""): return None
    n = int(txt)
    return n if 1 <= n <= 100 else None

async def number_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    n = valid_num(update.message.text)
    if n is None:
        await update.message.reply_text("تکایە ژمارەیەکی نێوان ١ تا ١٠٠ بنووسە.")
        return NUMBER
    DATA["users"].setdefault(uid, {})
    DATA["users"][uid]["number"] = n
    save_data()
    await update.message.reply_text("٤) ناوی هاوڕێکەت بنووسە:")
    return FRIEND_NAME

async def friend_name_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    fname = (update.message.text or "").strip()
    DATA["users"].setdefault(uid, {})
    DATA["users"][uid]["friend_name"] = fname
    save_data()
    await update.message.reply_text("٥) ژمارەی هاوڕێکەت بنووسە (١–١٠٠):")
    return FRIEND_NUMBER

async def friend_number_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    n = valid_num(update.message.text)
    if n is None:
        await update.message.reply_text("تکایە ژمارەیەکی نێوان ١ تا ١٠٠ بنووسە.")
        return FRIEND_NUMBER
    DATA["users"].setdefault(uid, {})
    DATA["users"][uid]["friend_number"] = n
    save_data()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("بەڵێ ✅", callback_data="done_yes"),
         InlineKeyboardButton("نەخێر ❌", callback_data="done_no")]
    ])
    await update.message.reply_text("٦) لەبەرکردنی ئەمڕۆت ئەنجامداوە؟", reply_markup=kb)
    return TODAY_DONE

async def today_done_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    day = today_str()
    DATA["done"].setdefault(day, [])
    if q.data == "done_yes" and uid not in DATA["done"][day]:
        DATA["done"][day].append(uid)
    save_data()
    await q.edit_message_text("سوپاس! تۆماركرایەوە. فەرمانە بەکاربهێنە: /report ، /makeup YYYY-MM-DD")
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفتوگۆ هەڵوەشاوە.")
    return ConversationHandler.END

# -------- Commands: done / report / makeup --------
async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    day = today_str()
    DATA["done"].setdefault(day, [])
    if uid not in DATA["done"][day]:
        DATA["done"][day].append(uid)
        save_data()
        await update.message.reply_text("✅ تۆماركرایەوە: ئەمڕۆت كرد.")
    else:
        await update.message.reply_text("پێشترش تۆمار كردووەی 😄")

def week_start_for(d: datetime.date):
    # شەممە (Saturday=5) وەک سەرەتای هەفتە
    wd = d.weekday()            # Mon=0 ... Sun=6
    back = (wd - 5) % 7
    return d - datetime.timedelta(days=back)

POST_DAYS = {5, 6, 0, 1, 2}  # Sat..Wed

def included_days_for(d: datetime.date):
    if d.weekday() not in POST_DAYS:
        return []
    start = week_start_for(d)
    days = []
    cur = start
    while cur <= d:
        days.append(cur)
        cur += datetime.timedelta(days=1)
    return days

def format_table(for_date: datetime.date):
    days = included_days_for(for_date)
    if not days:
        return None

    day_labels = {
        5: "شەم", 6: "یەک", 0: "دوو", 1: "سێ", 2: "چوار", 3: "پێنج", 4: "هەینی"
    }
    cols = [f"{day_labels[d.weekday()]}-{d.strftime('%m/%d')}" for d in days]

    uids = list(DATA["users"].keys())
    uids.sort(key=lambda x: (DATA["users"][x].get("number", 9999), DATA["users"][x].get("name","")))

    lines = []
    lines.append("📊 خشتەی ڕاپۆرت\n")
    header = "👤 ناسناو".ljust(18) + " | " + " | ".join(c.ljust(8) for c in cols)
    lines.append(header)
    lines.append("-" * len(header))

    for uid in uids:
        row = label_user(uid).ljust(18) + " | "
        marks = []
        for d in days:
            key = d.isoformat()
            ok = uid in set(DATA["done"].get(key, []))
            marks.append(("✅" if ok else "❌").ljust(8))
        row += " | ".join(marks)
        lines.append(row)

    # بەشی قەرەبوون
    if DATA.get("makeups"):
        relevant = [d.isoformat() for d in days if d.isoformat() in DATA["makeups"] and DATA["makeups"][d.isoformat()]]
        if relevant:
            lines.append("\n🟨 قەرەبوونی ڕۆژە نەكراوەكان:")
            for key in relevant:
                who = [label_user(u) for u in DATA["makeups"].get(key, [])]
                lines.append(f"• {key}: " + (", ".join(who) if who else "—"))

    return "\n".join(lines)

async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(TZ).date()
    txt = format_table(now)
    if not txt:
        await update.message.reply_text("ئەم ڕۆژە بڵاودانەوە نییە (پێنجشەممە/هەینی دەچێتە ناو).")
        return
    await update.message.reply_text(txt)

async def makeup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /makeup YYYY-MM-DD
    if len(context.args) != 1:
        await update.message.reply_text("بەکاربهێنە: /makeup 2025-10-12")
        return
    try:
        d = datetime.date.fromisoformat(context.args[0])
    except ValueError:
        await update.message.reply_text("فۆرمات هەڵەیە. نمونە: 2025-10-12")
        return
    uid = str(update.effective_user.id)
    DATA["makeups"].setdefault(d.isoformat(), [])
    if uid not in DATA["makeups"][d.isoformat()]:
        DATA["makeups"][d.isoformat()].append(uid)
        save_data()
        await update.message.reply_text(f"🟨 قەرەبوون تۆمار كرایەوە بۆ {d.isoformat()}.")
    else:
        await update.message.reply_text("پێشتر قەرەبوونت بۆ ئەم ڕۆژە تۆماركراوە.")

# -------- Scheduling (daily auto-post at 00:00, Sat..Wed only) --------
async def _auto_daily_report(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(TZ).date()
    if now.weekday() not in POST_DAYS:
        return
    txt = format_table(now)
    if not txt:
        return
    for gid in DATA.get("group_ids", []):
        try:
            await context.bot.send_message(chat_id=gid, text=txt)
        except Exception:
            pass

async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in DATA["group_ids"]:
        DATA["group_ids"].append(chat_id)
        save_data()

    # Remove old job
    for job in context.job_queue.get_jobs_by_name("midnight_report"):
        job.schedule_removal()

    now = datetime.datetime.now(TZ)
    first = now.replace(hour=MIDNIGHT_HOUR, minute=0, second=0, microsecond=0)
    if first <= now:
        first += datetime.timedelta(days=1)

    context.job_queue.run_daily(
        _auto_daily_report,
        time=first.timetz(),            # 00:00 local TZ
        days=(0,1,2,3,4,5,6),
        name="midnight_report",
    )
    await update.message.reply_text("🕛 ڕاپۆرتی خۆکار لە 00:00 (کاتی هەولێر) چالاک کرا. پێنجشەممە/هەینی بڵاوناكەوێت.")

# -------- Friendly hint (non-command texts) --------
async def text_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        await update.message.reply_text("فەرمانەکان: /start ، /done ، /report ، /makeup YYYY-MM-DD ، /schedule")

# -------- Main --------
def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN نەدۆزرایەوە — لە .env دابنێ.")

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_step)],
            NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, number_step)],
            FRIEND_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, friend_name_step)],
            FRIEND_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, friend_number_step)],
            TODAY_DONE: [CallbackQueryHandler(today_done_cb, pattern="^done_(yes|no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("done", done_cmd))
    app.add_handler(CommandHandler("report", report_cmd))
    app.add_handler(CommandHandler("makeup", makeup_cmd))
    app.add_handler(CommandHandler("schedule", schedule_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_hint))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
