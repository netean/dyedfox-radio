import requests
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool

BASE_URL = "https://de1.api.radio-browser.info/json"
HEADERS = {"User-Agent": "dyedfox-radio/1.0"}


class _Signals(QObject):
    result = pyqtSignal(list)
    error = pyqtSignal(str)


class _ApiWorker(QRunnable):
    def __init__(self, url: str, params: dict):
        super().__init__()
        self.setAutoDelete(True)
        self.url = url
        self.params = params
        self.signals = _Signals()

    def run(self):
        try:
            resp = requests.get(self.url, params=self.params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            self.signals.result.emit(resp.json())
        except Exception as e:
            self.signals.error.emit(str(e))


class _PostApiWorker(QRunnable):
    def __init__(self, url: str, data: dict):
        super().__init__()
        self.setAutoDelete(True)
        self.url = url
        self.data = data
        self.signals = _Signals()

    def run(self):
        try:
            resp = requests.post(self.url, data=self.data, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            self.signals.result.emit(resp.json())
        except Exception as e:
            self.signals.error.emit(str(e))


class RadioBrowserClient:
    def __init__(self):
        self._pool = QThreadPool.globalInstance()

    def top_stations(self, limit: int = 100, on_result=None, on_error=None):
        self._run(f"{BASE_URL}/stations/topvote/{limit}", {}, on_result, on_error)

    def search(self, query: str, limit: int = 100, on_result=None, on_error=None):
        self._run(
            f"{BASE_URL}/stations/search",
            {"name": query, "limit": limit, "hidebroken": "true"},
            on_result,
            on_error,
        )

    def by_tag(self, tag: str, on_result=None, on_error=None):
        self._run(f"{BASE_URL}/stations/bytag/{tag}", {}, on_result, on_error)

    def stations_by_uuids(self, uuids: list[str], on_result=None, on_error=None):
        if not uuids:
            if on_result:
                on_result([])
            return
        worker = _PostApiWorker(
            f"{BASE_URL}/stations/byuuid",
            {"uuids": ",".join(uuids)},
        )
        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        self._pool.start(worker)

    def _run(self, url: str, params: dict, on_result, on_error):
        worker = _ApiWorker(url, params)
        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        self._pool.start(worker)
