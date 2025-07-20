import datetime
import socket
from subprocess import Popen
import subprocess
import time
from typing import Any
import pyjson5


def get_json () -> dict[str, Any]:
	with Popen(
			[ 'vtysh', '-uc', 'show bgp summary json' ],
			stdin = subprocess.DEVNULL,
			stdout = subprocess.PIPE) as p:
		return pyjson5.load(p.stdout)

def do_insert_unicast (db, obj: dict[str, Any], ipv: str) -> tuple[int, datetime.datetime]:
	with db.cursor() as c:
		c.execute(
				'''INSERT INTO "bgp-unicast" (
					"ipv",
					"routerId",
					"as",
					"vrfId",
					"vrfName",
					"tableVersion",
					"ribCount",
					"ribMemory",
					"peerCount",
					"peerMemory",
					"peerGroupCount",
					"peerGroupMemory",
					"failedPeers",
					"displayedPeers",
					"totalPeers",
					"dynamicPeers"
				)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
				RETURNING rid, ts''',
				(
					ipv,
					obj.get('routerId'),
					obj.get('as'),
					obj.get('vrfId'),
					obj.get('vrfName'),
					obj.get('tableVersion'),
					obj.get('ribCount'),
					obj.get('ribMemory'),
					obj.get('peerCount'),
					obj.get('peerMemory'),
					obj.get('peerGroupCount'),
					obj.get('peerGroupMemory'),
					obj.get('failedPeers'),
					obj.get('displayedPeers'),
					obj.get('totalPeers'),
					obj.get('dynamicPeers')
				)
			)
		ret = c.fetchone()

		return (ret[0], ret[1])

def do_insert_peer (
		db,
		parent: int,
		peer: str,
		obj: dict[str, Any]):
	with db.cursor() as c:
		c.execute(
			'''INSERT INTO "bgp-peers" (
				"parent",
				"peer",
				"softwareVersion",
				"remoteAs",
				"localAs",
				"version",
				"msgRcvd",
				"msgSent",
				"tableVersion",
				"outq",
				"inq",
				"peerUptime",
				"peerUptimeMsec",
				"peerUptimeEstablishedEpoch",
				"pfxRcd",
				"pfxSnt",
				"state",
				"peerState",
				"connectionsEstablished",
				"connectionsDropped",
				"idType"
			)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
			(
				parent,
				peer,
				obj.get("softwareVersion"),
				obj.get("remoteAs"),
				obj.get("localAs"),
				obj.get("version"),
				obj.get("msgRcvd"),
				obj.get("msgSent"),
				obj.get("tableVersion"),
				obj.get("outq"),
				obj.get("inq"),
				obj.get("peerUptime"),
				obj.get("peerUptimeMsec"),
				obj.get("peerUptimeEstablishedEpoch"),
				obj.get("pfxRcd"),
				obj.get("pfxSnt"),
				obj.get("state"),
				obj.get("peerState"),
				obj.get("connectionsEstablished"),
				obj.get("connectionsDropped"),
				obj.get("idType")
			)
		)

def do_dump (db) -> list[tuple[int, datetime.datetime]]:
	ret = list[tuple[int, datetime.datetime]]()
	vty_output = get_json()

	v6u = vty_output.get('ipv6Unicast')
	if v6u:
		parent, ts = do_insert_unicast(db, v6u, '6')
		ret.append((parent, ts))

		for k, v in v6u.get('peers', {}).items():
			do_insert_peer(db, parent, k, v)

	return ret

def do_trunc (db, bfr: datetime.datetime):
	with db.cursor() as c:
		c.execute('''DELETE FROM "bgp-unicast" WHERE "ts" < %s''', (bfr,))
		c.execute('''DELETE FROM "ping" WHERE "ts" < %s''', (bfr,))

def do_tcping_inner (dst: str, port: int, timeo: float) -> tuple[str, int, int, float]:
	for res in socket.getaddrinfo(dst, port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0):
		af, socktype, proto, canonname, sa = res
		s = socket.socket(af, socktype)
		s.settimeout(timeo)

		c_start = time.monotonic_ns()
		s.connect(sa)
		sport = int(s.getsockname()[1])
		s.close()
		c_end = time.monotonic_ns()

		return (sa[0], sport, port, float(c_end - c_start) / 1000000000.0)

def insert_tcping_result (
		db,
		res: list[tuple[str, int, int, float]],
		l3proto: int,
		ts: datetime.datetime):
	with db.cursor() as c:
		for dst, a, b, dt in res:
			c.execute(
					'''INSERT INTO "ping" (
						"l3dst",
						"l3proto",
						"l4id_a",
						"l4id_b",
						"dt",
						"ts"
					) VALUES (%s, %s, %s, %s, %s, %s)''',
					(dst, l3proto, a, b, dt, ts))

def do_tcping (db, dst: str, port: int, cnt: int, timeo: float) -> list[float]:
	ret = list[tuple[str, int, int, float]]()
	ts = datetime.datetime.now(datetime.UTC)
	c_start = time.monotonic_ns()
	c_end = c_start + int(timeo * 1000000000.0)

	for _ in range(cnt):
		tpl = do_tcping_inner(dst, port, timeo)
		ret.append(tpl)

		c_now = time.monotonic_ns()
		if not (c_start <= c_now and c_now < c_end):
			break

	insert_tcping_result(db, ret, socket.IPPROTO_TCP, ts)

	return ret
