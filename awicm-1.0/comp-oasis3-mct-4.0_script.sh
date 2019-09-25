# Dummy script generated by esm-tools, to be removed later: 
module purge
module load gcc/4.8.2
module unload intel
module load intel
module load cdo nco
module unload netcdf
module load netcdf_c/4.3.2-gcc48
module unload cmake
module load cmake/3.5.2

export I_MPI_FABRICS=shm:dapl
export I_MPI_FALLBACK=disable
export I_MPI_SLURM_EXT=1
export I_MPI_LARGE_SCALE_THRESHOLD=8192
export I_MPI_DYNAMIC_CONNECTION=0
export DAPL_NETWORK_NODES=$SLURM_NNODES
export DAPL_NETWORK_PPN=$SLURM_NTASKS_PER_NODE
export DAPL_WR_MAX=500
export OMPI_MCA_pml=cm
export OMPI_MCA_mtl=mxm
export OMPI_MCA_coll=^ghc
export OMPI_MCA_mtl_mxm_np=0
export MXM_RDMA_PORTS=mlx5_0:1
export MXM_LOG_LEVEL=FATAL
export HDF5ROOT=/sw/rhel6-x64/hdf5/hdf5-1.8.14-threadsafe-gcc48
export HDF5_C_INCLUDE_DIRECTORIES=$HDF5ROOT/include
export ESM_HDF5_DIR=/sw/rhel6-x64/hdf5/hdf5-1.8.16-parallel-impi-intel14/
export NETCDFFROOT=/sw/rhel6-x64/netcdf/netcdf_fortran-4.4.3-intel14
export NETCDFROOT=/sw/rhel6-x64/netcdf/netcdf_c-4.4.0-gcc48
export NETCDF_Fortran_INCLUDE_DIRECTORIES=$NETCDFFROOT/include
export NETCDF_C_INCLUDE_DIRECTORIES=$NETCDFROOT/include
export NETCDF_CXX_INCLUDE_DIRECTORIES=/sw/rhel6-x64/netcdf/netcdf_cxx-4.2.1-gcc48/include
export ESM_NETCDF_C_DIR=/sw/rhel6-x64/netcdf/netcdf_c-4.4.0-parallel-impi-intel14/
export ESM_NETCDF_F_DIR=/sw/rhel6-x64/netcdf/netcdf_fortran-4.4.3-parallel-impi-intel14/
export PERL5LIB=/usr/lib64/perl5
export SZIPROOT=/sw/rhel6-x64/sys/libaec-0.3.2-gcc48
export LAPACK_LIB=-mkl=sequential
export LAPACK_LIB_DEFAULT=-L/sw/rhel6-x64/intel/intel-18.0.1/mkl/lib/intel64 -lmkl_intel_lp64 -lmkl_core -lmkl_sequential
export OASIS3MCT_FC_LIB=-L$NETCDFFROOT/lib -lnetcdff
export MPIROOT=$(${mpifc} -show | perl -lne 'm{ -I(.*?)/include } and print $1')
export MPI_LIB=$(${mpifc} -show |sed -e 's/^[^ ]*//' -e 's/-[I][^ ]*//g')
export PATH=/sw/rhel6-x64/gcc/binutils-2.24-gccsys/bin:${PATH}
export LD_LIBRARY_PATH=/sw/rhel6-x64/grib_api/grib_api-1.15.0-intel14/lib:${NETCDFF_ROOT}/lib:${HDF5ROOT}/lib:${NETCDF_ROOT}/lib:${SZIPROOT}/lib:$LD_LIBRARY_PATH

cd oasis3-mct-4.0
mkdir -p build; cd build; cmake ..;   make -j `nproc --all`
cd ..