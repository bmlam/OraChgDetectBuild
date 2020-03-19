#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3
"""
  Copy DDL files extracted in given location to a folder for diff. 
  In a feature version, we want to extract the script directly

call example:
  ./quickDiff.py -e uat2,prod -e prod -o process.sk_process_control.pks,licensing.sk_preclaim.pkb

Example for connectQuad: 10.10.8.188:1521:pdbliongd1:lionrep
"""
import argparse, enum, json, os, re, subprocess, sys, shutil, tempfile

## my modules 
from dbx import _dbx, _infoTs, _errorExit, setDebug
from textFileUtils import genUnixDiff, persistAndPrintName
import charCounter, plstopa, fsm, oraUtils 


g_mapDbNameOfEnvCode = { "gd1" : "PDBLIONGD1"
, "gt2" : "PDBLIONGT2"
, "uat1" : "LIONPREP"
, "uat2" : "LIONUAT"
, "prod" : "LIONP01"
, "s1" : "PDBLIONGD_S1"
, "s2" : "PDBLIONGD_S2"
, "s3" : "PDBLIONGD_S3"
, "s4" : "PDBLIONGD_S4"
}



g_baseOfDDLScripts = "c:\\temp"
g_diffLocation = "c:\\temp/for-diff"


def parseCmdLine() :
  import argparse

  parser = argparse.ArgumentParser()
  # lowercase shortkeys
  parser.add_argument( '-a', '--action', choices= ['dbs', 'extract', 'grepInst', 'os', 'testJson' ], help=
  """dbs: input are from databases, grepInst: extract install objects from install scripts , os: input is file path 
  """
, required= True )
  parser.add_argument( '-b', '--baseLocation', help='base location of input files' )
  # parser.add_argument( '-c', '--connectQuad', help='Oracle connect 4-tuple h:p:s:u to the database to extract scripts from' )
  parser.add_argument( '-e', '--environments' , help='comma separated list of environment codes, e.g prod, uat2, gt2', required= False )
  parser.add_argument( '-i', '--inputFilePath' , help='path to input file', required= False )
  parser.add_argument( '-I', '--inputRelPaths' , help='comma separated input file paths', required= False )
  parser.add_argument( '-j', '--jsonCfgFile' , help='json file containing various input data', required= False )
  parser.add_argument( '-o', '--objects' , help='comma separated list of objects, e.g: process.sk_process_control.pks', required= False )
  parser.add_argument( '--debug', help='print debugging messages', required= False, action='store_true' )
  parser.add_argument( '--no-debug', help='do not print debugging messages', dest='debug', action='store_false'  )

  result= parser.parse_args()


  if result.action == 'dbs':
    if result.environments == None or result.objects == None: 
      _errorExit( "Action '%s' requires both env codes ans object list" % (result.action ) ) 
  elif result.action == 'grepInst':
    if result.baseLocation == None or result.inputRelPaths == None: 
      _errorExit( f"Action {result.action} require baseLocation and inputRelPaths" ) 
  elif result.action == 'extract':
    #if result.connectQuad == None or result.objects == None:  _errorExit( "Action '%s' require connectQuad and objects" % (result.action ) ) 
    if result.environments == None or result.objects == None: 
      _errorExit( "Action '%s' requires both env codes ans object list" % (result.action ) ) 
  elif result.action == 'os':
    if result.inputFilePath == None : 
      _errorExit( "Action '%s' require inputFilePath" % (result.action ) ) 
  elif result.action == 'testJson':
    if result.jsonCfgFile == None : 
      _errorExit( "Action '%s' require jsonCfgFile" % (result.action ) ) 

  return result

def getEnvList( csv):
  """ convert CSV string in expected format to list of environment code
  ensuring that the code is valid
  """
  retVal = []
  for ix, envCode in enumerate( objectCsv.split( "," ) ):
    _dbx( "%d. env %s " % ( ix, envCode ) )
    if envCode not in  g_mapDbNameOfEnvCode.keys():
      _errorExit( "envCode %s is not mapped!" % (envCode) ) 

    retVal.append( envCode )

  return retVal

def getObjectList( objectCsv):
  """ convert CSV string in expected format to list of DBObject instances 
  """
  retVal = []
  for ix, obj in enumerate( objectCsv.split( "," ) ):
    _dbx( "%d. obj %s " % ( ix, obj ) )
    tokens = obj.split( "." )
    if len( tokens ) != 3: 
      _errorExit( "object %s does not conform to expected format of schema.name.type_code" % (obj) )
    (owner, name, typeCode ) = tokens[:]
    _dbx( "owner %s typ %s" % ( obj, typeCode ) )
    typeOfficial = oraUtils.g_mapFileExtDbmsMetaDataTypeToad[ typeCode ]
    _dbx( "typeOfficial %s" % ( typeOfficial ) )

    retVal.append( oraUtils.DBObject(name=name, owner=owner, type=typeOfficial, fileExt= typeCode ) )

  return retVal

def getDdlScriptPath( dbName, object ): # fixme: consider using os.path.join or os.path.sep 
  """ compose full path name of DDL script. example: 
    "/C/temp/LIONP01/SK_INVOICE_LSI-LIONP01.pkb"
  """
  retVal = "%s\\%s\\%s-%s.%s" % ( g_baseOfDDLScripts, dbName, object.name.upper(), dbName, object.fileExt )
  _dbx( "retVal: %s" % retVal )

  return retVal 


def uglyFormat( inputFilePath ):
  """ Read in lines of the input SQL file, format it with the simple/ugly formatter,
  * does some QA
  * dump the format result into a tempfile 
  * return the temppath 
  """
  inputLines = open(inputFilePath, "r").readlines()
  _dbx( "read %d lines from %s" % (len( inputLines ), inputFilePath ) ) 
  tree = fsm.plsqlTokenize( inputLines )
  formattedLines = tree.simpleFormatSemicolonAware()
  
  if True or "want to" == "QA":
    textWordCounter_a = charCounter.WordCounter( name="sql input" , lines= inputLines, shortCode= "sqlInput" )
    textWordCounter_a.scan()
    wordCountResultLines_a = textWordCounter_a.report( printToStdout= False )
    forWordCountCheck_a = tempfile.mktemp()
    _dbx ( "forWordCountCheck_a: %s" % (forWordCountCheck_a ))
    open( forWordCountCheck_a, "w").write( "\n".join( wordCountResultLines_a ) )

    textWordCounter_b = charCounter.WordCounter( name="formatted result" , lines= formattedLines, shortCode= "sqlFormatted" )
    textWordCounter_b.scan()
    wordCountResultLines_b = textWordCounter_b.report( printToStdout= False )
    forWordCountCheck_b = tempfile.mktemp()
    _dbx ( "forWordCountCheck_b: %s" % (forWordCountCheck_b ))
    open( forWordCountCheck_b, "w").write( "\n".join( wordCountResultLines_b ) )

    if "want see result of wordCount diff " == "which is barely usseful":
      _infoTs( " ************ DIFFing WordCounts ... ")
      diffWordCountResult = genUnixDiff( forWordCountCheck_a, forWordCountCheck_b)

      diffLinesToShow = 10 
      _infoTs( " ************ result of DIFFing WORD Counts, first %d lines only " % diffLinesToShow)
      print( "\n".join( diffWordCountResult.split( "\n") [0: diffLinesToShow ] ) )

  inputFileBaseName = os.path.basename( inputFilePath )
  outPath= persistAndPrintName( textName= "formatted %s" % inputFilePath, textContent= formattedLines, baseNamePrefix= inputFileBaseName + '-' )
    
  return outPath

def CopyFilesForObjectListForEnv( envCode, objectList ):
  dbName = g_mapDbNameOfEnvCode[ envCode ]
  _dbx( "db %s" % ( dbName ) ) 
  
  
  for obj in objectList: 
    scriptPath = getDdlScriptPath( object= obj, dbName= dbName )
    if not os.path.exists( scriptPath ):
      _infoTs( "File %s does not seem to exist!" % ( scriptPath ) ) 
    else:
      formattedOutPath = uglyFormat( inputFilePath = scriptPath )
      shutil.copy( formattedOutPath, g_diffLocation  )
      _infoTs( "File %s copied to target" % ( formattedOutPath ) ) 



#### 
def action_extractScripts( objCsv, envCsv, executeScript= True, connData= None ):
  """
    extract scripts into the expected local directory 
  """
  envs = envCsv.split( "," )

  connObjects = oraUtils.loadOraConnectionData()
  for envCode in envs: 
    conn = oraUtils.getConnectionByNickname( nickname= envCode, nicknamedConns= connObjects ) 

    if conn == None:
      raise ValueError( "env %s is not found in configuration!" % envCode )

    objectList = getObjectList( objCsv )
    

    sqlplusScriptPath =  oraUtils.spoolScriptWithSqlplusTempClob ( dbObjects = objectList, conn = conn, spoolDestRoot= "C:\\temp\\" , dirSep="\\" )
    
    if executeScript:
      # dummyInput = input( "Hit ENTER to run SQPLUS script" )
      _infoTs( "Running sqlplus script %s..." % (sqlplusScriptPath), True )
      subprocess.call( f"sqlplus /nolog @{sqlplusScriptPath}" )
      _infoTs( "Executed sqlplus script.", True )
  
def action_dbs ( envCsv, objCsv ):
  """ Extract DDL script for objects given by cmdArgs
  """
  objectList = getObjectList( objCsv )
  envList = envCsv.split( "," )
  
  action_extractScripts( objCsv = objCsv, envCsv= envCsv ) 

  for env in envList:
    CopyFilesForObjectListForEnv( envCode= env, objectList= objectList )
  
def action_grepInst ( baseLocation, inputRelPaths ):
  objectScripts = []
  _dbx( baseLocation )
  for relPath in inputRelPaths.split(","):
    # relPath = relPath.replace( "/", "\\" )
    dir_name, file_name = os.path.split( relPath )
    schema = dir_name 
    #_dbx( f"dir {dir_name} file {file_name}" )
    fullPath = os.path.join( baseLocation , dir_name, file_name )
    _infoTs( f"grep'ing {fullPath}.." )
    for line in open( fullPath, 'r').readlines():
      match = re.search( "^(STA|STAR|START|@@)\s*(.*)$" , line.lstrip().upper() )
      if match != None:
        # _dbx( f"{len( match.groups() )}" )
        objScript = match.group(2)
        if not objScript.startswith( "DML\\"):
          #_dbx( f"objScript: {objScript}" )
          objectScripts.append( os.path.join ( schema , objScript ) )
  if len( objectScripts ) > 0:
    _infoTs( "Following object scripts have been identified: \n%s" % "\n".join ( objectScripts ) ) 
  else: 
    _infoTs( "No object scripts have been identified!" ) 

def action_os ( inputFilePath):
    if not os.path.exists( inputFilePath ):
      _infoTs( "File %s does not seem to exist!" % ( inputFilePath ) ) 
    else:
      formattedOutPath = uglyFormat( inputFilePath = inputFilePath )
      shutil.copy( formattedOutPath, g_diffLocation  )
      _infoTs( "File %s copied to target" % ( formattedOutPath ) ) 

def action_testJson ( inputFilePath):
    if not os.path.exists( inputFilePath ):
      _errorExit( "File %s does not seem to exist!" % ( inputFilePath ) ) 

    jStr =  open( inputFilePath, "r").read()
    jData = json.loads( jStr )
    connDataList = jData[ "connectData" ]
    print( connDataList )


def main():
  argParserResult = parseCmdLine()

  setDebug( argParserResult.debug ) 
  if argParserResult.action == 'dbs':
    action_dbs( envCsv= argParserResult.environments, objCsv = argParserResult.objects )
  elif argParserResult.action == 'extract':
    action_extractScripts( objCsv= argParserResult.objects, envCsv = argParserResult.environments )
  elif argParserResult.action == 'grepInst':
    action_grepInst( baseLocation= argParserResult.baseLocation, inputRelPaths = argParserResult.inputRelPaths )
  elif argParserResult.action == 'os':
    action_os( inputFilePath = argParserResult.inputFilePath )
  elif argParserResult.action == 'testJson':
    action_testJson( inputFilePath = argParserResult.jsonCfgFile )

if __name__ == "__main__" : 
  main()