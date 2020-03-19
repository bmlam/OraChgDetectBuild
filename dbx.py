import inspect, sys, time 

g_dbxActive = True
g_dbxCnt = 0
g_maxDbxMsg = 999
g_seq = 0
 
foo = "got here"
def _dbx ( text ):
    global g_dbxCnt , g_dbxActive

    # print( inspect.stack() ); return 

    if g_dbxActive :
        print( 'dbx%d: %s - Ln%d: %s' % ( g_dbxCnt, inspect.stack()[1][3], inspect.stack()[1][2], text ) )
        g_dbxCnt += 1
        if g_dbxCnt > g_maxDbxMsg:
            _errorExit( "g_maxDbxMsg of %d exceeded" % g_maxDbxMsg )
 
def _infoTs ( text , withTs = False, isWarning = False ):
    if withTs :
        print( '%s: %s(Ln%d) %s' % ( "WARNING" if isWarning else "INFO", time.strftime("%H:%M:%S"), inspect.stack()[1][2], text ) )
    else :
        print( '%s(Ln%d): %s' % ( "WARNING" if isWarning else "INFO", inspect.stack()[1][2], text ) )
 
def _errorExit ( text ):
    print( 'ERROR raised from %s - Ln%d: %s' % ( inspect.stack()[1][3], inspect.stack()[1][2], text ) )
    sys.exit(1)

def setDebug( flag ):
  global g_dbxActive
  g_dbxActive = flag 