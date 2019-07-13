#include <stdio.h>
#include <math.h>

//Computes natural logarithm of x element-wise
//In tensorFlow only log with base e is used.

int main()
{
int size = 6;
float tensor1[6] = {1, 2, 3, 4, 5, 6};
// expected log values:
//array([[0.       , 0.6931472, 1.0986123],
//       [1.3862944, 1.609438 , 1.7917595]], dtype=float32)

for ( int i=0; i<size; i++){

    tensor1[i] = log(tensor1[i]);
    printf("%f\t",tensor1[i]);
}

}
