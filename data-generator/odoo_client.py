"""Schlanke Verbindung zu Odoo über JSON-RPC, Anmeldung mit API-Schlüssel.

JSON-RPC statt XML-RPC: Odoo-Methoden wie create_invoices geben Werte mit None zurück,
die XML-RPC nicht übertragen kann.
"""

import json
import urllib.request

from config import load_config


class OdooError(RuntimeError):
    pass


class OdooClient:
    def __init__(self, config=None):
        config = config or load_config()
        self.url = config["ODOO_URL"].rstrip("/")
        self.db = config["ODOO_DB"]
        self.user = config["ODOO_USER"]
        self._key = config["ODOO_API_KEY"]
        self._id = 0
        self.uid = None

    def _rpc(self, service, method, *args):
        self._id += 1
        payload = {"jsonrpc": "2.0", "method": "call", "id": self._id,
                   "params": {"service": service, "method": method, "args": list(args)}}
        request = urllib.request.Request(f"{self.url}/jsonrpc", data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=300) as response:
            answer = json.loads(response.read())
        if answer.get("error"):
            data = answer["error"].get("data", {})
            raise OdooError(data.get("message") or answer["error"].get("message"))
        return answer.get("result")

    def version(self):
        return self._rpc("common", "version")

    def login(self):
        self.uid = self._rpc("common", "authenticate", self.db, self.user, self._key, {})
        if not self.uid:
            raise SystemExit("Anmeldung fehlgeschlagen: Benutzer oder API-Schlüssel stimmt nicht.")
        return self.uid

    def call(self, model, method, *args, **kwargs):
        # Ohne Sprachangabe liefert Odoo englische Namen
        context = {"lang": "de_CH", **kwargs.pop("context", {})}
        kwargs["context"] = context
        return self._rpc("object", "execute_kw", self.db, self.uid, self._key, model, method, list(args), kwargs)

    def search_read(self, model, domain=None, fields=None, **kwargs):
        if fields is not None:
            kwargs["fields"] = fields
        return self.call(model, "search_read", domain or [], **kwargs)

    def search_count(self, model, domain=None):
        return self.call(model, "search_count", domain or [])

    def fields(self, model):
        return self.call(model, "fields_get", attributes=["string", "type", "relation"])
