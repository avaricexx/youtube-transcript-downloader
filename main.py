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

def extract_channel_id(channel_url: str) -> Optional[str]:
    """
    Extracts channel ID from various forms of YouTube channel URLs.
    Makes an API call if necessary to resolve custom URLs.

    Args:
        channel_url (str): The URL of the YouTube channel

    Returns:
        Optional[str]: The channel ID if found, None otherwise
    """
    # Clean the URL
    channel_url = channel_url.strip().rstrip('/')

    # Try direct ID extraction first
    patterns = [
        (r'youtube\.com/channel/(UC[\w-]+)', lambda x: x),  # Standard channel URL
        (r'youtube\.com/c/([^/]+)', lambda x: resolve_custom_url(x)),  # Custom channel URL
        (r'youtube\.com/@([^/]+)', lambda x: resolve_custom_handle(x)),  # Handle URL
        (r'youtube\.com/user/([^/]+)', lambda x: resolve_username(x))  # Legacy username URL
    ]

    for pattern, resolver in patterns:
        match = re.search(pattern, channel_url)
        if match:
            identifier = match.group(1)
            try:
                channel_id = resolver(identifier)
                if channel_id:
                    return channel_id
            except Exception as e:
                print(f"Error resolving channel identifier '{identifier}': {str(e)}")
                continue

    # If no pattern matches, try resolving the entire URL
    try:
        return resolve_channel_url(channel_url)
    except Exception as e:
        print(f"Error resolving channel URL: {str(e)}")
        return None

def resolve_custom_url(custom_url: str) -> Optional[str]:
    """
    Resolves a custom channel URL to a channel ID using the YouTube API.

    Args:
        custom_url (str): The custom URL part of the channel

    Returns:
        Optional[str]: The channel ID if found, None otherwise
    """
    try:
        youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part='snippet',
            q=custom_url,
            type='channel',
            maxResults=1
        )
        response = request.execute()

        items = response.get('items', [])
        if items:
            return items[0]['snippet']['channelId']
        return None
    except Exception as e:
        raise Exception(f"Failed to resolve custom URL: {str(e)}")

def resolve_custom_handle(handle: str) -> Optional[str]:
    """
    Resolves a channel handle to a channel ID using the YouTube API.

    Args:
        handle (str): The channel handle (without @)

    Returns:
        Optional[str]: The channel ID if found, None otherwise
    """
    try:
        youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part='snippet',
            q=f"@{handle}",
            type='channel',
            maxResults=1
        )
        response = request.execute()

        items = response.get('items', [])
        if items:
            return items[0]['snippet']['channelId']
        return None
    except Exception as e:
        raise Exception(f"Failed to resolve handle: {str(e)}")

def resolve_username(username: str) -> Optional[str]:
    """
    Resolves a YouTube username to a channel ID using the YouTube API.

    Args:
        username (str): The YouTube username

    Returns:
        Optional[str]: The channel ID if found, None otherwise
    """
    try:
        youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.channels().list(
            part='id',
            forUsername=username
        )
        response = request.execute()

        items = response.get('items', [])
        if items:
            return items[0]['id']
        return None
    except Exception as e:
        raise Exception(f"Failed to resolve username: {str(e)}")

def resolve_channel_url(url: str) -> Optional[str]:
    """
    Attempts to resolve any YouTube URL to a channel ID using the YouTube API.

    Args:
        url (str): The YouTube channel URL

    Returns:
        Optional[str]: The channel ID if found, None otherwise
    """
    try:
        youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part='snippet',
            q=url,
            type='channel',
            maxResults=1
        )
        response = request.execute()

        items = response.get('items', [])
        if items:
            return items[0]['snippet']['channelId']
        return None
    except Exception as e:
        raise Exception(f"Failed to resolve channel URL: {str(e)}")

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

        # Extract channel ID
        channel_id = extract_channel_id(channel_url)
        if not channel_id:
            print("Error: Could not extract or resolve channel ID. Please check the URL and try again.")
            return

        print(f"Resolved channel ID: {channel_id}")

        # Get output format from user
        output_format = get_output_format()
        print(f"Selected format: {output_format.value}")

        # Get all video IDs from the channel
        try:
            video_ids = get_channel_videos(channel_id)
            if not video_ids:
                print("No videos found in the channel. The channel might be private or have no public videos.")
                return
            print(f"Found {len(video_ids)} videos")
        except Exception as e:
            print(f"Error retrieving videos from channel: {str(e)}")
            return

        # Create output directory
        output_dir = Path('transcripts') / channel_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download transcripts for each video
        successful = 0
        failed = 0
        no_captions = 0

        for i, video_id in enumerate(video_ids, 1):
            try:
                print(f"\nProcessing video {i}/{len(video_ids)}: {video_id}")
                transcript = YouTubeTranscriptApi.get_transcript(video_id)

                # Save transcript in the selected format
                output_file = output_dir / video_id
                save_transcript(transcript, output_file, output_format)
                print(f"Saved transcript to {output_file}.{output_format.value}")
                successful += 1

            except Exception as e:
                error_message = str(e)
                if "No transcripts were found" in error_message:
                    print(f"No captions available for video {video_id}")
                    no_captions += 1
                else:
                    print(f"Error downloading transcript for video {video_id}: {error_message}")
                    failed += 1
                continue

        # Print summary
        print(f"\nDownload Summary:")
        print(f"Total videos found: {len(video_ids)}")
        print(f"Successfully downloaded: {successful}")
        print(f"No captions available: {no_captions}")
        print(f"Failed to download: {failed}")
        print(f"Transcripts saved in: {output_dir}")

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
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' does not exist.")
            return

        # Get output format from user
        output_format = get_output_format()
        print(f"Selected format: {output_format.value}")

        # Create output directory
        output_dir = Path('transcripts') / 'multiple_videos'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Read and process video URLs
        successful = 0
        failed = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            video_urls = [line.strip() for line in f if line.strip()]
            total_videos = len(video_urls)

            if total_videos == 0:
                print("No video URLs found in the file.")
                return

            print(f"\nFound {total_videos} video URLs in the file.")

            for i, video_url in enumerate(video_urls, 1):
                try:
                    print(f"\nProcessing video {i}/{total_videos}: {video_url}")

                    # Extract video ID
                    video_id = extract_video_id(video_url)
                    if not video_id:
                        print(f"Error: Could not extract video ID from URL: {video_url}")
                        failed += 1
                        continue

                    print(f"Extracted video ID: {video_id}")

                    # Download transcript
                    transcript = YouTubeTranscriptApi.get_transcript(video_id)

                    # Save transcript in the selected format
                    output_file = output_dir / video_id
                    save_transcript(transcript, output_file, output_format)
                    print(f"Saved transcript to {output_file}.{output_format.value}")
                    successful += 1

                except Exception as e:
                    print(f"Error processing video {video_url}: {str(e)}")
                    failed += 1
                    continue

        # Print summary
        print(f"\nDownload Summary:")
        print(f"Total videos processed: {total_videos}")
        print(f"Successfully downloaded: {successful}")
        print(f"Failed to download: {failed}")
        print(f"Transcripts saved in: {output_dir}")

    except Exception as e:
        print(f"Error reading file: {str(e)}")

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
