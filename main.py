from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import yt_dlp
import asyncio
import os
from pathlib import Path

app = FastAPI()

# 配置模板和静态文件
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 创建临时下载目录
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/info/{video_id}")
async def get_video_info(video_id: str):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info['formats']:
                if f.get('filesize'):
                    formats.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'quality': f.get('quality', 0),
                        'filesize': f['filesize'],
                        'resolution': f.get('resolution', 'N/A')
                    })
            return {
                'title': info['title'],
                'thumbnail': info['thumbnail'],
                'formats': formats
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download/{video_id}/{format_id}")
async def download_video(video_id: str, format_id: str):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        output_path = DOWNLOAD_DIR / f"{video_id}.%(ext)s"
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': str(output_path)
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)
            
        def iterfile():
            with open(filename, mode="rb") as file_like:
                yield from file_like
            os.unlink(filename)  # 下载完成后删除文件
            
        return StreamingResponse(
            iterfile(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(filename)}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 