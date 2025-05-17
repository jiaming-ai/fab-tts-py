# README

## Setup Instructions

### 1. Create and Activate a Virtual Environment

To ensure that dependencies are managed properly, it is recommended to use a virtual environment. Follow the steps below to set up and activate a virtual environment:

```sh
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### 2. Install Dependencies
```
pip install -r requirements.txt
```


### 3. Run audio generation AI
Download the code by run the command
```
git clone https://github.com/jiaming-ai/fab-tts-py.git
```

You can also go to https://github.com/jiaming-ai/fab-tts-py and download the code directly as a zip file. Then unzip it.

Note:
Put the music files in data foler as shown below

the structure is like
-root
 - fab_audio/
 - data/
  - bg_music/
  - misc/
  - sfx/
 - generated_stories/
 - main.py
 - ...


The following argument can be specified when running main.py:
use --language to specify the language: en, zh, fr, de
--n to specify the total number of stories
--story_path to specify the story text folder, by default it's in generated_stories

```
# make sure you are inside the root folder, then run with the argument as shwon above, for example
python main.py --language en --n 100
```
