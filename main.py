import os
import re
import logging
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import yt_dlp
from urllib.parse import unquote

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "youtube-stream-api-secret")

# Enable CORS for all routes
CORS(app)

def extract_video_id(url_or_id):
    """
    Extract YouTube video ID from a URL or return the ID if it's already a valid ID.
    """
    # Check if it's already a valid ID (11 characters of alphanumeric and some special chars)
    if re.match(r'^[0-9A-Za-z_-]{11}$', url_or_id):
        return url_or_id
    
    # Otherwise, try to extract ID from URL
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None

def get_youtube_stream_url(video_id):
    """
    Get the YouTube video stream URL using yt-dlp.
    Returns a tuple (stream_url, video_info, error)
    """
    # YoutubeDL options
    ydl_opts = {
        'format': 'best',  # Get the best quality
        'noplaylist': True,  # Only download the video, not the playlist
        'skip_download': True,  # Don't download the video, just get the info
        'quiet': True,  # Don't print debug output
        'no_warnings': True,  # Don't print warnings
    }
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Get the stream URL
            if 'url' in info:
                stream_url = info['url']
            else:
                formats = info.get('formats', [])
                if formats:
                    # Get the URL of the first format
                    stream_url = formats[0]['url']
                else:
                    return None, None, "No stream URL found in video info"
            
            # Extract useful information
            video_info = {
                'title': info.get('title', 'Unknown'),
                'description': info.get('description', ''),
                'channel_name': info.get('channel', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
            }
            
            return stream_url, video_info, None
    except yt_dlp.utils.DownloadError as e:
        error_message = str(e)
        if "Video unavailable" in error_message:
            return None, None, "Video is unavailable or has been removed"
        elif "Private video" in error_message:
            return None, None, "This video is private"
        elif "Sign in to confirm your age" in error_message:
            return None, None, "Age-restricted video"
        else:
            return None, None, f"Error downloading video information: {error_message}"
    except Exception as e:
        return None, None, f"Unexpected error: {str(e)}"

@app.route('/')
def index():
    """Render the index page with instructions"""
    return render_template('index.html')

@app.route('/<path:video_id_or_url>')
def get_stream(video_id_or_url):
    """
    Endpoint to get the stream URL for a YouTube video.
    Accept both direct video IDs and full YouTube URLs.
    """
    # Decode URL in case it's URL-encoded
    video_id_or_url = unquote(video_id_or_url)
    
    # Extract the video ID
    video_id = extract_video_id(video_id_or_url)
    
    if not video_id:
        return jsonify({
            'success': False,
            'error': 'Invalid YouTube video ID or URL'
        }), 400
    
    # Get video information
    stream_url, video_info, error = get_youtube_stream_url(video_id)
    
    if error:
        logger.error(f"Error for video ID {video_id}: {error}")
        return jsonify({
            'success': False,
            'error': error,
            'video_id': video_id
        }), 404
    
    # Return the stream URL with cache expiration note
    response = {
        'success': True,
        'video_id': video_id,
        'stream_url': stream_url,
        'video_info': video_info,
        'cache_info': 'Stream URL expires after maximum 12 hours'
    }
    
    return jsonify(response)

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)