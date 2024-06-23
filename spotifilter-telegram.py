import os
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


TOKEN: Final = os.getenv("TELEGRAM_TOKEN")
USERNAME: Final = os.getenv("TELEGRAM_USERNAME")
POLLING_INTERVAL: Final = int(os.getenv("POLLING_INTERVAL", 5))


# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello, World!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Help message")


async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Custom command")


# Responses
def handle_response(text: str) -> str:
    if "hello" in text.lower():
        return "Hey there!"
    if "tomato paste" in text.lower():
        return "Who puts tomato paste in meatballs?!"
    if "28" in text:
        return "The 28th is the payout day!"

    return "I don't understand what you're saying."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_type = update.message.chat.type
    text = update.message.text
    print(f"User {update.message.chat.id} in {message_type}: {text}")

    if USERNAME not in text and message_type == "group":
        return

    response = handle_response(text)
    print(f"Bot: {response}")
    await update.message.reply_text(response)


async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"An error occurred in {update}: {context.error}")


def main() -> None:
    print("Starting bot...")
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("custom", custom_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(handle_error)

    # Run bot
    print("Polling...")
    app.run_polling(poll_interval=POLLING_INTERVAL)


if __name__ == "__main__":
    main()
