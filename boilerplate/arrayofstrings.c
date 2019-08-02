#include<stdio.h>
#include<stdlib.h>
#include<string.h>

/*
This code serves as boiler plate for an array of variable-length strings.
Obviously, it could be modified for an array of any variable-length object.
As written, it memory safe, using both secure functions for string operations
as well as freeing all memory - as shown by valgrind.
*/


/*Usage - Only 1 argument - the number of strings to accept*/
void usage(char **argv){
   printf("Usage: %s <# of strings to accept>\n", argv[0]);
   exit(1);
}

int main(int argc, char** argv){
  if(argc != 2) usage(argv);
  char *buff;
  char **stringArray;
  int i = 0;
  int numStrings = atoi(argv[1]);
  int len;

  /*Initialize and array of character pointers to hold the strings*/
  stringArray = (char **)malloc(numStrings * sizeof(char *));
  /*Initialize a temp buffer to hold the incoming strings*/
  buff = (char *)malloc(1000*sizeof(char));

  printf("Buff has size %lu\n", sizeof(buff));

  /*Prompt user for N strings*/
  printf("Please give me %d strings:\n", numStrings);
  /*Iterate N times, asking for a string each time*/
  for(i = 0; i < numStrings; i++)
  { 
     printf("String #%i\n", i+1);
     /*Store the string in the temp buffer*/
     if(fgets(buff, 1000, stdin) != NULL){
       /*Find the len of the string, to include the null terminating character*/
       len = strlen(buff);
       buff[len-1] = '\0';
       printf("Len of %s is %i\n", buff, len);
       /*If successful, dynamically allocate memory for the string in the array*/
       stringArray[i] = (char *)malloc(len*sizeof(char)); 
       strncpy(stringArray[i], buff, len);
     }
  } 

  printf("*********************************************************\n");
  printf("Here's a log of the strings you provided:\n");
  for(i = 0; i < numStrings; i++)
  {
     printf("%s\n", stringArray[i]);
  }
  printf("*********************************************************\n");
  printf("Now free all the memory...\n");
  for(i = 0; i < numStrings; i++)
  {
     free(stringArray[i]);
  }
  free(stringArray);
  free(buff);
  printf("Done!\n");
  return 0;

}
