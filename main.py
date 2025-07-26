from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import config

def main() -> None:
    updater = Updater(token=config.TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", config.start))
    dispatcher.add_handler(CallbackQueryHandler(config.button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()


