#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3
""" This program takes a list of relative paths from a file tree complying to the 
ICE PLSQL repo file structure and "sorts" the files based on object type folder or file extension 
In the end the list of files are emitted with a proper start command in sorted order.

call example: 
  git log --name-only -5 | grep "/" | egrep -v "^ +" | sort | uniq | mk_install_lines.py  -t $SANDBOX/bin/install_template.sql

"""

import argparse, inspect, os, re, subprocess, sys, tempfile , zipfile 
from dbx import _dbx, _infoTs, _errorExit, setDebug

g_path_separator = "\\"
g_internalSepator = ":" 
g_excludeTouchWithExtensions = [ '.BAT', '.DOCX', '.TXT'  ]

def dosPath2Unix( inp ):
  return inp.replace( "C:" , r"/c/" ).replace( "\\", r"/" )

def parseCmdLine() :
  global g_scriptTemplatePath 
  parser = argparse.ArgumentParser()
  # lowercase shortkeys
  parser.add_argument( '-a', '--action', help='make: create the install scripts, extract: only print touched scripts, zip: files touched since baseCommit', choices=[ 'extract', 'make', 'zip' ], default="make" )
  parser.add_argument( '-b', '--baseCommit', help='baseline commit, used to determined touched scripts up to HEAD' )
  parser.add_argument( '-f', '--featureName', help='branch or feature name, will be used as part of install SQL script names', default="unknown_feature"  )
  parser.add_argument( '-l', '--lastCommit', help='last commit, used to determined touched scripts from base up to here', required= False, default= "HEAD" )
  parser.add_argument( '-t', '--sqlScriptTemplatePath', help='path of install script template', required= False )
  parser.add_argument( '--debug', help='print debugging messages', required= False, action='store_true' )
  parser.add_argument( '--no-debug', help='do not print debugging messages', dest='debug', action='store_false'  )
  parser.add_argument( '--storeRelMeta', help='store release metadata to DB', required= False, action='store_true' )
  parser.add_argument( '--no-storeRelMeta', help='do not store release metadata to DB', dest='storeRelMeta', action='store_false'  )
  # long keywords only
  # parser.add_argument( '--batch_mode', dest='batch_mode', action='store_true', help= "Run in batch mode. Interactive prompts will be suppressed" )

  result= parser.parse_args()
  if result.action == "make":
    if result.sqlScriptTemplatePath == None:
      raise ValueError( "for action %s, sqlScriptTemplatePath must be provided!" % (result.action) )
  if result.sqlScriptTemplatePath != None:
    g_scriptTemplatePath = result.sqlScriptTemplatePath 

  if result.lastCommit != None and result.lastCommit != 'HEAD':
    raise ValueError( "currently only HEAD is supported as lastCommit!" ) 
  return result

def fill_listIndexedBySchemaType( linesOfTouchedScripts ):
  global g_internalSepator, g_listIndexedBySchemaType, g_schemataFound
  # _dbx( "foo" );  return 
  _dbx( ": %d" % ( len( linesOfTouchedScripts ) ) )
  schemaScripts = {}
  for line in linesOfTouchedScripts:
    pathNodes = line.split( "/" )
    _dbx( " nodes: %d" % ( len( pathNodes ) ) )
    schema = pathNodes[0]
    if len( pathNodes ) <= 2: # skip scripts which are on top level, e.g. BASIC_DATA/master.sql 
      continue
    if schema not in schemaScripts.keys ():
      _dbx( line ); _dbx( schema )
      schemaScripts[ schema ] = []

    relPath = "/".join( pathNodes[ 1: ] ).rstrip( "\n" )

    schemaScripts[ schema ].append ( relPath ) 

  _infoTs( "Found touched scripts for schemata:\n  %s" % ( ",".join( schemaScripts.keys() ) ) )

  g_listIndexedBySchemaType = {}
  g_schemataFound = schemaScripts.keys()
  for schema in g_schemataFound: 
    
    scriptList = schemaScripts[ schema ]
    for script in scriptList:
      fileExt = os.path.splitext( script )[1]
      if fileExt.upper() not in  g_excludeTouchWithExtensions : 
        scriptType = "UnknownScriptType"
        # _dbx( " ext: %s" % (  fileExt) )
        # extract subfolder name 
        pathNodes = script.split("/")
        if len( pathNodes ) > 1 : # pattern object_type / script_file
          subFolder = pathNodes[0]
        else:
          subFolder = None 
        scriptType = "%s%s" % ( subFolder if subFolder != None else '', fileExt.upper() )
      
        schemaType = schema + g_internalSepator + scriptType
        # _dbx("dbx script %s --> schemaType %s" % (script, schemaType) ) 
        if not schemaType in g_listIndexedBySchemaType.keys():
          g_listIndexedBySchemaType[ schemaType ]= []
        _dbx( script )
        script = script.replace( '/', '\\' )
        script = "@@" + script 
        _dbx( script )
        g_listIndexedBySchemaType[ schemaType ].append ( script ) 


def createSchemataInstallScripts( sqlScriptTemplatePath, baseCommit, lastCommit, featureName= "test", storeReleaseMetadata= True ):
  """ Create SQL and BAT install scripts for the schemata with deployable scripts
  Deployable scripts are: 1) file is not at top level of the schema 
  and 2) extension is not blacklisted 
  """
  global g_internalSepator, g_listIndexedBySchemaType , g_schemataFound

  insertSqlStmtTemplate = """
--------------------------------------------------------------------------------
-- Store software release information: at this position we also record attempted 
-- deployment  
--------------------------------------------------------------------------------
DECLARE
  lv_rel_id NUMBER;
BEGIN 
  SELECT basic_data.APPL_RELEASE_SQ.nextval INTO lv_rel_id FROM dual;
  INSERT INTO basic_data.t_applied_releases( id, release_no, creation_dt ) VALUES( lv_rel_id, q'[{featureName}]', sysdate );
  INSERT INTO basic_data.t_applied_files( id, release_id, filename ) 
  SELECT appl_files_sq.nextval, lv_rel_id, q'[{basenameSqlScript}, git-branch: {featureName}, baseline-commit:{baselineCommit}, last-commit:{lastCommit}]' 
  FROM dual;

  COMMIT;
END;
/
  """

  suffixUsed = "-"+featureName if featureName != "" else ""
  sentinelPatPrefix = "REM place_here_scripts_for:"
  fh = open( sqlScriptTemplatePath, mode="r" )
  inpTemplateLines = fh.readlines()
  _dbx( "got %d lines from template" % ( len( inpTemplateLines ) ) )
  scriptTemplateText = "".join( inpTemplateLines )
  
  tmpDir = tempfile.mkdtemp()
  _infoTs( "install scripts will be placed under %s" % ( tmpDir ) ) 
  
  batchScriptTemplate = """
SET NLS_LANG=GERMAN_GERMANY.WE8MSWIN1252

SQLPLUS /nolog @{sqlScriptBaseName}
"""

  readmeContentHeader = """
Order to run install scripts:
"""
  readmeContentFooter = """
All processes in groups xxx, yyy must be stopped
"""

  batchScripts = []
  for schema in g_schemataFound:
    _dbx( "schema %s\n" % ( schema ) ) 
    script4Schema = scriptTemplateText
    script4Schema = script4Schema.replace( "<TARGET_SCHEMA>" , schema )
    for schemaType in g_listIndexedBySchemaType.keys():
      if schemaType.startswith ( schema ): 
        typeOnly = schemaType.split( g_internalSepator )[1]
        if typeOnly.upper() not in [ '.SQL' ]: # dirty fix to filter out top-level sql script 
          sentinelPattern = "%s%s" % ( sentinelPatPrefix, typeOnly.upper() ) 
          _dbx("schemaType %s, sentinel %s" % ( schemaType, sentinelPattern ) ) 
          listOfScripts = g_listIndexedBySchemaType[ schemaType ]
          _dbx("cnt scripts %s" % ( len( listOfScripts ) ) )
          # aggregate scripts of schemaType into one string 
          stringToAppend = "\n".join ( listOfScripts )
          _dbx( stringToAppend )
          found = script4Schema.find ( sentinelPattern )
          if found > 0 :
            _dbx( "found pattern" )
            script4Schema = script4Schema.replace( sentinelPattern , "\n%s\n%s" % ( sentinelPattern, stringToAppend) )    
          else:
              _errorExit( "Sentinel '%s' not found in template!" %(sentinelPattern) ) # , isWarning = True 
    # print( script4Schema )

    # now remove the sentinel's
    tempScript = script4Schema
    newLines = []
    for line in tempScript.split( "\n"):
      if not line.startswith( sentinelPatPrefix ) :
        newLines.append( line )
    script4Schema = "\n".join( newLines )

    basenameSqlScript = "install_%s%s.sql" % ( schema, suffixUsed )
    _dbx( basenameSqlScript )
    scriptPathSql = os.path.join( tmpDir, basenameSqlScript )

    if storeReleaseMetadata: 
      # for INSERT of applied release information 
      insertSqlStmt = insertSqlStmtTemplate.format( featureName= featureName \
        , baselineCommit= baseCommit, lastCommit= lastCommit, basenameSqlScript= basenameSqlScript )
      _dbx( insertSqlStmt )
      script4Schema = script4Schema.format( placeHolderStoreReleaseMetadata = insertSqlStmt, baselineCommit= baseCommit, featureName= featureName  )
    else:
      script4Schema = script4Schema.format( placeHolderStoreReleaseMetadata = "", baselineCommit= baseCommit, featureName= featureName )

    scriptPathBat = os.path.join( tmpDir, "install_%s.bat" % ( schema ) )
    fh = open( scriptPathSql, mode= "w" ); fh.write( script4Schema ); fh.close()
    sqlScriptBaseName = os.path.basename( scriptPathSql )

    batchScriptContent = batchScriptTemplate.format( sqlScriptBaseName= sqlScriptBaseName )
    fh = open( scriptPathBat, mode= "w" ); fh.write( batchScriptContent ); fh.close()
    _infoTs( "output SQL script unix-style >>>>> %s \nDOS style >>>: %s" % ( dosPath2Unix(scriptPathSql), scriptPathSql) ) 
    _infoTs( "output BAT script unix-style >>>>> %s \nDOS style >>>: %s" % ( dosPath2Unix(scriptPathBat), scriptPathBat) ) 
    #_errorExit( "in test - stopped after 1 schema!! " );
    batchScripts.append ( os.path.basename( scriptPathBat ) )

  # create install readme
  readmeFile = os.path.join( tmpDir, "install%s-readme.txt" % ( suffixUsed ) )
  items = []
  for batchScript in batchScripts: 
    items.append( "?. %s" % ( batchScript ) )
    _dbx( batchScript ) 
  itemsText = "\n".join( items ) 
  readmeText = "%s\n%s\n%s\n" % ( readmeContentHeader,itemsText, readmeContentFooter )

  fh = open( readmeFile, mode= "w" ); 
  fh.write( readmeText ); 
  fh.close()
  _infoTs( "readme file unix-style >>>>> %s \nDOS style >>>: %s" % ( dosPath2Unix(readmeFile), readmeFile) ) 

def extractTouchedScripts( commitA, commitB="HEAD" ):
  """ STILL in development (not so critical) 
  """
  args = ["git", "diff" , "--name-only" , commitA, commitB ]
  outFh, tmpOutFile = tempfile.mkstemp()
  _dbx( "using %s to capture output from git diff \nunix-style: %s" % ( tmpOutFile,  dosPath2Unix( tmpOutFile ) ) )
  # outFh = open( tmpOutFile, "w" )
  subprocess.run( args, stdout = outFh )
  
  # _errorExit("test exit") 
  gitOutLines = open( tmpOutFile, "r" ).readlines()
  if len( gitOutLines ) == 0 :
    _errorExit( "No lines found in git diff output file %s" % ( tmpOutFile ) )
  scriptsSet = set()
  for line in gitOutLines:
    if "we used git diff --name-status" == "but then there are issues with renames":
      # _dbx( line )
      match = re.search( "^([ADM])\s+(.*)$", line) 
      if match == None: 
        raise ValueError( "git diff returned line with unexpected content: %s" % line )
      else:
        staCode, script = match.groups(1)[0:2]
        #_dbx( staCode)# ; _dbx( script )
        if staCode in "AM": 
          scriptsSet.add( script )
        elif staCode == "D":
          scriptsSet.discard( script )
    else:
      scriptsSet.add( line ) 
  _dbx( len( scriptsSet) )
  return list( scriptsSet )

def action_createZip( files ):
  """zip the given files:
  1. if at least 1 file starts with root, find a common root of all. In worst case it is the root. 
     For example /a/b/file1.txt and /a/foo/bar.py  would have /a as common root 
  2. remove the common root from all 
     The 2 files above become b/file1.txt foo/bar.py 
  3. put the files into the zip with the remaining relative paths
  """
  if len( files ) == 0 :
    raise ValueError( "list of files is empty" )

  if files[0].startswith( "/" ):
    # if any file path starts with root, we strip off the common prefix
    commonRoot = os.path.commonprefix( files )
    _dbx( "commonRoot %s" % commonRoot )
    pathsUsed = [ os.path.relpath( file, commonRoot ).rstrip("\n")  for file in files ]
  else:
    pathsUsed = [ file.rstrip("\n")  for file in files ]
  _dbx( "pathsUsed %s" %  pathsUsed )

  zipArcPath = tempfile.mkstemp( suffix = ".zip") [1]
  _dbx( "zipArcPath  type %s" %  zipArcPath )

  if True:
    with zipfile.ZipFile( zipArcPath, 'w') as zipArc:
     for filePath in pathsUsed:
       zipArc.write(filePath)

  return zipArcPath 

def main(): 
  global g_listIndexedBySchemaType, g_scriptTemplatePath

  cmdLnConfig = parseCmdLine()
  setDebug( cmdLnConfig.debug ) 
  if cmdLnConfig.baseCommit:
    linesOfTouchedScripts = extractTouchedScripts( commitA= cmdLnConfig.baseCommit, commitB = cmdLnConfig.lastCommit )
  else: 
    _infoTs( "reading touched lines from stdin.." )
    linesOfTouchedScripts = sys.stdin.readlines()

  if cmdLnConfig.action == "extract":
    _infoTs( "scripts found: %s" % "\n".join( linesOfTouchedScripts ) )
  elif cmdLnConfig.action == "make":
    fill_listIndexedBySchemaType( linesOfTouchedScripts= linesOfTouchedScripts ) 
    createSchemataInstallScripts( sqlScriptTemplatePath= g_scriptTemplatePath \
      , baseCommit= cmdLnConfig.baseCommit, lastCommit= cmdLnConfig.lastCommit \
      , featureName= cmdLnConfig.featureName, storeReleaseMetadata = cmdLnConfig.storeRelMeta  \
      ) 
  elif cmdLnConfig.action == "zip":
    zipFile = action_createZip( files = linesOfTouchedScripts )
    _infoTs( "zip file created at %s" % zipFile )

if __name__ == "__main__" : 
  main()