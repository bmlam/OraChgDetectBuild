#! /Library/Frameworks/Python.framework/Versions/3.8/bin/python3

#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3

"""
"""
import json , os 

from collections import namedtuple
from dbx import _dbx, _infoTs

def parseCmdLine() :
  import argparse

  parser = argparse.ArgumentParser()

  parser.add_argument( '-s', '--subject' , required= True )
  parser.add_argument( '-r', '--recipient' , required= True )
  parser.add_argument( '-m', '--messagePlainText' , default= "test message" )
  parser.add_argument( '-H', '--htmlTextFile' )
  parser.add_argument( '-a', '--attachmentFile' )
  parser.add_argument( '-i', '--senderInfoFile', help="path of JSON file containing sender info", default = "senderInfo.json" )

  result= parser.parse_args()

  return result 

class SenderInfo ( namedtuple( 'SenderInfo', 'host, port, username, secret ' ) ): 
  pass 

def getSenderInfo( infoJsonString ):
  """ get sender server, port, username. password will be extracted from environment variable SENDER_SECRET 
  """
  infoDict = json.loads( infoJsonString )
  host = infoDict ["host"]
  username = infoDict ["username"]
  port = infoDict ["port"]
  _dbx( host )
  senderSecret  = os.environ[ "SENDER_SECRET" ]
  senderInfo = SenderInfo( host= host, port= port, username= username, secret= senderSecret )

  return senderInfo 

if __name__ == "__main__" : 

  argConfig = parseCmdLine() 

  senderInfoJson = "".join ( open( argConfig.senderInfoFile, "r").readlines () )
  _dbx( senderInfoJson)
  senderInfo = getSenderInfo( infoJsonString= senderInfoJson )

  if "want to " == "create json sender info ":
    testDict = {  'host': 'messenger',  'port': "123",  'username': 'Facebook',  'secret': "100" }
    print( json.dumps( testDict ) ) 

