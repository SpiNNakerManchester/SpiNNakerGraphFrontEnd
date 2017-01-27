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
 * used sin and cos not sinf and cosf (since all data are doubles)
 * needed to declare arrays +1 to cope with Fortran indexing
 * Compile:
 * gcc -O2 -c wtime.c
 * gcc -O2 -o sb shallow_base-f-style.c -lm wtime.o
 * May need to set 'ulimit -s unlimited' to run large problems (e.g. 512x512)
 * Results are consistent with Fortran version of the code
 *
 * TO DO: 
 *  - fix array declarations and loop bounds for C (0 to <N style)
 *  - reverse i and j loops for stride 1 in C (not F!)
 *
 */ 

#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define MIN(x,y) ((x)>(y)?(y):(x))
#define MAX(x,y) ((x)>(y)?(x):(y))

#define TRUE 1
#define FALSE 0
#define M 64
#define N 64
#define M_LEN M + 1
#define N_LEN N + 1
#define ITMAX 4000
#define L_OUT TRUE

extern double wtime(); 


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

int main(int argc, char **argv) {
  
  // solution arrays
  double u[M_LEN+1][N_LEN+1],v[M_LEN+1][N_LEN+1],p[M_LEN+1][N_LEN+1];
  double unew[M_LEN+1][N_LEN+1],vnew[M_LEN+1][N_LEN+1],pnew[M_LEN+1][N_LEN+1];
  double uold[M_LEN+1][N_LEN+1],vold[M_LEN+1][N_LEN+1],pold[M_LEN+1][N_LEN+1];
  double cu[M_LEN+1][N_LEN+1],cv[M_LEN+1][N_LEN+1],z[M_LEN+1][N_LEN+1],h[M_LEN+1][N_LEN+1],psi[M_LEN+1][N_LEN+1];

  double dt,tdt,dx,dy,a,alpha,el,pi;
  double tpi,di,dj,pcf;
  double tdts8,tdtsdx,tdtsdy,fsdx,fsdy;

  int mnmin,ncycle;
  int i,j;
 
  // timer variables 
  double mfs100,mfs200,mfs300,mfs310;
  double t100,t200,t300;
  double tstart,ctime,tcyc,time,ptime;
  double t100i,t200i,t300i;
  double c1,c2;

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
  pi = 4. * atanf(1.);
  tpi = pi + pi;
  di = tpi / M;
  dj = tpi / N;
  pcf = pi * pi * a * a / (el * el);

  // Initial values of the stream function and p
  for (j=1;j<=N_LEN;j++) {
    for (i=1;i<=M_LEN;i++) {
      psi[i][j] = a * sin((i - .5) * di) * sin((j - .5) * dj);
      p[i][j] = pcf * (cos(2. * (i - 1) * di) + cos(2. * (j - 1) * dj)) + 50000.;
    }
  }
    
  // Initialize velocities
  for (j=1;j<=N;j++) {
    for (i=1;i<=M;i++) {
      u[i + 1][j] = -(psi[i + 1][j + 1] - psi[i + 1][j]) / dy;
      v[i][j + 1] = (psi[i + 1][j + 1] - psi[i][j + 1]) / dx;
    }
  }
     
  // Periodic continuation
  for (j=1;j<=N;j++) {
    u[1][j] = u[M + 1][j];
    v[M + 1][j + 1] = v[1][j + 1];
  }
  for (i=1;i<=M;i++) {
    u[i + 1][N + 1] = u[i + 1][1];
    v[i][1] = v[i][N + 1];
  }
  u[1][N + 1] = u[M + 1][1];
  v[M + 1][1] = v[1][N + 1];
  for (j=1;j<=N_LEN;j++) {
    for (i=1;i<=M_LEN;i++) {
      uold[i][j] = u[i][j];
      vold[i][j] = v[i][j];
      pold[i][j] = p[i][j];
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
    printf(" initial diagonal elements of p\n");
    for (i=1; i<=mnmin; i++) {
      printf("%f ",p[i][i]);
    }
    printf("\n initial diagonal elements of u\n");
    for (i=1; i<=mnmin; i++) {
      printf("%f ",u[i][i]);
    }
    printf("\n initial diagonal elements of v\n");
    for (i=1; i<=mnmin; i++) {
      printf("%f ",v[i][i]);
    }
    printf("\n");
  }

  // Start timer
  tstart = wtime(); 
  time = 0.;
  t100 = 0.;
  t200 = 0.;
  t300 = 0.;

  // ** Start of time loop ** 

  for (ncycle=1;ncycle<=ITMAX;ncycle++) {
    
    // Compute capital u, capital v, z and h
    c1 = wtime();  

    for (j=1;j<=N;j++) {
      for (i=1;i<=M;i++) {
        cu[i + 1][j] = .5 * (p[i + 1][j] + p[i][j]) * u[i + 1][j];
      }
    }
    for (j=1;j<=N;j++) {
      for (i=1;i<=M;i++) {
        cv[i][j + 1] = .5 * (p[i][j + 1] + p[i][j]) * v[i][j + 1];
      }
    }
    for (j=1;j<=N;j++) {
      for (i=1;i<=M;i++) {
        z[i + 1][j + 1] = (fsdx * (v[i + 1][j + 1] - v[i][j + 1]) - fsdy * (u[i + 1][j + 1] - u[i + 1][j])) / (p[i][j] + p[i + 1][j] + p[i + 1][j + 1] + p[i][j + 1]);
      }
    }
    for (j=1;j<=N;j++) {
      for (i=1;i<=M;i++) {
        h[i][j] = p[i][j] + .25 * (u[i + 1][j] * u[i + 1][j] + u[i][j] * u[i][j] + v[i][j + 1] * v[i][j + 1] + v[i][j] * v[i][j]);
      }
    }

    c2 = wtime();  
    t100 = t100 + (c2 - c1); 

    // Periodic continuation
    for (j=1;j<=N;j++) {
      cu[1][j] = cu[M + 1][j];
      cv[M + 1][j + 1] = cv[1][j + 1];
      z[1][j + 1] = z[M + 1][j + 1];
      h[M + 1][j] = h[1][j];
    }
    for (i=1;i<=M;i++) {
      cu[i + 1][N + 1] = cu[i + 1][1];
      cv[i][1] = cv[i][N + 1];
      z[i + 1][1] = z[i + 1][N + 1];
      h[i][N + 1] = h[i][1];
    }
    cu[1][N + 1] = cu[M + 1][1];
    cv[M + 1][1] = cv[1][N + 1];
    z[1][1] = z[M + 1][N + 1];
    h[M + 1][N + 1] = h[1][1];
     
    // Compute new values u,v and p
    tdts8 = tdt / 8.;
    tdtsdx = tdt / dx;
    tdtsdy = tdt / dy;

    c1 = wtime(); 

    for (j=1;j<=N;j++) {
      for (i=1;i<=M;i++) {
        unew[i + 1][j] = uold[i + 1][j] + tdts8 * (z[i + 1][j + 1] + z[i + 1][j]) * (cv[i + 1][j + 1] + cv[i][j + 1] + cv[i][j] + cv[i + 1][j]) - tdtsdx * (h[i + 1][j] - h[i][j]);
      }
    }
    for (j=1;j<=N;j++) {
      for (i=1;i<=M;i++) {
        vnew[i][j + 1] = vold[i][j + 1] - tdts8 * (z[i + 1][j + 1] + z[i][j + 1]) * (cu[i + 1][j + 1] + cu[i][j + 1] + cu[i][j] + cu[i + 1][j]) - tdtsdy * (h[i][j + 1] - h[i][j]);
      }
    }
    for (j=1;j<=N;j++) {
      for (i=1;i<=M;i++) {
        pnew[i][j] = pold[i][j] - tdtsdx * (cu[i + 1][j] - cu[i][j]) - tdtsdy * (cv[i][j + 1] - cv[i][j]); 
      }
    }

    c2 = wtime();  
    t200 = t200 + (c2 - c1); 

    // Periodic continuation
    for (j=1;j<=N;j++) {
      unew[1][j] = unew[M + 1][j];
      vnew[M + 1][j + 1] = vnew[1][j + 1];
      pnew[M + 1][j] = pnew[1][j];
    }
    for (i=1;i<=M;i++) {
      unew[i + 1][N + 1] = unew[i + 1][1];
      vnew[i][1] = vnew[i][N + 1];
      pnew[i][N + 1] = pnew[i][1];
    }
    unew[1][N + 1] = unew[M + 1][1];
    vnew[M + 1][1] = vnew[1][N + 1];
    pnew[M + 1][N + 1] = pnew[1][1];

    time = time + dt;

    // Time smoothing and update for next cycle
    if ( ncycle > 1 ) {

      c1 = wtime(); 

      for (j=1;j<=N_LEN;j++) {
        for (i=1;i<=M_LEN;i++) {
          uold[i][j] = u[i][j] + alpha * (unew[i][j] - 2. * u[i][j] + uold[i][j]);
        }
      }
      for (j=1;j<=N_LEN;j++) {
        for (i=1;i<=M_LEN;i++) {
          vold[i][j] = v[i][j] + alpha * (vnew[i][j] - 2. * v[i][j] + vold[i][j]);
        }
      }
      for (j=1;j<=N_LEN;j++) {
        for (i=1;i<=M_LEN;i++) {
          pold[i][j] = p[i][j] + alpha * (pnew[i][j] - 2. * p[i][j] + pold[i][j]);
        }
      }
      for (j=1;j<=N_LEN;j++) {
        for (i=1;i<=M_LEN;i++) {
          u[i][j] = unew[i][j];
        }
      }
      for (j=1;j<=N_LEN;j++) {
        for (i=1;i<=M_LEN;i++) {
          v[i][j] = vnew[i][j];
        }
      }
      for (j=1;j<=N_LEN;j++) {
        for (i=1;i<=M_LEN;i++) {
          p[i][j] = pnew[i][j];
        }
      }

      c2 = wtime(); 
      t300 = t300 + (c2 - c1);
     
    } else {
      tdt = tdt + tdt;

      for (j=1;j<=N_LEN;j++) {
        for (i=1;i<=M_LEN;i++) {
          uold[i][j] = u[i][j];
          vold[i][j] = v[i][j];
          pold[i][j] = p[i][j];
          u[i][j] = unew[i][j];
          v[i][j] = vnew[i][j];
          p[i][j] = pnew[i][j];
        }
      }

    }
  }

  // ** End of time loop ** 

  // Output p, u, v fields and run times.
  if (L_OUT) {
    ptime = time / 3600.;
    printf(" cycle number %d model time in hours %f\n", ITMAX, ptime);
    printf(" diagonal elements of p\n");
    for (i=1; i<=mnmin; i++) {
      printf("%f ",pnew[i][i]);
    }
    printf("\n diagonal elements of u\n");
    for (i=1; i<=mnmin; i++) {
      printf("%f ",unew[i][i]);
    }
    printf("\n diagonal elements of v\n");
    for (i=1; i<=mnmin; i++) {
      printf("%f ",vnew[i][i]);
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
