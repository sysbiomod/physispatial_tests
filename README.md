# physispatial_tests

Pruebas unitarias de **PhysiSpatial** sobre PhysiBoSS para las tres geometrías idealizadas de la tarea 2.2 de SPIRE: **prisma**, **cilindro** y **esfera**.

Este repositorio contiene la distribución completa que preparó Alejandro Madrid (octubre de 2026): PhysiBoSS **v2.2.3** (PhysiCell 1.14.0, commit upstream `514efcfce9d0`), la librería MaBoSS 2.5.6 en código fuente (se compila sin conexión a internet) y los tres proyectos recuperados de los experimentos originales de MN5. Está pensado para que **Rafa** (TFM) y **Jorge** (doctorado) lo clonen, compilen y ejecuten sin tocar C++.

- Documentación técnica original de Alejandro (en inglés): [PHYSISPATIAL_README.md](PHYSISPATIAL_README.md)
- Qué se validó y qué no: [VALIDATION_REPORT.md](VALIDATION_REPORT.md)
- Procedencia exacta de cada fichero: [CODE_PROVENANCE.md](CODE_PROVENANCE.md)
- Problemas conocidos y tareas pendientes: [PROBLEMAS_PENDIENTES.md](PROBLEMAS_PENDIENTES.md)
- README de cada proyecto: [prisma](sample_projects_intracellular/boolean/physispatial_prism/README.md), [cilindro](sample_projects_intracellular/boolean/physispatial_cylinder/README.md), [esfera](sample_projects_intracellular/boolean/physispatial_sphere/README.md)

## Estado comprobado (29-10-2026)

Comprobado desde una copia limpia del ZIP de Alejandro en Ubuntu 24.04 (WSL2), GCC 13.3, GNU Make 4.3, flex 2.6.4, bison 3.8.2, Python 3.12, 24 CPU y 62 GB de RAM.

| Prueba | Prisma | Cilindro | Esfera |
| --- | --- | --- | --- |
| Compila (`make physispatial-<geo>` + `make`) | ✅ | ✅ | ✅ |
| Smoke run con el tejido completo (0,02 min simulados), BM0 | ✅ 1.216 células | ✅ 10.752 células | ✅ 50.232 células |
| Smoke run, otra población | ✅ BM1 | ✅ BM2 | ✅ BM1 (31.651 células) |
| Memoria máxima (RSS) | ~1 GB | ~8,3 GB | ~39 GB (BM0), ~25 GB (BM1/BM2) |
| Tiempo de pared del smoke (8 hilos) | ~8 s | ~1 min | ~5 min (BM0), ~3 min (BM1) |

Además pasan las comprobaciones de Alejandro: `validate_integration.py` (17 comprobaciones) y `test_sweeps.py` (4 comprobaciones).

Novedad respecto al informe de Alejandro: los smoke runs completos de **cilindro y esfera** no se habían podido ejecutar por falta de memoria; aquí terminan bien (estado `FINISHED`). Lo que tarda y lo que ocupa memoria es la **inicialización** (crear las células y sus redes booleanas MaBoSS), no los minutos simulados.

> **Ojo con la memoria.** El prisma corre en cualquier portátil. El cilindro necesita ~8 GB libres dentro de WSL. La esfera necesita ~40 GB y **debe ejecutarse en Garnatxa**, no en el portátil.

## 1. Requisitos

Linux x86-64 (Ubuntu en WSL2 sirve). En Ubuntu:

```bash
sudo apt update
sudo apt install -y build-essential git flex bison python3
```

**flex y bison son imprescindibles**: MaBoSS se compila desde el código fuente incluido. El protocolo técnico del TFM (sección 1.2) no los incluye; hay que añadirlos. No hacen falta paquetes de Python para compilar ni para ejecutar (sólo la biblioteca estándar). NumPy/SciPy/pcdl sólo para analizar salidas.

Clona el repositorio **en el disco de Linux** (`~/`, no `/mnt/c/...`) y en una ruta **sin espacios** (el C++ original copia ficheros con comandos de shell sin comillas):

```bash
mkdir -p ~/tfm && cd ~/tfm
git clone git@github.com:sysbiomod/physispatial_tests.git
cd physispatial_tests
bash physispatial_tools/check_environment.sh
```

El script dice qué falta y avisa si la RAM no alcanza para alguna geometría. Para darle más memoria a WSL, ver el protocolo técnico, sección 1.3 (`.wslconfig`).

## 2. Primera prueba: prisma en un minuto

Desde la raíz del repositorio, un único comando compila el prisma (la primera vez también MaBoSS, ~1 min) y ejecuta un smoke run con el tejido completo:

```bash
python3 -B physispatial_tools/run.py --geometry prism --population BM0 --seed 0 --threads 4 --smoke-minutes 0.02 --timeout 600
```

Al final imprime la carpeta de la ejecución, `physispatial_runs/prism_BM0_<fecha>/`. La ejecución es correcta si su `run_manifest.json` dice `"state": "FINISHED"`:

```bash
grep '"state"' physispatial_runs/prism_BM0_*/run_manifest.json
```

Lo mismo para las otras geometrías (cambia `--geometry` por `cylinder` o `sphere`; recuerda la memoria).

## 3. Compilar a mano (flujo estándar de PhysiCell)

Equivale al `make load PROJ=t22 && make` del protocolo técnico (sección 4.3):

```bash
make physispatial-prism POPULATION=BM0
make -j4 ARCH=x86-64
```

Deja en la raíz el ejecutable `physispatial_prism` y copia en `config/` el XML y los ficheros de entrada de la población elegida. Para cambiar de geometría o de población se vuelve a cargar y a compilar (la carga anterior se guarda en `physispatial_work/backups/`, no se pierde nada):

```bash
make physispatial-cylinder POPULATION=BM1
make -j4 ARCH=x86-64
```

Poblaciones disponibles: `BM0`, `BM1`, `BM2` (por defecto `BM0`). `ARCH=x86-64` da un binario portable; sin él se optimiza para la CPU de la máquina.

**No lances `./physispatial_prism config/PhysiCell_settings.xml` sin editar antes el XML**: la configuración original simula 300.000 min con 112 hilos (`<omp_num_threads>`) y escribe en `output_0/`, que debe existir. Para todo lo que no sea reproducir la ejecución original, usa `run.py` (sección 4), que ajusta tiempo, hilos, semilla y carpeta de salida en una copia del XML.

## 4. Ejecuciones aisladas con `run.py`

`physispatial_tools/run.py` compila (con caché) y prepara cada ejecución en su propia carpeta `physispatial_runs/<nombre>/` con `config/run.xml`, las entradas originales, `run_manifest.json` (parámetros, hashes de entradas y del ejecutable, tiempo de pared, estado), `simulation.log` y `output/`. Nunca sobrescribe una ejecución existente.

```bash
python3 -B physispatial_tools/run.py \
  --geometry prism --population BM0 \
  --diffusion 500 --concentration 1e-7 \
  --seed 42 --threads 8 \
  --name prueba_prisma_D500 \
  --prepare-only
```

| Opción | Qué cambia en el XML |
| --- | --- |
| `--diffusion` | D del fármaco `drug_A`, en µm²/min (`microenvironment_setup/variable[@name='drug_A']/.../diffusion_coefficient`) |
| `--concentration` | C en la fuente (`user_parameters/drug_conc`), en las unidades numéricas originales |
| `--seed` | `user_parameters/random_seed` (en este proyecto la semilla está en `user_parameters`, no en `<options>`) |
| `--threads` | `parallel/omp_num_threads` |
| `--smoke-minutes` | `overall/max_time`, sólo de 0 a 1 min (sin esta opción ni `--max-time` se usa el horizonte original de 300.000 min) |
| `--max-time` | `overall/max_time`, cualquier horizonte en min. Incompatible con `--smoke-minutes` |
| `--drug-time` | `user_parameters/time_remove_o2`: minuto en que se encienden las fuentes del fármaco (0 = desde el principio). Pese al nombre, no quita oxígeno |
| `--initial-tissue` | sólo prisma. `original` (1.216 células, x de -470 a -110, sección 8 × 8 en y,z de -70 a 70) o `full-section` (sección completa del tubo, 10 × 10 en y,z de -70 a 110, empezando junto a la tapa en x = -490). Genera el CSV dentro de la ejecución y apunta `initial_conditions/cell_positions/filename` a él |
| `--fill-fraction` | con `full-section`: fracción del interior del tubo que se llena, redondeada a rodajas enteras de 20 µm. Por defecto 0,75: 38 rodajas, 3.800 células, frente en x = 250. Con 0,5: 25 rodajas, 2.500 células, frente en x = -10 |
| `--source-footprint` | sólo prisma. `original` (placa en x = 510 con y,z de -90 a 90, desplazada 20 µm respecto al tubo; el lector se salta la primera línea y usa 99 vóxeles) o `tube` (placa con y,z de -70 a 110, igual que la sección del tubo y de `full-section`; el fichero lleva cabecera para que se usen los 100 vóxeles). Cambia `user_parameters/blood_source_file` |
| `--cells-file` | prisma o cilindro: un CSV propio (`x,y,z,tipo` en µm, sin cabecera). Se valida, se copia a la ejecución como `custom_<nombre>.csv` y se usa en lugar del original |
| `--memory-gb`, `--timeout` | límites del proceso; no cambian la biología |

`--prepare-only` sólo crea la carpeta; quítalo para ejecutar. D, C, el tiempo del fármaco y las células iniciales se leen al arrancar: **cambiarlos no requiere recompilar**. Cambiar de población sí. Los ficheros originales de `config/BM*` no se modifican nunca; el `run_manifest.json` guarda `drug_activation_time`, `initial_tissue`, `initial_cells` y el hash del CSV usado.

Sin `--drug-time`, el fármaco se activa en el minuto 35.000 (prisma) o 30.000 (cilindro y esfera). En un smoke run corto es normal que el campo de fármaco sea cero.

Ejemplo (prisma lleno al 75 % con la sección completa, fuentes alineadas con el tubo, fármaco desde el minuto 0, 100.000 min simulados):

```bash
python3 -B physispatial_tools/run.py --geometry prism --population BM0 \
  --diffusion 1000 --concentration 1e-6 --seed 1 --threads 8 \
  --initial-tissue full-section --fill-fraction 0.75 --source-footprint tube \
  --drug-time 0 --max-time 100000 \
  --name prisma_BM0_D1000_C1e-6_full75_tube
```

Barridos de D × C × población × semilla (prepara, no ejecuta): `physispatial_tools/sweep.py`; ver [PHYSISPATIAL_README.md](PHYSISPATIAL_README.md#dc-parameter-sweeps).

## 5. Salidas

En `physispatial_runs/<nombre>/output/`: `initial.xml`, `outputNNNNNNNN.xml` con sus `_cells.mat` y `_microenvironment0.mat`, `final.xml`, el CSV de estados booleanos y SVG. Se leen con pcdl. Una ejecución es válida sólo si existe `final.xml` al tiempo pedido y el manifiesto dice `FINISHED`: el `main` original puede devolver 0 aunque haya capturado una excepción.

Al analizar, **excluye la fila `total_attack_time`** de las matrices de células: es un campo heredado que el código original no inicializa.

## 6. Garnatxa (SLURM)

Misma receta que en el portátil, cargando antes el módulo de GCC (≥ 11) y comprobando flex y bison (`bash physispatial_tools/check_environment.sh`); como MaBoSS va incluido, no hace falta salida a internet desde el clúster. Hay una plantilla de array de SLURM para barridos preparados con `sweep.py`: [physispatial_tools/slurm_array.sbatch](physispatial_tools/slurm_array.sbatch). Se escribió para MN5: ajusta `--mem` según la tabla de arriba (la esfera necesita ≥ 48 GB) y pasa partición y cuenta de Garnatxa en la línea de `sbatch`. Los nombres de módulos y colas los confirma Jorge (protocolo técnico, sección 6).

## 7. Comprobaciones automáticas

```bash
python3 -B physispatial_tools/validate_integration.py   # 17 comprobaciones estáticas y de interfaz
python3 -B physispatial_tools/test_sweeps.py            # 4 comprobaciones de barridos
python3 -B physispatial_tools/test_tfm_options.py       # 13 comprobaciones de las opciones del TFM
```

GitHub Actions ([.github/workflows/physispatial.yml](.github/workflows/physispatial.yml)) compila las tres geometrías, pasa estas comprobaciones y hace el smoke run del prisma en cada push a `main` y en cada pull request. Cilindro y esfera no caben en la memoria de un runner estándar.

## 8. Cosas a saber

- **Rafa compila, no modifica C++.** Si hace falta un observable nuevo que no salga de las salidas, lo escribe Jorge.
- No borres ni renombres ficheros de `config/BM*`: los `norm_0.cfg` tienen contenidos distintos en cada población aunque se llamen igual. La población se elige con `POPULATION=` o `--population`.
- `make reset` vuelve al Makefile por defecto de PhysiBoSS y mantiene los tres objetivos `physispatial-*`. `make clean` borra objetos y el ejecutable.
- `physispatial_runs/`, `physispatial_work/`, `output_*/`, los ejecutables y los ficheros que copia la carga de un proyecto (`main.cpp`, `custom_modules/`, `config/BM*`) están en `.gitignore`: no se suben al repositorio.
- Cargar un proyecto modifica dos ficheros versionados, `Makefile` y `config/PhysiCell_settings.xml`. Es lo normal en PhysiCell; antes de hacer commit, devuélvelos a su estado con `git restore Makefile config/PhysiCell_settings.xml`. Para trabajo propio (envoltorio, resúmenes, cuadernos), usa tu propio repositorio (p. ej. `physiboss-abc`) y deja este como el simulador de referencia.
- Los ficheros biológicos de entrada (modelos booleanos, posiciones, fuentes) proceden de experimentos no publicados. Antes de hacer público el repositorio hay que confirmarlo con los autores (ver [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

## Licencia

Código de PhysiCell/PhysiBoSS/BioFVM/MaBoSS bajo sus licencias originales (carpeta [licenses/](licenses/)). El resto, [BSD 3-Clause](LICENSE).
