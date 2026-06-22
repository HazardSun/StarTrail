from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer

# Use at most 2 background threads to avoid oversubscribing the NPU/GPU
QThreadPool.globalInstance().setMaxThreadCount(2)


class _TaskSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class _Task(QRunnable):
    def __init__(self, target, args, kwargs, signals):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._signals = signals

    def run(self):
        try:
            result = self._target(*self._args, **self._kwargs)
            try:
                self._signals.finished.emit(result)
            except RuntimeError:
                pass  # app shutting down
        except Exception as e:
            try:
                self._signals.error.emit(str(e))
            except RuntimeError:
                pass  # app shutting down


_SIGNAL_REFS = []


def run_in_background(target, on_finished=None, on_error=None, args=None, kwargs=None):
    """Run `target(*args, **kwargs)` in a background thread via QThreadPool."""
    signals = _TaskSignals()
    _SIGNAL_REFS.append(signals)  # prevent GC of the C++ QObject

    task = _Task(target, args or (), kwargs or {}, signals)

    def release():
        if signals in _SIGNAL_REFS:
            _SIGNAL_REFS.remove(signals)

    if on_finished:
        signals.finished.connect(on_finished)
    if on_error:
        signals.error.connect(on_error)
    signals.finished.connect(release)
    signals.error.connect(release)

    QThreadPool.globalInstance().start(task)


class DebouncedRunner:
    """Debounce repeated calls: only the last call within `delay_ms` runs."""

    def __init__(self, delay_ms=2000):
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        self._delay = delay_ms
        self._pending_fn = None

    def schedule(self, fn, args=None, kwargs=None):
        self._pending_fn = (fn, args or (), kwargs or {})
        self._timer.start(self._delay)

    def _fire(self):
        if self._pending_fn:
            fn, args, kwargs = self._pending_fn
            self._pending_fn = None
            run_in_background(fn, args=args, kwargs=kwargs)

    def cancel(self):
        self._timer.stop()
        self._pending_fn = None
