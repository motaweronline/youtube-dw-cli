# YouTube Download CLI

A CLI tool built in Python that downloads videos from YouTube, either as MP4 video files or as MP3 audio files. Downloading is handled by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

# Usage

After installation the tool can be accessed from the terminal. You need to specify a YouTube URL or a bare video id. Everything else is optional: the mode to switch between video and audio (`mp4` or `mp3`), an output directory, and cookies for restricted videos. By default all downloaded files are saved in the current working directory.

Works on macOS, Linux and Windows.

### Help

```bash
$ youtube-download-cli -h

usage: youtube-download-cli [-h] [-o [o]] [-c [BROWSER]] [--cookies FILE] [-f] [U] [M]

positional arguments:
  U                     youtube video url or bare video id which needs to be
                        downloaded, like
                        "https://www.youtube.com/watch?v=Fd_3EkGr0-4",
                        "https://youtu.be/Fd_3EkGr0-4" or just "Fd_3EkGr0-4"
  M                     download mode can be "mp3"/"mp4"/"audio"/"video"

options:
  -h, --help            show this help message and exit
  -o [o]                output directory (optional, defaults to current
                        working directory)
  -c, --cookies-from-browser [BROWSER]
                        load cookies from a browser to download age-restricted
                        or private videos, like "chrome"/"safari"/"firefox"
                        (optionally "chrome:ProfileName"), defaults to
                        "chrome" when given without a browser name
  --cookies FILE        load cookies from a Netscape-format cookies.txt file
                        instead of a browser
  -f, --force           overwrite the output file if it already exists,
                        without asking
```

### Download as MP4 video

```bash
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4"
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4" mp4
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4" video
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4" -o "~/Downloads"
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4" mp4 -o "~/Downloads"
```

### Download as MP3 audio

```bash
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4" mp3
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4" audio
youtube-download-cli "https://www.youtube.com/watch?v=Fd_3EkGr0-4" mp3 -o "~/Downloads"
```

### Video ids and short URLs

The full watch URL is not required, a bare 11 character video id is enough:

```bash
youtube-download-cli Fd_3EkGr0-4 mp4
```

Short and mobile URLs are accepted too: `youtu.be/...`, `m.youtube.com/...`, `music.youtube.com/...`, and URLs pasted without the `https://` prefix.

If a video id starts with a dash, put `--` before it so it isn't mistaken for a flag:

```bash
youtube-download-cli -- -Fd3EkGr0-4 mp4
```

### Age-restricted and private videos

YouTube requires a signed-in account for age-restricted videos. Pass cookies from a browser you are logged into:

```bash
youtube-download-cli Fd_3EkGr0-4 mp4 -c
youtube-download-cli Fd_3EkGr0-4 mp4 -c firefox
youtube-download-cli Fd_3EkGr0-4 mp4 -c "chrome:Profile 1"
```

`-c` on its own defaults to Chrome. Supported browsers are brave, chrome, chromium, edge, firefox, opera, safari, vivaldi and whale. A `cookies.txt` file works as an alternative:

```bash
youtube-download-cli Fd_3EkGr0-4 mp4 --cookies /path/to/cookies.txt
```

Requests made with cookies are tied to your signed-in account.

Put `-c` at the end of the command. Because its browser name is optional, `-c mp4 Fd_3EkGr0-4` reads `mp4` as a browser name and fails.

### Overwriting existing files

If the output file already exists, the tool asks before replacing it and keeps the file by default. Use `-f` to overwrite without asking. When there is no terminal to ask in, such as a script or a cron job, the download is refused instead of prompting.

# Requirements

* Python 3.9 or newer
* [ffmpeg](https://ffmpeg.org/) on your `PATH`

ffmpeg is required to save MP3 audio and to merge the separate video and audio streams that YouTube serves for higher resolutions. Without it, MP3 downloads fail with an explanatory message and MP4 downloads fall back to a lower quality single-file stream.

```bash
# macOS
brew install ffmpeg

# Windows
winget install Gyan.FFmpeg

# Debian / Ubuntu
sudo apt install ffmpeg
```

A JavaScript runtime is also needed. YouTube requires solving a JavaScript challenge before it hands out media formats, and without a runtime no downloadable formats are returned. [Deno](https://deno.com/), Node.js, Bun and QuickJS are all detected automatically if installed. The solver script itself is fetched from the yt-dlp repository on first use and cached afterwards.

# Video quality

MP4 downloads prefer H.264 video, which plays everywhere. YouTube also serves AV1 and VP9 at higher resolutions, but those decode poorly in QuickTime and Windows Media Player, where the picture stays black while the audio plays fine. Preferring H.264 caps downloads at 1080p, which is a deliberate trade of resolution for playback that works out of the box.

# Installation

## Normal installation

```bash
pip install youtube-download-cli
```

## Development installation

```bash
git clone https://github.com/motaweronline/youtube-dw-cli.git
cd youtube-dw-cli
pip install --editable .
```

## Windows

Use the `py` launcher, which is installed with Python and always resolves even when `pip` itself isn't on your `PATH`:

```batch
git clone https://github.com/motaweronline/youtube-dw-cli.git
cd youtube-dw-cli
py -m pip install --editable .
```

### 'pip' is not recognized as an internal or external command

`pip.exe` lives in Python's `Scripts` folder, which is only added to `PATH` when the "Add python.exe to PATH" box is ticked during installation. Rather than fixing `PATH`, invoke pip through Python itself:

```batch
py -m pip install --editable .
```

If `py` isn't recognized either, Python is not installed or not on `PATH`. Install it and open a **new** terminal afterwards, since `PATH` changes don't reach terminals that are already open:

```batch
winget install Python.Python.3.12
```

### 'youtube-download-cli' is not recognized

The command is installed into Python's `Scripts` folder, which has the same `PATH` problem as above. Run it as a module instead:

```batch
py -m youtube_download_cli.command_line Fd_3EkGr0-4 mp4
```

Or add the folder to your `PATH`, printed by:

```batch
py -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

### ffmpeg on Windows

ffmpeg is not bundled with Windows and must be installed separately, again followed by a new terminal:

```batch
winget install Gyan.FFmpeg
```

Check that it resolves with `ffmpeg -version`. Without it MP3 downloads are refused and MP4 downloads fall back to a lower quality single-file stream.
