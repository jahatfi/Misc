#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<dirent.h>

/*
This code serves as boiler plate for an array of variable-length strings.
Obviously, it could be modified for an array of any variable-length object.
As written, it memory safe, using both secure functions for string operations
as well as freeing all memory - as shown by valgrind.
*/


//=============================================================================
int getNumFilesInDir(char *path)
{
  int file_count = 0;
  DIR * dirp;
  struct dirent * entry;

  dirp = opendir(path); 
  if(dirp == NULL) return 0;

  while ((entry = readdir(dirp)) != NULL) {
    /* If the entry is a regular file */
    //if (entry->d_type == DT_REG) {
    file_count++;
    }
  //}
  closedir(dirp);
  return file_count-2;
}

//=============================================================================
int getDirListing(char * dir, char **stringArray, int *index)
{
  DIR *dp;
  struct dirent *ep;
  int fileLen = 0;     
  dp = opendir (dir);


  if (dp != NULL)
  {
    while ( ep = readdir(dp))
      //if(ep->d_type == DT_REG)
    { 
        if( ( strcmp(ep->d_name, ".") == 0) || strcmp(ep->d_name, "..") == 0)
           continue;
        //printf("Prior to adding %s, index is %i\n", ep->d_name, *index);
        fileLen = strlen(ep->d_name);
        //printf("Filename Length: %i\n",fileLen);
        stringArray[*index] = (char*)malloc(fileLen*sizeof(char));
        strncpy(stringArray[(*index)], ep->d_name, fileLen); 
        (*index)++;
    }
    (void) closedir (dp);
  }
  else
    perror ("Couldn't open the directory");

  return 0;
}


//=============================================================================
/*Usage - Only 1 argument - the number of strings to accept*/
void usage(char **argv){
   printf("Usage: %s <# of strings to accept>\n", argv[0]);
   exit(1);
}
//=============================================================================
int main(){
  char **stringArray;
  int i = 0;
  int len;
  int totalFiles = 0;
  int *saIndex;  //Pointer to an int that represents the first empty slot in stringArray
  *saIndex = 0;

  totalFiles = getNumFilesInDir("/bin/");
  totalFiles += getNumFilesInDir("/sbin/");
  printf("Total files: %i\n", totalFiles);

  /*Initialize and array of character pointers to hold the strings*/
  stringArray = (char **)malloc(totalFiles * sizeof(char *));
  getDirListing("/bin", stringArray, saIndex);
  getDirListing("/sbin", stringArray, saIndex);
  printf("----------------------------------------------------------\n");
  //for(i = 0; i < totalFiles; i++) printf("%s\n", stringArray[i]);

  printf("----------------------------------------------------------\n");
  printf("Now free all the memory...\n");
  for(i = 0; i < totalFiles; i++)
  {
     free(stringArray[i]);
  }
  free(stringArray);
  printf("Done!\n");
  return 0;

}
