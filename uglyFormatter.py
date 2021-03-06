#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3

""" 
on AirBook : 
#!/usr/bin/python3
on iMac:

on Windows:
#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3

the UglyFormatter is supposed to format PLSQL solely for the purpose of providing consistent output given tbe same input
"""


import inspect, os.path, subprocess, sys, tempfile, time 

## my modules 
import charCounter, plstopa, fsm
from dbx import _dbx, _errorExit, _infoTs
from textFileUtils import genUnixDiff, persistAndPrintName, mixedDosPathToUnix


#g_dbxActive = False 
#g_dbxCnt = 0
#g_maxDbxMsg = 999

g_inpFilePath= None
g_inpLines = ""
g_outFilePath= None

#def _dbx ( text ):
#	global g_dbxCnt , g_dbxActive
#	if g_dbxActive :
#		print( 'dbx: %s - Ln%d: %s' % ( inspect.stack()[1][3], inspect.stack()[1][2], text ) )
#		g_dbxCnt += 1
#		if g_dbxCnt > g_maxDbxMsg:
#			_errorExit( "g_maxDbxMsg of %d exceeded" % g_maxDbxMsg )

#def _infoTs ( text , withTs = False ):
#	if withTs :
#		print( '%s (Ln%d) %s' % ( time.strftime("%H:%M:%S"), inspect.stack()[1][2], text ) )
#	else :
#		print( '(Ln%d) %s' % ( inspect.stack()[1][2], text ) )

#def _errorExit ( text ):
#	print( 'ERROR raised from %s - Ln%d: %s' % ( inspect.stack()[1][3], inspect.stack()[1][2], text ) )
#	sys.exit(1)

def parseCmdLine() :
	import argparse

	global g_inpFilePath, g_outFilePath, g_inpLines, g_fsmInitStatusCode

	parser = argparse.ArgumentParser()
	# lowercase shortkeys
	parser.add_argument( '-i', '--inFile' , help='input file, could also be sent as STDIN', required= False )
	parser.add_argument( '-o', '--outFile' , help='output file', required= False )
	parser.add_argument( '-f', '--fsmStartStatus' , help='finite machine start status', required= False )

	result= parser.parse_args()

	if result.inFile != None:
		g_inpFilePath = result.inFile
		g_inpLines =  open( g_inpFilePath, "r" ).readlines()
	else: 
		g_inpLines =  sys.stdin.readlines() 
		
	_dbx( len( g_inpLines) )
	# _dbx( "\n".join( g_inpLines[:3] ) )

	if result.outFile != None:
		pass

	if result.fsmStartStatus != None:
		g_fsmInitStatusCode = result.fsmStartStatus
	else:
		g_fsmInitStatusCode = None

	return result


def main():
	global g_fsmInitStatusCode
	argParserResult = parseCmdLine()

	if True:
		tree = fsm.plsqlTokenize( g_inpLines )
		formattedLines = tree.simpleFormatSemicolonAware()
		# print( "\n".join( formattedLines ) )

	if False or "want to" == "compare output manually":
		#print( "*"*20 + "input sql" + "*"*20 )
		#print( "".join( g_inpLines))
		
		print( "*"*20 + "formatted" + "*"*20 )
		print( "\n".join( formattedLines))
		
	if "want to compare" == "char count":
		forCharCountCheck_A = tempfile.mktemp()
		_dbx ( "forCharCountCheck_A: %s" % (forCharCountCheck_A ))
		charCounter_A = charCounter.TextCharStatsIgnoreCase( textName = "sql input", txt = g_inpLines)
		charCountResultLines_A = charCounter_A.report( printToStdout= False )
		open( forCharCountCheck_A, "w").write( "\n".join( charCountResultLines_A ) )

		forCharCountCheck_B = tempfile.mktemp()
		_dbx ( "forCharCountCheck_B: %s" % (forCharCountCheck_B ))
		charCounter_B = charCounter.TextCharStatsIgnoreCase( textName = "formatted output", txt = formattedLines)
		charCountResultLines_B = charCounter_B.report( printToStdout= False )
		open( forCharCountCheck_B, "w").write( "\n".join( charCountResultLines_B ) )

		_infoTs( " ************ DIFFing CharCounts ... ")
		diffCharCountResult = genUnixDiff( forCharCountCheck_A, forCharCountCheck_B)

		_infoTs( " ************ result of DIFFing CharCounts")
		print( diffCharCountResult ) 

	if True:
		textWordCounter_a = charCounter.WordCounter( name="sql input" , lines= g_inpLines, shortCode= "sqlInput" )
		textWordCounter_a.scan()
		wordCountResultLines_a = textWordCounter_a.report( printToStdout= False )
		forWordCountCheck_a = tempfile.mktemp()
		_dbx ( "forWordCountCheck_a: %s" % (forWordCountCheck_a ))
		open( forWordCountCheck_a, "w").write( "\n".join( wordCountResultLines_a ) )

		textWordCounter_b = charCounter.WordCounter( name="sql input" , lines= formattedLines, shortCode= "sqlInput" )
		textWordCounter_b.scan()
		wordCountResultLines_b = textWordCounter_b.report( printToStdout= False )
		forWordCountCheck_b = tempfile.mktemp()
		_dbx ( "forWordCountCheck_b: %s" % (forWordCountCheck_b ))
		open( forWordCountCheck_b, "w").write( "\n".join( wordCountResultLines_b ) )

		_infoTs( " ************ DIFFing WordCounts ... ")
		diffWordCountResult = genUnixDiff( forWordCountCheck_a, forWordCountCheck_b)

		_infoTs( " ************ result of DIFFing WORD Counts")
		print( diffWordCountResult ) 

		persistAndPrintName( textName= "formatted %s" % argParserResult.inFile, textContent= formattedLines, baseNamePrefix=argParserResult.inFile+'-' )

	if "want to " == "use fsmMain":
		commentStack, signifStack = plstopa.separateCommentsFromSignficants( tree )

		#print( "*"*80 ); 		commentStack.simpleDump()
		#print( "*"*80 ); 		signifStack.simpleDump()

		signifStack.assembleComplexTokens( )
		#signifStack.simpleDump( markComplexIdents= True )

		useStatus = fsm.kickStartStatusByCode[g_fsmInitStatusCode] if g_fsmInitStatusCode != None else plstopa.FsmState.start
		parsedTree = fsm.fsmMain( signifStack, startStatus = useStatus )
		# parsedTree.simpleDump()

		# eunitedTree = plstopa.mergeTokenTrees( commentStack, parsedTree )
		reunitedTree = plstopa.mergeSignifcantAndCommentTrees( signifTree= parsedTree, commentTree= commentStack )
		_dbx( "reunitedTree len %d" % (len( reunitedTree.arr) ) )
		print( "*"*30 + "reunited " + "*"*20); 	
		#eunitedTree.simpleDump( markComplexIdents = True )
			
		# reunitedTree.finalizeStats()
		# for node in reunitedTree.arr: node.showInfo()
		print( reunitedTree.formatTokenText() )

	if False: 
		tree.assembleComplexTokens()
		# tree.simpleDump( markComplexIdents= False )
		tree.simpleDump( markComplexIdents= False )
	
main()


