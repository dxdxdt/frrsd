from datetime import timedelta
import fcntl
import os
import sys
from time import sleep
import traceback

import psycopg2

from frrsd import do_dump, do_tcping, do_trunc

db_opts = {
	'user': 'frrsd',
	'database': 'frrsd'
}

def do_interation ():
	with psycopg2.connect(**db_opts) as db:
		rows = do_dump(db)

		latest = None
		for _, ts in rows:
			if latest is None or latest < ts:
				latest = ts

		if latest is not None:
			bfr = latest - timedelta(days = 30) # watch out for underflow!
			if False: # FIXME debug code
				sys.stderr.write('''trunc before: ''' + bfr.isoformat() + os.linesep)
			do_trunc(db, bfr)

		try:
			do_tcping(db, '1.1.1.1', 443, 4, 10.0)
		except Exception as e:
			traceback.print_exception(e)

		db.commit()

with open('/run/frrsd.pid') as f:
	fcntl.flock(f.fileno(), fcntl.LOCK_EX)

	if True:
		while True:
			do_interation()
			sleep(60)
	else:
		# FIXME test code
		for _ in range(43200): # a month's worth of data
			do_interation()
