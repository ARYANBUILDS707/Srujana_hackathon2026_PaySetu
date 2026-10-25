"""Print the API's OpenAPI document as JSON (input for the frontend type generator).

Run via `make api-types`. Uses throwaway in-memory settings: nothing is read from `.env`,
no database file is created and no network is used.
"""

import json
import sys
import tempfile

from app.config import load_settings
from app.main import create_app


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        settings = load_settings(
            _env_file=None,
            app_env="development",
            public_base_url="http://localhost:3000",
            database_url="sqlite://",
            storage_dir=directory,
            token_hash_key="openapi-export-only-key-0123456789abcdef",
            email_mode="simulated",
        )
        schema = create_app(settings).openapi()
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
