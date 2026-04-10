import os

print("[add_header_request] Script loaded")

_headers = {
    key[len("ZAP_AUTH_HEADER_"):]: value
    for key, value in os.environ.items()
    if key.startswith("ZAP_AUTH_HEADER_")
}

if _headers:
    print(f"[add_header_request] Found {len(_headers)} header(s) to inject: {list(_headers.keys())}")
else:
    print("[add_header_request] No ZAP_AUTH_HEADER_* env vars found — no headers will be injected")


def sendingRequest(msg, initiator, helper):
    for header_name, value in _headers.items():
        msg.getRequestHeader().setHeader(header_name, value)


def responseReceived(msg, initiator, helper):
    pass