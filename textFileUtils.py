"""
  contains various help routine which deal with general text or file conversion , handling 
"""

import os, re, subprocess, sys, shutil, tempfile

# my stuff 
from dbx import _dbx, _infoTs, _errorExit

### 
def mixedDosPathToUnix ( path ):
  if path[1] == ":":
    drive = path[0]
    return '/' + drive + '/' + path[3:]
  else:
    return path 

### 
def unixToDosPath ( path ):
  pass 

####
def genUnixDiff ( oldPath, newPath, recursive= False ):
    """Calls the unix diff command and returns its output to the calling function
    bomb out if any error was detected but only displayed upto 10 lines of the stderr
    """
    diffCmdArgsUnix= [ 'diff', '-b', oldPath, newPath ]
    if recursive: diffCmdArgsUnix.insert( 1, '-r' )

    # for a in diffCmdArgsUnix: _dbx( a ); _errorExit( 'test' )
    proc= subprocess.Popen( diffCmdArgsUnix, stdin=subprocess.PIPE, stdout=subprocess.PIPE ,stderr=subprocess.PIPE, universal_newlines= True )
    unixOutMsgs, errMsgs= proc.communicate()

    if len( errMsgs ) > 0 : # got error, return immediately
        _errorExit( 'got error from diff. Only first 10 lines are shown:\n%s ' % '\n'.join( errMsgs [ 0: 10]  ) )

    _dbx(  len( unixOutMsgs ) )
    return unixOutMsgs

def persistAndPrintName( textName, textContent, baseNamePrefix ):
  outPath = tempfile.mktemp()
  if baseNamePrefix != None:
    tempDirName  = os.path.dirname( outPath )
    tempBaseName = os.path.basename( outPath )
    outPath = os.path.join( tempDirName, baseNamePrefix + tempBaseName )
    
  _infoTs( "Text named '%s' will be written to %s" % ( textName, mixedDosPathToUnix(outPath) ), withTs= True )
  fh = open( outPath, "w")
  fh.write( "\n".join(textContent ) ) 
  return outPath 


def getGitCurrBranchName():
  args = ["git", "branch" ]
  outFh, tmpOutFile = tempfile.mkstemp()
  _dbx( "using %s to capture output from git branch \nunix-style: %s" % ( tmpOutFile, tmpOutFile ) )
  # outFh = open( tmpOutFile, "w" )
  subprocess.run( args, stdout = outFh )
  
  # _errorExit("test exit") 
  gitOutLines = open( tmpOutFile, "r" ).readlines()
  if len( gitOutLines ) == 0 :
    _errorExit( "No lines found in git branch output file %s" % ( tmpOutFile ) )

  branchName= None
  for line in gitOutLines:
    if line.startswith( '*'):
      branchName = line.split()[1]

  return branchName

