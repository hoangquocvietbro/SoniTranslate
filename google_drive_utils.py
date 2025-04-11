# Thông tin OAuth 2.0 từ Google Developer Console
CLIENT_ID = "925033313970-9lr61c64njpv9brqnp3rc4ut7kdt0uli.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REFRESH_TOKEN = "1//04SAIRpuZugbkCgYIARAAGAQSNwF-L9IrEElJPgwKMdoauW8iNhu9No7sv1-_SIGDBqBxKnFra1R4nXmGUBYQrdhP-aloJOS_Sko"
TOKEN_URI = "https://oauth2.googleapis.com/token"
VIDEO_FILE = "output.mp4"  # Đường dẫn tệp video
TITLE = "Your Video Title"
DESCRIPTION = "Your Video Description"
TAGS = ["tag1", "tag2"]
CATEGORY_ID = "22"  # Ví dụ: 22 là "People & Blogs"
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
import requests
import os
import io

def download_from_drive(file_name, folder_id):
    access_token = refresh_access_token()
    credentials = Credentials(
        token=access_token,
        refresh_token=REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    service = build("drive", "v3", credentials=credentials)

    # Tìm kiếm file trong folder_id theo tên
    query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        raise FileNotFoundError(f"Không tìm thấy {file_name} trong folder {folder_id}")

    file_id = items[0]['id']

    # Tải file về
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, mode='wb')
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Đang tải: {int(status.progress() * 100)}%")

    print(f"Đã tải xong {file_name}")


# Hàm làm mới access_token
def refresh_access_token():
    response = requests.post(TOKEN_URI, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    })
    response_data = response.json()

    if "access_token" in response_data:
        return response_data["access_token"]
    else:
        raise Exception(f"Lỗi khi làm mới token: {response_data}")

# Tạo dịch vụ YouTube API
def get_authenticated_service():
    access_token = refresh_access_token()
    credentials = Credentials(
        token=access_token,
        refresh_token=REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    return build("youtube", "v3", credentials=credentials)

# Tải video lên google drive thay thế file nếu đã tồn tại
def upload_to_drive_folder(file_path, folder_id):
    access_token = refresh_access_token()
    credentials = Credentials(
        token=access_token,
        refresh_token=REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )

    drive_service = build("drive", "v3", credentials=credentials)

    file_name = os.path.basename(file_path)  # chỉ lấy tên file, không lấy đường dẫn
    file_metadata = {
        "name": file_name,
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)

    try:
        # Tìm file trùng tên trong thư mục
        query = f"'{folder_id}' in parents and name='{file_name}' and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            # Nếu đã tồn tại file, thì update
            file_id = files[0]['id']
            updated_file = drive_service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id, webViewLink, webContentLink"
            ).execute()
            print("♻️ Đã cập nhật file cũ trên Google Drive!")
            print("🆔 File ID:", updated_file["id"])
            print("🔗 Link xem:", updated_file.get("webViewLink"))
            print("🔗 Link tải:", updated_file.get("webContentLink"))
            return updated_file
        else:
            # Nếu chưa có file trùng tên, thì tạo mới
            created_file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink"
            ).execute()
            print("✅ Upload thành công file mới lên Google Drive!")
            print("🆔 File ID:", created_file["id"])
            print("🔗 Link xem:", created_file.get("webViewLink"))
            print("🔗 Link tải:", created_file.get("webContentLink"))
            return created_file

    except Exception as e:
        print("❌ Lỗi upload:", e)


# Tải video lên youtube với chế độ resumable upload
def upload_video_resumable():
    youtube = get_authenticated_service()
    request_body = {
        "snippet": {
            "title": "Your Video Title",
            "description": "Your Video Description",
            "tags": ["tag1", "tag2"],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "private"
        },
    }

    media = MediaFileUpload(
        VIDEO_FILE,
        chunksize=1024 * 1024 * 8,
        resumable=True,
    )

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")

        print("Upload hoàn tất! Video ID:", response["id"])

    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
