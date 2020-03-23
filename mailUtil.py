#! /Library/Frameworks/Python.framework/Versions/3.8/bin/python3

#! /c/Users/bonlam/AppData/Local/Programs/Python/Python37-32/python3

"""
"""
import json , os 

import email, smtplib, ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from collections import namedtuple
from dbx import _dbx, _infoTs

def parseCmdLine() :
  import argparse

  parser = argparse.ArgumentParser()

  parser.add_argument( '-s', '--subject' , required= True )
  parser.add_argument( '-r', '--recipients' , required= True )
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

def sendMail( senderInfo, recipients, subject, plainText, htmlFile= None, binAttachFile= None ):
  """ plainText is the mininum payload of the mail. html and binAttachFile will be converted 
  to base64 parts
  """


  body = plainText 

  # Create a multipart message and set headers
  message = MIMEMultipart()
  message["From"] = senderInfo.username 
  message["To"] = recipients
  message["Subject"] = subject

  # Add body to email
  message.attach(MIMEText(body, "plain"))

  if binAttachFile:

  # Open attachment file in binary mode
    with open(binAttachFile, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        partBin = MIMEBase("application", "octet-stream")
        partBin.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email    
    encoders.encode_base64(partBin)

    # Add header as key/value pair to attachment part
    fileBaseName = os.path.basename( binAttachFile )
    partBin.add_header(
        "Content-Disposition",
        f"attachment; filename= {fileBaseName}",
    )

    # Add attachment to message and convert message to string
    message.attach(partBin)

  text = message.as_string()

  # Log in to server using secure context and send email
  context = ssl.create_default_context()
  with smtplib.SMTP_SSL( senderInfo.host, senderInfo.port, context=context) as server:
      server.login(senderInfo.username, senderInfo.secret )
      server.sendmail(senderInfo.username, recipients, text )

if __name__ == "__main__" : 

  argConfig = parseCmdLine() 

  senderInfoJson = "".join ( open( argConfig.senderInfoFile, "r").readlines () )
  _dbx( senderInfoJson)
  senderInfo = getSenderInfo( infoJsonString= senderInfoJson )

  sendMail(senderInfo= senderInfo, recipients= argConfig.recipients \
    , subject= argConfig.subject, plainText = argConfig.messagePlainText \
    , htmlFile = argConfig.htmlTextFile, binAttachFile = argConfig.attachmentFile
  )
  if "want to " == "create json sender info ":
    testDict = {  'host': 'messenger',  'port': "123",  'username': 'Facebook',  'secret': "100" }
    print( json.dumps( testDict ) ) 

