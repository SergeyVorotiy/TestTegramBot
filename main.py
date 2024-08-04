import Bot

if __name__ == '__main__':

    while True:
        try:
            Bot.bot.infinity_polling()
        except:
            continue
