import sys
import os
from typing import List, Optional, Dict, Any
from enum import Enum
from dotenv import load_dotenv
import googleapiclient.discovery
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
from pathlib import Path

# Load environment variables
load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

class OutputFormat(Enum):
    """Supported output formats for transcripts."""
    JSON = 'json'
    TXT = 'txt'
    SRT = 'srt'

def get_output_format() -> OutputFormat:
    """
    Asks user to select the desired output format.

    Returns:
        OutputFormat: The selected output format
    """
    print("\nAvailable output formats:")
    for i, format in enumerate(OutputFormat, 1):
        print(f"{i}. {format.value}")

    while True:
        try:
            choice = int(input("\nSelect output format (1-3): "))
            if 1 <= choice <= len(OutputFormat):
                return list(OutputFormat)[choice - 1]
            print(f"Please enter a number between 1 and {len(OutputFormat)}.")
        except ValueError:
            print("Please enter a valid number.")

def save_transcript(transcript: List[Dict[str, Any]], output_file: Path, format: OutputFormat) -> None:
    """
    Saves the transcript in the specified format.

    Args:
        transcript (List[Dict[str, Any]]): The transcript data
        output_file (Path): The output file path (without extension)
        format (OutputFormat): The desired output format
    """
    if format == OutputFormat.JSON:
        with open(f"{output_file}.json", 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)

    elif format == OutputFormat.TXT:
        with open(f"{output_file}.txt", 'w', encoding='utf-8') as f:
            for entry in transcript:
                f.write(f"{entry['text']}\n")

    elif format == OutputFormat.SRT:
        with open(f"{output_file}.srt", 'w', encoding='utf-8') as f:
            for i, entry in enumerate(transcript, 1):
                start = entry['start']
                duration = entry.get('duration', 0)
                end = start + duration

                # Convert to SRT time format (HH:MM:SS,mmm)
                start_time = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
                end_time = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},{int((end%1)*1000):03d}"

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{entry['text']}\n\n")

def extract_channel_id(channel_url: str) -> str:
    """
    Extracts channel ID from various forms of YouTube channel URLs.

    Args:
        channel_url (str): The URL of the YouTube channel

    Returns:
        str: The channel ID
    """
    patterns = [
        r'youtube\.com/channel/(UC[\w-]+)',  # Standard channel URL
        r'youtube\.com/c/([^/]+)',           # Custom channel URL
        r'youtube\.com/@([^/]+)'             # Handle URL
    ]

    for pattern in patterns:
        match = re.search(pattern, channel_url)
        if match:
            return match.group(1)

    return channel_url  # Return as is if no pattern matches

def extract_video_id(video_url: str) -> str:
    """
    Extracts video ID from a YouTube video URL.

    Args:
        video_url (str): The URL of the YouTube video

    Returns:
        str: The video ID
    """
    patterns = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',  # Standard video URL
        r'youtu\.be/([a-zA-Z0-9_-]+)',              # Short URL
        r'youtube\.com/v/([a-zA-Z0-9_-]+)',         # Embedded URL
        r'youtube\.com/embed/([a-zA-Z0-9_-]+)'      # Embed URL
    ]

    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)

    return video_url  # Return as is if no pattern matches

def get_channel_videos(channel_id: str) -> List[str]:
    """
    Gets all video IDs from a YouTube channel.

    Args:
        channel_id (str): The channel ID

    Returns:
        List[str]: List of video IDs
    """
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    video_ids: List[str] = []
    next_page_token: Optional[str] = None

    while True:
        try:
            # Get channel's uploads with maximum results per page
            request = youtube.search().list(
                part='id',
                channelId=channel_id,
                maxResults=50,  # Maximum allowed by API
                type='video',
                pageToken=next_page_token
            )

            response = request.execute()

            # Extract video IDs
            for item in response.get('items', []):
                if isinstance(item, dict) and 'id' in item and isinstance(item['id'], dict):
                    video_id = item['id'].get('videoId')
                    if video_id:
                        video_ids.append(video_id)

            # Get next page token
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

            print(f"Retrieved {len(video_ids)} videos so far...")

        except Exception as e:
            print(f"Error retrieving videos: {str(e)}")
            break

    return video_ids

def download_channel_transcripts(channel_url: str) -> None:
    """
    Downloads all available transcripts from a YouTube channel.

    Args:
        channel_url (str): The URL of the YouTube channel
    """
    try:
        print(f"\nProcessing channel: {channel_url}")

        # Get output format from user
        output_format = get_output_format()
        print(f"Selected format: {output_format.value}")

        # Extract channel ID
        channel_id = extract_channel_id(channel_url)
        print(f"Extracted channel ID: {channel_id}")

        # Get all video IDs from the channel
        video_ids = get_channel_videos(channel_id)
        print(f"Found {len(video_ids)} videos")

        # Create output directory
        output_dir = Path('transcripts') / channel_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download transcripts for each video
        for i, video_id in enumerate(video_ids, 1):
            try:
                print(f"\nProcessing video {i}/{len(video_ids)}: {video_id}")
                transcript = YouTubeTranscriptApi.get_transcript(video_id)

                # Save transcript in the selected format
                output_file = output_dir / video_id
                save_transcript(transcript, output_file, output_format)
                print(f"Saved transcript to {output_file}.{output_format.value}")

            except Exception as e:
                print(f"Error downloading transcript for video {video_id}: {str(e)}")
                continue

        print(f"\nFinished processing channel. Transcripts saved in {output_dir}")

    except Exception as e:
        print(f"Error processing channel: {str(e)}")

def download_single_video_transcript(video_url: str) -> None:
    """
    Downloads transcript from a specific YouTube video.

    Args:
        video_url (str): The URL of the YouTube video
    """
    try:
        print(f"\nProcessing video: {video_url}")

        # Get output format from user
        output_format = get_output_format()
        print(f"Selected format: {output_format.value}")

        # Extract video ID
        video_id = extract_video_id(video_url)
        print(f"Extracted video ID: {video_id}")

        try:
            # Download transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            # Create output directory
            output_dir = Path('transcripts') / 'single_videos'
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save transcript in the selected format
            output_file = output_dir / video_id
            save_transcript(transcript, output_file, output_format)
            print(f"Saved transcript to {output_file}.{output_format.value}")

        except Exception as e:
            print(f"Error downloading transcript: {str(e)}")

    except Exception as e:
        print(f"Error processing video: {str(e)}")

def download_multiple_video_transcripts(file_path: str) -> None:
    """
    Downloads transcripts from multiple YouTube videos listed in a file.

    Args:
        file_path (str): Path to the file containing video URLs (one per line)
    """
    # TODO: Implement multiple video transcript download functionality
    pass

def display_menu() -> None:
    """Displays the main menu of the application."""
    print("\n=== YouTube Transcript Downloader ===")
    print("1. Download ALL transcripts from a YouTube channel")
    print("2. Download transcript from a specific video")
    print("3. Download transcripts from multiple videos (using a file)")
    print("4. Exit")
    print("=====================================")

def get_user_choice() -> int:
    """
    Gets and validates user's menu choice.

    Returns:
        int: The validated user choice (1-4)
    """
    while True:
        try:
            choice = int(input("\nEnter your choice (1-4): "))
            if 1 <= choice <= 4:
                return choice
            print("Please enter a number between 1 and 4.")
        except ValueError:
            print("Please enter a valid number.")

def main():
    """Main application loop."""
    while True:
        display_menu()
        choice = get_user_choice()

        if choice == 1:
            channel_url = input("Enter the YouTube channel URL: ")
            download_channel_transcripts(channel_url)

        elif choice == 2:
            video_url = input("Enter the YouTube video URL: ")
            download_single_video_transcript(video_url)

        elif choice == 3:
            file_path = input("Enter the path to the file containing video URLs: ")
            download_multiple_video_transcripts(file_path)

        else:  # choice == 4
            print("\nThank you for using YouTube Transcript Downloader!")
            sys.exit(0)

if __name__ == "__main__":
    main()
