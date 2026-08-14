import argparse
import os
import re
import shutil
import sys
import traceback
import colorama
from colorama import Fore, Style
from yt_dlp import YoutubeDL
from yt_dlp.cookies import SUPPORTED_BROWSERS
from yt_dlp.utils import DownloadError


# YouTube video ids are always 11 characters of this alphabet
VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')

ACCEPTED_URL_PREFIXES = (
    "https://www.youtube.com/",
    "https://youtube.com/",
    "https://m.youtube.com/",
    "https://music.youtube.com/",
    "https://youtu.be/",
    "http://www.youtube.com/",
    "http://youtube.com/",
    "http://youtu.be/",
)


def prepare_console():
    """Make the console behave the same on Windows as it does elsewhere."""
    # Without this, cmd.exe and older terminals print the colour codes as literal garbage
    colorama.init()

    # Video titles are often non-latin, and the legacy Windows code pages can't encode them.
    # Replacing the odd character is much better than crashing right before a finished download.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass


def has_ffmpeg():
    """ffmpeg ships with macOS package managers but is rarely present on a fresh Windows box."""
    return shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None


def normalize_input_url(user_input):
    """Turn a bare video id or a YouTube URL into a full watch URL, or None if it is neither."""
    # A bare video id is expanded into a normal watch URL
    if VIDEO_ID_PATTERN.match(user_input):
        return 'https://www.youtube.com/watch?v=' + user_input

    if user_input.startswith(ACCEPTED_URL_PREFIXES):
        return user_input

    # Tolerate URLs pasted without the scheme, like "youtube.com/watch?v=..."
    for bare_host in ('www.youtube.com/', 'youtube.com/', 'm.youtube.com/', 'music.youtube.com/', 'youtu.be/'):
        if user_input.startswith(bare_host):
            return 'https://' + user_input

    return None


def should_overwrite(output_file_path, force_overwrite):
    """Decide whether an already existing output file may be replaced."""
    if force_overwrite:
        print(Fore.YELLOW + 'INFO!' + Style.RESET_ALL + ' Overwriting existing file at "' + output_file_path + '"')
        return True

    # Without a terminal there is nobody to ask, so keep the safe old behaviour.
    # On Windows a GUI-launched process can have no stdin at all, hence the None check.
    if sys.stdin is None or not sys.stdin.isatty():
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' File already exists at "' + output_file_path + '" and we don\'t want to accidentally overwrite it, pass -f to overwrite it')
        return False

    print(Fore.YELLOW + 'WARNING!' + Style.RESET_ALL + ' File already exists at "' + output_file_path + '"')
    try:
        answer = input('Overwrite it? [y/N] ').strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        answer = ''

    if answer in ('y', 'yes'):
        return True

    print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Keeping the existing file, nothing was downloaded')
    return False


def main():
    prepare_console()

    # Pars all CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('url', metavar='U', type=str, nargs='?', help='youtube video url or bare video id which needs to be downloaded, like "https://www.youtube.com/watch?v=Fd_3EkGr0-4", "https://youtu.be/Fd_3EkGr0-4" or just "Fd_3EkGr0-4"')
    parser.add_argument('mode', metavar='M', type=str, nargs='?', choices=["mp3", "mp4", "audio", "video"], default="mp4", help='download mode can be "mp3"/"mp4"/"audio"/"video"')
    parser.add_argument('-o', metavar='o', type=str, nargs='?', default="", help='output directory (optional, defaults to current working directory)')
    parser.add_argument('-c', '--cookies-from-browser', metavar='BROWSER', type=str, nargs='?', default=None, const='chrome', help='load cookies from a browser to download age-restricted or private videos, like "chrome"/"safari"/"firefox" (optionally "chrome:ProfileName"), defaults to "chrome" when given without a browser name')
    parser.add_argument('--cookies', metavar='FILE', type=str, default=None, help='load cookies from a Netscape-format cookies.txt file instead of a browser')
    parser.add_argument('-f', '--force', action='store_true', help='overwrite the output file if it already exists, without asking')
    args = parser.parse_args()
    input_mode = args.mode
    input_url = args.url
    input_output_folder_path = args.o
    input_cookies_from_browser = args.cookies_from_browser
    input_cookies_file = args.cookies
    input_force_overwrite = args.force
    cwd_path = os.getcwd()

    # Make sure URL is valid
    if input_url is None or len(str(input_url).strip()) == 0:
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Please provide a valid YouTube URL like "https://www.youtube.com/watch?v=Fd_3EkGr0-4" or "https://youtu.be/Fd_3EkGr0-4"')
        exit(1)
    input_url = normalize_input_url(str(input_url).strip())
    if input_url is None:
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Please provide a valid YouTube URL like "https://www.youtube.com/watch?v=Fd_3EkGr0-4" or "https://youtu.be/Fd_3EkGr0-4", or just the video id like "Fd_3EkGr0-4"')
        exit(2)

    # Decide where to save the video (default to current working dir)
    output_folder_path = cwd_path
    if input_output_folder_path is not None:
        input_output_folder_path = str(input_output_folder_path).strip()

        # Strip the path of trailing slashes, on Windows those can be backslashes too.
        # normpath leaves drive roots like "C:\" alone, which is exactly what we want.
        if len(input_output_folder_path) > 0:
            input_output_folder_path = os.path.normpath(os.path.expanduser(input_output_folder_path))

        # If a path was submitted
        if len(input_output_folder_path) > 0:
            # Make sure path exists
            if not os.path.exists(input_output_folder_path):
                print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Specified output directory doesn\'t exist "' + str(input_output_folder_path) + '"')
                exit(3)
            else:
                output_folder_path = input_output_folder_path

    # Work out where cookies should come from (needed for age-restricted or private videos)
    cookies_from_browser = None
    if input_cookies_from_browser is not None:
        # yt-dlp expects a (browser, profile, keyring, container) tuple, we support "browser" and "browser:profile"
        browser_name, _, browser_profile = str(input_cookies_from_browser).strip().partition(':')
        browser_name = browser_name.lower()
        if browser_name not in SUPPORTED_BROWSERS:
            print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Unsupported browser "' + browser_name + '", supported ones are ' + ', '.join(sorted(SUPPORTED_BROWSERS)))
            exit(5)
        cookies_from_browser = (browser_name, browser_profile or None, None, None)

    cookies_file = None
    if input_cookies_file is not None:
        cookies_file = str(input_cookies_file).strip()
        if not os.path.exists(cookies_file):
            print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Specified cookies file doesn\'t exist "' + cookies_file + '"')
            exit(6)

    # Extra error if download mode is invalid
    if input_mode not in ["mp3", "audio", "mp4", "video"]:
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Please provide a valid download mode like "mp3"/"mp4"/"audio"/"video"')
        exit(4)

    is_audio = input_mode in ["mp3", "audio"]
    target_extension = 'mp3' if is_audio else 'mp4'

    # mp3 conversion and merging separate video/audio streams both need ffmpeg
    ffmpeg_available = has_ffmpeg()
    if is_audio and not ffmpeg_available:
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' ffmpeg is required to save audio as mp3 but it wasn\'t found on PATH')
        print(Fore.YELLOW + 'INFO!' + Style.RESET_ALL + ' Install it with "winget install Gyan.FFmpeg" on Windows, "brew install ffmpeg" on macOS, or your package manager on Linux')
        exit(7)

    # Common options, yt-dlp handles the throwaway intermediate files itself
    ydl_options = {
        'outtmpl': os.path.join(output_folder_path, '%(title)s.%(ext)s'),
        'overwrites': False,
        'noprogress': False,
        'quiet': True,
        'no_warnings': True,
        'consoletitle': False,

        # YouTube requires solving a JS "n challenge" before it hands out real media formats.
        # Enable every runtime we might find locally (unavailable ones are simply skipped), and
        # allow yt-dlp to fetch its official EJS solver script, which it caches after the first run.
        'js_runtimes': {'deno': {}, 'node': {}, 'bun': {}, 'quickjs': {}},
        'remote_components': ['ejs:github'],
    }
    if cookies_from_browser is not None:
        ydl_options['cookiesfrombrowser'] = cookies_from_browser
    if cookies_file is not None:
        ydl_options['cookiefile'] = cookies_file
    if is_audio:
        ydl_options['format'] = 'bestaudio/best'
        ydl_options['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    elif not ffmpeg_available:
        # Nothing can be merged without ffmpeg, so stick to the streams that already carry both
        # video and audio in a single file, at the cost of a lower maximum resolution
        print(Fore.YELLOW + 'WARNING!' + Style.RESET_ALL + ' ffmpeg wasn\'t found on PATH, falling back to a lower quality single-file stream')
        ydl_options['format'] = 'best[vcodec^=avc1][acodec!=none]/best[ext=mp4][acodec!=none]/best'
    else:
        # Prefer H.264 ("avc1") - AV1 and VP9 play back poorly in QuickTime, Windows Media Player
        # and other native players, which looks like a broken, audio-only file even though the
        # video track is there
        ydl_options['format'] = (
            'bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/'
            'best[vcodec^=avc1]/'
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/'
            'best[ext=mp4]/'
            'bestvideo+bestaudio/best'
        )
        ydl_options['merge_output_format'] = 'mp4'

    print(Fore.YELLOW + 'INFO!' + Style.RESET_ALL + ' Started downloading from "' + input_url + '"')
    try:
        with YoutubeDL(ydl_options) as ydl:
            # Resolve the final filename first, so we never overwrite anything
            info = ydl.extract_info(input_url, download=False)
            output_file_path = os.path.splitext(ydl.prepare_filename(info))[0] + '.' + target_extension
            if os.path.exists(output_file_path):
                if not should_overwrite(output_file_path, input_force_overwrite):
                    raise FileExistsError()
                ydl.params['overwrites'] = True
                os.remove(output_file_path)

            ydl.download([input_url])

        print(Fore.GREEN + 'SUCCESS! 1/1' + Style.RESET_ALL + ' Downloaded ' + target_extension + ' from "' + input_url + '" to "' + output_file_path + '"')
    except FileExistsError:
        exit(-1)
    except PermissionError:
        # Windows refuses to replace a file that is still open somewhere, e.g. in a media player
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Permission denied writing to "' + output_folder_path + '", close the file if it is open in another program and try again')
        exit(-1)
    except DownloadError as e:
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' ' + str(e))
        exit(-1)
    except:
        traceback.print_exc()
        print(Fore.RED + 'ERROR!' + Style.RESET_ALL + ' Unexpected exception occurred')
        exit(-1)


if __name__ == "__main__":
    main()
