import base64
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEED = {
    "ip/address": [
        {"address": "192.168.10.1/24", "interface": "ether1"},
        {"address": "10.99.99.1/24", "interface": "ether3"},
    ],
    "ip/route": [],
    "ip/firewall/filter": [],
    "ip/firewall/address-list": [],
    "ip/service": [
        {"name": "telnet", "disabled": "false"},
        {"name": "ftp", "disabled": "true"},
        {"name": "www", "disabled": "false"},
        {"name": "ssh", "disabled": "false"},
        {"name": "www-ssl", "disabled": "false"},
    ],
    "user": [{"name": "admin", "group": "full"}, {"name": "api-user", "group": "full"}],
}


class Lab:
    def __init__(self, user, password, ubus_password):
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.auth = f"Basic {token}"
        self.ubus_password = ubus_password
        self.session_token = "a" * 32
        self.lock = threading.Lock()
        self.counter = 0
        self.rest = {path: [self.with_id(i) for i in items] for path, items in SEED.items()}
        self.interfaces = {"GigabitEthernet1": True, "GigabitEthernet2": False}
        self.lan_ip = "192.168.1.1"
        self.pending_ip = None

    def with_id(self, item):
        self.counter += 1
        return {".id": f"*{self.counter}", **item}


def make_handler(lab):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body=None, content_type="application/json"):
            data = b"" if body is None else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def body(self):
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length)) if length else {}

        def route(self, method):
            path = self.path.split("?")[0].strip("/")
            if path == "ubus" and method == "POST":
                return self.ubus()
            if self.headers.get("Authorization") != lab.auth:
                return self.send(401, {"error": 401, "message": "Unauthorized"})
            if path.startswith("rest/"):
                return self.rest(method, path[len("rest/"):])
            if path.startswith("restconf/data/"):
                return self.restconf(method, path[len("restconf/data/"):])
            self.send(404, {"error": 404, "message": "Not Found"})

        def rest(self, method, path):
            parts = path.split("/")
            item_id = parts.pop() if parts[-1].startswith("*") else None
            resource = "/".join(parts)
            if resource not in lab.rest:
                return self.send(404, {"error": 404, "message": "no such resource"})
            with lab.lock:
                items = lab.rest[resource]
                found = next((i for i in items if i[".id"] == item_id), None)
                if item_id and found is None:
                    return self.send(404, {"error": 404, "message": "no such item"})
                if method == "GET":
                    return self.send(200, found if item_id else items)
                if method in ("POST", "PUT") and not item_id:
                    payload = self.body()
                    if not payload:
                        return self.send(400, {"error": 400, "message": "empty payload"})
                    item = lab.with_id(payload)
                    items.append(item)
                    return self.send(201, item)
                if method == "PATCH" and item_id:
                    found.update(self.body())
                    return self.send(200, found)
                if method == "DELETE" and item_id:
                    items.remove(found)
                    return self.send(204)
            self.send(405, {"error": 405, "message": "Method Not Allowed"})

        def restconf(self, method, path):
            kind = "application/yang-data+json"
            if path == "ietf-interfaces:interfaces" and method == "GET":
                listing = [{"name": n, "enabled": e} for n, e in lab.interfaces.items()]
                return self.send(200, {"ietf-interfaces:interfaces": {"interface": listing}}, kind)
            prefix = "ietf-interfaces:interfaces/interface="
            if path.startswith(prefix):
                name = path[len(prefix):]
                if name not in lab.interfaces:
                    return self.send(404, {"errors": "invalid-value"}, kind)
                if method == "GET":
                    reply = {"ietf-interfaces:interface": {"name": name, "enabled": lab.interfaces[name]}}
                    return self.send(200, reply, kind)
                if method == "PATCH":
                    lab.interfaces[name] = self.body()["ietf-interfaces:interface"]["enabled"]
                    return self.send(204)
            self.send(404, {"errors": "invalid-value"}, kind)

        def ubus(self):
            request = self.body()
            session, obj, method, args = request["params"]

            def reply(result):
                self.send(200, {"jsonrpc": "2.0", "id": request.get("id"), "result": result})

            if (obj, method) == ("session", "login"):
                if args.get("username") == "root" and args.get("password") == lab.ubus_password:
                    return reply([0, {"ubus_rpc_session": lab.session_token}])
                return reply([6])
            if session != lab.session_token:
                return reply([6])
            if (obj, method) == ("network.interface", "dump"):
                lan = {
                    "interface": "lan",
                    "up": True,
                    "ipv4-address": [{"address": lab.lan_ip, "mask": 24}],
                    "statistics": {"rx_bytes": 1024, "tx_bytes": 2048},
                }
                return reply([0, {"interface": [lan]}])
            if (obj, method) == ("uci", "set"):
                lab.pending_ip = args["values"]["ipaddr"]
                return reply([0, {}])
            if (obj, method) == ("uci", "commit"):
                lab.lan_ip = lab.pending_ip or lab.lan_ip
                return reply([0, {}])
            reply([4])

        def do_GET(self):
            self.route("GET")

        def do_POST(self):
            self.route("POST")

        def do_PUT(self):
            self.route("PUT")

        def do_PATCH(self):
            self.route("PATCH")

        def do_DELETE(self):
            self.route("DELETE")

    return Handler


def start(port=0, user="api-user", password="lab-pass", ubus_password="openwrt"):
    lab = Lab(user, password, ubus_password)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(lab))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, lab


if __name__ == "__main__":
    ports = [int(p) for p in sys.argv[1:]] or [8080, 8081]
    for number in ports:
        start(number)
        print(f"Lab simulé sur http://127.0.0.1:{number} (api-user / lab-pass)")
    threading.Event().wait()
