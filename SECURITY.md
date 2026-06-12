# Security Policy

## Supported Versions

Only the default branch is intended to receive updates.

## Reporting a Vulnerability

Please report security issues privately by opening a GitHub security advisory or contacting the repository owner.

Do not include sensitive health, medical, or personal data in reports. This project should only be used with non-sensitive personal inputs.

## Feedback Data

The Streamlit feedback controls store thumbs feedback in the current local session only. The app does not upload feedback, profile inputs, or generated meal plans. If a user exports the feedback CSV, that file should be treated as user-controlled local data and should not be committed if it contains personal notes or profile details.

The FastAPI feedback endpoint is intended for local experiments. Feedback writes are disabled by default; `POST /feedback` returns `403` unless `AI_NUTRITIONIST_ENABLE_API_FEEDBACK=1` is set before app startup. The feedback store is initialized lazily only after enabled feedback writes are used; health, OpenAPI, recommendation endpoints, disabled feedback writes, and the default-disabled feedback readback route do not create persistent feedback storage. Enabled writes default to `.local/feedback.sqlite`, or to `AI_NUTRITIONIST_FEEDBACK_DB` if explicitly configured. `AI_NUTRITIONIST_MAX_FEEDBACK_ENTRIES` bounds API-readable local rows with a default of `1000` and a hard cap of `10000`; SQLite `secure_delete` is enabled on store connections before old rows are trimmed, but exported CSVs and local databases remain user data and should be removed when no longer needed. `GET /feedback` returns `403` unless `AI_NUTRITIONIST_ENABLE_FEEDBACK_READBACK=1` is set for local review. `.local/`, `.local_*` runtime markers, `.env` files, exported feedback, private keys, PDFs, ZIP archives, cache directories, SQLite/DB files, and raw data archives must not be committed.

## API Boundary

The API returns public-safe recommendation payloads and omits internal neural, heuristic, and quality scores. Recommendation preference terms and feedback avoid terms are length-bounded to reduce accidental abuse and memory pressure. Recipe ingredient grocery output is generated only for reviewed recipe-backed pilot rows and uses informational allergen tags; those tags are not allergy-safety guarantees. The API does not provide authentication or user management, and its only persistence path is the opt-in local feedback endpoint described above. Do not expose it as a production public service without adding rate limiting, privacy policy, retention rules, and abuse controls.

## Safety Scope

AI Nutritionist is not medical advice and does not make clinical claims. Reports about medical correctness, nutritional adequacy, or health outcomes should be treated as product-safety feedback rather than security vulnerabilities.
