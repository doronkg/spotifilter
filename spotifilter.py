"""Spotifilter harnesses ChatGPT to effortlessly filter explicit tracks from your Spotify playlists\
, ensuring a clean and family-friendly listening experience."""

import os
import time
import spotipy
import requests
import asyncio
from typing import Final
from openai import OpenAI
from dotenv import load_dotenv
from lyricsgenius import Genius
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


# Load environment variables
load_dotenv()
GENIUS_API_KEY: Final = os.getenv("GENIUS_API_KEY")
OPENAI_API_KEY: Final = os.getenv("OPENAI_API_KEY")
BOT_TOKEN: Final = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME: Final = os.getenv("TELEGRAM_USERNAME")
BOT_POLLING_INTERVAL: Final = float(os.getenv("POLLING_INTERVAL", 0.0))


def get_playlist_info(playlist_id: str) -> tuple[bool, str, list]:
    """Return the playlist information."""
    auth_manager = SpotifyClientCredentials()
    sp = spotipy.Spotify(auth_manager=auth_manager)

    try:
        playlist = sp.playlist(playlist_id)
        return (
            True,
            "Looking for explicit content in playlist " \
            f"'{playlist['name']}' by '{ playlist['owner']['display_name']}'... 🔍",
            [ playlist["name"], playlist["owner"]["display_name"], playlist["tracks"]["total"], ]
        )
    except spotipy.SpotifyException as e:
        if e.http_status == 404:
            return False, "Playlist not found. Please check if the playlist ID is correct.", []
        else:
            return False, "An error occurred. Validate your input and retry, or run '/report'", []


def get_playlist_tracks(playlist_id):
    """Return playlist tracks."""
    auth_manager = SpotifyClientCredentials()
    sp = spotipy.Spotify(auth_manager=auth_manager)
    track_list = []

    try:
        playlist = sp.playlist(playlist_id)
        for track in playlist["tracks"]["items"]:
            track_list.append(
                (track["track"]["name"], track["track"]["artists"][0]["name"])
            )
        return track_list
    except spotipy.SpotifyException as e:
        if e.http_status == 404:
            print("Playlist not found. Please check if the playlist ID is correct.")
        else:
            print("An error occurred:", e)
        return None


def get_song_lyrics(title, artist):
    """Return song lyrics."""
    genius = Genius(GENIUS_API_KEY)

    try:
        song_lyrics = genius.search_song(title, artist)
        if song_lyrics:
            return song_lyrics.lyrics
    except requests.exceptions.Timeout as e:
        print("An error occurred:", e)
    return None


def check_explicitly(title, artist, lyrics):
    """Check for explicit content in lyrics."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    explicit_content = [
        "violence",
        "sex",
        "drugs",
        "alcoholism",
        "addiction",
        "smoking",
        "profanity",
    ]

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {
                "role": "system",
                "content": "Your are a helpful assistant designed to determine if a track contains "
                "explicit content, to ensure a clean and family-friendly listening experience\n"
                "The explicit content should be listed by line numbers.",
            },
            {
                "role": "system",
                "content": "For each track lyrics, go through these steps:\n"
                "Firstly, remove stanza lines ([Chorus], [Bridge], etc...).\n"
                "1. List every line containing explicit content related to one or more "
                f"topics: {explicit_content} with line number.\n"
                "2. The header of your response should be:\nTITLE: 'title', ARTIST: "
                "'artist', EXPLICIT: TRUE/FALSE, REASONS: [].\nTRUE if contains explicit content"
                ", FALSE if not.\nREASONS should contain why it's considered explicit, with one or "
                f"more topics from this list: {explicit_content}\n."
                "3. Squash the line numbers of repeated lines from the output.\n"
                "4. Censor profanity words in the output.\n",
            },
            {
                "role": "user",
                "content": "Song: 'Leftovers', Artist: 'Dennis Lloyd', Lyrics:\nI'm a drunk and I "
                "will always be\nBegging, Baby, take my hand before I fall back down\n"
                "Fuck, I'm about to lose it all\nFuck, I'm about to lose it all",
            },
            {
                "role": "assistant",
                "content": "TITLE: 'Leftovers', ARTIST: 'Dennis Lloyd', EXPLICIT: TRUE, REASONS: "
                "['alcoholism', 'profanity'].\n- Line 1 - I'm a drunk and I will always be\n"
                "- Lines [3-4] - F***, I'm about to lose it all",
            },
            {
                "role": "user",
                "content": "Song: 'Hello', Artist: 'Adele', Lyrics:\nHello, it's me\nI was "
                "wondering if after all these years you'd like to meet\nTo go over everything",
            },
            {
                "role": "assistant",
                "content": "TITLE: 'Hello', ARTIST: 'Adele', EXPLICIT: FALSE, REASONS: [].",
            },
            {
                "role": "user",
                "content": "Song: 'Playa (Say That)', Artist: 'Dennis Lloyd', Lyrics:\nHow could "
                "you say that\nHow could you fucking say that\nHow could you say that\nHow could "
                "you fucking say that\nBaby hold on, baby hold on\nSay my motherfuckin name\nWhile "
                "we're fuckin all night long",
            },
            {
                "role": "assistant",
                "content": "TITLE: 'Playa (Say That)', ARTIST: 'Dennis Lloyd', EXPLICIT: TRUE, "
                "REASONS: ['profanity', 'sex'].\n- Lines [2, 4] - How could you f***ing say that\n"
                "- Line 6 - Say my motherf***in name\n- Line 7 - While we're f***in all night long",
            },
            {
                "role": "user",
                "content": f"Song: '{title}', Artist: '{artist}', Lyrics:\n{lyrics}",
            },
        ],
    )

    return (
        completion.choices[0].message.content
        + "\n\n"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to Spotifilter!")


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("You need to provide a playlist ID after the /filter command.")
    else:
        await update.message.reply_text(get_playlist_info(context.args[0])[1])
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, logic, context.args[0])
        await update.message.reply_text(report)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Please send any reports or bugs to us here: "
                                    "https://github.com/doronkg/spotifilter/issues")


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("I don't know what it is.")


async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"An error occurred in {update}: {context.error}")


def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("filter", filter_command))
    app.add_handler(CommandHandler("report", report_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_unknown))
    app.add_handler(MessageHandler(filters.COMMAND, handle_unknown))

    # Errors
    app.add_error_handler(handle_error)

    # Run bot
    print("Polling...")
    app.run_polling(poll_interval=BOT_POLLING_INTERVAL)


def logic(playlist_id: str) -> str:
    """Track filtering starts here"""
    status, message, result = get_playlist_info(playlist_id)

    if status:
        playlist_name, playlist_author, playlist_total = result

        track_list = get_playlist_tracks(playlist_id)
        explicit_counter = 0
        explicit_tracks = []

        for i, track in enumerate(track_list, start=1):
            print(f"\n({i}/{playlist_total})")
            title, artist = track
            song_lyrics = get_song_lyrics(title, artist)

            if song_lyrics:
                explicitly_result = check_explicitly(title, artist, song_lyrics)
                if "EXPLICIT: TRUE" in explicitly_result:
                    explicit_counter += 1
                    explicit_tracks.append(explicitly_result)
                time.sleep(3)

        if explicit_counter == 0:
            return "\n\nPlaylist is valid! No explicit content was found!"
        else:
            response = f"\n\n🔉🔉🔉\nPlaylist contains {explicit_counter} explicit tracks " \
                       "and may not fit all audiences.\n"
            for track in explicit_tracks:
                response += "\n" + track

            return response


if __name__ == "__main__":
    main()
