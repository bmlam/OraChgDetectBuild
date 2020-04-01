import inspect, sys, time 

g_dbxActive = True 
g_dbxCnt = 0
g_maxDbxMsg = 999

def _dbx ( text ):
	global g_dbxCnt , g_dbxActive
	if g_dbxActive :
		print( 'dbx: %s:%s - Ln%d: %s' % ( inspect.stack()[1][3], inspect.stack()[1][1], inspect.stack()[1][2], text ) )
		g_dbxCnt += 1
		if g_dbxCnt > g_maxDbxMsg:
			_errorExit( "g_maxDbxMsg of %d exceeded" % g_maxDbxMsg )

def _infoTs ( text , withTs = False, expecttAck= False, ackPrompt=None  ):
	if withTs :
		print( '%s (Ln%d) %s' % ( time.strftime("%H:%M:%S"), inspect.stack()[1][2], text ) )
	else :
		print( '(Ln%d) %s' % ( inspect.stack()[1][2], text ) )
	if expecttAck:
		dummy= raw_input( "%s: " % ackPrompt if ackPrompt else "Hit enter to proceed" )

def _errorExit ( text ):
	print( 'ERROR raised from %s:%s - Ln%d: %s' % ( inspect.stack()[1][1],inspect.stack()[1][3], inspect.stack()[1][2], text ) )
	sys.exit(1)

def setDebug( flag):
	global g_dbxActive
	g_dbxActive = flag
