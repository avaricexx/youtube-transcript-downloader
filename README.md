# YouTube Transcript Download

A Python script for YouTube transcript download. This script can download transcripts for:
- Individual videos
- Every video from a YouTube channel
- Multiple videos from a file

## Features

- Download transcripts in multiple formats (JSON, TXT, SRT)
- Support for various YouTube URL formats (channel URLs, video URLs)
- Batch Processing Features
- Progress tracking and summary
- Handles for YouTube channel URLs (@handles, custom URLs, channel IDs)

## Setup

1. Clone the repository
2. Install dependencies:
```bash
#
pip install -r requirements.txt
```

3. Create the .env file under the base directory using your YouTube API key:
```
YOUTUBE_API_KEY=your_api_key_here
```

To get your YouTube API key:
1. Go to the Google Cloud console
2. Create a new project/pick existing one
3. Enable the YouTube Data API v3
4. Create the credentials
5. Copy the API token over into your `.env'

## Usage

Run the program
```bash
cd
python main.py
```

### Options

1. Download all transcripts from a given YouTube channel
- Enter the url for the YouTube Channel (supports multiple formats):
- `https://youtube.com/@ChannelHandle`
- `https://youtube.com/c/CustomURL`
- `https://youtube.com/channel/ChannelID`

2. Download the transcript for the provided video
- Enter the YouTube address:
- `https://youtube.com/watch?v=VideoID`
- `https://youtu.be/VideoID`

3. Download transcripts for multiple videos
- Create the text file containing the videos' URLs (one line for each).
- Enter the directory for your file when asked

### Output Modes

1. JSON - Possesses very fine-grained timing data

2. TXT - Straight text transcript

3. SRT - subtitles formatting including timing

Transcripts are located under the `transcripts` directory

## Error handling

The program covers all possible scenarios:

- Private or unavailable videos
- Invalid URLs
- API quota limits

Failed downloads will also be reported with error descriptions.
