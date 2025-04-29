#!/usr/bin/env python
# Simple import to run the app directly
from youtube_stream_api.app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)