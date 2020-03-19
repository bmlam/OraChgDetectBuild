--------------------------------------------------------------------------------
-- accept parameters for DB Connection
--------------------------------------------------------------------------------
ACCEPT hostname DEFAULT liono-db.gema.de PROMPT "machine description or IP to install the release [LIONO-DB.GEMA.DE]: "
ACCEPT servicename DEFAULT srv_user_it_e PROMPT "machine servicename to install the release [SRV_USER_IT_E]: "
ACCEPT username DEFAULT <TARGET_SCHEMA> PROMPT "enter target username [<TARGET_SCHEMA>]: "
ACCEPT userpw PROMPT "enter password of &username on target machine: "
SET TERMOUT OFF

--------------------------------------------------------------------------------
-- connect to Database
--------------------------------------------------------------------------------
CONNECT &username/&userpw@(DESCRIPTION=(enable=broken)(ADDRESS=(PROTOCOL=TCP)(Host=&hostname)(Port=1521))(CONNECT_DATA=(SERVICE_NAME=&servicename)))

--------------------------------------------------------------------------------
-- handle the release name, default value is current date/time
-- accept optional as an additional parameter
--------------------------------------------------------------------------------
column release_tag new_value release_tag
select to_char(sysdate, 'yyyy.mm.dd.hh24')||substr( '-{featureName}', 1, 50 ) as release_tag from dual;
SET VERIFY OFF
SET ECHO OFF
SET SERVEROUTPUT OFF
SET HEADING ON
SET FEEDBACK ON
SET SQLBLANKLINES ON
SET TERMOUT ON
SET DEFINE ON
ACCEPT releasename DEFAULT &release_tag PROMPT "enter releasename of current release [&release_tag]: "

--------------------------------------------------------------------------------
-- activate logging
--------------------------------------------------------------------------------
SPOOL install_<TARGET_SCHEMA>.log

--------------------------------------------------------------------------------
-- information about connection
--------------------------------------------------------------------------------
PROMPT connected as &username on &hostname

--------------------------------------------------------------------------------
-- set error action
--------------------------------------------------------------------------------
WHENEVER SQLERROR CONTINUE 
WHENEVER OSERROR EXIT 

--------------------------------------------------------------------------------
-- ensure that objects are installed in the right schema
--------------------------------------------------------------------------------

PROMPT change session to <TARGET_SCHEMA>
ALTER SESSION SET CURRENT_SCHEMA = <TARGET_SCHEMA>;
ALTER SESSION SET NLS_LANGUAGE = GERMAN;


PROMPT =========================================================================
PROMPT show invalid objects BEFORE deployment ...
PROMPT =========================================================================
set pages 120 lines 100
col object_name format a30 
col object_type format a20 

SELECT object_name, object_type, status FROM user_objects WHERE status <> 'VALID'
;

{placeHolderStoreReleaseMetadata}

--------------------------------------------------------------------------------
-- start releasing the scripts
--------------------------------------------------------------------------------
PROMPT install release files...
SET DEFINE OFF
PROMPT =========================================================================
PROMPT install Sequences...
PROMPT =========================================================================
REM place_here_scripts_for:SEQUENCES
PROMPT =========================================================================
PROMPT install Foreign Key Constraints...
PROMPT =========================================================================
REM place_here_scripts_for:FK_CONSTRAINTS

PROMPT =========================================================================
PROMPT install Database Links...
PROMPT =========================================================================
REM place_here_scripts_for:DB_Links

PROMPT =========================================================================
PROMPT install Sequences...
PROMPT =========================================================================
REM place_here_scripts_for:Sequences

PROMPT =========================================================================
PROMPT install Synonyms...
PROMPT =========================================================================
REM place_here_scripts_for:Synonyms

PROMPT =========================================================================
PROMPT install Tables...
PROMPT =========================================================================
REM place_here_scripts_for:TABLES.SQL 

PROMPT =========================================================================
PROMPT install Views...
PROMPT =========================================================================
REM place_here_scripts_for:VIEWS.VW

PROMPT =========================================================================
PROMPT install Indexes ...
PROMPT =========================================================================
REM place_here_scripts_for:INDEXES.SQL

PROMPT =========================================================================
PROMPT install Triggers...
PROMPT =========================================================================
REM place_here_scripts_for:TRIGGERS.TRG

PROMPT =========================================================================
PROMPT install Type Specs...
PROMPT =========================================================================
REM place_here_scripts_for:TYPES.TPB

PROMPT =========================================================================
PROMPT install Type Bodies...
REM place_here_scripts_for:TYPES.TPS

PROMPT =========================================================================
PROMPT =========================================================================
PROMPT install Packages Spec for Table DML operations (table APIs)...
PROMPT =========================================================================
REM place_here_scripts_for:PACKAGES_API.PKS

PROMPT =========================================================================
PROMPT install Packages Body for Table DML operations (table APIs)...
PROMPT =========================================================================
REM place_here_scripts_for:PACKAGES_API.PKB

PROMPT =========================================================================
PROMPT install Packages Spec with Business Logic...
PROMPT =========================================================================
REM place_here_scripts_for:PACKAGES.PKS

PROMPT =========================================================================
PROMPT install Packages Body with Business Logic...
PROMPT =========================================================================
REM place_here_scripts_for:PACKAGES.PKB

PROMPT =========================================================================
PROMPT install single Procedures...
PROMPT =========================================================================
REM place_here_scripts_for:PROCEDURES

PROMPT =========================================================================
PROMPT install single Functions...
PROMPT =========================================================================
REM place_here_scripts_for:FUNCTIONS

PROMPT =========================================================================
PROMPT install Grants provided by other users...
PROMPT =========================================================================
REM place_here_scripts_for:GRANTS_FROM.SQL

PROMPT =========================================================================
PROMPT install Grants provided to other users...
PROMPT =========================================================================
REM place_here_scripts_for:GRANTS_TO.SQL

PROMPT =========================================================================
PROMPT install DML scripts required for the release...
PROMPT =========================================================================
REM place_here_scripts_for:DML.SQL

-- @@"DML\example_DML.sql"
PROMPT =========================================================================
PROMPT compile schema <TARGET_SCHEMA>
PROMPT =========================================================================
BEGIN
  DBMS_UTILITY.compile_schema(schema => '<TARGET_SCHEMA>', compile_all => FALSE);
END;
/

PROMPT =========================================================================
PROMPT show invalid objects after deployment ...
PROMPT =========================================================================
set pages 120 lines 100
col object_name format a30 
col object_type format a20 

SELECT object_name, object_type, status FROM user_objects WHERE status <> 'VALID'
;

PROMPT ... done

--------------------------------------------------------------------------------
-- finish the logfile
--------------------------------------------------------------------------------
SPOOL OFF
--------------------------------------------------------------------------------
-- finish the release
--------------------------------------------------------------------------------
EXIT



