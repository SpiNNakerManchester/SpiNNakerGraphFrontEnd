#include <stdio.h>
#include <math.h>


int main()
{
// Same shape
float tensor1[6] = {1, 2, 3, 4, 5, 6};     // shape = [2 ,3]
float tensor2[6] = {7, 8, 9, 10, 11, 12};  // shape = [2 ,3]
int size = 6;

for (int i=0; i<size; i++){
    tensor1[i] *= tensor2[i];
    printf("%f\t", tensor1[i]);
}
}
