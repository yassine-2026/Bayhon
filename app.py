from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile

app = Flask(__name__)
CORS(app)  # يسمح للواجهة بالاتصال

@app.route('/api/info', methods=['POST'])
def info():
    url = request.form.get('url')
    if not url:
        return jsonify({"success": False, "error": "الرابط مفقود"})
    
    # حفظ الكوكيز إن وجدت
    cookies_file = None
    if 'cookies' in request.files:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        request.files['cookies'].save(tmp.name)
        cookies_file = tmp.name

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'ignoreerrors': True,
    }
    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:  # قائمة تشغيل
                info = info['entries'][0]
            
            formats = []
            for f in info.get('formats', []):
                if f.get('video_ext') != 'none' or f.get('acodec') != 'none':
                    formats.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'quality': f.get('format_note', 'audio only'),
                        'filesize': f.get('filesize')
                    })
            
            return jsonify({
                "success": True,
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "platform": info.get('extractor_key'),
                "formats": formats[:15]  # نحدد العدد
            })
    except Exception as e:
        return jsonify({"success": False, "error": f"فشل التحليل: {str(e)}"})
    finally:
        if cookies_file:
            os.unlink(cookies_file)

@app.route('/api/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_id = request.form.get('format_id')
    cookies_file = None
    if 'cookies' in request.files:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        request.files['cookies'].save(tmp.name)
        cookies_file = tmp.name

    ydl_opts = {
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'format': format_id if format_id else 'best',
        'quiet': True,
    }
    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            # البحث عن الملف المحمل
            for f in os.listdir('/tmp/'):
                if f.endswith(('.mp4', '.webm', '.mkv', '.mp3')):
                    filepath = os.path.join('/tmp/', f)
                    return send_file(filepath, as_attachment=True)
            return jsonify({"success": False, "error": "لم يتم العثور على الملف"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        if cookies_file:
            os.unlink(cookies_file)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
