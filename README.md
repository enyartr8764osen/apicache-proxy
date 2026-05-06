# apicache-proxy

> Lightweight local caching proxy for REST APIs to reduce redundant calls during development.

---

## Installation

```bash
pip install apicache-proxy
```

Or install from source:

```bash
git clone https://github.com/youruser/apicache-proxy.git
cd apicache-proxy
pip install -e .
```

---

## Usage

Start the proxy server, pointing it at your target API:

```bash
apicache-proxy --target https://api.example.com --port 8080
```

Then direct your development requests to `http://localhost:8080` instead of the real API. Responses are cached locally and replayed on subsequent identical requests.

**Python API:**

```python
from apicache_proxy import ProxyServer

proxy = ProxyServer(target="https://api.example.com", port=8080, ttl=300)
proxy.start()
```

- `target` — the upstream API base URL
- `port` — local port to listen on (default: `8080`)
- `ttl` — cache time-to-live in seconds (default: `60`)

Cache is stored in `.apicache/` in the current directory. To clear it:

```bash
apicache-proxy --clear-cache
```

---

## Why?

During development, hitting a live API repeatedly wastes quota, adds latency, and can trigger rate limits. `apicache-proxy` sits between your code and the API, returning cached responses transparently with zero changes to your application logic.

---

## License

[MIT](LICENSE)