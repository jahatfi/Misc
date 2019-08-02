#include<stdio.h>

void usage(char *this_ex){
    printf("Project Euler Problem #1:\n");
    printf("Find the sum of all the multiples of 3 or 5 below N\n");
    printf("Pass N in via the command line as follows:\n");
    printf("%s <N>\n", this_ex);   
}


//This takes 1.7 seconds for n = 400000000
unsigned long long naive_sol(n){
    unsigned long long sum = 0;
    int i = 0;
    for(i = 0; i < n; i++){
        if(i % 3 == 0 || i % 5 == 0){
            sum += i;
        }
    }
    return sum;
}


//This takes .7 seconds for n = 400000000
unsigned long long naive_sol2(n){
    unsigned long long sum = 0;
    int i = 0;
    for(i = 0; i < n; i+=5){
        if (i % 3 != 0) sum += i;
    }
    for(i = 0; i < n; i+=3){
            sum += i;
    }
    return sum;
}

int main(int argc, char **argv){
    if(argc != 2){
        usage(argv[0]);
        return -1;
    }
    int n = atoi(argv[1]);
    printf("N is %d\n", n);

    if(n < 5){
        printf("Please use a value of n between 5 and 2,147,483,647.\n");
        return -1;
    }
    //printf("The sum is %lld\n", naive_sol(n));
    printf("The sum is %lld\n", naive_sol2(n));

    return 0;
}

