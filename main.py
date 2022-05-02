import os
import logging
import requests

from dotenv import load_dotenv
from pydantic import BaseModel, parse_obj_as
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from telegram.ext import (
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
    CallbackContext,
)


load_dotenv()


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

__version__ = "0.0.2"


def start_command(update: Update, _):
    ikeyboard = [
        [InlineKeyboardButton("Site 🌐", url="https://telegra.ph/")],
    ]
    if os.getenv("SHOW_SOURCE_URL", "false").lower() == "true":
        ikeyboard.append(
            [
                InlineKeyboardButton(
                    "Developer 👨‍💻",
                    url="https://t.me/hasibulkabir",
                ),
                InlineKeyboardButton(
                    "Source Code 📚",
                    url="https://github.com/hasibulkabir/telegraphbot",
                ),
            ],
        )

    update.effective_message.reply_text(
        f"Hello {update.effective_message.from_user.mention_markdown_v2(update.effective_user.full_name)}.\n\n"
        "I can upload photos from telegram to telegra.ph 🤫",
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup(ikeyboard),
        quote=True,
    )


class UploadSuccess(BaseModel):
    src: str

    @property
    def url(self):
        return f"https://telegra.ph/{self.src}"


class UploadError(BaseModel):
    error: str


def upload_image(update: Update, context: CallbackContext):
    user_file = f"{update.effective_message.from_user.id}.jpg"
    context.bot.get_file(update.effective_message.photo[-1].file_id).download(
        user_file
    )

    if not os.path.exists(user_file):
        return update.effective_message.reply_text(
            "Failed to upload. Reason: File not found.",
            quote=True,
        )

    elif os.path.getsize(user_file) > 5242880:
        return update.effective_message.reply_text(
            "File size is greater than 5MB.",
            quote=True,
        )

    try:
        with open(user_file, "rb") as file:
            with requests.post(
                "https://telegra.ph/upload", files={"files": file}
            ) as resp:
                if resp.ok and isinstance(content := resp.json(), list):
                    model = parse_obj_as(list[UploadSuccess], content)
                    update.effective_message.reply_text(
                        model[0].url, quote=True
                    )

                elif isinstance(content, dict):
                    model = parse_obj_as(UploadError, resp.json())
                    return update.effective_message.reply_text(
                        f"Failed to upload. Reason: {model.error}",
                        quote=True,
                    )

                else:
                    return update.effective_message.reply_text(
                        f"Failed to upload. Reason: {content}",
                        quote=True,
                    )

    finally:
        os.remove(user_file)


def upload(update: Update, context: CallbackContext):
    if not update.effective_message:
        return

    if update.effective_message.document.file_size > 5242880:
        return update.effective_message.reply_text(
            "File size is greater than 5MB.",
            quote=True,
        )

    if update.effective_message.document.file_name[-3:].lower() not in [
        "jpg",
        "peg",
        "png",
        "gif",
        "mp4",
    ]:
        return update.effective_message.reply_text(
            "File type not supported.", quote=True
        )

    user_file = f'{str(update.effective_message.from_user.id)}.{update.effective_message.document.file_name.rsplit(".", 1)[-1]}'
    context.bot.get_file(update.effective_message.document.file_id).download(
        user_file
    )

    if not os.path.exists(user_file):
        return update.effective_message.reply_text(
            "Failed to upload. Reason: File not found.",
            quote=True,
        )

    try:
        with open(user_file, "rb") as file:
            with requests.post(
                "https://telegra.ph/upload", files={"files": file}
            ) as resp:
                if resp.ok and isinstance(content := resp.json(), list):
                    model = parse_obj_as(list[UploadSuccess], content)
                    update.effective_message.reply_text(
                        model[0].url, quote=True
                    )
                elif isinstance(content, dict):
                    model = parse_obj_as(UploadError, resp.json())
                    return update.effective_message.reply_text(
                        f"Failed to upload. Reason: {model.error}",
                        quote=True,
                    )
                else:
                    return update.effective_message.reply_text(
                        f"Failed to upload. Reason: {content}",
                        quote=True,
                    )

    finally:
        os.remove(user_file)


def error(_, context: CallbackContext):
    logger.error(context.error, exc_info=True)


def main():
    updater = Updater(token=os.getenv("BOT_TOKEN", ""), use_context=True)
    updater.dispatcher.add_handler(
        CommandHandler(
            "start",
            start_command,
            filters=Filters.chat_type.private,
        )
    )
    updater.dispatcher.add_handler(
        MessageHandler(Filters.photo & Filters.chat_type.private, upload_image)
    )
    updater.dispatcher.add_handler(
        MessageHandler(Filters.document & Filters.chat_type.private, upload)
    )
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
