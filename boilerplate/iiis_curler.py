#!/usr/bin/python
#TODO Update the line below
#Date last updated: 27 Mar 2018

#NO7 Web logs
#Software: Microsoft Internet Information Services 7.0
#Version: 1.0
#Date: 2011-12-11 00:00:00
#Fields: date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip cs(User-Agent) sc-status sc-substatus sc-win32-status time-taken

#NO1 Web logs
#Software: Microsoft Internet Information Services 6.0
#Version: 1.0
#Date: 2008-02-14 15:28:35
#Fields: date time s-sitename s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip cs(User-Agent) sc-status sc-substatus sc-win32-status 

#NO1 HTTP Error logs
#Software: Microsoft HTTP API 1.0/2.0
#Version: 1.0
#Date: 2017-12-05 07:17:02
#Fields: date time c-ip c-port s-ip s-port cs-version cs-method cs-uri sc-status s-siteid s-reason s-queuename

#NO2 IIS Logs
#Software: Microsoft Internet Information Services 8.5
#Version: 1.0
#Date: 2017-09-17 00:00:00
#Fields: date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip cs(User-Agent) cs(Referer) sc-status sc-substatus sc-win32-status time-taken



import signal,sys,os,time,requests,errno,tarfile
import multiprocessing as mp
from subprocess import call
from subprocess import check_output
from cStringIO import StringIO

#Define globals
g_header = {"Content-Type": "application/json"}
g_index = ""
g_stop = False
g_curlLock = mp.Lock()
g_printLock = mp.Lock()
g_numFiles = 0
g_logformat = '#Fields: date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip cs(User-Agent) cs(Referer) sc-status sc-substatus sc-win32-status time-taken'

FNULL = open(os.devnull, 'w')
sCurrentFile = mp.Value('i', 0)


'''
#Use the dictionary below for NO1 HTTP error logs
g_iisMailField = {
  "date"           : 0,
  "time"           : 1,
  "c-ip"           : 2,    #Source IP
  "c-port"         : 3,
  "s-ip"           : 4,    #Dest IP
  "s-port"         : 5,
  "cs-version"     : 6,
  "cs-method"      : 7,
  "cs-uri"         : 8,
  "sc-status"      : 9 
  #"s-siteid"       :10,
  #"s-reason"       :11,
  #"s-queuename"    :12
}
'''

#Fields: date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip cs(User-Agent) cs(Referer) sc-status sc-substatus sc-win32-status time-taken
#Use the dictionary below for NO2 web logs

g_iisMailField = {
  "date"           : 0,
  "time"           : 1,
  "s-ip"           : 2,
  "cs-method"      : 3,
  "cs-uri-stem"    : 4,
  "cs-uri-query"   : 5,
  "s-port"         : 6,
  "cs-username"    : 7,
  "c-ip"           : 8, 
  "cs(User-Agent)" : 9,
  "cs(Referer)"    :10, 
  "sc-status"      :11, 
  "sc-substatus"   :12,
  "sc-win32-status":13,
  "time-taken"     :14
}


#Use the dictionary below for NO7 web logs
'''
g_iisMailField = {
  "date"           : 0,
  "time"           : 1,
  "s-ip"           : 3,
  "cs-method"      : 4,
  "cs-uri-stem"    : 5,
  "cs-uri-query"   : 6,
  "s-port"         : 7,
  "cs-username"    : 8,
  "c-ip"           : 9, 
  "cs(User-Agent)" :10,
  "sc-status"      :11, 
  "sc-substatus"   :12,
  "sc-win32-status":13,
  "time-taken"     :14
}
'''

#===========================signalHandler()====================================
def signalHandler(signal, frame):
   global g_stop 
   g_stop = True
   print "Caught an interrupt signal.  Cleaning up; this may take a few minutes,"
   print "as it will complete processing the logs that are currently open."
      
signal.signal(signal.SIGINT, signalHandler)
#===========================processFile()======================================

def processFile(filename):
   global g_stop
   if g_stop: return
   
   global g_numFiles
   global g_curlLock
   global g_printLock
   global g_index
   global sCurrentFile
   global g_header
   global g_iisMailField
   
   elastic_url = "http://localhost:9200/" + str(g_index) + "/log/_bulk"

   #json_result = ''
   

   with sCurrentFile.get_lock(), g_printLock:
      sCurrentFile.value += 1
      print "Processing file: {:<50} File #{} of {}".format(filename,sCurrentFile.value,g_numFiles)
      sys.stdout.flush()

   if logfile.endswith(".tar.gz"):
      try: logfile = tarfile.open(filename,'r')

      except IOError:
         print 'cannot open', arg
      
    #TODO Check if tar file, otherwise, simply open as a normal plaintext file
    #TODO move everything  below this to an else statement; add and except for error handling
    #TODO Don't foget to close the file!

      #Opened file successfully
      
      
      #Grab the 4th line and strip the newline
      for i in range(0,4):
         line = logfile.readline().strip()

      #If it's the same as g_logformat, then this is an exchange log.  Otherwise, return False (indicates error)
      if line != g_logformat:
         with g_printLock:
            print 'Unrecognized header in ' + str(filename) + '\nHEADER: ' + line + '\nSkipping ' + str(filename)
            print "EXPECTED", g_logformat
            sys.stdout.flush()
            return 
      #Reset the count
      count = 0
      #Now for every entry
      for line in logfile:
         if count == 0:
            json_result = '\n'

            
         #Skip comment fields
         if line.startswith("#"): continue
         #Split on white splace
         line = line.split()
         #TODO Ensure proper # of fields 
         if len(line) != 15:
            with g_printLock: 
               print "Missing or extra fields in line:",line 
               sys.stdout.flush()
               continue

         #Empty fields are denoted as "-", but Elastic prefers the empty string
         #TODO Remove this - it's slow
         for i in range(len(line)):
            if line[i] == "-":
               line[i] = ""
         '''
         if line[5] == "-":
            line[5] = ""
         if line[7] == "-":
            line[7] = ""
         #Escape the escape character '\'
         elif line[7].__contains__("\\"):   #username field
            line[7] = line[7].replace("\\","\\\\")
         '''

         #TODO Rather than hard code these fields, have the user select an existing dictionary to use or
         #create a new one, then iterate over the keys in the dictionary and parse the logs with those mappings
         #TODO Note that some fields (e.g. time,date) require different parsing, so remove them from the dictionary
         #and handle them first, then loop over and handle the rest of the dictionary
         #e.g.:
         #for item in dictionary:
         #   json_result += Key, line[value]

         json_result += "{\"index\":{}}"   + '\n'
         json_result += "{\"time\" : \"" + str(line[g_iisMailField["date"]]) + "T" + str(line[g_iisMailField["time"]]) +"\","
         json_result += "\"dest_ip\" : \"" + str(line[g_iisMailField["s-ip"]].split("%")[0]) +"\"," 
         json_result += "\"cs_method\" : \"" + str(line[g_iisMailField["cs-method"]]) +"\","
         json_result += "\"cs_uri_stem\" : \"" + str(line[g_iisMailField["cs-uri-stem"]]) +"\","
         json_result += "\"cs_uri_query\" : \"" + str(line[g_iisMailField["cs-uri-query"]]) +"\"," 
         json_result += "\"dest_port\" :  \"" + str(line[g_iisMailField["s-port"]]) +"\","
         json_result += "\"cs_username\" : \"" + str(line[g_iisMailField["cs-username"]]) +"\","
         json_result += "\"source_ip\" :\"" + str(line[g_iisMailField["c-ip"]]) +"\","
         json_result += "\"cs(User-Agent)\" : \"" + str(line[g_iisMailField["cs(User-Agent)"]]) +"\","
         json_result += "\"cs(Referer)\" : \"" + str(line[g_iisMailField["cs(Referer)"]]) +"\","
         json_result += "\"sc_status\" :  \"" + str(line[g_iisMailField["sc-status"]]) +"\","
         #json_result += "\"sc_substatus\" :  \"" + str(line[g_iisMailField["sc-substatus"]]) +"\","
         #json_result += "\"sc_win32-status\" : \"" + str(line[12]) +"\","
         json_result += "\"time_taken\" : \"" + str(line[g_iisMailField["time-taken"]]) +"\"}"        

         count+=1
         #Assuming we don't DOS elastic, crank up this number for increased network performance
         #2000 seems to work well
         if count == 2000:
            count = 0
            json_result += '\n'
            #Curl data
            ret = requests.put(elastic_url, data=json_result, headers=g_header)

            #print ret   
            #Print to console for testing
            #TODO Remove once curl is verified to work
#            with g_printLock:
#               print json_result
#               sys.stdout.flush()

            if (ret.status_code > 300) and (ret.status_code < 200):
               with g_printLock:   
                  print "Possible error curling JSON: "
                  print "Response code is: ", ret.status_code
                  #print "Response content:", ret.text
                  sys.stdout.flush()
                  logfile.close()
                  return
            
         else:
            json_result += '\n'
         
      #We might reach the end of the file with fewer than 200 lines in json_result, so
      #be sure to curl that remaining data prior to returning from this function
      #I used 10 as an arbitrary # to check if it has data, as at a minimum json_result will
      # be "[\n,\n" at this point, but if it is that short string, do nothing      
      if len(json_result) > 10:
         #Close the list
         json_result += '\n'
         #Curl data
         ret = requests.put(elastic_url, data=json_result, headers=g_header)

         #Print to console for testing
         #TODO Remove once curl is verified to work         
#         with g_printLock:
#            print "=========================================================="
#            print json_result
#            sys.stdout.flush()

         if (ret.status_code > 300) or (ret.status_code < 200):
            with g_printLock:   
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
 #=============================================================================
         '''print json.dumps(data_list)# print json.dumps(data_list, sort_keys=True, indent=0)
         while (len(data_list) < 201):
            data_list.append(index_string)
            count = count + 1
            data_list.append(json_result)
            count = count + 1 
            ret = 0
            if (len(data_list) == 200):
                                                                
               ret = call(["curl", "-XPUT","-H","http://X.X.X.X:9200/" +str(g_index)+ "/log/_bulk", "-d", str(data_list)], stderr=FNULL,stdout=FNULL) 
               if ret != 0:
                                        
                  with g_printLock:   
                     print "Error curling JSON: " + str(data_list) + "   Return value is",ret
                     sys.stdout.flush()
                     return
               count = 0
            '''
#============================================================================
      
   except IOError as e:
      result = False
      if e == errno.EACCES:
         with g_printLock:
            print 'Error opening ', filename
            sys.stdout.flush()
      else: 
         with g_printLock:
            print 'Unknown error encountered while opening ',filename
            print "EXCEPTION: ",e
            sys.stdout.flush()
#==============================================================================
def usage(this_script ):
         print 'Usage: ' + this_script + ' <full index name> <directory of logs to send to elasticsearch>'
#==============================================================================
def main(argv):

   #Conduct error and sanity checking
   #Ensure that 2 args were passed in
   this_script = str(sys.argv[0])
   if len(sys.argv) != 3:
      usage(this_script )
      sys.exit(1)

   #Ensure the index provided actually exists
   index = sys.argv[1]
#   indices =  check_output(["curl", "-XGET", "http://X.X.X.X:9200/_cat/indices?v"])
#   if index not in indices: 
#      print "The index: " + str(index) + " does not exist"
#      print "Type 'curl -XGET http://X.X.X.X:9200/_cat/indices?v' in a terminal to see all indices"
#      print "Hint: Do NOT include a trailing backslash."
#      sys.exit(1)

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
   global g_stop              #Flag used to terminate in case of SIGINT
   global g_index             #Index name
   global g_numFiles
   g_index = index

   #Debugging statements
   #print "log_dir: " + str(log_dir)
   #print "os.listdir(log_dir)[0:5]: " + str(os.listdir(log_dir)[5])
   #print "os.path.join(log_dir,f):" + str(os.path.join(log_dir,os.listdir(log_dir)[5]))

   #Populate list of log files
   for f in os.listdir(log_dir):
       path = os.path.join(log_dir,f)
       if os.path.isfile(path) and f.endswith(".log"):
           files.append(path) 

   #Sort the files (Useful in case I need to terminate early.)
   files.sort()
   g_numFiles = len(files)
   print 'About to process ' + str(len(files)) + ' files'  
   #for f in files:
   #   print f
   sys.stdout.flush()

'''
   #Parallelize!
   #Only use half the cores - save the other half for Elastic
   n = mp.cpu_count()
   pool = mp.Pool(n/2)
   pool.map(processFile, files)
   pool.close()
   pool.join()
'''
   if g_stop:
      print "Program received interrupt signal.  Exiting."
   else: 
      print 'Done!'

#==============================================================================

if __name__ == '__main__':
   main(sys.argv)
