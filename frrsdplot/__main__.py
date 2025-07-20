import psycopg2

from frrsdplot import do_fetch, do_fetch_ping, do_plot


ssh_opts = {}

db_opts = {
	'user': 'frrsd',
	'database': 'frrsd'
}

with psycopg2.connect(**db_opts) as db:
	data = do_fetch(db)
	ping_data = do_fetch_ping(db)
	do_plot(data, ping_data)
