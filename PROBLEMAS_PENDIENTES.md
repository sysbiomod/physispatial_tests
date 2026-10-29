# Problemas pendientes

Problemas encontrados el 29-10-2026 al verificar la distribución de Alejandro Madrid (ZIP `PhysiBoSS_PhysiSpatial_UnitTests.zip`) e importarla en este repositorio. Cada punto se puede abordar por separado. El estado verificado está en [README.md](README.md#estado-comprobado-29-10-2026).

**Regla general:** no cambiar la física ni las entradas biológicas de los proyectos. Los ficheros de `core/`, `modules/`, `BioFVM/` y `addons/PhysiBoSS/src/` están comprobados por hash (`physispatial_tools/validate_integration.py`), y los `config/BM*` y `profiles/BM*` de cada proyecto son los originales. Después de cualquier cambio deben seguir pasando:

```bash
bash physispatial_tools/check_environment.sh
python3 -B physispatial_tools/validate_integration.py
python3 -B physispatial_tools/test_sweeps.py
python3 -B physispatial_tools/run.py --geometry prism --population BM0 --seed 0 --threads 2 --smoke-minutes 0.02 --timeout 600
```

---

## A. Protocolo técnico del TFM (fuera del repositorio)

Fichero: `/home/amontagud2/repos/info TFM Rafa/TFM-Rafa-Casajus-protocolo-tecnico-instalacion-y-uso.docx` (el plan semanal lo cita como `.md`). Hay que corregirlo para que encaje con este repositorio.

1. **Faltan `flex` y `bison` en la instalación (sección 1.2).** MaBoSS se compila desde el código fuente incluido y sin ellos `make` falla. Añadirlos a la línea de `sudo apt install`. En Garnatxa hay que comprobar que existen o cargarlos como módulo (sección 6.2).
2. **Dice que el Makefile descarga MaBoSS precompilado (secciones 4.2 y 6.2, y la sección 10 de errores).** En este repositorio MaBoSS 2.5.6 va incluido y se compila sin internet. Se puede quitar el aviso de que el nodo de entrada no tiene salida a internet.
3. **Sección 4.3: los comandos de carga no son los de este proyecto.** Allí pone `make load PROJ=t22`, `./project` y `config/PhysiCell_settings_prisma.xml`. Aquí se usa `make physispatial-<prism|cylinder|sphere> POPULATION=BM0|BM1|BM2`, `make`, y el ejecutable `physispatial_<geometría>` lee `config/PhysiCell_settings.xml`. Mejor aún: recomendar `physispatial_tools/run.py` (README, secciones 2 y 4) y usar `git rev-parse` de este repositorio para el hash.
4. **Sección 4.4: la semilla no está en `<options><random_seed>`.** En estos proyectos está en `user_parameters/random_seed`, y `run.py --seed` la cambia ahí. Revisar también las rutas de D (`drug_A`), C (`user_parameters/drug_conc`, que no es una condición de Dirichlet del XML) y θ_d en el XML real.
5. **Falta un aviso de memoria.** Cilindro, ~8,3 GB; esfera, ~39 GB (BM0) o ~25 GB (BM1/BM2). La esfera no corre en el portátil; ajustar `.wslconfig` (sección 1.3) y los `--mem` de SLURM (secciones 6 y 7).

## B. Configuración por defecto peligrosa para ejecutar a mano

6. Los tres `sample_projects_intracellular/boolean/physispatial_*/config/PhysiCell_settings.xml` (y los de `config/BM*/`) tienen `max_time` 300000, `omp_num_threads` 112 y `save/folder` `output_0`, que debe existir. Ejecutar `./physispatial_prism config/PhysiCell_settings.xml` en un portátil lanza 112 hilos durante días. Opciones, sin tocar los XML originales:
   - (a) añadir un objetivo `make physispatial-smoke GEOMETRY=... POPULATION=...` en `physispatial_tools/projects.mk` que llame a `run.py --smoke-minutes`; o
   - (b) generar al cargar un `config/PhysiCell_settings_laptop.xml` con pocos hilos y `output/` (en `physispatial_tools/select_project.py`).
   Comprobar que `validate_integration.py` sigue pasando (verifica que el Makefile por defecto empiece por el original de upstream).

## C. SLURM

7. `physispatial_tools/slurm_array.sbatch` se escribió para MN5 con `--mem=32G`, 8 CPU y 2 h. Con 32 GB no cabe la esfera BM0 (~39 GB de RSS) y los horizontes originales no caben en 2 h. Crear una variante para Garnatxa (`slurm_array_garnatxa.sbatch`), con memoria por geometría y huecos `[confirmar con Jorge]` para la partición y el módulo de GCC. No inventar nombres de colas.

## D. Git y flujo de trabajo

8. **`make reset` no deja limpio el árbol.** El `reset` de upstream copia `config/PhysiCell_settings-backup.xml` sobre `config/PhysiCell_settings.xml`, pero esa copia es la del proyecto cargado antes, no la versionada. Tras `make physispatial-*` + `make reset`, `git status` muestra `config/PhysiCell_settings.xml` modificado (el README lo documenta con `git restore`). Posible arreglo: que `select_project.py` guarde la copia de seguridad solo si el fichero coincide con `HEAD`, o un objetivo `physispatial-reset` que haga `make reset` y después `git restore Makefile config/PhysiCell_settings.xml`. No modificar la receta `reset` de upstream.
9. **La CI no se ha ejecutado nunca en GitHub.** `.github/workflows/physispatial.yml` solo se ha simulado en local. Revisar la primera ejecución en el PR y el consumo de minutos de Actions en un repositorio privado de la organización.
10. `.github/ISSUE_TEMPLATE/*` son plantillas de PhysiCell. Adaptarlas a este repositorio o borrarlas.

## E. Preguntas para Alejandro o Jorge (no cambiar código sin respuesta)

11. **Entradas de la esfera.** En el `run_manifest.json` del smoke de la esfera BM0, `input_sha256` incluye `config/BM0/cells_prisma.csv` y `config/BM0/cilindro_enndo.tsv`, que son nombres de prisma y cilindro. Las posiciones de la esfera se generan por código (`tumor_radius`), así que puede que el CSV no se use. Confirmar que estos ficheros son los originales de la esfera y documentarlo en `sample_projects_intracellular/boolean/physispatial_sphere/README.md`.
12. **Semilla de MaBoSS.** ¿Deriva de `user_parameters/random_seed` o es independiente? Rafa lo necesita en la semana 1 del TFM. Comprobarlo con dos smoke runs del prisma con la misma semilla, comparando `final_boolean_intracellular.csv`.
13. **Sin validar a horizonte largo.** Solo hay smoke runs de 0,02 min. Falta una ejecución larga de cada geometría que pase la activación del fármaco (35.000 min en el prisma, 30.000 en cilindro y esfera) en Garnatxa, con su tiempo y memoria (`sacct`) para la tabla de coste de la semana 3.

## F. Riesgos conocidos que se mantienen a propósito

No arreglar sin decisión de los autores, porque cambiaría el comportamiento original. Solo documentarlos donde haga falta.

- El lector TSV de fuentes se salta la primera línea y usa `while(!eof())`: el prisma tiene 99 fuentes efectivas de 100 nominales.
- `total_attack_time` no está inicializado: excluirlo de cualquier análisis.
- El `main` original puede devolver 0 tras capturar una excepción: la validez la da `final.xml` y `"state": "FINISHED"` en el manifiesto.
- Las unidades de concentración del modelo son inconsistentes y no se convierten.

## G. Licencias y visibilidad

14. El repositorio es privado. Los modelos booleanos y las entradas biológicas proceden de experimentos no publicados (ver `THIRD_PARTY_NOTICES.md`). Antes de hacerlo público, o antes de que el repositorio del TFM de Rafa (que el plan quiere público) copie estas entradas, hay que tener la confirmación por escrito de los autores.
