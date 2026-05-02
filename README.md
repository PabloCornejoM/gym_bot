# GymBot

Automates gym slot reservations on [agendaqr.cl](https://www.agendaqr.cl). Logs in with RUT, picks preferred time slot 3 days in advance, and sends a confirmation screenshot to your phone via Telegram.

Two run modes:
- **Scheduled** (`main.py`) — meant for cron, books the next available preferred slot 3 days out
- **On-demand** (`listener.py`) — polls Telegram and books immediately when you send a message

## Features

- Books your gym session 3 days ahead (the booking window the site allows)
- Tries slots in priority order, falls back to first available
- On-demand booking via Telegram — send a time like `"14:00"` or just any message to use the current hour's slot
- Sends a Telegram notification with a screenshot on success or failure
- Runs headless — no display needed, works on a Linux server
- Configurable via `.env` — no credentials in code

## Requirements

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda
- A Telegram bot ([setup guide](#telegram-setup))

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/gym_bot.git
cd gym_bot

# 2. Create and activate the conda environment
conda env create -f environment.yml
conda activate gym_bot

# 3. Install the Chromium browser
playwright install chromium

# On Linux, also run:
playwright install-deps chromium
```

## Configuration

Create a `.env` file in the project root:

```env
RUT=12345678-9
GYM_URL=https://www.agendaqr.cl/agenda/24/ingresar
HEADLESS=true
PREFERRED_SLOTS=08:00 - 09:00,09:00 - 10:00,10:00 - 11:00

TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

| Variable | Description |
|---|---|
| `RUT` | Your Chilean RUT (e.g. `12345678-9`) |
| `GYM_URL` | Login URL for your gym on agendaqr.cl |
| `HEADLESS` | `true` for servers, `false` to watch the browser |
| `PREFERRED_SLOTS` | Comma-separated time slots in priority order |
| `TELEGRAM_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram user ID |

## Telegram Setup

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts — copy the token it gives you
3. Send any message to your new bot, then open this URL in your browser:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Find `"chat": {"id": 123456789}` — that number is your Chat ID

## Usage

### Scheduled mode

Run once to book 3 days ahead using your preferred slots:

```bash
conda activate gym_bot
python main.py
```

### On-demand mode (Telegram listener)

Keep this running on your server. Send a message to your bot to trigger a booking:

```bash
conda activate gym_bot
python listener.py
```

- Send **any message** → books the slot for the current hour
- Send a **time** like `"14:00"` or `"14"` → books that specific slot
- Messages from unauthorized chat IDs are ignored

## Automated Daily Runs (Linux + cron)

To run the bot automatically every day at 7:00 AM:

```bash
crontab -e
```

Add this line (adjust paths to match your setup):

```
0 7 * * * /home/user/miniconda3/envs/gym_bot/bin/python /home/user/gym_bot/main.py >> /home/user/gym_bot/gymbot.log 2>&1
```

## Debugging

Screenshots are saved in the project folder at each step:

| File | When |
|---|---|
| `01_login.png` | Login page loaded |
| `02_calendar.png` | After login |
| `03_modal.png` | After clicking today's cell |
| `04_before_submit.png` | Form filled, before submitting |
| `05_result.png` | After submission |
| `error.png` | If something goes wrong |

To watch the browser instead of running headless, set `HEADLESS=false` in your `.env`.

## How It Works

1. Launches a Chromium browser and navigates to the gym login page
2. Fills in the RUT and submits the login form
3. Finds the target date cell (3 days from now) on the FullCalendar calendar and clicks it
4. In the booking modal: selects branch, preferred time slot, and activity
5. Checks the oath checkbox and clicks Save
6. Sends the result screenshot to Telegram

The listener mode follows the same booking flow, but triggers on incoming Telegram messages instead of a cron schedule, and lets you specify a slot inline in the message text.

## License

MIT
