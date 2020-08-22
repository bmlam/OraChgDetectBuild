import inspect, os.path, sys, time  

g_dbxActive = True 
g_dbxCnt = 0
g_maxDbxMsg = 999

g_modLineOccur = {}
g_modLineKeepalive = {}
g_modPathCommonPrefix = "/"

def _dbx ( text , maxPrint= 9 ):
	global g_dbxCnt , g_dbxActive
	if g_dbxActive :
		modLine = inspect.stack()[1][1] + ':' + str( inspect.stack()[1][2] )
		if modLine in g_modLineOccur.keys():
			g_modLineOccur[ modLine ] += 1 
		else:
			g_modLineOccur[ modLine ] = 1
			g_modLineKeepalive[ modLine ] = maxPrint		
		if g_modLineOccur[ modLine ] < maxPrint :
			print( 'dbx: %s:%s - Ln%d: %s' % ( inspect.stack()[1][1], inspect.stack()[1][3], inspect.stack()[1][2], text ) )
		if g_modLineOccur[ modLine ] == g_modLineKeepalive[ modLine ]  : # adaptive keepalive threshold reached
			print( 'dbx KEEPALIVE %d: %s:%s - Ln%d: %s' % ( g_modLineOccur[ modLine ], inspect.stack()[1][1], inspect.stack()[1][3], inspect.stack()[1][2], text ) )
			g_modLineKeepalive[ modLine ] *= 2
		g_dbxCnt += 1
		if g_dbxCnt > g_maxDbxMsg:
			_errorExit( "g_maxDbxMsg of %d exceeded" % g_maxDbxMsg )

def _infoTs ( text , withTs = False ):
	global g_modPathCommonPrefix
	modPathFull = inspect.stack()[1][1] 
	modPathRel = os.path.relpath( modPathFull, g_modPathCommonPrefix )
	if withTs :
		print( '%s (Ln%d) %s' % ( time.strftime("%H:%M:%S"), inspect.stack()[1][2], text ) )
	else :
		print( '(%s:%d) %s' % ( modPathRel, inspect.stack()[1][2], text ) )

def _errorExit ( text ):
	print( 'ERROR raised from %s - Ln%d: %s' % ( inspect.stack()[1][3], inspect.stack()[1][2], text ) )
	sys.exit(1)

def setDebug( flag):
	global g_dbxActive
	g_dbxActive = flag

def setModPathCommonPrexit( prefix ):
	global g_modPathCommonPrefix
	g_modPathCommonPrefix = prefix 
