from __future__ import annotations

from quant_os.data.warehouse import ensure_local_dirs

if __name__ == "__main__":
    ensure_local_dirs()
    print("local directories ready")
