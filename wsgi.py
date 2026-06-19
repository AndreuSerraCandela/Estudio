"""
WSGI entry point para IIS.
Permite que IIS ejecute la aplicación Flask usando HttpPlatformHandler (igual que Rutas).
"""
import os
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr.encoding != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

os.chdir(project_dir)

log_file = None
try:
    log_file = os.path.join(project_dir, "logs", "wsgi.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n=== Iniciando WSGI - {os.getenv('HTTP_PLATFORM_PORT', 'N/A')} ===\n")
        f.write(f"Project dir: {project_dir}\n")
        f.write(f"Python path: {sys.executable}\n")
        f.write(f"Python version: {sys.version}\n")
        f.write(f"Working directory: {os.getcwd()}\n")
except Exception:
    pass

try:
    from run import app

    application = app
    try:
        if log_file:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("Aplicacion Flask importada correctamente\n")
                f.flush()
    except Exception:
        pass
except Exception as e:
    error_msg = f"Error importando aplicacion: {str(e)}\n"
    try:
        if log_file:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(error_msg)
                import traceback

                f.write(traceback.format_exc())
                f.flush()
    except Exception:
        pass
    raise

if os.environ.get("HTTP_PLATFORM_PORT"):
    try:
        port = int(os.environ.get("HTTP_PLATFORM_PORT", "8000"))
        try:
            if log_file:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"Iniciando waitress en puerto {port} (IIS)\n")
                    f.flush()
        except Exception:
            pass
        from waitress import serve

        print(f"Iniciando servidor en puerto {port} (IIS)", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        serve(application, host="127.0.0.1", port=port, threads=4, channel_timeout=120)
    except Exception as e:
        error_msg = f"Error iniciando waitress: {str(e)}\n"
        try:
            if log_file:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(error_msg)
                    import traceback

                    f.write(traceback.format_exc())
                    f.flush()
        except Exception:
            pass
        print(f"Error: {str(e)}", file=sys.stderr, flush=True)
        sys.stderr.flush()
        raise

if __name__ == "__main__" and not os.environ.get("HTTP_PLATFORM_PORT"):
    from app.config import settings

    application.run(debug=settings.flask_debug, host=settings.host, port=settings.port)
