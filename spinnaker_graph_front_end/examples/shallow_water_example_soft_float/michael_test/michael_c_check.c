
#include <stdio.h>
#include <limits.h>
#include <math.h>


int main()
{
   double x;
   unsigned int i;

   for ( i = 0; i < 1001; i++ ) {

      x = i / 300.0;

   	printf(" %d %17.13f %17.13f %17.13f %17.13f %17.13f %17.13f \n", i, x, sin(x), cos(x), tan(x), log(x), exp(x) );

      }
    printf(" %20.16f  %20.16f \n", M_PI, sin(M_PI));

   return 0;
}