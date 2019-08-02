#!/usr/bin/python
#TODO Update the line below
#Date last updated: 27 Mar 2018

#----------------------#Import libraries and classes===========================
import signal,sys,os,time,requests,errno,tarfile
import multiprocessing as mp
from subprocess import call
from subprocess import check_output
from cStringIO import StringIO
#===========================Global Variables===================================
gHeader = {"Content-Type": "application/json"}
gIndex = ""
gStop = False
#gCurlLock = mp.Lock()
gPrintLock = mp.Lock()
gNumFiles = 0
gCurrentFile = mp.Value('i', 0)


g_desiredFields = [
  "date"         ,
  "time"         ,
  "s-ip"         ,
  "cs-method"    ,
  "cs-uri-stem"  ,
  "cs-uri-query" ,
  "s-port"       ,
  "cs-username"  ,
  "c-ip"         ,
  "cs(User-Agent)" ,
  "cs(Referer)"    , 
  "sc-status"      ,
  "sc-substatus"   ,
  "sc-win32-status",
  "time-taken"     ,
]

gRequiredFields = [   
  "date",
  "time",
  "c-ip",    #Source IP
  "s-port"   #Dest port
]

gLogToELKMapping = {
  "date"         :    "date",
  "time"         :    "time",
  "s-ip"         :    "s_ip",
  "cs-method"    :    "cs_method",
  "cs-uri-stem"  :    "cs_uri_stem",
  "cs-uri-query" :    "cs_uri_query", 
  "s-port"       :    "s_port",
  "cs-username"  :    "cs_username",
  "c-ip"         :    "c_ip",
  "cs(User-Agent)" :  "cs(User_Agent)", 
  "cs(Referer)"    :  "cs(Referer)",
  "sc-status"      :  "sc_status", 
  "sc-substatus"   :  "sc_substatus",
  "sc-win32-status":  "sc_win32-status",
  "time-taken"     :  "time_taken"
}

#TODO Create a list of fields that are often empty ("-") and maybe need to be
#changed to the empty string ("")
#===========================signalHandler()====================================
def signalHandler(signal, frame):
   global gStop 
   gStop = True
   print "Caught an interrupt signal.  Cleaning up; this may take a few minutes,"
   print "as it will complete processing the logs that are currently open."
      
signal.signal(signal.SIGINT, signalHandler)
#===========================processFile()======================================

def processFile(filename):
   #Enable access to and check the status of the global stop flag - exit if True
   global gStop
   if gStop: return  
   global gNumFiles
   #global gCurlLock
   global gPrintLock
   global gIndex
   global gCurrentFile
   global gHeader
   global g_desiredFields
   global gRequiredFields
   
   #Declare all the local variables
   elastic_url = "http://localhost:9200/" + str(gIndex) + "/log/_bulk"
   fields = {}
   dateIndex = 1
   timeIndex = 2   
   count = 0
   json_result = ''

   #Chokepoint
   #Update the global progress counter
   with gCurrentFile.get_lock():
      gCurrentFile.value += 1

   #Chokepoint
   #Show the current log being processed
   with gPrintLock:    
      print "Processing file: {:<50} File #{} of {}".format(filename,gCurrentFile.value,gNumFiles)
      sys.stdout.flush()

   #If it's a tar.gz, try to open it with the tarfile library
   if filename.endswith(".tar.gz"):
      try: logfile = tarfile.open(filename,'r')

      except IOError as e:
         #Chokepoint
         with gPrintLock:
            print 'ERROR: In processFile(), cannot open ', file
            print 'Exception is:', e
            sys.stdout.flush()
            return          


   #Otherwise, it's likely just a plaintext file
   else:
      try: logfile = open(filename,'r')

      except IOError as e:
         #Chokepoint
         with gPrintLock:
            print 'ERROR: In processFile(), cannot open ', file
            print 'Exception is:', e
            sys.stdout.flush()
            return    

      #Opened file successfully
      #Grab the 4th line and strip the newline
      for i in range(0,4):
         line = logfile.readline().strip()

      #If the fourth line has the familiar '#Fields: Date, Time, ..." format, map each field to its index location
      if line.startswith("#Fields:"):
         line = line.split()
         for requiredField in gRequiredFields:
            if requiredField not in line:
               #Chokepoint
               with gPrintLock:
                  print 'Skipping ', filename, ' because it has no ', requiredField  , ' field.'
                  sys.stdout.flush()
                  logfile.close()
                  return

         #The minimum required fields are present, so iterate over the (split) header 
         #and map each desired field that is present to its index location
         #TODO Add regex parser here
         for index, field in enumerate(line):
            if field in g_desiredFields:
               #For each desired field present, map its new ELK field name to its index location
               fields[gLogToELKMapping[field]] = index

         dateIndex = fields.pop['date']
         timeIndex = fields.pop['time']
                  

      #If the familiar head is not present, skip this file, as we don't yet have logic to parse logs with no headers
      else:
         with gPrintLock:
            print 'Skipping file: ', filename, ' because it has no "#Fields..." header on the 4th line.'           
            sys.stdout.flush()
            logfile.close()
            return          

      #At the point the file has been sucessfully open and has the necessary 
      #fields to store in ELK - parse it line-by-line
      #Now for every entry
      for line in logfile:
          
         #Skip and additional comment fields
         if line.startswith("#"): continue
         #Split on white splace
         line = line.split()

         tmp_result += "{\"index\":{}}\n"
         tmp_result += "{\"time\" : \"" + str(line[dateIndex]) + "T" + str(line[timeIndex]) +"\","

         #Iterate over each known, desired field in the record
         for field in fields:
            if line[fields][field] == "-":
               temp_result += field + ' : \"\",'
            elif field == "cs-username": 
               temp_result +=  field + " : "+  line[fields][field].replace("\\", "\\\\") + "\","
            else:
               temp_result +=  field + " : "+  line[fields][field] + "\","

         temp_result += "}\n" 
         json_result += tmp_result
         count+=1
         #Assuming we don't DOS elastic, crank up this number for increased network performance
         #2000 seems to work well
         if count == 2000:
            count = 0
            #Curl data
            ret = requests.put(elastic_url, data=json_result, headers=gHeader)
            json_result = '\n'
#            Uncomment the lines below for offline testing
#            with gPrintLock:
#               print json_result
#               sys.stdout.flush()

            if (ret.status_code > 300) and (ret.status_code < 200):
               #Chokepoint
               with gPrintLock:   
                  print "Possible error curling JSON: "
                  print "Response code is: ", ret.status_code
                  #print "Response content:", ret.text
                  sys.stdout.flush()
                  logfile.close()
                  return
            
      #We might reach the end of the file with fewer than 200 lines in json_result, so
      #be sure to curl that remaining data prior to returning from this function
      #At a minimum json_result will be "\n" at this point, so if it's longer  
      if json_result != "\n":

         #Curl data
         ret = requests.put(elastic_url, data=json_result, headers=gHeader)

         #Print to console for testing
         #Remove the lines below for offline teseting        
#         with gPrintLock:
#            print "=========================================================="
#            print json_result
#            sys.stdout.flush()

         if (ret.status_code > 300) or (ret.status_code < 200):
            with gPrintLock:   
               print "Possible error curling JSON: "
               print "Response code is: ", ret.status_code
               #print "Response content:", ret.text
               sys.stdout.flush()
               logfile.close()
               return
         #print ret
         #print ret.text

      #json_result is empty, so be sure the close the log file prior to returning
      else:
         logfile.close()
         return

#==============================================================================
def usage(this_script ):
    print 'Usage: ' + this_script + ' <full index name> <directory of logs to send to elasticsearch>'
    print 'NOTE:  ' + this_script + ' currently only processes files with a ".log" file extension.'
#==============================================================================
def main(argv):

   #Conduct error and sanity checking
   #Ensure that 2 args were passed in
   this_script = str(sys.argv[0])
   if len(sys.argv) != 3:
      usage(this_script )
      sys.exit(1)

   index = sys.argv[1]

   #Ensure that the final argument is a directory
   log_dir = sys.argv[2]
   if not os.path.isdir(sys.argv[2]):
       print 'ERROR: ' + str(sys.argv[2]) + ' is not a directory.'
       usage(this_script)
       sys.exit(1)

   #Convert the log_dir path to an absolute path, rather than a (possibly) relative path
   log_dir = os.path.abspath(log_dir)

   #Declare variables
   #suffixes = ('.log')       #All files in the log_dir with these extensions will be processed
   files = []                 #With hold the list of files to send to elastic
   global gStop              #Flag used to terminate in case of SIGINT
   global gIndex             #Index name
   global gNumFiles
   gIndex = index

   #Debugging statements
   #print "log_dir: " + str(log_dir)
   #print "os.listdir(log_dir)[0:5]: " + str(os.listdir(log_dir)[5])
   #print "os.path.join(log_dir,f):" + str(os.path.join(log_dir,os.listdir(log_dir)[5]))

   #Populate list of log files
   for f in os.listdir(log_dir):
       path = os.path.join(log_dir,f)
       if os.path.isfile(path) and f.endswith(".log"):
           files.append(path) 
       else:
           print "Skipping non-.log file/directory:" , f
   #TODO Add support for other file extensions

   #Sort the files (Useful in case I need to terminate early.)
   files.sort()
   gNumFiles = len(files)
   n = mp.cpu_count()/2
   print 'About to process ' + str(len(files)) + ' files with',n,'cores (max).'  
   #for f in files:
   #   print f
   sys.stdout.flush()


   #Parallelize!
   #Only use half the cores - save the other half for Elastic
   n = mp.cpu_count()/2
   pool = mp.Pool(n)
   pool.map(processFile, files)
   pool.close()
   pool.join()

   if gStop:
      print "Program received interrupt signal.  Exiting."
   else: 
      print 'Done!'

#==============================================================================

if __name__ == '__main__':
   main(sys.argv)
