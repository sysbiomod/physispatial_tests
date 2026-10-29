#!/usr/bin/env bash
# Checks that this machine can build and run the PhysiSpatial projects.
# Usage (from the repository root):  bash physispatial_tools/check_environment.sh
# Exit code 0 = everything required is present. Warnings do not fail.

fail=0
ok()   { printf '  [OK]    %s\n' "$1"; }
bad()  { printf '  [FALTA] %s\n' "$1"; fail=1; }
warn() { printf '  [AVISO] %s\n' "$1"; }

echo "Comprobando requisitos de PhysiSpatial..."

# Must be run from the root, and the path must not contain spaces
# (original C++ uses unquoted shell copy commands).
if [ ! -f physispatial_tools/projects.mk ]; then
  bad "Ejecuta este script desde la raíz del repositorio"
fi
case "$PWD" in
  *[[:space:]]*) bad "La ruta '$PWD' contiene espacios: clona el repositorio en una ruta sin espacios" ;;
  /mnt/[a-z]/*)  warn "Estás en el disco de Windows ($PWD): compila y ejecuta en ~/ (disco de Linux), es mucho más rápido" ;;
esac

CXX="${PHYSICELL_CPP:-g++}"
for tool in "$CXX" make flex bison python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool ($("$tool" --version 2>&1 | head -n1))"
  else
    bad "$tool  ->  sudo apt install build-essential flex bison python3"
  fi
done

if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    ok "Python >= 3.9"
  else
    bad "Python >= 3.9 requerido"
  fi
fi

if command -v "$CXX" >/dev/null 2>&1; then
  tmp=$(mktemp -d)
  printf '#include <omp.h>\nint main(){return omp_get_max_threads()>0?0:1;}\n' > "$tmp/omp.cpp"
  if "$CXX" -fopenmp "$tmp/omp.cpp" -o "$tmp/omp" >/dev/null 2>&1 && "$tmp/omp"; then
    ok "OpenMP"
  else
    bad "OpenMP no funciona con $CXX"
  fi
  rm -rf "$tmp"
fi

cpus=$(nproc 2>/dev/null || echo "?")
mem_gb=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo 2>/dev/null)
echo "  [INFO]  CPUs: $cpus   RAM: ${mem_gb:-?} GB"
if [ -n "$mem_gb" ]; then
  # Measured peak RSS of the full-tissue smoke runs (see README.md).
  [ "$mem_gb" -lt 4 ]  && warn "Menos de 4 GB de RAM: ni siquiera el prisma tiene margen"
  [ "$mem_gb" -lt 10 ] && warn "Menos de 10 GB de RAM: el cilindro (~8 GB) probablemente no arranque"
  [ "$mem_gb" -lt 42 ] && warn "Menos de 42 GB de RAM: la esfera (~25-40 GB) debe ejecutarse en Garnatxa"
fi

if [ "$fail" -eq 0 ]; then
  echo "Todo listo."
else
  echo "Faltan requisitos (ver [FALTA] arriba)."
fi
exit "$fail"
