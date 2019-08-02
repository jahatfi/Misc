#include<stdio.h>    //file/console I/O
#include<stdbool.h>  //boolean types
#include<stdlib.h>   //calloc()
/*
The prime 41, can be written as the sum of six consecutive primes:

41 = 2 + 3 + 5 + 7 + 11 + 13
This is the longest sum of consecutive primes that adds to a prime below one-hundred.

The longest sum of consecutive primes below one-thousand that adds to a prime, contains 21 terms, and is equal to 953.

Which prime, below one-million, can be written as the sum of the most consecutive primes?
*/

void usage(char *this_ex){
    printf("Project Euler Problem #50:\n");
    printf("Find the largest prime less than N that is a sum of consecutive primes.\n");
    printf("Pass N in via the command line as follows:\n");
    printf("%s <N>\n", this_ex);   
}

bool isPrime(unsigned long long n){


unsigned long long naive_sol(unsigned long long n){
    printf("n: %lld, n/2: %lld\n", n, n/2);
    //Define a array of ints to hold the Sieve of Erethenes
    n = n/2;
    int *sieve = calloc(n/1000, sizeof(int));
    sieve[0] = 2;   
    int sieveIdx = 0;
    int i = 0;
    int j = 0;
    bool isPrime = false;
    unsigned long long sum = 0;

    for(i = 3; i <= n; i++){
        //printf("Checking if %d is prime.\n", i);
        //printf("Sieve: ");
        //for(j = 0; j <= sieveIdx; j++) printf(" %d ",sieve[j]);
        //printf("\n");
        //Reset the isPrime flag.
        isPrime = true;
        for(j = 0; j <= sieveIdx; j++){
            if(i % sieve[j] == 0){
                //printf("%d is divisible by %d.\n", i,sieve[j]);
                isPrime = false;
                break;
            }
        }
        if(isPrime){
           printf("%d is prime!\n", i);
           sieveIdx += 1;
           sum += i;
           //printf("Adding %d to sieve at sieve index %d\n", i, sieveIdx); 
           sieve[sieveIdx] = i;
        }
    }
    i  =  sieve[sieveIdx];
    free(sieve);
    return i;
}

int main(int argc, char **argv){
    if(argc != 2){
        usage(argv[0]);
        return -1;
    }
    unsigned long long n = strtoull(argv[1], NULL, 10);
    printf("N is %lld\n", n);

    if(n < 1){
        printf("Please use a value of n between 1 and 2^64-1.\n");
        return -1;
    }
    //printf("The sum is %lld\n", naive_sol(n));
    printf("The max prime is %lld\n", naive_sol(n));

    return 0;
}

