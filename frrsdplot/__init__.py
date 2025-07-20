import sys
import matplotlib.pyplot as plt

def do_fetch (db) -> dict[str, list]:
	ribCount = []
	peerCount = []
	peerGroupCount = []
	failedPeers = []
	displayedPeers = []
	dynamicPeers = []
	ts = []

	ret = {
		"ribCount": ribCount,
		"peerCount": peerCount,
		"peerGroupCount": peerGroupCount,
		"failedPeers": failedPeers,
		"displayedPeers": displayedPeers,
		"dynamicPeers": dynamicPeers,
		"ts": ts
	}

	with db.cursor() as c:
		c.execute(
			'''SELECT
				"ribCount",
				"peerCount",
				"peerGroupCount",
				"failedPeers",
				"displayedPeers",
				"dynamicPeers",
				"ts"
			FROM "bgp-unicast"
			WHERE
				"ts" >= timezone('utc', now()) - make_interval(days => 1)
			ORDER BY "ts" ASC''')
		while True:
			r = c.fetchone()
			if not r: break

			ribCount.append(r[0])
			peerCount.append(r[1])
			peerGroupCount.append(r[2])
			failedPeers.append(r[3])
			displayedPeers.append(r[4])
			dynamicPeers.append(r[5])
			ts.append(r[6])

	return ret

def do_fetch_ping (db) -> dict[str, list]:
	l3dst = []
	dt = []
	ts = []

	ret = {
		"l3dst": l3dst,
		"dt": dt,
		"ts": ts
	}

	with db.cursor() as c:
		c.execute(
			'''SELECT
				"l3dst",
				"dt",
				"ts"
			FROM "ping"
			WHERE
				"ts" >= timezone('utc', now()) - make_interval(days => 1)
			ORDER BY "ts" ASC''')
		while True:
			r = c.fetchone()
			if not r: break

			l3dst.append(r[0])
			dt.append(r[1])
			ts.append(r[2])

	return ret


def do_plot (data: dict[str, list], ping_data: dict[str, list]):
	ribCount = data['ribCount']
	peerCount = data['peerCount']
	peerGroupCount = data['peerGroupCount']
	failedPeers = data['failedPeers']
	displayedPeers = data['displayedPeers']
	dynamicPeers = data['dynamicPeers']
	ts = data['ts']

	ts_start = ts[0]
	ts_end = ts[-1]

	fig, (ax_ribCount, ax_pc, ax_ping) = plt.subplots(
			3,
			1,
			sharex = True,
			constrained_layout = True,
			figsize = [ 8.0, 10.0 ])

	ax_ribCount.set_title('AS214301 Peering Health (%s - %s)' %
			(ts_start.isoformat(timespec='seconds'), ts_end.isoformat(timespec='seconds')))
	ax_ribCount.plot(ts, ribCount)
	ax_ribCount.set_ylabel('ribCount')

	ax_pc.set_title('BGP Sample count: %d' % (len(ts)))
	ax_pc.plot(ts, peerCount, label = 'peerCount')
	ax_pc.plot(ts, peerGroupCount, label = 'peerGroupCount')
	ax_pc.plot(ts, failedPeers, label = 'failedPeers')
	ax_pc.plot(ts, displayedPeers, label = 'displayedPeers')
	ax_pc.plot(ts, dynamicPeers, label = 'dynamicPeers')
	ax_pc.legend(loc = 'upper right')
	ax_pc.set_ylabel('Peer counts')

	ax_ping.set_title('PING sample count: %d' % (len(ping_data["ts"])))
	ax_ping.plot(ping_data["ts"], ping_data["dt"])
	ax_ping.set_ylabel('PING (seconds)')

	if sys.stdout.isatty():
		plt.show()
		# raise OSError("Refusing to write to terminal")
	else:
		plt.savefig('/dev/stdout', format = 'png')
