
import json
import os
import sys
import urllib.request
from pathlib import Path

PROFILE_URL = "https://www.tiktok.com/@brennizfps"
STATE_FILE = Path("data/seen.json")
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

TARGET_VIDEO_ID = "7711815699815025927"


def get_videos():
    from yt_dlp import YoutubeDL

    options = {
        "extract_flat": "in_playlist",
        "playlistend": 10,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(PROFILE_URL, download=False)

    if not info:
        raise RuntimeError("Não foi possível acessar o perfil do TikTok.")

    videos = [
        video for video in (info.get("entries") or [])
        if video and video.get("id")
    ]

    print("VÍDEOS ENCONTRADOS:", len(videos))
    print("IDs RECEBIDOS:", [str(v["id"]) for v in videos])

    target_found = any(
        str(v["id"]) == TARGET_VIDEO_ID for v in videos
    )

    print("VÍDEO QUE ESTAMOS INVESTIGANDO:", 
          "ENCONTRADO" if target_found else "NÃO ENCONTRADO")

    return videos


def get_video_url(video):
    return (
        video.get("webpage_url")
        or f"https://www.tiktok.com/@brennizfps/video/{video['id']}"
    )


def get_thumbnail(video):
    thumbnails = video.get("thumbnails") or []

    for item in reversed(thumbnails):
        if isinstance(item, dict) and item.get("url"):
            return item["url"]

    return video.get("thumbnail")


def send_notification(video):
    title = (
        video.get("title")
        or video.get("description")
        or "Novo vídeo"
    )[:4000]

    embed = {
        "title": "🔥 BRENNIZ POSTOU!",
        "description": title,
        "url": get_video_url(video),
        "color": 0xE83E8C,
        "footer": {"text": "@brennizfps • TikTok"},
    }

    thumbnail = get_thumbnail(video)
    if thumbnail:
        embed["image"] = {"url": thumbnail}

    payload = json.dumps({
        "embeds": [embed],
        "allowed_mentions": {"parse": []},
    }).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status not in (200, 204):
            raise RuntimeError("Erro ao enviar mensagem ao Discord.")


def main():
    if not WEBHOOK:
        raise RuntimeError("Segredo DISCORD_WEBHOOK_URL não configurado.")

    videos = get_videos()

    if not videos:
        raise RuntimeError("Nenhum vídeo foi encontrado no perfil.")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not STATE_FILE.exists():
        ids = [str(video["id"]) for video in videos]
        STATE_FILE.write_text(
            json.dumps(ids, indent=2),
            encoding="utf-8",
        )
        print("Histórico inicial criado.")
        return

    seen = set(json.loads(STATE_FILE.read_text(encoding="utf-8")))

    print("IDs JÁ REGISTRADOS:", sorted(seen))

    new_videos = [
        video for video in reversed(videos)
        if str(video["id"]) not in seen
    ]

    print("NOVOS VÍDEOS:", [str(v["id"]) for v in new_videos])

    for video in new_videos:
        send_notification(video)
        seen.add(str(video["id"]))
        print("NOTIFICAÇÃO ENVIADA:", video["id"])

    recent_ids = [str(video["id"]) for video in videos]
    history = recent_ids + [
        video_id for video_id in seen
        if video_id not in recent_ids
    ]

    STATE_FILE.write_text(
        json.dumps(history[:200], indent=2),
        encoding="utf-8",
    )

    print("DIAGNÓSTICO CONCLUÍDO.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("ERRO:", error, file=sys.stderr)
        sys.exit(1)
        
