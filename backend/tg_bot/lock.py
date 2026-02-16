import atexit
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

LOCK_FILENAME = "election_manager_bot_runner.lock"

_WIN_MUTEX_HANDLE = None
_WIN_LOCK_FILE = None


def default_lock_path() -> str:
    return os.path.join(tempfile.gettempdir(), LOCK_FILENAME)


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            OpenProcess = kernel32.OpenProcess
            OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            OpenProcess.restype = wintypes.HANDLE

            GetExitCodeProcess = kernel32.GetExitCodeProcess
            GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            GetExitCodeProcess.restype = wintypes.BOOL

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not h:
                try:
                    err = int(ctypes.get_last_error())
                except Exception:
                    err = 0

                ERROR_INVALID_PARAMETER = 87
                ERROR_ACCESS_DENIED = 5
                if err == ERROR_INVALID_PARAMETER:
                    return False
                if err == ERROR_ACCESS_DENIED:
                    return True
                return True
            try:
                code = wintypes.DWORD(0)
                ok = GetExitCodeProcess(h, ctypes.byref(code))
                if not ok:
                    return False
                return int(code.value) == STILL_ACTIVE
            finally:
                CloseHandle(h)
        except Exception:
            pass

    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    else:
        return True


def acquire_single_instance_lock(lock_path: str) -> None:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            CreateMutexW = kernel32.CreateMutexW
            CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            CreateMutexW.restype = wintypes.HANDLE

            WaitForSingleObject = kernel32.WaitForSingleObject
            WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            WaitForSingleObject.restype = wintypes.DWORD

            ReleaseMutex = kernel32.ReleaseMutex
            ReleaseMutex.argtypes = [wintypes.HANDLE]
            ReleaseMutex.restype = wintypes.BOOL

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            WAIT_OBJECT_0 = 0
            WAIT_TIMEOUT = 258
            WAIT_ABANDONED = 0x80

            def _try_acquire_mutex(name: str):
                h = CreateMutexW(None, False, name)
                if not h:
                    return None, False

                res = int(WaitForSingleObject(h, 0))
                if res == WAIT_TIMEOUT:
                    try:
                        CloseHandle(h)
                    except Exception:
                        pass
                    return None, False

                if res not in {WAIT_OBJECT_0, WAIT_ABANDONED}:
                    try:
                        CloseHandle(h)
                    except Exception:
                        pass
                    return None, False

                return h, True

            h, ok = _try_acquire_mutex("Global\\ElectionManagerBotRunner")
            if not ok:
                h, ok = _try_acquire_mutex("Local\\ElectionManagerBotRunner")

            if not ok:
                raise SystemExit(
                    "bot_runner already running (Windows mutex). "
                    "If you started it via a VS Code background task, stop that task or kill the existing process."
                )

            if h is not None and ok:
                global _WIN_MUTEX_HANDLE
                _WIN_MUTEX_HANDLE = h

                def _cleanup_mutex() -> None:
                    try:
                        if _WIN_MUTEX_HANDLE:
                            try:
                                ReleaseMutex(_WIN_MUTEX_HANDLE)
                            except Exception:
                                pass
                            try:
                                CloseHandle(_WIN_MUTEX_HANDLE)
                            except Exception:
                                pass
                    except Exception:
                        pass

                atexit.register(_cleanup_mutex)
        except SystemExit:
            raise
        except Exception:
            pass

        try:
            import msvcrt

            lock_dir = os.path.dirname(lock_path)
            if lock_dir:
                os.makedirs(lock_dir, exist_ok=True)

            # If a previous run was killed hard, a stale lock file can remain.
            # It shouldn't block the actual file lock, but cleaning it up avoids confusion.
            try:
                if os.path.exists(lock_path):
                    with open(lock_path, "r", encoding="utf-8") as rf:
                        existing_raw = (rf.read() or "").strip().splitlines()[0] if rf else ""
                    existing_pid = int(existing_raw) if existing_raw else None
                    if isinstance(existing_pid, int) and existing_pid > 0 and not is_pid_running(existing_pid):
                        try:
                            os.remove(lock_path)
                        except Exception:
                            pass
            except Exception:
                pass

            existing_pid_for_msg = None
            try:
                if os.path.exists(lock_path):
                    with open(lock_path, "r", encoding="utf-8") as rf:
                        existing_raw = (rf.read() or "").strip().splitlines()[0] if rf else ""
                    existing_pid_for_msg = int(existing_raw) if existing_raw else None
            except Exception:
                existing_pid_for_msg = None

            f = open(lock_path, "a+", encoding="utf-8")
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

                pid_text = f"{os.getpid()}\n"
                f.seek(0)
                f.write(pid_text)
                f.flush()
                try:
                    f.truncate(max(len(pid_text), 1))
                except Exception:
                    pass
            except OSError:
                existing_pid = existing_pid_for_msg
                try:
                    f.close()
                except Exception:
                    pass

                if isinstance(existing_pid, int) and existing_pid > 0:
                    if is_pid_running(existing_pid):
                        raise SystemExit(
                            f"bot_runner already running (Windows file lock; pid={existing_pid}; lock={lock_path})"
                        )
                    raise SystemExit(
                        f"bot_runner lock file exists but PID is not running (pid={existing_pid}; lock={lock_path}). "
                        "Try deleting the lock file and restart."
                    )

                raise SystemExit(f"bot_runner already running (Windows file lock; lock={lock_path})")

            global _WIN_LOCK_FILE
            _WIN_LOCK_FILE = f

            def _cleanup_file_lock() -> None:
                try:
                    if _WIN_LOCK_FILE:
                        try:
                            _WIN_LOCK_FILE.seek(0)
                            msvcrt.locking(_WIN_LOCK_FILE.fileno(), msvcrt.LK_UNLCK, 1)
                        except Exception:
                            pass
                        try:
                            _WIN_LOCK_FILE.close()
                        except Exception:
                            pass

                    # Best-effort cleanup to avoid confusing stale lock files.
                    try:
                        if os.path.exists(lock_path):
                            with open(lock_path, "r", encoding="utf-8") as rf:
                                existing = (rf.read() or "").strip()
                            if existing == str(os.getpid()):
                                os.remove(lock_path)
                    except Exception:
                        pass
                except Exception:
                    pass

            atexit.register(_cleanup_file_lock)
            logger.info(f"Acquired bot_runner Windows file lock: {lock_path} (pid={os.getpid()})")
            return
        except SystemExit:
            raise
        except Exception:
            pass

    lock_dir = os.path.dirname(lock_path)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)

    pid = os.getpid()

    for _ in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(str(pid))

            def _cleanup() -> None:
                try:
                    if os.path.exists(lock_path):
                        with open(lock_path, "r", encoding="utf-8") as rf:
                            existing = (rf.read() or "").strip()
                        if existing == str(pid):
                            os.remove(lock_path)
                except Exception:
                    pass

            atexit.register(_cleanup)
            logger.info(f"Acquired bot_runner lock: {lock_path} (pid={pid})")
            return
        except FileExistsError:
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    existing_pid_raw = (f.read() or "").strip()
                existing_pid = int(existing_pid_raw) if existing_pid_raw else -1
            except Exception:
                existing_pid = -1

            if existing_pid > 0 and is_pid_running(existing_pid):
                raise SystemExit(
                    f"bot_runner already running (pid={existing_pid}). "
                    f"Stop the other process before starting a new one. lock={lock_path}"
                )

            try:
                os.remove(lock_path)
            except Exception:
                pass

    raise SystemExit(f"Could not acquire bot_runner lock: {lock_path}")
