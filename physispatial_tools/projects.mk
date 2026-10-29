# Included last, so the upstream default target and recipes remain unchanged.
POPULATION ?= BM0
PYTHON ?= python3
.PHONY: physispatial-prism physispatial-cylinder physispatial-sphere physispatial-list
physispatial-prism:
	$(PYTHON) -B physispatial_tools/select_project.py --geometry prism --population $(POPULATION)
physispatial-cylinder:
	$(PYTHON) -B physispatial_tools/select_project.py --geometry cylinder --population $(POPULATION)
physispatial-sphere:
	$(PYTHON) -B physispatial_tools/select_project.py --geometry sphere --population $(POPULATION)
physispatial-list:
	@echo "physispatial-prism physispatial-cylinder physispatial-sphere (POPULATION=BM0|BM1|BM2)"
