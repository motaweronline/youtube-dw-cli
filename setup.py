from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as readme_file:
    readme_text = readme_file.read()


setup_args = dict(
    entry_points = {
        'console_scripts': ['youtube-download-cli=youtube_download_cli.command_line:main'],
    },
    name='youtube-download-cli',
    version='0.1.0',
    description="A CLI tool to download YouTube videos as MP4 video files or MP3 audio files",
    keywords=['youtube', 'download', 'cli', 'mp3', 'mp4', 'video', 'audio', 'yt-dlp'],
    long_description=readme_text,
    long_description_content_type="text/markdown",
    license='Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License',
    packages=find_packages(),
    python_requires='>=3.9',
)


install_requires = [
    'colorama',
    'yt-dlp'
]


if __name__ == '__main__':
    setup(**setup_args, install_requires=install_requires)
