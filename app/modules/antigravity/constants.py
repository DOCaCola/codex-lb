"""Wire constants of the native Antigravity CLI (agy 1.4.10 capture, 2026-10-29)."""

from __future__ import annotations

ANTIGRAVITY_KIND = "antigravity"
# Client-facing model prefix; keeps Claude-on-Antigravity apart from native Claude sources.
MODEL_PREFIX = "antigravity/"

CLOUD_CODE_BASE_URL = "https://daily-cloudcode-pa.googleapis.com"
API_VERSION = "v1internal"

# Public installed-application OAuth client embedded in the Antigravity clients.
CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
CLIENT_SECRET = "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"
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
# The CLI's remote (SSH) flow: Google redirects here and the operator pastes the code back.
REDIRECT_URI = "https://antigravity.google/oauth-callback"
SCOPES = (
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
    "https://www.googleapis.com/auth/aicode",
    "openid",
)

MANIFEST_URL = "https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/{platform}.json"
PLATFORMS = ("darwin_arm64", "darwin_amd64", "linux_arm64", "linux_amd64", "windows_amd64", "windows_arm64")
DEFAULT_PLATFORM = "darwin_arm64"

# Thought-signature sentinel accepted for Gemini function calls without a valid signature.
SKIP_SIGNATURE = "skip_thought_signature_validator"
