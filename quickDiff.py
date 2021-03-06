#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3
"""
  Copy DDL files extracted in given location to a folder for diff. 
  In a feature version, we want to extract the script directly

call example:
  ./quickDiff.py -e uat2,prod -e prod -o process.sk_process_control.pks,licensing.sk_preclaim.pkb

Example for connectQuad: 10.10.8.188:1521:pdbliongd1:lionrep
"""
import argparse, difflib, enum, json, os, re, subprocess, sys, shutil, tempfile, time 

## my modules 
from dbx import _dbx, _infoTs, _errorExit, setDebug
from textFileUtils import genUnixDiff, persistAndPrintName, getGitCurrBranchName
import charCounter, plstopa, fsm, oraUtils 

g_defaultBranchName = "branch_xyz"

g_mapDbNameOfEnvCode = { "gd1" : "PDBLIONGD1"
, "sit" : "PDBLIONSIT"
, "uat" : "LIONUAT"
, "prod" : "LIONP01"
, "s1" : "PDBLIONGD_S1"
, "s2" : "PDBLIONGD_S2"
, "s3" : "PDBLIONGD_S3"
, "s4" : "PDBLIONGD_S4"
}



g_baseOfDDLScripts = "c:\\temp"
g_diffLocation = "c:\\temp\\for-diff"


def parseCmdLine() :
  import argparse

  parser = argparse.ArgumentParser()
  # lowercase shortkeys
  parser.add_argument( '-a', '--action', choices= ['dbs', 'extract',  'os', 'twoRepos', 'devTest' ], help=
  """dbs: input are from databases, os: input is comma separated file paths 
  twoRepos: provide the root location of 2 git repos on the local PC. This program will cd to the root location and extract the branch name. Input file paths are extracted from --inputPathsFromJsonFile, attribute inputFilePaths
  """
, required= True )
  parser.add_argument( '-b', '--baseLocation', help='base location of input files' )
  parser.add_argument( '-e', '--environments' , help='comma separated list of environment codes, e.g prod, uat2, gt2', required= False )
  parser.add_argument( '-f', '--featureName', help='branch or feature name, will be used to qualify the file name'   )  
  parser.add_argument( '-I', '--inputFilePaths' , help='comma separated input file paths', required= False )
  parser.add_argument( '-j', '--inputPathsFromJsonFile' , help='json file containing various input data', default=".\\scripts_for_quickDiff.json" )
  parser.add_argument( '-o', '--objects' , help='comma separated list of objects, e.g: process.sk_process_control.pks', required= False )
  parser.add_argument( '--debug', help='print debugging messages', required= False, action='store_true' )
  parser.add_argument( '--no-debug', help='do not print debugging messages', dest='debug', action='store_false'  )

  result= parser.parse_args()

  if result.featureName == None:
    result.featureName = getGitCurrBranchName()
    if result.featureName == None:
      result.featureName = g_defaultBranchName

  if result.action == 'dbs':
    if result.environments == None or result.objects == None: 
      _errorExit( "Action '%s' requires both env codes ans object list" % (result.action ) ) 
  elif result.action == 'extract':
    #if result.connectQuad == None or result.objects == None:  _errorExit( "Action '%s' require connectQuad and objects" % (result.action ) ) 
    if result.environments == None or result.objects == None: 
      _errorExit( "Action '%s' requires both env codes ans object list" % (result.action ) ) 
  elif result.action == 'os':
    if result.inputFilePaths == None and result.inputPathsFromJsonFile == None : 
      _errorExit( "Action '%s' require inputFilePaths or inputPathsFromJsonFile" % (result.action ) ) 
  elif result.action == 'devTest':
    if result.inputPathsFromJsonFile == None : 
      _errorExit( "Action '%s' require inputPathsFromJsonFile" % (result.action ) ) 

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

def CopyFilesForObjectListForEnv( envCode, objectList, staleMinutesOk= 20 ):
  dbName = g_mapDbNameOfEnvCode[ envCode ]
  _dbx( "db %s" % ( dbName ) ) 
  now = time.time() # returns seconds since epoch

  originFilePathsInDiffArea = []
  formattedFilePaths = []

  for obj in objectList: 
    orginScriptPath = getDdlScriptPath( object= obj, dbName= dbName )
    fileModTime = os.path.getmtime( orginScriptPath )
    _dbx( "now: %s mtime: %s" % ( now, fileModTime ) )
    elaMinutues = (now - fileModTime) / 60 
    _dbx( "elaMinutues %s" % elaMinutues )
    if elaMinutues > staleMinutesOk :
      raise ValueError( "file %s is %s minutes old!" % ( orginScriptPath, elaMinutues ) )
    if not os.path.exists( orginScriptPath ):
      _infoTs( "File %s does not seem to exist!" % ( orginScriptPath ) ) 
    else:
      prefix, fileExt = os.path.splitext( os.path.basename( orginScriptPath ) )

      # lets also copy the original but leave a copy for users convenience 
      newBaseName = prefix + '-orgF' + fileExt
      newPathOfOriginFile = os.path.join( g_diffLocation, newBaseName )      
      shutil.copy( orginScriptPath, newPathOfOriginFile  ) 
      _dbx( "newPathOfOriginFile %s" % ( newPathOfOriginFile ) ) 
      originFilePathsInDiffArea.append( newPathOfOriginFile )

      # create formatted copy and MOVE it to diff area 
      formattedOutPath = uglyFormat( inputFilePath = orginScriptPath )

      newBaseName = prefix + '-ugly' + fileExt
      newPathOfFormattedFile = os.path.join( g_diffLocation, newBaseName  )      

      shutil.move( formattedOutPath, newPathOfFormattedFile  )
      _infoTs( "Formatted file to be found as %s " % ( newPathOfFormattedFile ) ) 
      formattedFilePaths.append( newPathOfFormattedFile ) 

  # _errorExit( "originFilePathsInDiffArea len %s, formattedFilePaths len %s" % ( len( originFilePathsInDiffArea), len( formattedFilePaths) ) )

  return originFilePathsInDiffArea , formattedFilePaths

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
    
    _infoTs( "fixme: make extraction of script optional!" )
    sqlplusScriptPath =  oraUtils.spoolScriptWithSqlplusTempClob ( dbObjects = objectList, conn = conn, spoolDestRoot= "C:\\temp\\" , dirSep="\\", envCode=envCode )
    
    if executeScript:
      # dummyInput = input( "Hit ENTER to run SQPLUS script" )
      _infoTs( "Running sqlplus script %s..." % (sqlplusScriptPath), True )
      subprocess.call( f"sqlplus /nolog @{sqlplusScriptPath}" )
      _infoTs( "Executed sqlplus script.", True )
  
def getDiffStatsFromContents( contentA, contentB ):
  lnCntA = len( contentA ) 
  lnCntB = len( contentB ) 
  _dbx( "lnCntA %d" % (lnCntA ) )
  diffOutput = difflib.context_diff( contentA, contentB, fromfile="fileA", tofile= "fileB", n=1 )
  newCnt = 0; delOrChgCnt = 0 
  for ln in diffOutput:
    if ln.startswith( "! "): delOrChgCnt += 1
    elif ln.startswith( "+ "): newCnt += 1
  _dbx( "B has %d new lines and %d changed or deleted lines versus B" % (newCnt, delOrChgCnt ) )
  _dbx( "newCnt: %d" % ( newCnt ) )
  _dbx( "delOrChgCnt: %d" % ( delOrChgCnt ) )
  
  maxLnCnt = lnCntA if lnCntA > lnCntB else lnCntB 
  minLnCnt = lnCntA if lnCntA < lnCntB else lnCntA  
  if maxLnCnt == 0: maxLnCnt = 1
  if minLnCnt == 0: minLnCnt = 1
  avgLnCnt = (maxLnCnt + minLnCnt) / 2 
  _dbx( "minLnCnt: %d" %( minLnCnt) )
  _dbx( "maxLnCnt: %d" %( maxLnCnt) )
  _dbx( "avgLnCnt: %d" %( avgLnCnt) )
  # diffGrade meaning:
  # 0: no delta at all
  # 1: minor changes 
  # 2: substantial changes
  if ( maxLnCnt > minLnCnt * 2 ):
    diffGrade = 2 
  elif ( avgLnCnt > (newCnt + delOrChgCnt) * 10 ):
    diffGrade = 1
  elif avgLnCnt < 100 and (newCnt + delOrChgCnt) <= 10 :
    diffGrade = 1
  elif ( (newCnt + delOrChgCnt) == 0 ):
    diffGrade = 0 
  else :
    _dbx( "default diffGrade" )
    diffGrade = 2
  _dbx( diffGrade )

  return lnCntA, lnCntB, newCnt, delOrChgCnt, diffGrade

def getDiffStatsFromFiles( fileA, fileB ):
  contentA = open(fileA.strip(), "r").readlines()
  contentB = open(fileB.strip(), "r").readlines()

  lnCntA, lnCntB, newCnt, delOrChgCnt, diffGrade = getDiffStatsFromContents( contentA= contentA, contentB= contentB )
  return lnCntA, lnCntB, newCnt, delOrChgCnt, diffGrade 

def getHtmlDiffOutput( fileA, fileB ):
  contentA = open(fileA.strip(), "r").readlines()
  contentB = open(fileB.strip(), "r").readlines()
  
  hd = difflib.HtmlDiff( tabsize=2, wrapcolumn=100 )
  output = hd.make_file(contentA, contentB, context= True \
    , fromdesc= os.path.basename(fileA), todesc= os.path.basename( fileB )
  )

  return output 
  
def action_dbs ( envCsv, objCsv ):
  """ Extract DDL script for objects given by cmdArgs
  When we compare DDLs from 2 databases, the following additional task is performed:
  1. compute the diff grade of the original DDLs
  2. If the diff grade is zero or we generate the HTML diff report using the original DDLs 
  3. If the diff grade is high, we generate the HTML diff report using the formatted DDLs 
  """
  objectList = getObjectList( objCsv )
  # _errorExit( "test exit %s" % ( len( objectList ) ) ) 
  envList = envCsv.split( "," )
  if len ( envList ) > 2:
    raise ValueError( "diff report cannot be created for more than 2 databases. Consider action extract!" )

  # regardless we if need to process 1 or 2 databases, we need to extract the scripts to the target location first 
  action_extractScripts( objCsv = objCsv, envCsv= envCsv ) 
  
  for ix, env in enumerate( envList ):
    if ix == 0:
      dbOneOriginPaths, dbOneFormattedPaths =  CopyFilesForObjectListForEnv( envCode= env, objectList= objectList, staleMinutesOk= 60 )
      _dbx( "dbOneOriginPaths len: %s" % ( len( dbOneOriginPaths ) ) )
    elif ix == 1: 
      dbTwoOriginPaths, dbTwoFormattedPaths =  CopyFilesForObjectListForEnv( envCode= env, objectList= objectList, staleMinutesOk= 60 )

  concatDiffReport = "\n"
  if len( envList ) == 2:
    # _errorExit( "getHtmlDiffOutput method coded but not yet used! " )
    for i in range( len( dbOneOriginPaths ) ):
      fileAOrigin = dbOneOriginPaths[i]
      fileBOrigin = dbTwoOriginPaths[i]
      lnCntA, lnCntB, newCnt, delOrChgCnt, diffGrade = getDiffStatsFromFiles( fileA= fileAOrigin, fileB= fileBOrigin ) 
      if diffGrade == 0 or diffGrade == 1 :
        concatDiffReport +=  getHtmlDiffOutput( fileA= fileAOrigin, fileB= fileBOrigin ) 
      else:
        fileAFormatted = dbOneFormattedPaths[i]
        fileBFormatted = dbTwoFormattedPaths[i]
        concatDiffReport +=  getHtmlDiffOutput( fileA= fileAFormatted, fileB= fileBFormatted ) 

      _dbx( len( concatDiffReport ) )

    diffRepFile = tempfile.mkstemp( suffix= "-accu-diffs.html" )[1]
    open( diffRepFile, "w" ).write(  concatDiffReport ) 
    _infoTs( "Diff report generated as %s " % ( diffRepFile ) )
  

def action_os ( inputFilePathsCsv, branchName= g_defaultBranchName, inputPathsFromJsonFile = None ):

  if inputFilePathsCsv and inputPathsFromJsonFile:
    _infoTs( "both inputFilePaths and inputPathsFromJsonFile have been provided. Will only consider inputFilePaths!" )
    inputPathsFromJsonFile = None
    inputFilePaths = inputFilePathsCsv.split(",")
  if inputPathsFromJsonFile :
    inputFilePaths = action_devTest( jsonFile = inputPathsFromJsonFile )

  # assert all input files exist 
  for inputFilePath in inputFilePaths :
    if not os.path.exists( inputFilePath ):
      raise ValueError( "File %s does not seem to exist!" % ( inputFilePath ) ) 
  # now we have asserted all input files ... 
  for inputFilePath in inputFilePaths:
      prefix, fileExt = os.path.splitext( os.path.basename( inputFilePath ) )
      newBaseName = prefix + '-' + branchName + "-orgF" + fileExt 
      tgtPathOfOrgFile = os.path.join( g_diffLocation, newBaseName )
      shutil.copy( inputFilePath, tgtPathOfOrgFile  )

      formattedOutPath = uglyFormat( inputFilePath = inputFilePath )
      newBaseName = prefix + '-' + branchName + "-ugly" + fileExt 
      tgtPathOfFormattedFile = os.path.join( g_diffLocation, newBaseName )
      shutil.move( formattedOutPath, tgtPathOfFormattedFile )
      _infoTs( "Formatted file %s moved to target" % ( tgtPathOfFormattedFile ) ) 
  if inputPathsFromJsonFile:
    _infoTs( "Only input files specified in %s were considered " % ( inputPathsFromJsonFile ) )

def action_devTest ( jsonFile ):
    if not os.path.exists( jsonFile ):
      _errorExit( "File %s does not seem to exist!" % ( jsonFile ) ) 

    jStr =  open( jsonFile, "r").read()
    jData = json.loads( jStr )
    list = jData[ "filePaths" ]
    filePaths = []
    for elem in list : # .keys():
      _dbx( filePaths ) 
      filePath= elem[ 'path' ]
      filePaths.append( filePath )
    return filePaths 

def main():
  argParserResult = parseCmdLine()

  setDebug( argParserResult.debug ) 
  if argParserResult.action == 'dbs':
    action_dbs( envCsv= argParserResult.environments, objCsv = argParserResult.objects )
  elif argParserResult.action == 'extract':
    action_extractScripts( objCsv= argParserResult.objects, envCsv = argParserResult.environments )
#  elif argParserResult.action == 'grepInst':
#    action_grepInst( baseLocation= argParserResult.baseLocation, inputFilePaths = argParserResult.inputFilePaths )
  elif argParserResult.action == 'os':
    action_os( inputFilePathsCsv = argParserResult.inputFilePaths, branchName= argParserResult.featureName
      , inputPathsFromJsonFile= argParserResult.inputPathsFromJsonFile  )
  elif argParserResult.action == 'devTest':
    action_devTest( jsonFile = argParserResult.inputPathsFromJsonFile )
  else:
  	_errorExit( "action  %s is not yet implemented" % (argParserResult.action) )

if __name__ == "__main__" : 
  main()
