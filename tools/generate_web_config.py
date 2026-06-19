"""Genera web.config identico al patron Rutas/Fijaciones."""
from __future__ import annotations

import os
from pathlib import Path

PY_IIS = os.getenv("ESTUDIO_PYTHON", r"C:\Python\python.exe")
SITE_DIR = Path(os.getenv("ESTUDIO_SITE_DIR", Path(__file__).resolve().parent.parent)).resolve()
LOG_DIR = SITE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

web_config = f"""<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>

    <handlers>
      <add name="httpPlatformHandler"
           path="*"
           verb="*"
           modules="httpPlatformHandler"
           resourceType="Unspecified" />
    </handlers>

    <httpPlatform
        processPath="{PY_IIS}"
        arguments="wsgi.py"
        stdoutLogEnabled="true"
        stdoutLogFile="{LOG_DIR / 'stdout.log'}">

      <environmentVariables>
        <environmentVariable name="HTTP_PLATFORM_PORT" value="%HTTP_PLATFORM_PORT%" />
      </environmentVariables>

    </httpPlatform>

  </system.webServer>
</configuration>
"""

(SITE_DIR / "web.config").write_text(web_config, encoding="utf-8")
print(f"web.config -> {SITE_DIR / 'web.config'}")
print(f"Python IIS: {PY_IIS}")
print(f"Logs: {LOG_DIR / 'stdout.log'}")
