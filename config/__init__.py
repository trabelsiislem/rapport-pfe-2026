import os

# Use PyMySQL as a drop-in replacement for MySQLdb when mysqlclient
# is not available (convenient for development environments).
try:
	import pymysql
	pymysql.install_as_MySQLdb()
except Exception:
	# If PyMySQL isn't installed yet, Django will raise an import error at runtime.
	# We intentionally avoid failing at import time so the developer can install
	# the package via pip when ready.
	pass
