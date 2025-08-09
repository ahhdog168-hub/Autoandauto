# FB Reels Auto Uploader

Uploads YouTube videos or uploaded files as Facebook Reels.
- Cuts into 60s clips by scenes
- Adds watermark (optional)
- Posts 10/day, 30 min apart
- Supports scheduling

## Deployment

1. Fork this repo.
2. Create a free [Render](https://render.com) account.
3. Click "New Web Service" → connect repo.
4. Environment:
   - PYTHON_VERSION: 3.10.12
5. Deploy.

## Usage

1. Get a **long-lived Facebook Page access token**:
   - Create a Facebook App.
   - Add `pages_show_list`, `pages_manage_posts` permissions.
   - Use Graph API Explorer to get token.
2. Open your Render app URL.
3. Enter:
   - Page ID
   - Access Token
   - YouTube URL or upload a video
   - Optional watermark
4. Click **Process & Upload**.
