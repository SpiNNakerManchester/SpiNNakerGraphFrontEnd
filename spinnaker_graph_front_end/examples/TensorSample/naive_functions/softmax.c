
#include <stdio.h>
#include <math.h>



int main()
{


float t[2][3] = {     // human readable tensor representation
    {1, 2, 3},
    {4, 5, 6}
    };

float tensor1[6] = {1, 2, 3, 4, 5, 6};     // shape = [2 ,3]
int shape[2] = {2, 3};
float normal_exp[6];

float tensor2[7] = {1, 2, 3, 4, 1, 2, 3};     // shape = [1 ,7]
int shape2[2] = {1, 7};
float sum_exp_row[shape2[0]];

//1, 2, 3, 4, 1, 2, 3
//[0.024, 0.064, 0.175, 0.475, 0.024, 0.064, 0.175]

for (int i=0; i<shape2[0]; i++){
    for (int k=0; k<shape2[1]; k++){
        printf("%f \n",tensor2[k+i*shape2[1]]);
        printf("%f \n",exp(tensor2[k+i*shape2[1]]));

        sum_exp_row[i]+= exp(tensor2[k+i*shape2[1]]);
    }
    printf("sum of row is %f \n",sum_exp_row[i]);
}

for (int i=0; i<shape2[0]; i++){
    for (int j=0; j<shape2[1]; j++){
            normal_exp[i] = exp(tensor2[j+i*shape2[1]])/ sum_exp_row[i];
            printf("normal_exp %d : %f \n",i, normal_exp[i]);
        }
}

}
