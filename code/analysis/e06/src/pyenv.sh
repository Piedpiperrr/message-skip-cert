# login-node CPU python for this stage: OpenBLAS thread creation fails at the login-node process
# limit, so every BLAS-using library is pinned to one thread before python starts.
source "$HOME/.config/ClusterB-storage.sh"
unset PYTHONPATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PY=$DATA_ROOT/software/envs/c2c_official/bin/python
