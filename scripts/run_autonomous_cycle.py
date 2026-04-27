from __future__ import annotations

from quant_os.autonomy.supervisor import Supervisor

if __name__ == "__main__":
    state = Supervisor().run_once()
    print(state.model_dump_json(indent=2))
