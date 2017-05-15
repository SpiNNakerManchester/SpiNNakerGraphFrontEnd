/* Code converted from shallow_base.f90 using F2C-ACC program. 
 * Manually replaced: 
 * - WRITE statements with printf
 * - MOD operator with % 
 * - system_clock with wtime
 * Fixed several of the array references which had x dimension as 1, 
 * instead of M_LEN. 
 * Fixed values set using d and e notation. 
 * (7 June 2011)
 ***************
 * 'Pure' C version developed by G.D Riley (UoM) (25 Jan 2012)
 * removed all ftocmacros
 * used sin and cos not sinf and cosf (since all data are floats)
 * needed to declare arrays +1 to cope with Fortran indexing
 * Compile:
 * gcc -O2 -c wtime.c
 * gcc -O2 -o sb shallow_base.c -lm wtime.o
 * May need to set 'ulimit -s unlimited' to run large problems (e.g. 512x512)
 * Results are consistent with Fortran version of the code
 *
 */ 

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#define MIN(x,y) ((x)>(y)?(y):(x))
#define MAX(x,y) ((x)>(y)?(x):(y))
#define TRUE 1
#define FALSE 0
#define ITMAX 7
#define L_OUT TRUE

extern float wtime();

int M;
int N;
int M_LEN;
int N_LEN;


//! Benchmark weather prediction program for comparing the
//! preformance of current supercomputers. The model is
//! based on the paper - The Dynamics of Finite-Difference
//! Models of the Shallow-Water Equations, by Robert Sadourny
//! J. Atm. Sciences, Vol 32, No 4, April 1975.
//!     
//! Code by Paul N. Swarztrauber, National Center for
//! Atmospheric Research, Boulder, Co,  October 1984.
//! Modified by Juliana Rew, NCAR, January 2006
//!
//! In this version, shallow4.f, initial and calculated values
//! of U, V, and P are written to a netCDF file
//! for later use in visualizing the results. The netCDF data
//! management library is freely available from
//! http://www.unidata.ucar.edu/software/netcdf
//! This code is still serial but has been brought up to modern
//! Fortran constructs and uses portable intrinsic Fortran 90 timing routines. 
//! This can be compiled on the IBM SP using:
//! xlf90 -qmaxmem=-1 -g -o shallow4 -qfixed=132 -qsclk=micro \
//! -I/usr/local/include shallow4.f -L/usr/local/lib32/r4i4 -l netcdf
//! where the -L and -I point to local installation of netCDF
//!     
//! Changes from shallow4.f (Annette Osprey, January 2010):
//! - Converted to free-form fortran 90.  
//! - Some tidying up of old commented-out code.   
//! - Explicit type declarations.
//! - Variables n, m, ITMAX and mprint read in from namelist. 
//! - Dynamic array allocation.
//! - Only write to netcdf at mprint timesteps.
//! - Don't write wrap-around points to NetCDF file.
//! - Use 8-byte reals.
//!
//! Further changes (Annette Osprey & Graham Riley, February 2011): 
//! - Remove unnecessary halo updates.
//! - Split loops to improve TLB access.
//! - Modify timers to accumulate loop times over whole run. 
//! - Remove old-style indentation. 
//!
//! Minimal serial version (26 May 2011)


static int float_to_int( float data){
    union { float x; int y; } cast_union;
    cast_union.x = data;


    return cast_union.y;
}

static int module(int x, int y){
    if (x < 0){
        x = y - abs(x);
    }
    return x % y;
}

int main(int argc, char **argv) {

  if (argc < 2){
     printf("no args sent, using defaults\n");
     M = 3;
     N = 3;

  }
  else{
    M = atoi(argv[1]);
    N = atoi(argv[2]);
  }

  M_LEN = M + 1;
  N_LEN = N + 1;
  
  // solution arrays
  float u[M_LEN][N_LEN],v[M_LEN][N_LEN],p[M_LEN][N_LEN];
  float unew[M_LEN][N_LEN],vnew[M_LEN][N_LEN],pnew[M_LEN][N_LEN];
  float uold[M_LEN][N_LEN],vold[M_LEN][N_LEN],pold[M_LEN][N_LEN];
  float cu[M_LEN][N_LEN],cv[M_LEN][N_LEN],z[M_LEN][N_LEN],h[M_LEN][N_LEN],psi[M_LEN][N_LEN];

  float dt,tdt,dx,dy,a,alpha,el,pi;
  float tpi,di,dj,pcf;
  float tdts8,tdtsdx,tdtsdy,fsdx,fsdy;

  int mnmin,ncycle;
  int i,j;
 
  // timer variables 
  float mfs100,mfs200,mfs300,mfs310;
  float t100,t200,t300;
  float tstart,ctime,tcyc,time,ptime;
  float t100i,t200i,t300i;
  float c1,c2;

  // ** Initialisations ** 

  // Note below that two delta t (tdt) is set to dt on the first
  // cycle after which it is reset to dt+dt.
  dt = 90.;

  tdt = dt;
 
  dx = 100000.;
  dy = 100000.;
  fsdx = 4. / dx;
  fsdy = 4. / dy;

  a = 1000000.;
  alpha = .001;

  el = N * dx;
  pi = M_PI;
  tpi = pi + pi;
  di = tpi / M;
  dj = tpi / N;
  pcf = pi * pi * a * a / (el * el);

  printf("dt %08x\n", float_to_int(dt));
  printf("tdt %08x\n", float_to_int(tdt));
  printf("dx %08x\n", float_to_int(dx));
  printf("dy %08x\n", float_to_int(dx));
  printf("fsdx %08x\n", float_to_int(fsdx));
  printf("fsdy %08x\n", float_to_int(fsdy));
  printf("a %08x\n", float_to_int(a));
  printf("alpha %08x\n", float_to_int(alpha));
  printf("el %08x\n", float_to_int(el));
  printf("pi %08x\n", float_to_int(pi));
  printf("tpi %08x\n", float_to_int(tpi));
  printf("di %08x\n", float_to_int(di));
  printf("dj %08x\n", float_to_int(dj));
  printf("pcf %08x\n", float_to_int(pcf));

  FILE *f = fopen("initial_constants.txt", "w");
  fprintf(f, "%08x \n",float_to_int(dt));
  fprintf(f, "%08x\n", float_to_int(tdt));
  fprintf(f, "%08x\n", float_to_int(dx));
  fprintf(f, "%08x\n", float_to_int(dx));
  fprintf(f, "%08x\n", float_to_int(fsdx));
  fprintf(f, "%08x\n", float_to_int(fsdy));
  fprintf(f, "%08x\n", float_to_int(a));
  fprintf(f, "%08x\n", float_to_int(alpha));
  fprintf(f, "%08x\n", float_to_int(el));
  fprintf(f, "%08x\n", float_to_int(pi));
  fprintf(f, "%08x\n", float_to_int(tpi));
  fprintf(f, "%08x\n", float_to_int(di));
  fprintf(f, "%08x\n", float_to_int(dj));
  fprintf(f, "%08x\n", float_to_int(pcf));
  tdts8 = tdt / 8.0;
  fprintf(f, "%08x\n", float_to_int(tdts8));
  tdtsdx = tdt / dx;
  fprintf(f, "%08x\n", float_to_int(tdtsdx));
  tdtsdx = tdt / dy;
  fprintf(f, "%08x\n", float_to_int(tdtsdy));
  float tdt2s8 = (tdt + tdt) / 8.0;
  fprintf(f, "%08x\n", float_to_int(tdt2s8));
  float tdt2sdx = (tdt + tdt) / dx;
  fprintf(f, "%08x\n", float_to_int(tdt2sdx));
  float tdt2sdy = ((tdt + tdt) / dy);
  fprintf(f, "%08x\n", float_to_int(tdt2sdy));

  fclose(f);


  // Initial values of the stream function and p
  for (i=0;i<M_LEN;i++) {
    for (j=0;j<N_LEN;j++) {
      float sinx = sin((i + .5) * di);
      float siny = sin((j + .5) * dj);
      float total = a * sinx * siny;
      printf("psi %d%d, sinx %20.16f siny %20.16f total %08x %f\n", i, j,
        sinx, siny, float_to_int(total), total);
      psi[i][j] = a * sinf((i + .5) * di) * sinf((j + .5) * dj);
      p[i][j] = pcf * (cosf(2. * (i) * di) + cosf(2. * (j) * dj)) + 50000.;
    }
  }
    
  // Initialize velocities
  for (i=0;i<M;i++) {
    for (j=0;j<N;j++) {
      u[i + 1][j] = -(psi[i + 1][j + 1] - psi[i + 1][j]) / dy;
      v[i][j + 1] = (psi[i + 1][j + 1] - psi[i][j + 1]) / dx;
    }
  }

  f = fopen("initial_u_before.txt", "w");
  FILE *raw = fopen("initial_u_before_float.txt", "w");
    if (f == NULL)
    {
        printf("Error opening initial u file!\n");
        exit(1);
    }
    if (raw == NULL)
    {
        printf("Error opening initial u raw file!\n");
        exit(1);
    }
    printf("\n initial elements of u\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d, %d, %08x \n",i, j, float_to_int(u[i][j]));
      fprintf(f, "%d,%d,%08x \n",i, j, float_to_int(u[i][j]));
      fprintf(raw, "%d,%d,%f \n", i, j, u[i][j]);
      }
    }
    fclose(f);
    fclose(raw);

    printf("before periodic");
   // print out bits for each atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("u neirgbhours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(u[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(u[i][abs((j+1) % N)]),
        float_to_int(u[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(u[abs((i -1) % M)][j]),
        float_to_int(u[i][j]),
        float_to_int(u[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(u[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(u[i][abs((j -1) % N)]),
        float_to_int(u[(i+1) % M][abs((j - 1) % N)]));
      }
   }

  printf("periodic stuff\n");
  // Periodic continuation
  for (j=0;j<N;j++) {
    printf("%d,%d -> %d,%d\n", 0, j, M, j);
    u[0][j] = u[M][j];
    printf("%d,%d -> %d,%d\n", 0, j + 1, M, j+1);
    v[M][j + 1] = v[0][j + 1];
  }
  for (i=0;i<M;i++) {
    printf("%d,%d -> %d,%d\n", i + 1, 0, i + 1, N);
    u[i + 1][N] = u[i + 1][0];
    printf("%d,%d -> %d,%d\n", i, N, i, 0);
    v[i][0] = v[i][N];
  }
  printf("%d,%d -> %d,%d\n", M, 0, 0, N);
  u[0][N] = u[M][0];
  printf("%d,%d -> %d,%d\n", 0, N, M, 0);
  v[M][0] = v[0][N];


  for (i=0;i<M_LEN;i++) {
    for (j=0;j<N_LEN;j++) {
      uold[i][j] = u[i][j];
      vold[i][j] = v[i][j];
      pold[i][j] = p[i][j];

      printf(" old u %d:%d is %x\n", i, j, float_to_int(uold[i][j]));
      printf(" old v %d:%d is %x\n", i, j, float_to_int(vold[i][j]));
      printf(" old p %d:%d is %x\n", i, j, float_to_int(pold[i][j]));
    }
  }
     
  // Print initial values
  if ( L_OUT ) {
    printf(" number of points in the x direction %d\n", N); 
    printf(" number of points in the y direction %d\n", M); 
    printf(" grid spacing in the x direction     %f\n", dx); 
    printf(" grid spacing in the y direction     %f\n", dy); 
    printf(" time step                           %f\n", dt); 
    printf(" time filter parameter               %f\n", alpha); 

    mnmin = MIN(M,N);
    printf(" initial elements of p\n");


    f = fopen("initial_p.txt", "w");
    raw = fopen("initial_p_float.txt", "w");
    if (f == NULL)
    {
        printf("Error opening initial p file!\n");
        exit(1);
    }
    if (raw == NULL)
    {
        printf("Error opening initial p raw file!\n");
        exit(1);
    }
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d,%d,%08x \n",i, j, float_to_int(p[i][j]));
      fprintf(f, "%d,%d,%08x \n",i, j, float_to_int(p[i][j]));
      fprintf(raw, "%d,%d,%f \n", i, j, p[i][j] );
      }
    }
    fclose(f);
    fclose(raw);



    f = fopen("initial_u.txt", "w");
    raw = fopen("initial_u_float.txt", "w");
    if (f == NULL)
    {
        printf("Error opening initial u file!\n");
        exit(1);
    }
    if (raw == NULL)
    {
        printf("Error opening initial u raw file!\n");
        exit(1);
    }
    printf("\n initial elements of u\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d, %d, %08x \n",i, j, float_to_int(u[i][j]));
      fprintf(f, "%d,%d,%08x \n",i, j, float_to_int(u[i][j]));
      fprintf(raw, "%d,%d,%f \n", i, j, u[i][j]);
      }
    }
    fclose(f);
    fclose(raw);



    f = fopen("initial_v.txt", "w");
    raw = fopen("initial_v_float.txt", "w");
    if (f == NULL)
    {
        printf("Error opening initial v file!\n");
        exit(1);
    }
    if (raw == NULL)
    {
        printf("Error opening initial v raw file!\n");
        exit(1);
    }
    printf("\n initial elements of v\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d, %d, %08x \n",i, j, float_to_int(v[i][j]));
      fprintf(f, "%d,%d,%08x \n",i, j, float_to_int(v[i][j]));
      fprintf(raw, "%d,%d,%f \n", i, j, v[i][j]);
      }
    }
    fclose(f);
    fclose(raw);

    f = fopen("initial_psi.txt", "w");
    raw = fopen("initial_psi_float.txt", "w");
    if (f == NULL)
    {
        printf("Error opening psi file!\n");
        exit(1);
    }
    if (raw == NULL)
    {
        printf("Error opening initial psi raw file!\n");
        exit(1);
    }
    printf("\n initial elements of psi\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d, %d, %08x \n",i, j, float_to_int(psi[i][j]));
      fprintf(f, "%d,%d, %08x \n",i, j, float_to_int(psi[i][j]));
      fprintf(raw, "%d,%d,%f \n", i, j, psi[i][j]);
      }
    }
    fclose(f);
    fclose(raw);
    printf("\n");
  }

  // Start timer
  tstart = wtime(); 
  time = 0.;
  t100 = 0.;
  t200 = 0.;
  t300 = 0.;

  printf("attempt %d, %d %d %d\n\n\n\n",
  -1 % 3, abs(-1 % 3), abs(-1) % 3, 1% 3);

  // print out bits for each atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("p neirgbhours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(p[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(p[i][abs((j+1) % N)]),
        float_to_int(p[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(p[abs((i -1) % M)][j]),
        float_to_int(p[i][j]),
        float_to_int(p[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(p[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(p[i][abs((j -1) % N)]),
        float_to_int(p[(i+1) % M][abs((j - 1) % N)]));

        printf(
        "%d,%d   %d,%d   %d,%d\n%d,%d    %d%d,   %d%d\n%d,%d    %d%d,   "
        "%d%d\n\n\n",
        module( i-1 , M), abs((j+1)) % N,
        i, abs((j+1)) % N,
        abs((i + 1) % M), abs((j + 1) % N),
        module(i -1, M), j,
        i, j,
        (i+1) % M, j,
        module(i-1, M), module(j-1, N),
        i, module(j-1, N),
        (i+1) % M, module(j -1, N));
      }
   }
   
   // print out bits for each atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("u neirgbhours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(u[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(u[i][abs((j+1) % N)]),
        float_to_int(u[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(u[abs((i -1) % M)][j]),
        float_to_int(u[i][j]),
        float_to_int(u[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(u[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(u[i][abs((j -1) % N)]),
        float_to_int(u[(i+1) % M][abs((j - 1) % N)]));
      }
   }
   
   // print out bits for each atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("v neirgbhours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(v[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(v[i][abs((j+1) % N)]),
        float_to_int(v[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(v[abs((i -1) % M)][j]),
        float_to_int(v[i][j]),
        float_to_int(v[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(v[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(v[i][abs((j -1) % N)]),
        float_to_int(v[(i+1) % M][abs((j - 1) % N)]));
      }
   }
   
   // print out bits for each atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("h neirgbhours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(h[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(h[i][abs((j+1) % N)]),
        float_to_int(h[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(h[abs((i -1) % M)][j]),
        float_to_int(h[i][j]),
        float_to_int(h[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(h[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(h[i][abs((j -1) % N)]),
        float_to_int(h[(i+1) % M][abs((j - 1) % N)]));
      }
   }
   
   // print out bits for eacz atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("z neirgbrours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(z[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(z[i][abs((j+1) % N)]),
        float_to_int(z[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(z[abs((i -1) % M)][j]),
        float_to_int(z[i][j]),
        float_to_int(z[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(z[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(z[i][abs((j -1) % N)]),
        float_to_int(z[(i+1) % M][abs((j - 1) % N)]));
      }
   }
   
   // print out bits for eaccu atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("cu neirgbrours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(cu[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(cu[i][abs((j+1) % N)]),
        float_to_int(cu[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(cu[abs((i -1) % M)][j]),
        float_to_int(cu[i][j]),
        float_to_int(cu[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(cu[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(cu[i][abs((j -1) % N)]),
        float_to_int(cu[(i+1) % M][abs((j - 1) % N)]));
      }
   }
   
    // print out bits for eaccv atom
  for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("cv neirgbrours for %d,%d\n", i, j);
        printf("%08x    %08x    %08x \n",
        float_to_int(cv[abs((i-1) % M)][abs((j+1) % N)]),
        float_to_int(cv[i][abs((j+1) % N)]),
        float_to_int(cv[abs((i + 1) % M)][abs((j + 1) % N)]));
        printf("%08x    %08x    %08x \n",
        float_to_int(cv[abs((i -1) % M)][j]),
        float_to_int(cv[i][j]),
        float_to_int(cv[(i+1) % M][j]));
        printf("%08x    %08x    %08x \n\n\n",
        float_to_int(cv[abs((i -1) % M)][abs((j -1) % N)]),
        float_to_int(cv[i][abs((j -1) % N)]),
        float_to_int(cv[(i+1) % M][abs((j - 1) % N)]));
      }
   }


  // ** Start of time loop ** 

  for (ncycle=1;ncycle<=ITMAX;ncycle++) {
    
    // Compute capital u, capital v, z and h
    c1 = wtime();  

    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        printf("cu %d, %d, %08x %08x %08x %f %f %f \n",
               i+1, j, float_to_int(p[i+1][j]), float_to_int(p[i][j]),
               float_to_int(u[i+1][j]), p[i + 1][j], p[i][j], u[i + 1][j]);
               float point5 = 0.5;
        cu[i + 1][j] = point5 * (p[i + 1][j] + p[i][j]) * u[i + 1][j];
      }
    }
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        float point5 = 0.5;
        cv[i][j + 1] = point5 * (p[i][j + 1] + p[i][j]) * v[i][j + 1];
      }
    }
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {

      float top_bit = fsdx * (v[i + 1][j + 1] - v[i][j + 1]) - fsdy * (u[i +
       1][j + 1] - u[i + 1][j]);
       float bottom = (p[i][j] + p[i + 1][j] + p[i + 1][j + 1] + p[i][j + 1]);

         printf(
         "z: %d, %d, %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x\n",
         i+1, j + 1, float_to_int(fsdx), float_to_int(v[i + 1][j + 1]),
         float_to_int(v[i][j + 1]), float_to_int(fsdy), float_to_int(u[i + 1][j + 1]),
         float_to_int(u[i + 1][j]), float_to_int(p[i][j]), float_to_int(p[i + 1][j]),
         float_to_int(p[i + 1][j + 1]), float_to_int(p[i][j + 1]),
         float_to_int(top_bit), float_to_int(bottom));

        z[i + 1][j + 1] =
        (fsdx * (v[i + 1][j + 1] - v[i][j + 1]) - fsdy * (u[i + 1][j + 1] - u[i + 1][j])) /
             (p[i][j] + p[i + 1][j] + p[i + 1][j + 1] + p[i][j + 1]);
      }
    }



    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        //printf(
        //  "%d, %d, %f %f %f %f %f %f %f %f %f\n",i, j, p[i][j], u[i + 1][j],
        //  u[i + 1][j], u[i][j],
        //  u[i][j], v[i][j + 1], v[i][j + 1], v[i][j], v[i][j]);

        float point25 = 0.25;
        h[i][j] = p[i][j] +point25 *
        (u[i + 1][j] * u[i + 1][j] +
         u[i][j] * u[i][j] +
         v[i][j + 1] * v[i][j + 1] +
         v[i][j] * v[i][j]);
      }
    }

      for (i=0;i<M_LEN;i++) {
    for (j=0;j<N_LEN;j++) {

      printf(" old u %d:%d is %x\n", i, j, float_to_int(uold[i][j]));
      printf(" old v %d:%d is %x\n", i, j, float_to_int(vold[i][j]));
      printf(" old p %d:%d is %x\n", i, j, float_to_int(pold[i][j]));
    }
  }


    printf("\n elements of cu before periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d cu %08x cu raw %f\n",
             i, j, ncycle, float_to_int(cu[i][j]), cu[i][j]);
      }
    }

    printf("\n elements of cv before periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d cv %08x cvraw %f \n",
             i, j, ncycle, float_to_int(cv[i][j]), cv[i][j]);
      }
    }

    printf("\n elements of h before periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d h %08x \n",i, j, ncycle, float_to_int(h[i][j]));
      }
    }

    printf("\n elements of z before periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d z %08x \n",i, j, ncycle, float_to_int(z[i][j]));
      }
    }


    c2 = wtime();  
    t100 = t100 + (c2 - c1); 

    // Periodic continuation
    for (j=0;j<N;j++) {
      cu[0][j] = cu[M][j];
      cv[M][j + 1] = cv[0][j + 1];
      z[0][j + 1] = z[M][j + 1];
      h[M][j] = h[0][j];
    }
    for (i=0;i<M;i++) {
      cu[i + 1][N] = cu[i + 1][0];
      cv[i][0] = cv[i][N];
      z[i + 1][0] = z[i + 1][N];
      h[i][N] = h[i][0];
    }
    cu[0][N] = cu[M][0];
    cv[M][0] = cv[0][N];
    z[0][0] = z[M][N];
    h[M][N] = h[0][0];

          for (i=0;i<M_LEN;i++) {
    for (j=0;j<N_LEN;j++) {

      printf(" old u %d:%d is %x\n", i, j, float_to_int(uold[i][j]));
      printf(" old v %d:%d is %x\n", i, j, float_to_int(vold[i][j]));
      printf(" old p %d:%d is %x\n", i, j, float_to_int(pold[i][j]));
    }
  }

     printf("\n elements of cu after periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d cu %08x cu raw %f\n",
             i, j, ncycle, float_to_int(cu[i][j]), cu[i][j]);
      }
    }

    printf("\n elements of cv after periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d cv %08x cvraw %f \n",
             i, j, ncycle, float_to_int(cv[i][j]), cv[i][j]);
      }
    }

    printf("\n elements of h after periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d h %08x \n",i, j, ncycle, float_to_int(h[i][j]));
      }
    }

    printf("\n elements of z after periodic\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d z %08x \n",i, j, ncycle, float_to_int(z[i][j]));
      }
    }

     
    // Compute new values u,v and p
    tdts8 = tdt / 8.;
    tdtsdx = tdt / dx;
    tdtsdy = tdt / dy;

    printf("tdts8 = %x \n", float_to_int(tdts8));
    printf("tdtsdx = %x \n", float_to_int(tdtsdx));
    printf("tdtsdy = %x \n", float_to_int(tdtsdy));

    c1 = wtime(); 

    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        unew[i + 1][j] = uold[i + 1][j] + tdts8 *
        (z[i + 1][j + 1] + z[i + 1][j]) *
        (cv[i + 1][j + 1] + cv[i][j + 1] + cv[i][j] + cv[i + 1][j])
        - tdtsdx * (h[i + 1][j] - h[i][j]);
        printf("u %d, %d, %x, %x, %x, %x, %x, %x, %x, %x, %x, %x, %x \n", i
        + 1,
         j, float_to_int(uold[i + 1][j]), float_to_int(tdts8), float_to_int
         (z[i + 1][j + 1]), float_to_int(z[i + 1][j]), float_to_int(cv[i +
         1][j + 1]), float_to_int(cv[i][j + 1]), float_to_int(cv[i][j]),
         float_to_int(cv[i + 1][j]), float_to_int(tdtsdx), float_to_int(h[i
         + 1][j]), float_to_int(h[i][j]));
      }
    }
printf("before vnew \n");
          for (i=0;i<M_LEN;i++) {
    for (j=0;j<N_LEN;j++) {

      printf(" old u %d:%d is %x\n", i, j, float_to_int(uold[i][j]));
      printf(" old v %d:%d is %x\n", i, j, float_to_int(vold[i][j]));
      printf(" old p %d:%d is %x\n", i, j, float_to_int(pold[i][j]));
    }
  }

    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        vnew[i][j + 1] = vold[i][j + 1] - tdts8 *
        (z[i + 1][j + 1] + z[i][j + 1]) *
        (cu[i + 1][j + 1] + cu[i][j + 1] + cu[i][j] + cu[i + 1][j]) -
        tdtsdy * (h[i][j + 1] - h[i][j]);

        float part1 = z[i + 1][j + 1] + z[i][j + 1];
        printf("part1 = %x\n", float_to_int(part1));
        float part2 =cu[i + 1][j + 1] + cu[i][j + 1] + cu[i][j] + cu[i + 1][j];
        printf("part2 = %x\n", float_to_int(part2));
        float part3 = h[i][j + 1] - h[i][j];
        printf("part3 = %x\n", float_to_int(part3));
        // x * y * z - a * b
        float part4 = tdts8 * part1 * part2 * part3;
        printf("part4 = %x\n", float_to_int(part4));
        float part5 = tdtsdy * part5;
        printf("part5 = %x\n", float_to_int(part5));
        float part6 = vold[i][j + 1] - part4;
        printf("part6 = %x\n", float_to_int(part6));
        float part7 = part6 - part5;
        printf("part7 = %x\n", float_to_int(part7));

        printf("v %d, %d, %x, %x, %x, %x, %x, %x, %x, %x, %x, %x, %x\n",
        i, j +1, float_to_int(vold[i][j + 1]), float_to_int(tdts8),
        float_to_int(z[i + 1][j + 1]), float_to_int(z[i][j + 1]),
        float_to_int(cu[i + 1][j + 1]), float_to_int(cu[i][j + 1]),
        float_to_int(cu[i][j]), float_to_int(cu[i + 1][j]), float_to_int
        (tdtsdy), float_to_int(h[i][j + 1]), float_to_int( h[i][j]));

        /*printf("vnew\n");
        printf("%d, %d, %g, %g, %g, %g, %g, %g, %g, %g, %g\n",
            i,j,vold[i][j + 1], z[i + 1][j + 1], z[i][j + 1], cu[i + 1][j + 1],
            cu[i][j + 1], cu[i][j], cu[i + 1][j], h[i][j + 1], h[i][j]);*/
      }
    }
        printf("before pnew \n");
          for (i=0;i<M_LEN;i++) {
    for (j=0;j<N_LEN;j++) {

      printf(" old u %d:%d is %x\n", i, j, float_to_int(uold[i][j]));
      printf(" old v %d:%d is %x\n", i, j, float_to_int(vold[i][j]));
      printf(" old p %d:%d is %x\n", i, j, float_to_int(pold[i][j]));
    }
  }

    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
        pnew[i][j] = pold[i][j] - tdtsdx * (cu[i + 1][j] - cu[i][j]) -
        tdtsdy * (cv[i][j + 1] - cv[i][j]);
        printf("pnew = %d, %d, %x, %x, %x, %x, %x, %x, %x,\n",
        i,j, float_to_int(pold[i][j]), float_to_int(tdtsdx), float_to_int
        (cu[i + 1][j]), float_to_int(cu[i][j]), float_to_int(tdtsdy),
        float_to_int(cv[i][j + 1]), float_to_int(cv[i][j]));
      }
    }

          for (i=0;i<M_LEN;i++) {
    for (j=0;j<N_LEN;j++) {

      printf(" old u %d:%d is %x\n", i, j, float_to_int(uold[i][j]));
      printf(" old v %d:%d is %x\n", i, j, float_to_int(vold[i][j]));
      printf(" old p %d:%d is %x\n", i, j, float_to_int(pold[i][j]));
    }
  }

    c2 = wtime();  
    t200 = t200 + (c2 - c1);

    printf("before preiodic thingy");

    printf(" elements of p for cycle %d\n", ncycle);
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d p %08x praw %f \n",
             i, j, ncycle, float_to_int(pnew[i][j]), pnew[i][j]);
      }
    }
    printf("\n elements of u\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d u %08x uraw %f \n",
             i, j, ncycle, float_to_int(unew[i][j]), unew[i][j]);
      }
    }

    printf("\n elements of v\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d v %08x vraw %f \n",
             i, j, ncycle, float_to_int(vnew[i][j]), vnew[i][j]);
      }
    }



    // Periodic continuation
    for (j=0;j<N;j++) {
      unew[0][j] = unew[M][j];
      vnew[M][j + 1] = vnew[0][j + 1];
      pnew[M][j] = pnew[0][j];
    }
    for (i=0;i<M;i++) {
      unew[i + 1][N] = unew[i + 1][0];
      vnew[i][0] = vnew[i][N];
      pnew[i][N] = pnew[i][0];
    }
    unew[0][N] = unew[M][0];
    vnew[M][0] = vnew[0][N];
    pnew[M][N] = pnew[0][0];

    printf("u, v, p after periodic continuation");

    printf(" elements of p for cycle %d\n", ncycle);
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d p %08x praw %f \n",
             i, j, ncycle, float_to_int(pnew[i][j]), pnew[i][j]);
      }
    }
    printf("\n elements of u\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d u %08x uraw %f \n",
             i, j, ncycle, float_to_int(unew[i][j]), unew[i][j]);
      }
    }

    printf("\n elements of v\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d v %08x vraw %f \n",
             i, j, ncycle, float_to_int(vnew[i][j]), vnew[i][j]);
      }
    }

    time = time + dt;

    // Time smoothing and update for next cycle
    if ( ncycle > 1 ) {

      c1 = wtime(); 

      for (i=0;i<M_LEN;i++) {
        for (j=0;j<N_LEN;j++) {
          uold[i][j] = u[i][j] + alpha * (unew[i][j] - 2. * u[i][j] + uold[i][j]);
        }
      }
      for (i=0;i<M_LEN;i++) {
        for (j=0;j<N_LEN;j++) {
          vold[i][j] = v[i][j] + alpha * (vnew[i][j] - 2. * v[i][j] + vold[i][j]);
        }
      }
      for (i=0;i<M_LEN;i++) {
        for (j=0;j<N_LEN;j++) {
          pold[i][j] = p[i][j] + alpha * (pnew[i][j] - 2. * p[i][j] + pold[i][j]);
        }
      }
      for (i=0;i<M_LEN;i++) {
        for (j=0;j<N_LEN;j++) {
          u[i][j] = unew[i][j];
        }
      }
      for (i=0;i<M_LEN;i++) {
        for (j=0;j<N_LEN;j++) {
          v[i][j] = vnew[i][j];
        }
      }
      for (i=0;i<M_LEN;i++) {
        for (j=0;j<N_LEN;j++) {
          p[i][j] = pnew[i][j];
        }
      }

      c2 = wtime(); 
      t300 = t300 + (c2 - c1);
     
    } else {
    printf("AHHHHH");
      tdt = tdt + tdt;

      for (i=0;i<M_LEN;i++) {
        for (j=0;j<N_LEN;j++) {
          uold[i][j] = u[i][j];
          vold[i][j] = v[i][j];
          pold[i][j] = p[i][j];
          u[i][j] = unew[i][j];
          v[i][j] = vnew[i][j];
          p[i][j] = pnew[i][j];
        }
      }

    }

    printf(" elements of p for cycle %d\n", ncycle);
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d p %08x praw %f \n",
             i, j, ncycle, float_to_int(pnew[i][j]), pnew[i][j]);
      }
    }
    printf("\n elements of u\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d u %08x uraw %f \n",
             i, j, ncycle, float_to_int(unew[i][j]), unew[i][j]);
      }
    }

    printf("\n elements of v\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d v %08x vraw %f \n",
             i, j, ncycle, float_to_int(vnew[i][j]), vnew[i][j]);
      }
    }

        printf("\n elements of cu\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d cu %08x cu raw %f\n",
             i, j, ncycle, float_to_int(cu[i][j]), cu[i][j]);
      }
    }

        printf("\n elements of cv\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d cv %08x cvraw %f \n",
             i, j, ncycle, float_to_int(cv[i][j]), cv[i][j]);
      }
    }

        printf("\n elements of h\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d h %08x \n",i, j, ncycle, float_to_int(h[i][j]));
      }
    }

        printf("\n elements of z\n");
    for (i=0;i<M;i++) {
      for (j=0;j<N;j++) {
      printf("%d:%d:%d z %08x \n",i, j, ncycle, float_to_int(z[i][j]));
      }
    }


    printf("\n");
  }

  // ** End of time loop ** 

  // Output p, u, v fields and run times.
  if (L_OUT) {
    ptime = time / 3600.;
    printf(" cycle number %d model time in hours %f\n", ITMAX, ptime);
    printf(" diagonal elements of p\n");
    for (i=0; i<mnmin; i++) {
      printf("%08x ", float_to_int(pnew[i][i]));
    }
    printf("\n diagonal elements of u\n");
    for (i=0; i<mnmin; i++) {
      printf("%08x ", float_to_int(unew[i][i]));
    }
    printf("\n diagonal elements of v\n");
    for (i=0; i<mnmin; i++) {
      printf("%08x ", float_to_int(vnew[i][i]));
    }
    printf("\n");

    mfs100 = 0.0;
    mfs200 = 0.0;
    mfs300 = 0.0;
    // gdr t100 etc. now an accumulation of all l100 time
    if ( t100 > 0 ) { mfs100 = ITMAX * 24. * M * N / t100 / 1000000; }
    if ( t200 > 0 ) { mfs200 = ITMAX * 26. * M * N / t200 / 1000000; }
    if ( t300 > 0 ) { mfs300 = ITMAX * 15. * M * N / t300 / 1000000; }

    c2 = wtime(); 
    ctime = c2 - tstart;
    tcyc = ctime / ITMAX;

    printf(" cycle number %d total computer time %f time per cycle %f\n", ITMAX, ctime, tcyc);
    printf(" time and megaflops for loop 100 %.6f %.6f\n", t100, mfs100);
    printf(" time and megaflops for loop 200 %.6f %.6f\n", t200, mfs200);
    printf(" time and megaflops for loop 300 %.6f %.6f\n", t300, mfs300);
  }

  return(0);
}
