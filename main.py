from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
import os
import requests
from pydub import AudioSegment
import json

def ogg_to_wav(file_name):
    ogg_audio = AudioSegment.from_file(file_name+'.ogg', format='ogg')
    ogg_audio.export(file_name+'.wav', format="wav")

def wav_to_ogg(file_name):
    wav_audio = AudioSegment.from_file(file_name+'.wav', format='wav')
    wav_audio.export(file_name+'.ogg', format='ogg')

def send_voice_to_stt(audio_file):
    url = 'http://rav2.co.il:4444/speech_to_text'
    audio_file.download('check.ogg')
    file_name = 'check'
    ogg_to_wav(file_name)
    data = open(file_name+'.wav', 'rb')
    payload = {'sentence-audio': data}
    response = requests.post(url=url, files=payload)
    print(response.text)
    return json.loads(response.text)['output_text']

def send_text_to_parse_sentence(sentence):
    url = 'http://rav2.co.il:5000/parse_sentence'
    payload = {'sentence': sentence}
    response = requests.post(url=url, data=payload)
    print(response.text)
    return json.dumps(json.loads(response.text), indent=4, sort_keys=True)

def send_command_to_simulation(command):
    url = 'http://rav2.co.il:3000/response'
    command = json.loads(command)
    response = requests.post(url=url, json=command);
    print(response.text)
    return json.dumps(json.loads(response.text), indent=4, sort_keys=True)

def send_response_to_synthesizer(response):
    text = json.loads(response)['text']
    url ='http://rav2.co.il:3000/synth'
    response = requests.post(url=url, params={'text' : text})
    with open('synth.wav', 'wb') as f:
        f.write(response.content)
    wav_to_ogg('synth')

def handle_speech_to_text(bot, update):
    voice = bot.get_file(update.message.voice.file_id)
    try:
        text = send_voice_to_stt(voice)
    except:
        update.message.reply_text('Exception: Conversion from .ogg to .wav file')
    return text

def handle_main_proces(bot, update, text):
    print(type(text))
    print(text)
    try:
        text = send_text_to_parse_sentence(text)
    except:
        update.message.reply_text('Exception: Intent Command')
        return
    update.message.reply_text(text)

    try:
        text = send_command_to_simulation(text)
    except:
        update.message.reply_text('Exception: Response')
        return
    update.message.reply_text(text)
    try:
        send_response_to_synthesizer(text)
        synth = open('synth.ogg', "rb")
        chat_id = update.message.chat.id
        bot.send_voice(chat_id=chat_id, voice=synth)
    except:
        update.message.reply_text('Exception: Synth')
        return

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def voice_command(bot, update):
    """Echo the user message."""
    try:
        text = handle_speech_to_text(bot, update)
    except:
        update.message.reply_text('Exception: Speech To Text')
        return

    if text == " ":
        update.message.reply_text("Error: Can't detect speech")
        return
    else:
        update.message.reply_text(text)

    handle_main_proces(bot, update, text)

def text_command(bot, update):
    handle_main_proces(bot, update, update.message.text)
    #handle_main_proces(bot, update, "set frequency to 555.33")

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)

def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(os.environ["TELEGRAM_TOKEN"])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.voice, voice_command))
    dp.add_handler(MessageHandler(Filters.text, text_command))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()