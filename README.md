
# Telegram Quran Project Bot (Sorani)
بۆتێكی تێلگرام بۆ تۆمار/ڕاپۆرتی لەبەرکردنی ڕۆژانە — بەڕێوەبردنی هەفتە بە تەرزێكی تایبەتی.

## Features
- /start → قسەی گام‌به‌گام (ناو، ژمارە ١–١٠٠، ناوی/ژمارەی هاوڕێ، دۆخی ئەمڕۆ: بەڵێ/نەخێر)
- /done → تۆمارکردنی ئەمڕۆ
- /report → خشتەی هەفتە بەپێی ئەو قاعدانە: شەم تەنها شەم؛ یەک: شەم+یەک ... هەتا چوار
- /makeup YYYY-MM-DD → قەرەبوونی ڕۆژە نەكراوەکان
- /schedule → بڵاوکردنەوەی خۆکار لە 00:00 Asia/Baghdad (پێنجشەممە/هەینی بڵاوناكەوێت)

## Local run
```bash
pip install -r requirements.txt
cp .env.example .env  # توکن تێدا گۆڕە
python bot.py
```

## Deploy on Render (Worker)
1. Repo دروست بكە و ئەم پڕۆژەیە پۆش بكە بۆ GitHub.
2. بچۆ بۆ Render → New + → **Background Worker**.
3. بەستە بە repo ـەکەت.
4. **Start Command**: `python bot.py`
5. **Environment** → `BOT_TOKEN` تێبکە (لە BotFather بەرگیرەوە).
6. Deploy بکە. بۆتەکە بخە ناو گرووپ → `/schedule` بنووسە.

## Deploy on Railway
- New Project → Deploy from GitHub
- Service type: **Worker** (no HTTP)
- Add variable `BOT_TOKEN` → Deploy.

## Notes
- داتا لە `data.json` پاشەکەوت دەبێت. لە کڵاود هەمووچەند جار snapshot دەبێت — بەرگری بکە یان S3/DB دابنێ اگر پێویستە.
- توکن لە کۆد مهێڵە؛ تنها لە Environment Variables دابنێ.
