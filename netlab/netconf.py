import xml.etree.ElementTree as ET

NS = "urn:ietf:params:xml:ns:netconf:base:1.0"
IF_NS = "urn:ietf:params:xml:ns:yang:ietf-interfaces"


def rpc(body, message_id):
    return f'<rpc xmlns="{NS}" message-id="{message_id}">{body}</rpc>'


def get_config(source="running"):
    return rpc(f"<get-config><source><{source}/></source></get-config>", 1)


def edit_config(name, enabled, target="candidate"):
    config = (
        f'<interfaces xmlns="{IF_NS}"><interface><name>{name}</name>'
        f"<enabled>{str(enabled).lower()}</enabled></interface></interfaces>"
    )
    return rpc(f"<edit-config><target><{target}/></target><config>{config}</config></edit-config>", 2)


def commit():
    return rpc("<commit/>", 3)


def lock(target="candidate"):
    return rpc(f"<lock><target><{target}/></target></lock>", 4)


def parse_interfaces(xml):
    root = ET.fromstring(xml)
    result = {}
    for item in root.iter(f"{{{IF_NS}}}interface"):
        name = item.find(f"{{{IF_NS}}}name").text
        result[name] = item.find(f"{{{IF_NS}}}enabled").text == "true"
    return result


class Datastores:
    def __init__(self, interfaces):
        self.running = dict(interfaces)
        self.candidate = dict(interfaces)
        self.locked_by = None

    def check(self, who):
        if self.locked_by not in (None, who):
            raise RuntimeError(f"datastore verrouillé par {self.locked_by}")

    def lock(self, who):
        self.check(who)
        self.locked_by = who

    def unlock(self, who):
        self.check(who)
        self.locked_by = None

    def edit_config(self, who, name, enabled):
        self.check(who)
        self.candidate[name] = enabled

    def commit(self, who):
        self.check(who)
        self.running = dict(self.candidate)


def demo():
    stores = Datastores({"GigabitEthernet1": True, "GigabitEthernet2": False})
    stores.lock("alice")
    stores.edit_config("alice", "GigabitEthernet2", True)
    rows = [
        ("lock (alice)", "candidate verrouillé"),
        ("edit-config", f"candidate = {stores.candidate['GigabitEthernet2']}, running = {stores.running['GigabitEthernet2']}"),
    ]
    try:
        stores.edit_config("bob", "GigabitEthernet1", False)
    except RuntimeError as error:
        rows.append(("edit-config (bob)", f"refusé : {error}"))
    stores.commit("alice")
    stores.unlock("alice")
    rows.append(("commit + unlock", f"running = {stores.running['GigabitEthernet2']}"))
    return rows
