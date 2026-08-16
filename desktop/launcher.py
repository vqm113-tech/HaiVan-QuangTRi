import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


APP_PORT = 8501
APP_URL = f"http://127.0.0.1:{APP_PORT}"

WINDOW_TITLE = "ĐÀI KHÍ TƯỢNG THUỶ VĂN TRUNG BỘ - ĐÀI KHÍ TƯỢNG THUỶ VĂN TỈNH QUẢNG TRỊ"

# Cờ đặc biệt để nhận biết tiến trình con: khi launcher.py (hoặc chính file
# .exe đã đóng gói) được gọi lại với cờ này, nó sẽ CHỈ chạy Streamlit
# server rồi thoát -- không mở lại giao diện launcher/pywebview.
_SERVER_MODE_FLAG = "--run-streamlit-server"

# Opener HTTP luôn bỏ qua proxy hệ thống -- dùng để kiểm tra Streamlit đã
# sẵn sàng chưa (xem server_is_ready()). Nếu không có dòng này, urllib có
# thể cố định tuyến request tới 127.0.0.1 qua proxy công ty/phần mềm bảo
# mật đang cấu hình sẵn trên máy, khiến request luôn thất bại dù server
# local hoàn toàn bình thường.
_NO_PROXY_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({})
)


def resource_path(relative_path: str) -> str:
    """Lấy đường dẫn tài nguyên cho cả Python và PyInstaller."""

    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

    return os.path.join(base_path, relative_path)


def write_error_log(exc):
    try:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(__file__)

        error_file = os.path.join(base_dir, "HaiVan_error.log")

        import traceback

        with open(error_file, "w", encoding="utf-8") as f:
            f.write("HAI VAN STARTUP ERROR\n====================\n\n")
            f.write(str(exc))
            f.write("\n\n")
            traceback.print_exc(file=f)

    except Exception:
        pass


def server_is_ready() -> bool:
    """Kiểm tra Streamlit đã THẬT SỰ sẵn sàng trả nội dung (HTTP 200)."""

    try:
        with _NO_PROXY_OPENER.open(APP_URL, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _safe_print(*args, **kwargs):
    """print() an toàn khi console=False -- ở chế độ windowed (không có
    console), sys.stdout có thể là None hoặc không hỗ trợ ghi, khiến
    print() thường ném lỗi và làm crash app. Bọc lại để chỉ log khi có
    console thật (ví dụ lúc debug với console=True), im lặng bỏ qua khi
    không có console (bản chính thức)."""

    try:
        if sys.stdout is not None:
            print(*args, **kwargs)
    except Exception:
        pass


def wait_for_server(timeout: int = 120) -> bool:
    start = time.time()
    last_print = 0.0

    while time.time() - start < timeout:
        if server_is_ready():
            _safe_print("[HaiVan] Server đã sẵn sàng!", flush=True)
            return True

        elapsed = time.time() - start
        if elapsed - last_print >= 5:
            _safe_print(
                f"[HaiVan] Đang chờ server ({elapsed:.0f}s / {timeout}s) ...",
                flush=True,
            )
            last_print = elapsed

        time.sleep(0.5)

    return False


# ---------------------------------------------------------------------------
# TIẾN TRÌNH CON: chỉ chạy Streamlit server rồi thoát.
# ---------------------------------------------------------------------------
def run_streamlit_server_in_this_process():
    """
    Chạy TRONG TIẾN TRÌNH CON (được spawn lại từ chính launcher.py / file
    .exe với cờ --run-streamlit-server). Dùng đúng CLI CHÍNH THỨC của
    Streamlit (`streamlit.web.cli`, chính là code chạy khi gõ lệnh
    `streamlit run app.py` ngoài terminal) thay vì gọi thẳng
    bootstrap.run() với dict flag_options tự chế như trước.

    Lý do đổi cách này: log thực tế trên máy đích cho thấy gọi thẳng
    bootstrap.run(flag_options=...) không áp dụng đúng nhiều cờ cấu hình
    trên phiên bản Streamlit hiện tại (server.address bị bỏ qua -> bind
    0.0.0.0 thay vì 127.0.0.1; server.enableXsrfProtection bị bỏ qua).
    CLI chính thức parse tham số dòng lệnh theo đúng cách Streamlit tự
    kiểm thử, đáng tin cậy hơn hẳn so với gọi thẳng API nội bộ.

    Vì đây là TIẾN TRÌNH RIÊNG (không phải thread phụ trong cùng tiến
    trình launcher), main thread của tiến trình con này có thể tự do gọi
    signal.signal() (Streamlit cần) mà không đụng độ với main thread của
    tiến trình cha (đang dành cho pywebview) -- không cần "vá" signal
    như cách làm cũ nữa.
    """

    app_path = resource_path("app.py")

    if not os.path.isfile(app_path):
        write_error_log(
            FileNotFoundError(f"Không tìm thấy app.py:\n{app_path}")
        )
        sys.exit(1)

    app_dir = os.path.dirname(app_path)
    os.chdir(app_dir)

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.port", str(APP_PORT),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]

    try:
        from streamlit.web.cli import main as st_cli_main

        st_cli_main()

    except Exception as exc:
        write_error_log(exc)
        raise


# ---------------------------------------------------------------------------
# TIẾN TRÌNH CHA: spawn tiến trình con chạy Streamlit, rồi mở giao diện.
# ---------------------------------------------------------------------------
def start_streamlit_subprocess():
    """
    Spawn lại chính file thực thi này (launcher.py lúc dev, hoặc chính
    file .exe khi đã đóng gói) kèm cờ --run-streamlit-server, để tiến
    trình con biết chỉ cần chạy Streamlit server, không mở lại giao diện
    launcher.
    """

    if getattr(sys, "frozen", False):
        cmd = [sys.executable, _SERVER_MODE_FLAG]
    else:
        cmd = [sys.executable, os.path.abspath(__file__), _SERVER_MODE_FLAG]

    kwargs = {}
    if os.name == "nt":
        # Không cho tiến trình con tự bật thêm 1 cửa sổ console riêng khi
        # chạy dev bằng python.exe (bản .exe đóng gói vốn đã windowed nên
        # không bị ảnh hưởng).
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    return subprocess.Popen(cmd, **kwargs)


def main():

    app_path = resource_path("app.py")

    if not os.path.isfile(app_path):
        raise FileNotFoundError(
            f"Không tìm thấy file ứng dụng:\n{app_path}"
        )

    _safe_print("[HaiVan] Đang khởi động tiến trình Streamlit server...", flush=True)
    server_process = start_streamlit_subprocess()

    try:
        timeout = 120

        if not wait_for_server(timeout):
            raise TimeoutError(
                f"Streamlit không khởi động được trong {timeout} giây."
            )

        try:
            import webview

            # QUAN TRỌNG: pywebview mặc định TẮT HOÀN TOÀN mọi lượt tải
            # file (ALLOW_DOWNLOADS = False) -- nếu không bật dòng này,
            # bấm nút "Tải xuống" trong app sẽ không có phản ứng gì cả.
            webview.settings["ALLOW_DOWNLOADS"] = True

            # pywebview: PHẢI gọi ở main thread -> đang ở main() nên đúng.
            webview.create_window(
                WINDOW_TITLE, APP_URL, width=1280, height=860,
            )
            webview.start()

        except ImportError:
            # Chưa cài pywebview -> mở tab trình duyệt mặc định thay vào đó.
            webbrowser.open(APP_URL)

            while server_process.poll() is None:
                time.sleep(1)

    except Exception as exc:
        write_error_log(exc)
        raise

    finally:
        # Cửa sổ đã đóng (hoặc có lỗi) -> tắt luôn tiến trình Streamlit con
        # trước khi thoát, tránh để lại tiến trình mồ côi chiếm cổng 8501.
        if server_process.poll() is None:
            server_process.terminate()

            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()

        os._exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == _SERVER_MODE_FLAG:
        run_streamlit_server_in_this_process()
    else:
        main()
