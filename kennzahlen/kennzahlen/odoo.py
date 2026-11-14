"""Verbindung zu Odoo über JSON-RPC. Nur Lesemethoden, fest im Code.

Die Zugangsdaten kommen aus der Umgebung (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY).
Der Schlüssel erscheint nie in einer Ausgabe oder Fehlermeldung.
"""

import json
import os
import urllib.error
import urllib.request

# Alles andere bricht ab, bevor Odoo kontaktiert wird
ERLAUBTE_METHODEN = frozenset({"search_read", "read", "read_group", "search_count", "fields_get"})
UMGEBUNG = ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_API_KEY")


class OdooFehler(RuntimeError):
    pass


class Odoo:
    def __init__(self, url, db, user, key, timeout=60):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self._key = key
        self.timeout = timeout
        self.uid = None
        self._id = 0

    @classmethod
    def aus_umgebung(cls):
        fehlend = [name for name in UMGEBUNG if not os.environ.get(name)]
        if fehlend:
            raise OdooFehler(f"Umgebungsvariablen fehlen: {', '.join(fehlend)}")
        return cls(*(os.environ[name] for name in UMGEBUNG))

    def _rpc(self, service, method, *args):
        self._id += 1
        payload = {"jsonrpc": "2.0", "method": "call", "id": self._id,
                   "params": {"service": service, "method": method, "args": list(args)}}
        request = urllib.request.Request(f"{self.url}/jsonrpc", data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                answer = json.loads(response.read())
        except urllib.error.URLError as exc:
            raise OdooFehler(f"Odoo nicht erreichbar ({self.url}): {exc.reason}") from None
        if answer.get("error"):
            data = answer["error"].get("data", {})
            meldung = data.get("message") or answer["error"].get("message") or "unbekannter Fehler"
            raise OdooFehler(f"Odoo meldet: {meldung.replace(self._key, '***')}")
        return answer.get("result")

    def anmelden(self):
        self.uid = self._rpc("common", "authenticate", self.db, self.user, self._key, {})
        if not self.uid:
            raise OdooFehler("Anmeldung bei Odoo fehlgeschlagen: Benutzer oder Schlüssel stimmt nicht.")
        return self.uid

    def aufruf(self, model, method, args, kwargs=None):
        if method not in ERLAUBTE_METHODEN:
            raise OdooFehler(f"Abgebrochen: die Methode '{method}' ist nicht erlaubt.")
        if self.uid is None:
            self.anmelden()
        kwargs = dict(kwargs or {})
        kwargs["context"] = {"lang": "de_CH", **kwargs.get("context", {})}
        return self._rpc("object", "execute_kw", self.db, self.uid, self._key, model, method, args, kwargs)

    def search_read(self, model, domain, fields, **kwargs):
        return self.aufruf(model, "search_read", [domain], {"fields": fields, **kwargs})

    def read(self, model, ids, fields):
        return self.aufruf(model, "read", [ids], {"fields": fields})

    def read_group(self, model, domain, fields, groupby):
        return self.aufruf(model, "read_group", [domain, fields, groupby], {"lazy": False})
