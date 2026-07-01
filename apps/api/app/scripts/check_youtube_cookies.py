from __future__ import annotations

from app.core.youtube_diagnostics import diagnose_youtube_cookies


def main() -> int:
    result = diagnose_youtube_cookies()
    if result.ok:
        print("OK: cookies parecem autenticados")
        return 0

    print("ERRO: cookies nao contem LOGIN_INFO/SID/APISID/SAPISID")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
