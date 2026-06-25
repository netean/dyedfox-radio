from __future__ import annotations
import re
import requests
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

_SEARCH_URL = "https://api.deezer.com/search"
_HEADERS = {"User-Agent": "dyedfox-radio/1.0"}

# Bits of ICY metadata that are not song titles and should not be looked up.
_JUNK = re.compile(
    r"^\s*(ad(vertisement)?s?|jingle|station\s*id|unknown|n/?a|live|"
    r"www\.|https?://)",
    re.IGNORECASE,
)


def parse_now_playing(title: str) -> str | None:
    """Turn a raw ICY/ID3 'now playing' string into a Deezer search query.

    Radio metadata is inconsistent ('Artist - Title', bare titles, ads, station
    names). We build a best-effort query and reject obvious non-songs; a wrong
    or empty result simply falls back to the station favicon upstream.
    """
    if not title:
        return None
    text = title.strip()
    # Drop a trailing stream-quality/codec suffix some stations append.
    text = re.sub(r"\s*[\(\[][^\)\]]*\b(kbps|aac|mp3)\b[^\)\]]*[\)\]]\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -–—")
    if len(text) < 3 or not re.search(r"[A-Za-z0-9]", text):
        return None
    if _JUNK.match(text):
        return None
    # Collapse the common 'Artist - Title' separator into plain search terms.
    return text.replace(" - ", " ").replace(" – ", " ").strip()


class _ArtworkSignals(QObject):
    loaded = pyqtSignal(int, bytes, str)  # token, image bytes, art url
    finished = pyqtSignal(object)         # the loader itself, for keep-alive bookkeeping


class ArtworkLoader(QRunnable):
    """Look up cover art for a song on Deezer and download it, off the GUI thread.

    `token` ties the result to the song that was playing when the lookup started;
    the owner discards results whose token is stale (station or song changed).
    """

    def __init__(self, token: int, query: str):
        super().__init__()
        self.setAutoDelete(False)
        self._token = token
        self._query = query
        self.signals = _ArtworkSignals()

    def run(self):
        try:
            resp = requests.get(
                _SEARCH_URL,
                params={"q": self._query, "limit": 1},
                timeout=4,
                headers=_HEADERS,
            )
            if resp.ok:
                data = (resp.json() or {}).get("data") or []
                if data:
                    album = data[0].get("album") or {}
                    art_url = album.get("cover_xl") or album.get("cover_big") or ""
                    if art_url:
                        img = requests.get(art_url, timeout=4, headers=_HEADERS)
                        if img.ok and img.content:
                            try:
                                self.signals.loaded.emit(self._token, img.content, art_url)
                            except RuntimeError:
                                pass
        except Exception:
            pass
        finally:
            # autoDelete is False, so Python owns this QRunnable. Mirror the favicon
            # loader: the owner must hold a reference until run() returns, or the
            # pool dereferences a freed runnable (use-after-free). Signal completion.
            try:
                self.signals.finished.emit(self)
            except RuntimeError:
                pass
