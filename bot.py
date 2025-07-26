from telegram.ext import Updater
import config

def main() -> None:
    updater = Updater(config.TOKEN)
    dispatcher = updater.dispatcher

    from handlers import start, button
    dispatcher.add_handler(config.start_handler)
    dispatcher.add_handler(config.button_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
