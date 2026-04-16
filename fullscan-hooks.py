import os
import re
import requests
import traceback


def zap_started(zap, target):
    """
    Generic hook:
    0. Configures ZAP authentication (bearer/form/cookie/header) from env vars
    1. Runs katana (headless browser crawler) to discover all endpoints
    2. Extracts API paths from JS bundles via regex
    3. Checks for OpenAPI/Swagger specs
    4. Feeds everything to ZAP before active scanning
    """
    print("[HOOK] zap_started: Starting endpoint discovery...")

    # ========== Phase 0: Auth headers + scope restriction ==========
    print("[HOOK] Phase 0: Configuring auth headers and scope...")

    # Build target URL regex for scoping (e.g. "http://example.com:8080" → "http://example\\.com:8080.*")
    from urllib.parse import urlparse
    parsed = urlparse(target)
    target_regex = re.escape(parsed.scheme + "://" + parsed.netloc) + ".*"

    # Restrict ZAP context to target domain only — prevents spider/scanner from going off-scope
    try:
        zap.context.include_in_context("Default Context", target_regex)
        zap.context.exclude_from_context("Default Context", "(?:(?!%s).)*" % re.escape(parsed.netloc))
        print(f"[HOOK] Phase 0: Scope restricted to {parsed.netloc}")
    except Exception as e:
        print(f"[HOOK] Phase 0: Scope restriction failed (non-fatal): {e}")

    # Inject auth headers via replacer — scoped to target domain only (prevents token leak to external domains)
    header_count = 0
    for key, value in os.environ.items():
        if key.startswith("ZAP_AUTH_HEADER_"):
            header_name = key[len("ZAP_AUTH_HEADER_"):]
            try:
                zap._request(
                    zap.base + "replacer/action/addRule/",
                    {"description": f"Auth-{header_name}", "enabled": "true",
                     "matchType": "REQ_HEADER", "matchRegex": "false",
                     "matchString": header_name, "replacement": value,
                     "url": target_regex}
                )
                header_count += 1
                print(f"[HOOK] Phase 0: Added header → {header_name} (scoped to {parsed.netloc})")
            except Exception as e:
                print(f"[HOOK] Phase 0: Failed to add header {header_name}: {e}")
    if header_count == 0:
        print("[HOOK] Phase 0: No ZAP_AUTH_HEADER_* env vars found")

    # Build a requests-compatible headers dict from the same env vars so that
    # Phase 2 and Phase 3's direct HTTP calls also carry auth credentials.
    auth_headers = {
        k[len("ZAP_AUTH_HEADER_"):]: v
        for k, v in os.environ.items()
        if k.startswith("ZAP_AUTH_HEADER_")
    }

    api_endpoints = set()

    # ========== Phase 1: Read katana output file (if exists) ==========
    katana_file = os.environ.get("KATANA_URLS", "/zap/wrk/katana-urls.txt")
    print(f"[HOOK] Phase 1: Attempting to read katana output from {katana_file}...")
    try:
        with open(katana_file, "r") as f:
            katana_urls = [u.strip() for u in f.readlines() if u.strip()]
        print(f"[HOOK] Phase 1: Loaded {len(katana_urls)} URLs from katana output")

        for url in katana_urls:
            if target.rstrip("/") in url:
                path = url.replace(target.rstrip("/"), "")
                if path and not path.endswith(('.css', '.png', '.jpg', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.map')):
                    api_endpoints.add(path)
            elif url.startswith("/"):
                api_endpoints.add(url)

        print(f"[HOOK] Katana contributed {len(api_endpoints)} unique paths")

    except FileNotFoundError:
        print(f"[HOOK] Phase 1: No katana file found at {katana_file} — skipping, using JS parsing only")
    except Exception as e:
        print(f"[HOOK] Katana file error: {e}")

    # ========== Phase 2: JS bundle endpoint extraction ==========
    try:
        print("[HOOK] Phase 2: Parsing JS bundles for API endpoints...")
        resp = requests.get(target, headers=auth_headers, timeout=10)
        html = resp.text

        js_files = list(set(
            re.findall(r'src="([^"]*\.js)"', html) +
            re.findall(r"src='([^']*\.js)'", html)
        ))

        for common in ["/main.js", "/app.js", "/bundle.js", "/vendor.js", "/runtime.js"]:
            if common not in js_files:
                js_files.append(common)

        for js_file in js_files:
            if js_file.startswith("//"):
                js_url = "http:" + js_file
            elif js_file.startswith("/"):
                js_url = target.rstrip("/") + js_file
            elif js_file.startswith("http"):
                js_url = js_file
            else:
                js_url = target.rstrip("/") + "/" + js_file

            try:
                js_resp = requests.get(js_url, headers=auth_headers, timeout=15)
                if js_resp.status_code != 200:
                    continue
                js_content = js_resp.text

                # Generic API path patterns
                path_patterns = [
                    r'["\'](/api/[A-Za-z][A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/rest/[A-Za-z][A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/v[0-9]+/[A-Za-z][A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/graphql[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/auth/[A-Za-z][A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/login[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/register[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/admin[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/user[s]?/[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/account[s]?/[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/upload[s]?[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/search[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/profile[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/redirect[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/export[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/metrics[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/health[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                    r'["\'](/ftp[A-Za-z0-9_/.-]*)["\'\s\?\)]',
                ]

                for pattern in path_patterns:
                    matches = re.findall(pattern, js_content)
                    for m in matches:
                        if not any(m.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.map']):
                            api_endpoints.add(m)

                # Template literals: `/rest/something/${var}`
                for m in re.findall(r'`(/(?:api|rest|v[0-9]+)/[^`]*)`', js_content):
                    clean = re.sub(r'\$\{[^}]*\}', 'test', m)
                    if not clean.endswith(('.js', '.css', '.png', '.jpg', '.svg')):
                        api_endpoints.add(clean)

                # Concatenated strings: hostUrl + "/rest/user/login"
                for pattern in [
                    r'["\'](/(?:api|rest)/[A-Za-z0-9_/-]+)["\'\s]*\+',
                    r'\+\s*["\'](/(?:api|rest|ftp|admin)/[A-Za-z0-9_/-]+)["\']',
                    r'(?:hostUrl|baseUrl|apiUrl|host|url|URL|endpoint)\s*\+\s*["\'](/[A-Za-z0-9_/-]+)["\']',
                    r'["\'](/[A-Za-z][A-Za-z0-9_-]+/[A-Za-z][A-Za-z0-9_/-]*)["\']',
                ]:
                    for m in re.findall(pattern, js_content):
                        if len(m) > 3 and not m.endswith(('.js', '.css', '.png', '.jpg', '.svg', '.ico')):
                            api_endpoints.add(m)

                # Catch Angular/React route definitions: path: "administration"
                for m in re.findall(r'path:\s*["\'](/?\w[\w/-]*)["\']', js_content):
                    if len(m) > 2 and not m.endswith(('.js', '.css')):
                        path = m if m.startswith("/") else "/" + m
                        api_endpoints.add(path)

                # fetch/axios/http calls
                for pattern in [
                    r'(?:fetch|get|post|put|delete|patch|request)\s*\(\s*["\']([^"\']+)["\']',
                    r'\.(?:get|post|put|delete|patch)\s*(?:<[^>]*>)?\s*\(\s*[`"\']([^`"\']+)[`"\']',
                ]:
                    for m in re.findall(pattern, js_content, re.IGNORECASE):
                        if m.startswith("/") and not m.endswith(('.js', '.css', '.png', '.jpg', '.svg', '.ico')):
                            api_endpoints.add(m)

            except Exception:
                continue

        print(f"[HOOK] JS parsing: {len(api_endpoints)} total endpoints")

    except Exception as e:
        print(f"[HOOK] JS parsing error: {e}")

    # ========== Phase 3: OpenAPI/Swagger discovery ==========
    try:
        print("[HOOK] Phase 3: Checking for OpenAPI/Swagger specs...")
        for path in ["/swagger.json", "/openapi.json", "/api-docs", "/v2/api-docs", "/v3/api-docs", "/swagger/v1/swagger.json", "/.well-known/openapi.json"]:
            try:
                r = requests.get(target.rstrip("/") + path, headers=auth_headers, timeout=5)
                if r.status_code == 200 and ("openapi" in r.text.lower() or "swagger" in r.text.lower()):
                    spec = r.json()
                    for p in spec.get("paths", {}).keys():
                        api_endpoints.add(p)
                    print(f"[HOOK] Imported {len(spec.get('paths', {}))} paths from {path}")
                    break
            except:
                pass
    except:
        pass

    # ========== Phase 4: Expand with parameter variations ==========
    expanded = set()
    for ep in api_endpoints:
        expanded.add(ep)
        # Resource endpoints → add /1 for IDOR testing
        parts = ep.rstrip("/").split("/")
        last = parts[-1] if parts else ""
        if last and last[0].isupper() and last.endswith("s") and "?" not in ep:
            expanded.add(ep.rstrip("/") + "/1")
        # Search endpoints → add ?q=test
        if "search" in ep.lower() and "?" not in ep:
            expanded.add(ep + "?q=test")

    print(f"[HOOK] Expanded to {len(expanded)} endpoint variations")

    # ========== Phase 5: Feed to ZAP ==========
    fed_count = 0
    for endpoint in sorted(expanded):
        full_url = target.rstrip("/") + endpoint
        try:
            zap.core.access_url(url=full_url, followredirects=True)
            fed_count += 1
        except:
            try:
                zap.core.access_url(url=full_url, followredirects=False)
                fed_count += 1
            except:
                pass

    # POST requests for write endpoints
    post_keywords = ["login", "register", "feedback", "complaint", "user", "basket", "order", "recycle", "address", "card", "chatbot", "upload", "contact"]
    for endpoint in [ep for ep in expanded if any(k in ep.lower() for k in post_keywords) and "?" not in ep]:
        full_url = target.rstrip("/") + endpoint
        try:
            host = target.split("//")[1].rstrip("/")
            zap.core.send_request(
                request=f"POST {full_url} HTTP/1.1\r\nHost: {host}\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{{}}"
            )
            fed_count += 1
        except:
            pass

    print(f"[HOOK] Fed {fed_count} total requests to ZAP")
    print(f"[HOOK] Discovery complete. ZAP active scanner will now attack {len(expanded)} endpoints")