"""Zugang des Werkzeug-Servers zu Odoo (JSON-RPC, API-Schlüssel des Benutzers «Werkzeug-Server»).

Nur Standardbibliothek. Zugangsdaten kommen aus der Umgebung (werkzeug-server/.env), nie aus einem Aufruf.
"""

import json
import os
import urllib.request


class OdooFehler(RuntimeError):
    pass


class Odoo:
    def __init__(self):
        self.url = os.environ.get("ODOO_URL", "").rstrip("/")
        self.db = os.environ.get("ODOO_DB", "")
        self.user = os.environ.get("ODOO_USER", "")
        self._key = os.environ.get("ODOO_API_KEY", "")
        self.uid = None

    @property
    def eingerichtet(self) -> bool:
        return bool(self.url and self.db and self.user and self._key)

    def _rpc(self, service, method, *args):
        body = json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1,
                           "params": {"service": service, "method": method, "args": list(args)}}).encode()
        anfrage = urllib.request.Request(f"{self.url}/jsonrpc", data=body,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            daten = json.loads(antwort.read())
        if daten.get("error"):
            fehler = daten["error"]
            raise OdooFehler(fehler.get("data", {}).get("message") or fehler.get("message"))
        return daten.get("result")

    def anmelden(self):
        if not self.eingerichtet:
            raise OdooFehler("Odoo-Zugang des Servers ist nicht eingerichtet (werkzeug-server/.env).")
        if self.uid is None:
            self.uid = self._rpc("common", "authenticate", self.db, self.user, self._key, {})
            if not self.uid:
                raise OdooFehler("Anmeldung bei Odoo fehlgeschlagen.")
        return self.uid

    def call(self, model, method, *args, **kwargs):
        self.anmelden()
        kwargs["context"] = {"lang": "de_CH", **kwargs.pop("context", {})}
        return self._rpc("object", "execute_kw", self.db, self.uid, self._key, model, method, list(args), kwargs)

    def search_read(self, model, domain, fields, **kwargs):
        return self.call(model, "search_read", domain, fields=fields, **kwargs)
