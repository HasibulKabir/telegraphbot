import os
import logging
import requests

from telegram import Update
from pydantic import BaseModel, parse_obj_as
from dotenv import load_dotenv

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

__version__ = "0.0.1"


def start_command(update: Update, _):
    update.message.reply_text(
        f"Hello {update.message.from_user.first_name}.\n\n"
        "I can upload photos from telegram to telegra.ph 🤫"
    )


class UploadSuccess(BaseModel):
    src: str

    @property
    def url(self):
        return f"https://telegra.ph/{self.src}"


class UploadError(BaseModel):
    error: str


def upload_image(update: Update, context: CallbackContext):
    user_file = f"{update.message.from_user.id}.jpg"
    context.bot.get_file(update.message.photo[-1].file_id).download(user_file)

    if not os.path.exists(user_file):
        return update.message.reply_text(
            "Failed to upload. Reason: File not found"
        )

    elif os.path.getsize(user_file) > 5242880:
        return update.message.reply_text("File size is greater than 5MB")

    try:
        with open(user_file, "rb") as file:
            with requests.post(
                "https://telegra.ph/upload", files={"files": file}
            ) as resp:
                if resp.ok and isinstance(content := resp.json(), list):
                    model = parse_obj_as(list[UploadSuccess], content)
                    update.message.reply_text(model[0].url)

                elif isinstance(content, dict):
                    model = parse_obj_as(UploadError, resp.json())
                    return update.message.reply_text(
                        f"Failed to upload. Reason: {model.error}"
                    )

                else:
                    return update.message.reply_text(
                        f"Failed to upload. Reason: {content}"
                    )

    finally:
        os.remove(user_file)


def upload(update: Update, context: CallbackContext):
    if update.message.document.file_size > 5242880:
        return update.message.reply_text("File size is greater than 5MB")

    if update.message.document.file_name[-3:].lower() not in [
        "jpg",
        "peg",
        "png",
        "gif",
        "mp4",
    ]:
        return update.message.reply_text("File type not supported.")

    user_file = f'{str(update.message.from_user.id)}.{update.message.document.file_name.rsplit(".", 1)[-1]}'
    context.bot.get_file(update.message.document.file_id).download(user_file)

    if not os.path.exists(user_file):
        return update.message.reply_text(
            "Failed to upload. Reason: File not found"
        )

    try:
        with open(user_file, "rb") as file:
            with requests.post(
                "https://telegra.ph/upload", files={"files": file}
            ) as resp:
                if resp.ok and isinstance(content := resp.json(), list):
                    model = parse_obj_as(list[UploadSuccess], content)
                    update.message.reply_text(model[0].url)
                elif isinstance(content, dict):
                    model = parse_obj_as(UploadError, resp.json())
                    return update.message.reply_text(
                        f"Failed to upload. Reason: {model.error}"
                    )
                else:
                    return update.message.reply_text(
                        f"Failed to upload. Reason: {content}"
                    )

    finally:
        os.remove(user_file)


def error(_, context: CallbackContext):
    logger.error(context.error, exc_info=True)


def main():
    updater = Updater(token=os.getenv("BOT_TOKEN", ""), use_context=True)
    updater.dispatcher.add_handler(CommandHandler("start", start_command))
    updater.dispatcher.add_handler(MessageHandler(Filters.photo, upload_image))
    updater.dispatcher.add_handler(MessageHandler(Filters.document, upload))
    updater.dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
