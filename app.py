import os
import tempfile
import subprocess
import requests
import datetime
from flask import Flask, request, send_from_directory
from scenedetect import detect, ContentDetector, open_video

UPLOAD_FOLDER = tempfile.gettempdir()
app = Flask(__name__, static_url_path="", static_folder=".")

def download_youtube(url):
    """Download video from YouTube and return file path."""
    output_path = os.path.join(UPLOAD_FOLDER, "%(title)s.%(ext)s")
    subprocess.run([
        "yt-dlp", "-f", "mp4", "-o", output_path, url
    ])
    for f in os.listdir(UPLOAD_FOLDER):
        if f.endswith(".mp4"):
            return os.path.join(UPLOAD_FOLDER, f)
    return None

def split_video_by_scenes(file_path, max_length=60):
    """Split video by detected scenes."""
    video = open_video(file_path)
    scene_list = detect(video, ContentDetector(threshold=27.0))

    clips = []
    for scene in scene_list:
        start_time, end_time = scene[0].get_seconds(), scene[1].get_seconds()
        duration = end_time - start_time
        if duration > max_length:
            num_parts = int(duration // max_length) + 1
            for part in range(num_parts):
                part_start = start_time + part * max_length
                part_end = min(end_time, part_start + max_length)
                clips.append((part_start, part_end))
        else:
            clips.append((start_time, end_time))

    output_files = []
    for idx, (start, end) in enumerate(clips, start=1):
        output_path = os.path.join(UPLOAD_FOLDER, f"scene_{idx:03d}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", file_path,
            "-ss", str(start), "-to", str(end),
            "-c", "copy", output_path
        ])
        output_files.append(output_path)
    return output_files

def add_watermark(input_path, watermark_path):
    """Add watermark to video."""
    output_path = input_path.replace(".mp4", "_wm.mp4")
    subprocess.run([
        "ffmpeg", "-i", input_path, "-i", watermark_path,
        "-filter_complex", "overlay=10:10",
        "-codec:a", "copy", output_path
    ])
    return output_path

def upload_reel(page_id, page_token, video_path, description, schedule_time=None):
    """Upload Reel to Facebook Page."""
    url = f"https://graph-video.facebook.com/v17.0/{page_id}/video_reels"
    files = {'video_file': open(video_path, 'rb')}
    data = {
        'access_token': page_token,
        'description': description
    }
    if schedule_time:
        data['scheduled_publish_time'] = int(schedule_time.timestamp())
        data['published'] = 'false'
    r = requests.post(url, files=files, data=data)
    return r.text

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/upload", methods=["POST"])
def upload():
    page_id = request.form["page_id"]
    page_token = request.form["page_token"]
    description = request.form["description"]
    youtube_url = request.form.get("youtube_url", "").strip()
    watermark = request.files.get("watermark")
    video_file = request.files.get("video")

    if youtube_url:
        original_path = download_youtube(youtube_url)
    elif video_file:
        original_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
        video_file.save(original_path)
    else:
        return "No video provided", 400

    watermark_path = None
    if watermark:
        watermark_path = os.path.join(UPLOAD_FOLDER, watermark.filename)
        watermark.save(watermark_path)

    clips = split_video_by_scenes(original_path, max_length=60)

    log = []
    clips_per_day = 10
    interval_minutes = 30
    start_hour = 9

    for idx, clip in enumerate(clips, start=1):
        final_clip = clip
        if watermark_path:
            final_clip = add_watermark(clip, watermark_path)

        day_offset = (idx - 1) // clips_per_day
        slot_index = (idx - 1) % clips_per_day
        schedule_time = (
            datetime.datetime.utcnow().replace(hour=start_hour, minute=0, second=0, microsecond=0)
            + datetime.timedelta(days=day_offset, minutes=slot_index * interval_minutes)
        )

        desc_text = f"{description} {idx}"
        result = upload_reel(page_id, page_token, final_clip, desc_text, schedule_time)
        log.append(f"Clip {idx} scheduled for {schedule_time} UTC: {result}")

    return "\n".join(log)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
