#include<stdio.h>    //file/console I/O
#include<stdbool.h>  //boolean types
#include<stdlib.h>   //calloc()
#include<math.h>
/*The prime factors of 13195 are 5, 7, 13 and 29.
 *
 * What is the largest prime factor of the number 600851475143 ?
 */

void usage(char *this_ex){
    printf("Project Euler Problem #3:\n");
    printf("Find the largest prime factor of N\n");
    printf("Pass N in via the command line as follows:\n");
    printf("%s <N>\n", this_ex);   
}


unsigned long long naive_sol(unsigned long long n){
    //Define a array of ints to hold the Sieve of Erethenes
    int sieveSize = 5;
    int *sieve = calloc(sieveSize, sizeof(int));

    sieve[0] = 2;   
    int sieveIdx = 0;
    int i = 0;
    int j = 0;
    bool isPrime = false;

    printf("2 is prime!\n");

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
           if( sieveIdx == sieveSize){
                printf("Sieve could only hold %d elements, so now we have to double it!\n", sieveSize);
                sieveSize *= 2;
                sieve = realloc(sieve, sieveSize*sizeof(int));
           }
           //printf("Adding %d to sieve at sieve index %d\n", i, sieveIdx); 
           sieve[sieveIdx] = i;
        }
    }
    i  =  sieve[sieveIdx];
    printf("CumSum is %s\n", cumSumArray(&sieve[0], sieveIdx));
    free(sieve);
    return i;
}

int cumSumArray(int *array, int size){
    int sum = 0;
    int i = 0;
    for(i = 0; i < size; i++) sum+=array[i];
    return sum;
}

unsigned long long naive_sol2(unsigned long long n){
    printf("n: %lld, n/2: %lld\n", n, n/2);
    //Define a array of ints to hold the Sieve of Erethenes
 
    int i = 0;
    int maxFactor = 0;
    while(n){
        printf("n: %lld\n",n);
        for(i = 2; i <= n/2; i++){
           if(n % i == 0){
              printf("%lld is divisible by %d\n",n,i);
              n /= i;
              if(i > maxFactor) maxFactor = i;
              break;
           }   
           else if(i == n/2){
              if( n > maxFactor) return n;  
           }
        }   
    } 
    return maxFactor;
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

