#include <stdio.h>

int a[2][3] = {     // human readable tensor representation
    {1, 2, 3},
    {4, 5, 6}
    };

int b[3][2] = {     // human readable tensor representation
    {7, 8},
    {9, 10},
    {11, 12}
    };

int a_1[6] = {1, 2, 3, 4, 5, 6};     // shape = [2 ,3]
int b_1[6] = {7, 8, 9, 10, 11, 12};  // shape = [3, 2]

int main()
{
    int a_dim1 = 2; // rows of tensor a_1
    int a_dim2 = 3; // columns of tensor a_1

    int b_dim1 = 3; // rows of tensor b_1
    int b_dim2 = 2; // columns of tensor b_1

    int multiply[a_dim1*b_dim2]; // vector storing the result of multiplication
    int sum=0;
    int l = 0;

    for(int i=0; i<a_dim1; i++){       //iterates over the number of rows of matrix a
        for(int j=0; j<b_dim2; j++){   // iterates over the number of columns of matrix b
            for(int k=0; k<a_dim2; k++){  //iterates over the number of columns of matrix a
                sum += a_1[k+ a_dim2*i] * b_1[(k * b_dim2) + j];
            }
            multiply[l] = sum;
            printf(" multiply[%d] %d :\n", l, multiply[l]);
            sum=0;
            l++;
                }

    }
}




