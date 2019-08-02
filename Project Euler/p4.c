#include<stdio.h>    //file/console I/O
#include<stdbool.h>  //boolean types
#include<stdlib.h>   //calloc()

/*A palindromic number reads the same both ways. The largest palindrome made from the product of two 2-digit numbers is 9009 = 91 × 99.
 *
 * Find the largest palindrome made from the product of two n-digit numbers.
 */



void usage(char *this_ex){
    printf("Project Euler Problem #4:\n");
    printf("Find the largest palindrome number of two n-digit numbers\n");
    printf("Pass N in via the command line as follows:\n");
    printf("%s <N>\n", this_ex);   
}


bool isPalindrome(int n){
    int temp = n;
    int digits = 0;
    int i = 0;
    char front = 'a';
    char back = 'b';
    char *numStr = NULL;
    //I need to know how many digits in n
    while(temp != 0){
        temp /= 10;
        digits++;
    }
    //Now allocate space for its string representation and the terminating null char
    numStr = (char*)malloc((digits+1)*sizeof(char));
    snprintf(numStr, digits+1, "%d", n);

    for(i = 0; i <= digits/2; i++){
        front = (char)numStr[i];
        back = (char)numStr[digits-1-i];
        printf(".");
        //printf("i: %d front: %c back: %c\n",i,front, back);
        if(front != back) return false;
    }
    //printf("It's a palindrome!\n");
    free(numStr);
    return true;
    
}

unsigned long long maxPalindrome(int n){
    char* numStr = calloc(n+1,sizeof(char));
    int num = 0;
    int i = 0;
    int j = 0;
    int first = 0;
    int second = 0;
    int largest = 0;
    int temp = 0;


    for(i = 0; i < n; i++) numStr[i] = '9';
    numStr[n] = '\0';
    num = atoi(numStr);
    free(numStr);
    printf("So the largest number (as an int) is %d\n", num);

    for(i = num; i > num/10; i--){
        for(j = i; j >= num/10; j--){
            temp = i*j;
            if(isPalindrome(temp)){
                printf("\nFound palindrome: %d * %d = %d\n", i, j, temp);
                if(temp > largest){
                    largest = temp;
                    first = i;
                    second = j;
                }           
            }
        }
    }

    return largest;
}

int main(int argc, char **argv){
    if(argc != 2){
        usage(argv[0]);
        return -1;
    }
    int n = strtoull(argv[1], NULL, 10);
    printf("N is %lld\n", n);

    if(n < 1){
        printf("Please use a value of n between 1 and 2^32 - 1.\n");
        return -1;
    }
    isPalindrome(n);
    //printf("The sum is %lld\n", naive_sol(n));
    printf("The largest palindrome is %lld\n", maxPalindrome(n));

    return 0;
}

