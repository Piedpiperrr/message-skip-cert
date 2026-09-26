# Common per-stage environment for the E7 / E6 replay processes (one model residency per process).
W=$DATA_DIR/P2_R2_E7_20260919T231531Z
GPUW=$DATA_DIR/P2_R2_GPU_20260919T220941Z
source "$HOME/.config/ClusterB-storage.sh"
export PATH="$PATH:/opt/pbs/bin"
unset PYTHONPATH
export http_proxy=http://proxy.cluster.invalid:3128 https_proxy=http://proxy.cluster.invalid:3128
export HTTP_PROXY=http://proxy.cluster.invalid:3128 HTTPS_PROXY=http://proxy.cluster.invalid:3128
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1
export E7_RECERT=$GPUW/e7/E7_ARGMAX_RECERT.json
PY=$DATA_ROOT/software/envs/c2c_official/bin/python
ulimit -c 0
