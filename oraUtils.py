#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3
""" various utilities for working with Oracle database 
"""
import getpass, inspect, json, os, subprocess, tempfile, sys 
from collections import namedtuple

from dbx import _dbx, _infoTs, _errorExit, setDebug

g_mapFileExtDbmsMetaDataTypeToad = \
{ "pkb" : "PACKAGE_BODY"
, "pks" : "PACKAGE_SPEC"
, "tpb" : "TYPE_BODY"
, "tps" : "TYPE_SPEC"
, "prc" : "PROCEDURE"
, "fnc" : "FUNCTION"
, "trg" : "TRIGGER"
}


class DBObject ( namedtuple( 'DBObject', 'owner, name, type, fileExt' ) ):
  # __init__ inherited from base class 

  def initFromPathWithSchemaTypeFileNameV1 ( self, s ):
    """ Example valid input : 
      LICENSING\PACKAGES\SK_GIAF.PKS
      PROCESS\VIEWS\V_PENDING_DIDAS_RES_PROCESSES.SQL
    """
    tokensByBackSl = s.split ( "\\" )
    tokensByForwSl = s.split ( "/" )
    if len( tokensByBackSl ) != 3 and len( tokensByForwSl ) != 3:
      raise ValueError( "No path separator found in input string or it is invalid. Expect schema sep type sep basename. Found '%s'" % s ) 
    tokens = tokensByBackSl if len( tokensByBackSl ) > 0 else tokensByForwSl
    owner, type, fileName = tokens

def loadOraConnectionData( inputFilePath = None):
  """read connection data from json input file and return a list of dictionaires to the caller
  NO CONNECTIONs are actually opened to the database! Also password must be acquired by 
  other means.
  """
  if inputFilePath == None:
    moduleSelfDir = os.path.dirname( inspect.getfile(inspect.currentframe()) ) 
    inputFilePath = os.path.join ( moduleSelfDir, './ora_connection_cfg.json' ) 
  if not os.path.exists( inputFilePath ):
    _errorExit( "File %s does not seem to exist!" % ( inputFilePath ) ) 
  
  conns = []
  jData = json.load( open(inputFilePath, "r") )
  _dbx( len( jData ) )
  connRecs = jData[ "connectData" ]
  # __errorExit( "fixme: json structure chagned!" ) 
  for connDict in connRecs : # .keys():
    _dbx( connDict ) 
    nickname= connDict[ 'nickname' ]
    host= connDict[ 'host' ]
    port= connDict[ 'port' ]
    service= connDict[ 'service' ]
    user= connDict[ 'user' ]
    conn = NicknamedOraConnection( nickname= nickname, host=host, port= port, service= service, username= user )
    _dbx( str( conn ) )
    conns.append( conn )
  _dbx( len( conns ) ) 
  return conns

def getConnectionByNickname ( nickname, nicknamedConns ):
  for conn in nicknamedConns:
    if conn.nickname == nickname: return conn
  return None

class OraConnection ( namedtuple( 'OraConnection', 'host, port, service, username' ) ):
  pass

class NicknamedOraConnection ( namedtuple( 'NamedOraConnection', 'nickname, host, port, service, username' ) ):
  pass
    
def getOraPassword ( oraUser, oraPasswordEnvVar, batchMode ):
  """Prompt for Oracle password if it is not found from environment variable. 
  Password entered will be hidden.
  """
  passwordEnv= None; hiddenPassword= ""
  if oraPasswordEnvVar in os.environ:
    passwordEnv= os.environ[ oraPasswordEnvVar ]
    if passwordEnv:
      print('INFO: Found a value from the environment varable %s. Will use it if you just hit Enter on the password prompt' % oraPasswordEnvVar )
      if batchMode:
        return passwordEnv
  else:
    _errorExit ( "getpass does not work on Windows! Use environment variable " )

    print('INFO: Password could be passed as environment variable %s however it is not set.' % oraPasswordEnvVar )
    hiddenPassword = getpass.getpass('Enter password for Oracle user %s. (The input will be hidden if supported by the OS platform)' % oraUser )
  if hiddenPassword == "" :
    if passwordEnv:
      hiddenPassword= passwordEnv
  return hiddenPassword


####
def getSqlRunner( oraUser, password, host, port, service ):
  """ set up an Oracle session and return a cursor with which queries can be executed. Result of query
    can be fetched using fetchone or fetchall. Why exactly we need a cursor instead of using the 
    connection handle directly, remains to be clarified.
  """
  myDsn = cx_Oracle.makedsn(host, port, service_name= service) # if needed, place an 'r' before any parameter in order to address special characters such as '\'.
  
  conx= cx_Oracle.connect( user= oraUser, password= password, dsn= myDsn )   
  conx.outputtypehandler = conxOutputTypeHandler
  
  cur = conx.cursor()  # instantiate a handle
  cur.execute ("""select username, sys_context( 'userenv', 'db_name' ) from user_users""")  
  connectedAs, dbName = cur.fetchone()
  _infoTs( "connected as %s to %s" % ( connectedAs, dbName ) )

  return cur

####
def getSqlRunnerFromConnectQuad ( connectQuadruple ): # 4-tuple: host, port, service, user
  """ connect to Oracle DB and return a cursor to run SQL
  """
  
  host, port, service, username = connectQuadruple.split( ":" )
  password = getOraPassword ( oraUser= username, oraPasswordEnvVar= 'ORA_SECRET', batchMode= False )
  # _dbx( host ); _dbx( service )
  sqlRunner =  getSqlRunner( oraUser= username, password= password, host=host, port= port, service= service )

  return sqlRunner


####
def fetchOneScriptFromDatabase( objectSchema, objectType, objectName, sqlRunner ) :
  """Extract one DDL scripts from the given sqlRunner handle and return it as list of lines
  """
  _dbx( type( sqlRunner ) )

  extractorQuery = ' '.join( open( "./parameterized_extractor.sql", "r").readlines() )
  _dbx(  extractorQuery [ : 200] ) 
  _dbx(  len( extractorQuery ) )
  if "need to " == "use all_objects":
    extractorQuery = extractorQuery.replace( '/*replace_start*/ dba_objects /*replace_end*/', ' all_objects ' ) 
    _dbx(  len( extractorQuery ) )

  bindVar1 = ",".join( objectSchema );   _dbx( bindVar1 )
  bindVar2 = ",".join( objectType );   _dbx( bindVar2 )
  bindVar3 = ",".join( objectName );   _dbx( bindVar3 )
  # _errorExit( "test" )
  sqlRunner.execute( extractorQuery, [ bindVar1, bindVar2, bindVar3 ] )

  dbName, scriptContent = sqlRunner.fetchone()[0]
  _dbx( type( scriptContent ) )
  _dbx( len( scriptContent ) )
  
  return dbName, scriptContent 

def spoolScriptWithSqlplusDbmsMetadata ( spoolDestRoot, dirSep, dbObjects, connectQuadruple= None, connDataObj= None ): 
  """ Use sqlplus 
    connectQuadruple is colon(:) separated list of host, port, service, user
  """
  if connectQuadruple == None and connDataObj == None:
    raise ValueError( "either connectQuadruple or connDataObj has to be provided")
  if connectQuadruple != None and connDataObj != None:
    raise ValueError( "either connectQuadruple or connDataObj has to be provided")

  if connectQuadruple != None:
      host, port, service, username = connectQuadruple.split( ":" )
  elif connDataObj != None:
      host, port, service, username = connDataObj.host, connDataObj.part, connDataObj.service, connDataObj.username 
 
  spoolScriptHeader = """
CONNECT {v_ez_connect}
WHENEVER SQLERROR EXIT 

column db_name new_val db_name
column spool_path_current new_val spool_path_current

ALTER SESSION SET NLS_LANGUAGE=GERMAN
;
set termout ON 
SELECT sys_context( 'userenv', 'db_name' ) AS db_name 
  , user connect_as 
FROM dual 
;
"""
  # FIXME: we need to align the mapping of object type in the SQL script template and mapping defined in dict object! 
  scriptBlockFor1Object = """
set termout OFF 

WITH prep_ AS 
( SELECT 
   UPPER( '{v_object_name}' ) || '-'||'&db_name' as obj_name_and_db_name
  , CASE upper('{v_object_type}') 
    WHEN 'PACKAGE_BODY' THEN '.pkb' 
    WHEN 'PACKAGE_SPEC' THEN '.pks' 
    WHEN 'TRIGGER' THEN '.trg' 
    WHEN 'TYPE_BODY' THEN '.tpb' 
    WHEN 'TYPE_SPEC' THEN '.tps' 
    WHEN 'FUNCTION' THEN '.fnc' 
    WHEN 'PROCEDURE' THEN '.prc' 
    WHEN 'VIEW' THEN '.vw' 
    ELSE '.sql' 
    END AS file_ext 
  FROM DUAL 
) 
SELECT '{spool_dest_root}'|| '{dir_sep}' || '&db_name' || '{dir_sep}' ||obj_name_and_db_name ||file_ext 
  AS  spool_path_current 
FROM prep_ 
;

set echo off feedback off head off linesize 1000 longchunksize 9999999 long 9999999 pagesize 49999 termout off trimspool on

spool &spool_path_current

SELECT dbms_metadata.get_ddl( upper('{v_object_type}'), upper( '{v_object_name}' ), upper( '{v_schema}' ) ) 
FROM DUAL
;

spool off
"""

  spoolScriptTrailer = """
EXIT
"""

  password = getOraPassword ( oraUser= username, oraPasswordEnvVar= 'ORA_SECRET', batchMode= False )

  ezConnect = """%s/"%s"@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=%s)(PORT=%s)))(CONNECT_DATA=(SERVER=DEDICATED)(SERVICE_NAME=%s)))""" % ( username, password, host, port, service )
  spoolPath = tempfile.mktemp()

  if "want to fight" == "the DOS vs gitbash vs unix platform gap":
    sqlTermoutPath = tempfile.mktemp()
    _dbx( "sqlTermoutPath %s" )
    sqlpTermoutFh = open( sqlTermoutPath, "w" )

    sqlpJob = subprocess.Popen( [ "sqlplus", "/nolog" ], stdin = subprocess.PIPE, stdout= sqlpTermoutFh )
    sqlpJob.stdin.write( spoolScript.encode('utf-8') )
    sqlpJob.communicate( )
  
    sqlpTermoutFh = open( sqlTermoutPath, "r" )
    _dbx( sqlpTermoutFh.readlines() )
  else: # build one script block per DBObject
    
    scriptBlocks= []
    for obj in dbObjects:
      scriptBlocks.append( scriptBlockFor1Object.format( spool_dest_root= spoolDestRoot, v_schema= obj.owner, v_object_type= obj.type, v_object_name= obj.name, dir_sep= dirSep ) )

    _dbx( "len( scriptBlocks ) : %d " % len( scriptBlocks ) )

    headerFormatted = spoolScriptHeader.format( v_ez_connect= ezConnect )
    spoolScript = "%s \n%s \n%s" % ( headerFormatted, "\n".join( scriptBlocks), spoolScriptTrailer )
    sqlplusScriptPath =  tempfile.mktemp() + '.sql'
    _dbx( "sqlplusScriptPath: %s" % ( sqlplusScriptPath ) ) 
    open( sqlplusScriptPath, "w").write( spoolScript )

    return sqlplusScriptPath





def spoolScriptWithSqlplusTempClob ( spoolDestRoot, dirSep, dbObjects, conn= None ): 
  """ Use sqlplus 
    This method requires a global table accessible by the connecting user to write 
    the source code extracted from DBA_SOURCE line by line as CLOB 
  """
  host, port, service, username = conn.host, conn.port, conn.service, conn.username 
 
  spoolScriptHeader = """
WHENEVER SQLERROR EXIT 
WHENEVER OSERROR EXIT 

CONNECT {v_ez_connect}

column db_name new_val db_name
column spool_path_current new_val spool_path_current 


ALTER SESSION SET NLS_LANGUAGE=GERMAN
;
set termout ON 
SELECT sys_context( 'userenv', 'db_name' ) AS db_name 
  , user connect_as 
FROM dual 
;

set linesize 1000 longchunksize 9999999 long 9999999 pagesize 49999
"""
  scriptBlockFor1Object = """
WITH prep_ AS 
( SELECT 'c:\\temp\&db_name\\' as base_folder
  , UPPER( '{lv_object_name}' ) || '-'||'&db_name' as obj_name_and_db_name
  , CASE upper('{lv_object_type}') 
    WHEN 'PACKAGE_BODY' THEN '.pkb' 
    WHEN 'PACKAGE_SPEC' THEN '.pks' 
    WHEN 'TRIGGER' THEN '.trg' 
    WHEN 'TYPE_BODY' THEN '.tpb' 
    WHEN 'TYPE_SPEC' THEN '.tps' 
    WHEN 'FUNCTION' THEN '.fnc' 
    WHEN 'PROCEDURE' THEN '.prc' 
    WHEN 'VIEW' THEN '.vw' 
    ELSE '.sql' 
    END AS file_ext 
  FROM DUAL 
) 
SELECT base_folder||obj_name_and_db_name||file_ext as  spool_path_current 
FROM prep_ 
;

PROMPT spool_path_current set to &spool_path_current


--CREATE global TEMPORARY TABLE tt_extract_ddl_clob ( owner varchar2(30), type varchar2(30), name varchar2(30), text clob ) on COMMIT preserve rows;

SET ECHO OFF VERIFY OFF 

DECLARE 
  lv_schema VARCHAR2(30) :=  UPPER('{lv_schema}');
  lv_object_type VARCHAR2(30) :=  UPPER('{lv_object_type}');
  lv_type_to_filter  VARCHAR2(30) ;
  lv_object_name VARCHAR2(30) :=  UPPER('{lv_object_name}');
  lv_clob  CLOB := 'CREATE OR REPLACE ';
  lv_text  LONG;
BEGIN
  lv_type_to_filter := 
    CASE lv_object_type 
    WHEN 'PACKAGE_SPEC' THEN 'PACKAGE'
    WHEN 'PACKAGE_BODY' THEN 'PACKAGE BODY'
    WHEN 'TYPE_SPEC' THEN 'TYPE'
    WHEN 'TYPE_BODY' THEN 'TYPE BODY'
    ELSE lv_object_type
    END;

  EXECUTE IMMEDIATE 'truncate  table tt_extract_ddl_clob';
  FOR rec IN (
    SELECT line, text
    FROM dba_source
    WHERE owner = lv_schema
      AND type  = lv_type_to_filter 
      AND name  = lv_object_name
    ORDER BY line 
  ) LOOP
    lv_text := rec.text; 
    dbms_lob.append( lv_clob, lv_text );
    -- dbms_OUTPUT.put_line( 'Ln'||$$plsql_line||': '||lv_offset );
    -- IF mod(rec.line, 13) = 1 THEN       dbms_output.put_line( rec.text );    END IF;
  END LOOP;
  INSERT INTO tt_extract_ddl_clob( text ) VALUES ( lv_clob );
  COMMIT;
END;
/

set termout off trimspool on head off 

spool &spool_path_current


SELECT text FROM tt_extract_ddl_clob ;

spool off
"""

  spoolScriptTrailer = """
EXIT
"""

  password = getOraPassword ( oraUser= username, oraPasswordEnvVar= 'ORA_SECRET', batchMode= False )

  ezConnect = """%s/"%s"@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=%s)(PORT=%s)))(CONNECT_DATA=(SERVER=DEDICATED)(SERVICE_NAME=%s)))""" % ( username, password, host, port, service )
  spoolPath = tempfile.mktemp()

  if "want to fight" == "the DOS vs gitbash vs unix platform gap":
    sqlTermoutPath = tempfile.mktemp()
    _dbx( "sqlTermoutPath %s" )
    sqlpTermoutFh = open( sqlTermoutPath, "w" )

    sqlpJob = subprocess.Popen( [ "sqlplus", "/nolog" ], stdin = subprocess.PIPE, stdout= sqlpTermoutFh )
    sqlpJob.stdin.write( spoolScript.encode('utf-8') )
    sqlpJob.communicate( )
  
    sqlpTermoutFh = open( sqlTermoutPath, "r" )
    _dbx( sqlpTermoutFh.readlines() )
  else: # build one script block per DBObject
    
    scriptBlocks= []
    for obj in dbObjects:
      scriptBlocks.append( scriptBlockFor1Object.format( spool_dest_root= spoolDestRoot, lv_schema= obj.owner, lv_object_type= obj.type, lv_object_name= obj.name, dir_sep= dirSep ) )

    _dbx( "len( scriptBlocks ) : %d " % len( scriptBlocks ) )

    headerFormatted = spoolScriptHeader.format( v_ez_connect= ezConnect )
    spoolScript = "%s \n%s \n%s" % ( headerFormatted, "\n".join( scriptBlocks), spoolScriptTrailer )
    sqlplusScriptPath =  tempfile.mktemp() + '.sql'
    _dbx( "sqlplusScriptPath: %s" % ( sqlplusScriptPath ) ) 
    open( sqlplusScriptPath, "w").write( spoolScript )

    return sqlplusScriptPath




if __name__ == "__main__" : 
  
  setDebug( True )
  conns = loadOraConnectionData()
  _dbx( len( conns ) )
  